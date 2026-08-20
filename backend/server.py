import logging
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
REPO_ROOT = ROOT_DIR.parent
FRONTEND_BUILD_DIR = REPO_ROOT / "frontend" / "build"
load_dotenv(ROOT_DIR / ".env")

from fastapi import APIRouter, FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from ff.api import auth as auth_api  # noqa: E402
from ff.api import catalog as catalog_api  # noqa: E402
from ff.api import engine as engine_api  # noqa: E402
from ff.api import insights as insights_api  # noqa: E402
from ff.api import third_parties as third_parties_api  # noqa: E402
from ff.core.config import (CORS_ORIGINS, ENABLE_DEMO_USER, REQUIRE_REPLICA_SET,
                            validate_runtime_config)  # noqa: E402
from ff.core.csrf import CSRF_HEADER_NAME, CSRFMiddleware  # noqa: E402
from ff.core.db import client, ensure_indexes  # noqa: E402
from ff.services.demo_service import ensure_demo_user  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("future_flex")

app = FastAPI(title="Future Flex V2")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"app": "Future Flex V2", "status": "ok"}


@api_router.get("/health")
async def health():
    hello = await client.admin.command("hello")
    return {
        "status": "ok",
        "mongo": "ok",
        "replica_set": hello.get("setName"),
        "transactions_available": bool(hello.get("setName")),
    }


api_router.include_router(auth_api.router)
api_router.include_router(engine_api.router)
api_router.include_router(third_parties_api.router)
api_router.include_router(insights_api.router)
api_router.include_router(catalog_api.router)
app.include_router(api_router)

app.add_middleware(CSRFMiddleware)

if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=list(CORS_ORIGINS),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[CSRF_HEADER_NAME],
    )


@app.on_event("startup")
async def on_startup():
    validate_runtime_config()
    await ensure_indexes()
    hello = await client.admin.command("hello")
    replica_set = hello.get("setName")
    transactions_available = bool(replica_set)
    logger.info("MongoDB replicaSet=%s transacoes_acid=%s", replica_set,
                transactions_available)
    if REQUIRE_REPLICA_SET and not transactions_available:
        raise RuntimeError(
            "MongoDB precisa rodar como replica set para garantir transações ACID. "
            "Configure rs0 ou defina REQUIRE_REPLICA_SET=false apenas para diagnóstico."
        )
    if ENABLE_DEMO_USER:
        try:
            await ensure_demo_user()
        except Exception as exc:
            logger.error("Falha ao preparar conta demo: %s", exc)
            raise


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    """Serve the production React build from the API host."""
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    build_root = FRONTEND_BUILD_DIR.resolve()
    requested = (build_root / full_path).resolve() if full_path else build_root
    if requested != build_root and build_root not in requested.parents:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if requested.is_file():
        return FileResponse(requested)

    index = build_root / "index.html"
    if index.is_file():
        return FileResponse(index)

    raise HTTPException(
        status_code=404,
        detail="Frontend não está compilado neste ambiente",
    )
