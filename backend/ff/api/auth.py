import secrets
from datetime import timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, EmailStr

from ..core.config import (COOKIE_SAMESITE, COOKIE_SECURE, FRONTEND_URL, GOOGLE_CLIENT_ID,
                           GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, JWT_ALGORITHM,
                           JWT_SECRET)
from ..core.db import db
from ..core.deps import get_current_user
from ..core.security import (clear_auth_cookies, create_access_token, create_refresh_token,
                             decode_token, hash_password, password_hash_needs_upgrade,
                             set_auth_cookies, validate_new_password, verify_password)
from ..models.base import now_utc
from ..models.entities import User, UserProfile
from ..services.seed_service import seed_user_defaults

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15
GOOGLE_OAUTH_STATE_COOKIE = "ff_google_oauth_state"
GOOGLE_OAUTH_STATE_TTL_SECONDS = 10 * 60


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


def _build_google_state() -> str:
    return jwt.encode(
        {
            "type": "google_oauth_state",
            "nonce": secrets.token_urlsafe(16),
            "exp": now_utc() + timedelta(seconds=GOOGLE_OAUTH_STATE_TTL_SECONDS),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def _validate_google_state(state: str, cookie_state: str | None) -> dict:
    # A signed state by itself is not enough: it must also be the exact state placed
    # in the browser that initiated the OAuth flow (double-submit cookie binding).
    if not cookie_state or not secrets.compare_digest(state, cookie_state):
        raise HTTPException(status_code=400, detail="Estado OAuth não corresponde à sessão iniciada")
    try:
        payload = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "google_oauth_state" or not payload.get("nonce"):
            raise ValueError("state type/nonce")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Estado OAuth inválido ou expirado") from exc


def _set_google_state_cookie(response: Response, state: str) -> None:
    response.set_cookie(
        GOOGLE_OAUTH_STATE_COOKIE,
        state,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=GOOGLE_OAUTH_STATE_TTL_SECONDS,
        path="/api/auth/google",
    )


def _clear_google_state_cookie(response: Response) -> None:
    response.delete_cookie(
        GOOGLE_OAUTH_STATE_COOKIE,
        path="/api/auth/google",
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )


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


async def _upsert_google_user(data: dict) -> dict:
    email = str(data.get("email") or "").lower().strip()
    google_sub = str(data.get("sub") or "").strip()
    if not email or not google_sub:
        raise HTTPException(status_code=401, detail="Identidade do Google incompleta")

    user = await db.users.find_one({"email": email})
    if user:
        existing_google_sub = str(user.get("google_sub") or "").strip()
        if existing_google_sub and existing_google_sub != google_sub:
            raise HTTPException(status_code=409, detail="E-mail já vinculado a outra identidade Google")
        providers = set(user.get("auth_providers", [])) | {"google"}
        await db.users.update_one({"_id": user["_id"]}, {"$set": {
            "google_sub": google_sub,
            "auth_providers": list(providers),
            "profile.name": user.get("profile", {}).get("name") or data.get("name", ""),
            "profile.picture": data.get("picture"),
            "updated_at": now_utc(),
        }})
        return await db.users.find_one({"_id": user["_id"]})

    new_user = User(
        email=email,
        google_sub=google_sub,
        auth_providers=["google"],
        profile=UserProfile(name=data.get("name", ""), picture=data.get("picture")),
    )
    result = await db.users.insert_one(new_user.to_mongo())
    await seed_user_defaults(str(result.inserted_id))
    return await db.users.find_one({"_id": result.inserted_id})


@router.post("/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    try:
        validate_new_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
    # Auth tokens intentionally remain only in HttpOnly cookies for browser clients.
    return public_user(doc)


@router.post("/login")
async def login(payload: LoginIn, request: Request, response: Response):
    email = payload.email.lower()
    identifier = f"{request.client.host if request.client else 'unknown'}:{email}"
    await _check_lockout(identifier)
    user = await db.users.find_one({"email": email})
    stored_hash = user.get("password_hash") if user else ""
    if not user or not verify_password(payload.password, stored_hash or ""):
        await db.login_attempts.update_one({"identifier": identifier},
                                          {"$inc": {"count": 1},
                                           "$set": {"last_attempt": now_utc()}}, upsert=True)
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    await db.login_attempts.delete_one({"identifier": identifier})
    if password_hash_needs_upgrade(stored_hash or ""):
        upgraded = hash_password(payload.password)
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"password_hash": upgraded, "updated_at": now_utc()}},
        )
        user["password_hash"] = upgraded

    user_id = str(user["_id"])
    access = create_access_token(user_id, email)
    set_auth_cookies(response, access, create_refresh_token(user_id))
    return public_user(user)


@router.get("/google/start")
async def google_start():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Login com Google ainda não configurado")
    state = _build_google_state()
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "include_granted_scopes": "true",
        "prompt": "select_account",
    }
    response = RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}",
        status_code=302,
    )
    _set_google_state_cookie(response, state)
    return response


@router.get("/google/callback")
async def google_callback(request: Request, code: str | None = None, state: str | None = None,
                          error: str | None = None):
    if error:
        response = RedirectResponse(f"{FRONTEND_URL}/login?oauth_error=1", status_code=302)
        _clear_google_state_cookie(response)
        return response
    if not code or not state:
        raise HTTPException(status_code=400, detail="Callback do Google incompleto")
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Login com Google ainda não configurado")

    _validate_google_state(state, request.cookies.get(GOOGLE_OAUTH_STATE_COOKIE))

    async with httpx.AsyncClient(timeout=20) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    if token_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Não foi possível validar o login com Google")
    raw_id_token = token_response.json().get("id_token")
    if not raw_id_token:
        raise HTTPException(status_code=401, detail="Google não retornou identidade válida")
    try:
        identity = google_id_token.verify_oauth2_token(
            raw_id_token, GoogleAuthRequest(), GOOGLE_CLIENT_ID
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Identidade Google inválida") from exc
    if not identity.get("email_verified"):
        raise HTTPException(status_code=401, detail="E-mail Google não verificado")

    user = await _upsert_google_user(identity)
    user_id = str(user["_id"])
    response = RedirectResponse(url=f"{FRONTEND_URL}/", status_code=302)
    set_auth_cookies(response, create_access_token(user_id, user["email"]),
                     create_refresh_token(user_id))
    _clear_google_state_cookie(response)
    return response


# Compatibility endpoint for old clients. It never contacts Emergent.
@router.post("/google/session")
async def legacy_google_session():
    raise HTTPException(status_code=401, detail="Fluxo legado do Google desativado")


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
