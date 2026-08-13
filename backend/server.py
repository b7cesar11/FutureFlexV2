import logging
import os
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


api_router.include_router(auth_api.router)
api_router.include_router(engine_api.router)
api_router.include_router(insights_api.router)
api_router.include_router(catalog_api.router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await ensure_indexes()
    hello = await client.admin.command("hello")
    logger.info("MongoDB replicaSet=%s transacoes_acid=%s", hello.get("setName"),
                bool(hello.get("setName")))
    try:
        await ensure_demo_user()
    except Exception as exc:  # observabilidade: nunca falhar silenciosamente
        logger.error("Falha ao preparar conta demo: %s", exc)


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
