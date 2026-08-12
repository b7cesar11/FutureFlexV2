from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, Request

from .db import db
from .security import decode_token
import jwt


class DomainError(HTTPException):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


async def _user_from_session_token(token: str):
    session = await db.user_sessions.find_one({"session_token": token})
    if not session:
        return None
    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return await db.users.find_one({"_id": ObjectId(session["user_id"])})


async def get_current_user(request: Request) -> dict:
    session_token = request.cookies.get("session_token")
    if not session_token:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer ") and header[7:].startswith("ffs_"):
            session_token = header[7:]
    if session_token:
        user = await _user_from_session_token(session_token)
        if user:
            user["_id"] = str(user["_id"])
            user.pop("password_hash", None)
            return user

    token = request.cookies.get("access_token")
    if not token:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Tipo de token inválido")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


async def current_user_id(request: Request) -> str:
    user = await get_current_user(request)
    return user["_id"]
