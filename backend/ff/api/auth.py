import secrets
from datetime import datetime, timedelta, timezone

import httpx
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr

from ..core.config import EMERGENT_SESSION_DATA_URL, GOOGLE_SESSION_DAYS
from ..core.db import db
from ..core.deps import get_current_user
from ..core.security import (clear_auth_cookies, create_access_token, create_refresh_token,
                             decode_token, hash_password, set_auth_cookies, verify_password)
from ..models.base import now_utc
from ..models.entities import User, UserProfile
from ..services.seed_service import seed_user_defaults

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def public_user(user: dict) -> dict:
    return {
        "id": str(user.get("_id")),
        "email": user["email"],
        "role": user.get("role", "user"),
        "profile": user.get("profile", {"name": "", "picture": None}),
        "preferences": user.get("preferences", {}),
        "auth_providers": user.get("auth_providers", []),
    }


async def _check_lockout(identifier: str):
    doc = await db.login_attempts.find_one({"identifier": identifier})
    if not doc:
        return
    if doc.get("count", 0) >= MAX_ATTEMPTS:
        last = doc.get("last_attempt")
        if last and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last and last > now_utc() - timedelta(minutes=LOCK_MINUTES):
            raise HTTPException(status_code=429,
                                detail="Muitas tentativas. Tente novamente em 15 minutos.")
        await db.login_attempts.delete_one({"identifier": identifier})


@router.post("/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter ao menos 6 caracteres")
    user = User(email=email, password_hash=hash_password(payload.password),
                auth_providers=["password"],
                profile=UserProfile(name=payload.name or email.split("@")[0]))
    doc = user.to_mongo()
    result = await db.users.insert_one(doc)
    user_id = str(result.inserted_id)
    await seed_user_defaults(user_id)
    access = create_access_token(user_id, email)
    set_auth_cookies(response, access, create_refresh_token(user_id))
    doc["_id"] = user_id
    return {**public_user(doc), "access_token": access}


@router.post("/login")
async def login(payload: LoginIn, request: Request, response: Response):
    email = payload.email.lower()
    identifier = f"{request.client.host if request.client else 'unknown'}:{email}"
    await _check_lockout(identifier)
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("password_hash") or ""):
        await db.login_attempts.update_one({"identifier": identifier},
                                          {"$inc": {"count": 1},
                                           "$set": {"last_attempt": now_utc()}}, upsert=True)
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    await db.login_attempts.delete_one({"identifier": identifier})
    user_id = str(user["_id"])
    access = create_access_token(user_id, email)
    set_auth_cookies(response, access, create_refresh_token(user_id))
    return {**public_user(user), "access_token": access}


@router.post("/google/session")
async def google_session(request: Request, response: Response):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID ausente")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(EMERGENT_SESSION_DATA_URL,
                                headers={"X-Session-ID": session_id})
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Sessão do Google inválida")
    data = resp.json()
    email = data["email"].lower()

    user = await db.users.find_one({"email": email})
    if user:
        user_id = str(user["_id"])
        providers = set(user.get("auth_providers", [])) | {"google"}
        await db.users.update_one({"_id": user["_id"]}, {"$set": {
            "google_sub": data.get("id"), "auth_providers": list(providers),
            "profile.name": user.get("profile", {}).get("name") or data.get("name", ""),
            "profile.picture": data.get("picture"), "updated_at": now_utc()}})
        user = await db.users.find_one({"_id": user["_id"]})
    else:
        new_user = User(email=email, google_sub=data.get("id"), auth_providers=["google"],
                        profile=UserProfile(name=data.get("name", ""),
                                            picture=data.get("picture")))
        result = await db.users.insert_one(new_user.to_mongo())
        user_id = str(result.inserted_id)
        await seed_user_defaults(user_id)
        user = await db.users.find_one({"_id": result.inserted_id})

    session_token = data.get("session_token") or f"ffs_{secrets.token_urlsafe(32)}"
    await db.user_sessions.update_one({"session_token": session_token}, {"$set": {
        "user_id": str(user["_id"]), "session_token": session_token,
        "expires_at": now_utc() + timedelta(days=GOOGLE_SESSION_DAYS),
        "created_at": now_utc()}}, upsert=True)
    response.set_cookie("session_token", session_token, httponly=True, secure=True,
                        samesite="none", max_age=GOOGLE_SESSION_DAYS * 86400, path="/")
    return public_user(user)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token ausente")
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token inválido")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Tipo de token inválido")
    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    set_auth_cookies(response, create_access_token(str(user["_id"]), user["email"]),
                     create_refresh_token(str(user["_id"])))
    return public_user(user)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return public_user({**user, "_id": user["_id"]})


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    clear_auth_cookies(response)
    return {"ok": True}
