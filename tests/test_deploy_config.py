from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _services():
    data = yaml.safe_load((ROOT / "render.yaml").read_text())
    return {service["name"]: service for service in data["services"]}


def _env(service):
    return {item["key"]: item for item in service.get("envVars", [])}


def test_render_fullstack_preserves_production_financial_guards():
    services = _services()
    assert set(services) == {"futureflex-api"}

    api = services["futureflex-api"]
    env = _env(api)

    assert api["runtime"] == "python"
    assert api["plan"] == "free"
    assert api["healthCheckPath"] == "/api/health"
    assert api["autoDeployTrigger"] == "checksPass"
    assert api["startCommand"] == "cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT"
    assert "pip install -r backend/requirements.txt" in api["buildCommand"]
    assert "--frozen-lockfile" in api["buildCommand"]
    assert "REACT_APP_BACKEND_URL=" in api["buildCommand"]

    assert env["APP_ENV"]["value"] == "production"
    assert env["PASSWORD_MIN_LENGTH"]["value"] == "15"
    assert env["REQUIRE_REPLICA_SET"]["value"] == "true"
    assert env["ENABLE_DEMO_USER"]["value"] == "false"
    assert env["COOKIE_SECURE"]["value"] == "true"
    assert env["COOKIE_SAMESITE"]["value"] == "lax"
    assert env["MONGO_URL"]["sync"] is False
    assert env["JWT_SECRET"]["generateValue"] is True


def test_render_uses_same_origin_browser_session():
    api = _services()["futureflex-api"]
    env = _env(api)

    expected_origin = "https://futureflex-api.onrender.com"
    assert env["FRONTEND_URL"]["value"] == expected_origin
    assert env["CORS_ORIGINS"]["value"] == expected_origin
    assert "futureflex-web" not in _services()


def test_blueprint_does_not_hardcode_external_secrets():
    api_env = _env(_services()["futureflex-api"])

    assert "OPENAI_API_KEY" not in api_env
    assert "GOOGLE_CLIENT_SECRET" not in api_env
    assert api_env["MONGO_URL"] == {"key": "MONGO_URL", "sync": False}
