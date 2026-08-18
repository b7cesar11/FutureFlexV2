"""Release-security regression tests that do not mutate financial data."""

import os
import subprocess
import sys
from datetime import timedelta

import jwt
import pytest
from fastapi import HTTPException

from backend.ff.api.auth import _build_google_state, _validate_google_state
from backend.ff.core.config import JWT_ALGORITHM, JWT_SECRET
from backend.ff.models.base import now_utc


def _config_process(**overrides):
    env = os.environ.copy()
    env.update({
        "MONGO_URL": "mongodb://127.0.0.1:27017/?replicaSet=rs0",
        "DB_NAME": "futureflex_config_guard_test",
        "JWT_SECRET": "release-security-test-secret-1234567890",
        "APP_ENV": "production",
        "ENABLE_DEMO_USER": "false",
        "COOKIE_SECURE": "true",
        "COOKIE_SAMESITE": "lax",
        "GOOGLE_CLIENT_ID": "",
        "GOOGLE_CLIENT_SECRET": "",
        "GOOGLE_REDIRECT_URI": "https://api.example.com/api/auth/google/callback",
    })
    env.update({key: str(value) for key, value in overrides.items()})
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from backend.ff.core.config import validate_runtime_config; validate_runtime_config()",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


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


def test_samesite_none_requires_secure_cookie():
    result = _config_process(COOKIE_SAMESITE="none", COOKIE_SECURE="false")
    assert result.returncode != 0
    assert "COOKIE_SAMESITE=none" in (result.stderr + result.stdout)


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
