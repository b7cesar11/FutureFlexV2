import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import (ACCESS_TOKEN_MINUTES, COOKIE_SAMESITE, COOKIE_SECURE,
                     JWT_ALGORITHM, JWT_SECRET, PASSWORD_MAX_LENGTH,
                     PASSWORD_MIN_LENGTH, REFRESH_TOKEN_DAYS)


# Password login is currently a single authentication factor. Keep the policy
# length-based (passphrases welcome) instead of requiring artificial character classes.
_PASSWORD_SCHEME = "bcrypt_sha256$"


def validate_new_password(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"A senha deve ter ao menos {PASSWORD_MIN_LENGTH} caracteres")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"A senha deve ter no máximo {PASSWORD_MAX_LENGTH} caracteres")


def _bcrypt_sha256_input(password: str) -> bytes:
    # bcrypt only consumes a limited input length. Pre-hashing means the complete
    # UTF-8 password contributes to verification while bcrypt still supplies the
    # adaptive salted work factor. The prefix keeps old raw-bcrypt hashes readable.
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")


def hash_password(password: str) -> str:
    digest = _bcrypt_sha256_input(password)
    hashed = bcrypt.hashpw(digest, bcrypt.gensalt()).decode("utf-8")
    return f"{_PASSWORD_SCHEME}{hashed}"


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        if hashed.startswith(_PASSWORD_SCHEME):
            stored = hashed[len(_PASSWORD_SCHEME):]
            return bcrypt.checkpw(
                _bcrypt_sha256_input(plain),
                stored.encode("utf-8"),
            )
        # Backwards compatibility for users created before the release hardening.
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def password_hash_needs_upgrade(hashed: str) -> bool:
    return bool(hashed) and not hashed.startswith(_PASSWORD_SCHEME)


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "type": "refresh",
               "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def set_auth_cookies(response, access_token: str, refresh_token: str):
    response.set_cookie("access_token", access_token, httponly=True, secure=COOKIE_SECURE,
                        samesite=COOKIE_SAMESITE, max_age=ACCESS_TOKEN_MINUTES * 60, path="/")
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=COOKIE_SECURE,
                        samesite=COOKIE_SAMESITE, max_age=REFRESH_TOKEN_DAYS * 86400, path="/")


def clear_auth_cookies(response):
    for name in ("access_token", "refresh_token", "session_token"):
        response.delete_cookie(name, path="/", secure=COOKIE_SECURE,
                               samesite=COOKIE_SAMESITE)
