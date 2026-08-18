from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _services():
    data = yaml.safe_load((ROOT / "render.yaml").read_text())
    return {service["name"]: service for service in data["services"]}


def _env(service):
    return {item["key"]: item for item in service.get("envVars", [])}


def test_render_api_preserves_production_financial_guards():
    api = _services()["futureflex-api"]
    env = _env(api)

    assert api["runtime"] == "python"
    assert api["healthCheckPath"] == "/api/health"
    assert api["autoDeployTrigger"] == "checksPass"
    assert api["startCommand"] == "uvicorn server:app --host 0.0.0.0 --port $PORT"
    assert env["APP_ENV"]["value"] == "production"
    assert env["REQUIRE_REPLICA_SET"]["value"] == "true"
    assert env["ENABLE_DEMO_USER"]["value"] == "false"
    assert env["COOKIE_SECURE"]["value"] == "true"
    assert env["MONGO_URL"]["sync"] is False
    assert env["JWT_SECRET"]["generateValue"] is True


def test_render_frontend_uses_frozen_dependencies_and_spa_fallback():
    web = _services()["futureflex-web"]
    env = _env(web)

    assert web["runtime"] == "static"
    assert "--frozen-lockfile" in web["buildCommand"]
    assert web["staticPublishPath"] == "build"
    assert web["autoDeployTrigger"] == "checksPass"
    assert env["REACT_APP_BACKEND_URL"]["sync"] is False
    assert {
        "type": "rewrite",
        "source": "/*",
        "destination": "/index.html",
    } in web["routes"]


def test_blueprint_does_not_hardcode_external_secrets():
    services = _services()
    api_env = _env(services["futureflex-api"])

    assert "OPENAI_API_KEY" not in api_env
    assert "GOOGLE_CLIENT_SECRET" not in api_env
    assert api_env["MONGO_URL"] == {"key": "MONGO_URL", "sync": False}
    assert api_env["FRONTEND_URL"] == {"key": "FRONTEND_URL", "sync": False}
    assert api_env["CORS_ORIGINS"] == {"key": "CORS_ORIGINS", "sync": False}
