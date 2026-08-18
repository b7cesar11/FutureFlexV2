import logging
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import APIRouter, FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from ff.api import auth as auth_api  # noqa: E402
from ff.api import catalog as catalog_api  # noqa: E402
from ff.api import engine as engine_api  # noqa: E402
from ff.api import insights as insights_api  # noqa: E402
from ff.core.config import (CORS_ORIGINS, ENABLE_DEMO_USER, REQUIRE_REPLICA_SET,
                            validate_runtime_config)  # noqa: E402
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
api_router.include_router(insights_api.router)
api_router.include_router(catalog_api.router)
app.include_router(api_router)

if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=list(CORS_ORIGINS),
        allow_methods=["*"],
        allow_headers=["*"],
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
