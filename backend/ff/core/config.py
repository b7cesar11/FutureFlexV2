import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 12
REFRESH_TOKEN_DAYS = 7
GOOGLE_SESSION_DAYS = 7

# Production-safe defaults. Demo data must always be explicitly enabled.
ENABLE_DEMO_USER = env_bool("ENABLE_DEMO_USER", False)
REQUIRE_REPLICA_SET = env_bool("REQUIRE_REPLICA_SET", True)

# Cookies default to Secure only in production so local HTTP development remains usable.
COOKIE_SECURE = env_bool("COOKIE_SECURE", APP_ENV == "production")
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax").strip().lower()
if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    raise RuntimeError("COOKIE_SAMESITE deve ser lax, strict ou none")

# Comma-separated explicit origins are recommended when frontend/backend use different origins.
CORS_ORIGINS = tuple(
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "").split(",")
    if origin.strip()
)

# Native Google OAuth (preferred). FRONTEND_URL is the post-login destination.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI", "http://localhost:8001/api/auth/google/callback"
).strip()

# Legacy Emergent Google gateway kept temporarily for backward compatibility only.
EMERGENT_SESSION_DATA_URL = os.environ.get(
    "EMERGENT_SESSION_DATA_URL",
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
)

# Janela de materializacao de ocorrencias futuras (decisao do produto: 24 meses).
PROJECTION_WINDOW_MONTHS = int(os.environ.get("PROJECTION_WINDOW_MONTHS", "24"))

# AI can use a direct OpenAI key outside Emergent. The old key remains a fallback.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "gpt-5.5").strip()
AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai").strip().lower()
AI_DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT", "60"))

APP_TZ = "America/Sao_Paulo"


def validate_runtime_config() -> None:
    if APP_ENV == "production" and len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET deve ter pelo menos 32 caracteres em produção")
    if APP_ENV == "production" and ENABLE_DEMO_USER:
        raise RuntimeError("ENABLE_DEMO_USER não pode estar habilitado em produção")
    if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
        raise RuntimeError("COOKIE_SAMESITE=none exige COOKIE_SECURE=true")
    google_values = (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI)
    if any(google_values[:2]) and not all(google_values):
        raise RuntimeError("Google OAuth exige GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e GOOGLE_REDIRECT_URI")
