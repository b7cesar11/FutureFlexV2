import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 12
REFRESH_TOKEN_DAYS = 7
GOOGLE_SESSION_DAYS = 7

EMERGENT_SESSION_DATA_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

# Janela de materializacao de ocorrencias futuras (decisao do produto: 24 meses).
PROJECTION_WINDOW_MONTHS = int(os.environ.get("PROJECTION_WINDOW_MONTHS", "24"))

APP_TZ = "America/Sao_Paulo"
