"""Release-security regression tests that do not mutate financial data."""

import os
import subprocess
import sys
from datetime import timedelta

import bcrypt
import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.ff.api.auth import _build_google_state, _validate_google_state
from backend.ff.core.config import JWT_ALGORITHM, JWT_SECRET
from backend.ff.core.csrf import (make_csrf_token, request_session_binding,
                                  request_uses_explicit_bearer, validate_csrf_token)
from backend.ff.core.security import hash_password, verify_password
from backend.ff.models.base import now_utc


def _production_env(**overrides):
    env = os.environ.copy()
    env.update({
        "MONGO_URL": "mongodb://127.0.0.1:27017/?replicaSet=rs0",
        "DB_NAME": "futureflex_config_guard_test",
        "JWT_SECRET": "release-security-test-secret-1234567890",
        "APP_ENV": "production",
        "ENABLE_DEMO_USER": "false",
        "COOKIE_SECURE": "true",
        "COOKIE_SAMESITE": "lax",
        "PASSWORD_MIN_LENGTH": "15",
        "CORS_ORIGINS": "https://app.example.com",
        "GOOGLE_CLIENT_ID": "",
        "GOOGLE_CLIENT_SECRET": "",
        "GOOGLE_REDIRECT_URI": "https://api.example.com/api/auth/google/callback",
    })
    env.update({key: str(value) for key, value in overrides.items()})
    return env


def _python_process(code: str, **overrides):
    return subprocess.run(
        [sys.executable, "-c", code],
        env=_production_env(**overrides),
        capture_output=True,
        text=True,
        check=False,
    )


def _config_process(**overrides):
    return _python_process(
        "from backend.ff.core.config import validate_runtime_config; validate_runtime_config()",
        **overrides,
    )


def _request(*, cookie: str = "", authorization: str = "") -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", cookie.encode("latin-1")))
    if authorization:
        headers.append((b"authorization", authorization.encode("latin-1")))
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/api/accounts",
        "raw_path": b"/api/accounts",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("api.example.com", 443),
    })


def test_production_rejects_weak_jwt_secret():
    result = _config_process(JWT_SECRET="short")
    assert result.returncode != 0
    assert "32 caracteres" in (result.stderr + result.stdout)


def test_production_rejects_demo_user():
    result = _config_process(ENABLE_DEMO_USER="true")
    assert result.returncode != 0
    assert "ENABLE_DEMO_USER" in (result.stderr + result.stdout)


def test_production_accepts_secure_baseline():
    result = _config_process()
    assert result.returncode == 0, result.stderr


def test_production_rejects_password_policy_below_15():
    result = _config_process(PASSWORD_MIN_LENGTH="8")
    assert result.returncode != 0
    assert "PASSWORD_MIN_LENGTH" in (result.stderr + result.stdout)


def test_production_requires_secure_cookies():
    result = _config_process(COOKIE_SECURE="false")
    assert result.returncode != 0
    assert "COOKIE_SECURE" in (result.stderr + result.stdout)


def test_production_rejects_wildcard_cors():
    result = _config_process(CORS_ORIGINS="*")
    assert result.returncode != 0
    assert "wildcard" in (result.stderr + result.stdout)


def test_samesite_none_requires_secure_cookie_even_outside_production():
    result = _config_process(APP_ENV="test", COOKIE_SAMESITE="none", COOKIE_SECURE="false")
    assert result.returncode != 0
    assert "COOKIE_SAMESITE=none" in (result.stderr + result.stdout)


def test_production_never_exposes_access_token_in_json_mode():
    result = _python_process(
        "from backend.ff.core.config import EXPOSE_ACCESS_TOKEN_IN_RESPONSE; "
        "assert EXPOSE_ACCESS_TOKEN_IN_RESPONSE is False"
    )
    assert result.returncode == 0, result.stderr


def test_password_hash_uses_full_long_password_and_reads_legacy_bcrypt():
    long_password = "frase-secreta-" + ("á" * 80) + "-fim"
    hashed = hash_password(long_password)
    assert hashed.startswith("bcrypt_sha256$")
    assert verify_password(long_password, hashed)
    assert not verify_password(long_password + "x", hashed)

    legacy_password = "SenhaLegada@2026"
    legacy_hash = bcrypt.hashpw(legacy_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    assert verify_password(legacy_password, legacy_hash)


def test_csrf_token_is_signed_and_bound_to_session():
    binding = "refresh-session-A"
    token = make_csrf_token(binding)
    assert validate_csrf_token(token, binding)
    assert not validate_csrf_token(token, "refresh-session-B")
    assert not validate_csrf_token(token + "tampered", binding)
    assert not validate_csrf_token(None, binding)


def test_csrf_prefers_refresh_cookie_as_session_binding():
    request = _request(cookie="access_token=access-A; refresh_token=refresh-A; session_token=session-A")
    assert request_session_binding(request) == "refresh-A"


def test_explicit_bearer_is_detected_for_non_ambient_api_clients():
    assert request_uses_explicit_bearer(_request(authorization="Bearer abc.def.ghi"))
    assert not request_uses_explicit_bearer(_request())
    assert not request_uses_explicit_bearer(_request(authorization="Basic xyz"))


def test_google_oauth_state_is_bound_to_initiating_browser_cookie():
    state = _build_google_state()
    payload = _validate_google_state(state, state)
    assert payload["type"] == "google_oauth_state"
    assert payload["nonce"]

    with pytest.raises(HTTPException) as missing_cookie:
        _validate_google_state(state, None)
    assert missing_cookie.value.status_code == 400

    other_browser_state = _build_google_state()
    with pytest.raises(HTTPException) as wrong_browser:
        _validate_google_state(state, other_browser_state)
    assert wrong_browser.value.status_code == 400


def test_google_oauth_state_expiration_is_enforced():
    expired = jwt.encode(
        {
            "type": "google_oauth_state",
            "nonce": "expired-test-nonce",
            "exp": now_utc() - timedelta(seconds=1),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
        _validate_google_state(expired, expired)
    assert exc.value.status_code == 400
