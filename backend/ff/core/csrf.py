import hashlib
import hmac
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import COOKIE_SAMESITE, COOKIE_SECURE, JWT_SECRET, REFRESH_TOKEN_DAYS

CSRF_COOKIE_NAME = "ff_csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Login/registration/refresh accept JSON and are protected by the browser same-origin/CORS
# boundary. Refresh only rotates authentication credentials; it never mutates financial data.
# Google OAuth has its own signed, browser-bound state validation.
PUBLIC_UNSAFE_PATHS = frozenset({
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/auth/google/session",
})


def _binding_digest(binding: str) -> str:
    return hashlib.sha256(binding.encode("utf-8")).hexdigest()


def make_csrf_token(binding: str) -> str:
    """Create a signed token tied to the current authenticated browser session."""
    nonce = secrets.token_urlsafe(32)
    message = f"{_binding_digest(binding)}.{nonce}".encode("utf-8")
    signature = hmac.new(JWT_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"{nonce}.{signature}"


def validate_csrf_token(token: str | None, binding: str | None) -> bool:
    if not token or not binding or "." not in token:
        return False
    nonce, supplied_signature = token.rsplit(".", 1)
    if not nonce or not supplied_signature:
        return False
    message = f"{_binding_digest(binding)}.{nonce}".encode("utf-8")
    expected_signature = hmac.new(
        JWT_SECRET.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(supplied_signature, expected_signature)


def request_session_binding(request: Request) -> str | None:
    # Prefer the longer-lived refresh cookie so normal access-token rotation does not
    # invalidate every in-flight request. Refresh rotation issues a new CSRF token.
    return (
        request.cookies.get("refresh_token")
        or request.cookies.get("session_token")
        or request.cookies.get("access_token")
    )


def request_uses_explicit_bearer(request: Request) -> bool:
    header = request.headers.get("Authorization", "")
    return header.startswith("Bearer ") and bool(header[7:].strip())


def set_csrf_cookie(response: Response, binding: str, token: str | None = None) -> str:
    token = token if validate_csrf_token(token, binding) else make_csrf_token(binding)
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_DAYS * 86400,
        path="/",
    )
    response.headers[CSRF_HEADER_NAME] = token
    return token


def clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path="/",
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )


class CSRFMiddleware(BaseHTTPMiddleware):
    """Protect cookie-authenticated state changes with a signed double-submit token.

    Browser cookies are ambient credentials, so unsafe /api requests must prove they
    came through trusted application JavaScript by echoing X-CSRF-Token. Explicit
    Bearer clients are non-ambient and remain compatible with API regression tooling.
    """

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        binding = request_session_binding(request)
        existing_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        unsafe = request.method.upper() not in SAFE_METHODS
        bearer = request_uses_explicit_bearer(request)
        public_unsafe = request.url.path in PUBLIC_UNSAFE_PATHS

        if unsafe and binding and not bearer and not public_unsafe:
            supplied = request.headers.get(CSRF_HEADER_NAME)
            cookie_matches_header = bool(
                existing_cookie
                and supplied
                and hmac.compare_digest(existing_cookie, supplied)
            )
            if not cookie_matches_header or not validate_csrf_token(supplied, binding):
                response = JSONResponse(
                    status_code=403,
                    content={"detail": "Proteção CSRF inválida ou ausente. Recarregue e tente novamente."},
                )
                set_csrf_cookie(response, binding, existing_cookie)
                return response

        response = await call_next(request)

        # Auth handlers that rotate/set credentials attach a token bound to the new
        # refresh cookie themselves. Do not overwrite it with the pre-request binding.
        if CSRF_HEADER_NAME in response.headers:
            return response

        # Logout intentionally clears all auth/CSRF cookies.
        if request.url.path == "/api/auth/logout" and response.status_code < 400:
            return response

        if binding:
            set_csrf_cookie(response, binding, existing_cookie)

        return response
