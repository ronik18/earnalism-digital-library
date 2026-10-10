"""Actual health handlers on isolated ASGI; no server startup/DB access."""
import ast
import asyncio
import importlib
from pathlib import Path
from types import SimpleNamespace

import httpx
from fastapi import APIRouter, FastAPI, Response

from backend.utils.deployment_attestation import deployment_attestation


def test_provider_fields_only_and_missing_git_is_unavailable():
    env = {"GITHUB_SHA": "a" * 40, "EXPECTED_SHA": "b" * 40, "MONGODB_URL": "secret", "RAILWAY_TOKEN": "secret"}
    result = deployment_attestation(env)
    assert result["status"] == "UNAVAILABLE" and result["git_sha"] is None
    assert set(result) == {"status", "git_sha", "deployment_id", "project_id", "service_id", "environment_id"}
    assert "secret" not in str(result)


def test_valid_provider_identity_and_malformed_values():
    env = {key: "11111111-1111-1111-1111-111111111111" for key in (
        "RAILWAY_DEPLOYMENT_ID", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID", "RAILWAY_ENVIRONMENT_ID")}
    env["RAILWAY_GIT_COMMIT_SHA"] = "a" * 40
    assert deployment_attestation(env)["status"] == "AVAILABLE"
    for key in env:
        broken = {**env, key: "secret-or-malformed"}
        result = deployment_attestation(broken)
        assert result["status"] == "UNAVAILABLE"
        assert "secret-or-malformed" not in str(result)


def test_actual_health_routes_preserve_liveness_and_disable_caching(monkeypatch):
    # Extract unchanged-route wiring and the actual changed handlers, without
    # importing server (which opens production-capable service clients).
    import sys
    monkeypatch.setitem(sys.modules, "utils.deployment_attestation", importlib.import_module("backend.utils.deployment_attestation"))
    monkeypatch.setitem(sys.modules, "utils", SimpleNamespace())
    app, api = FastAPI(), APIRouter(prefix="/api")
    namespace = {"app": app, "api": api, "Response": Response, "MULTI_REPLICA_ENABLED": False}
    tree = ast.parse((Path(__file__).resolve().parents[1] / "server.py").read_text())
    handlers = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                and node.name in ("root_healthz_check", "api_healthz_check")]
    exec(compile(ast.Module(body=handlers, type_ignores=[]), "actual-health-handlers", "exec"), namespace)
    app.include_router(api)
    monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://synthetic") as client:
            for path in ("/healthz", "/api/healthz"):
                response = await client.get(path)
                assert response.status_code == 200
                assert response.json()["status"] == "ok"
                assert response.json()["replica"] == "single"
                assert response.json()["deployment"]["status"] == "UNAVAILABLE"
                assert response.headers["cache-control"] == "no-store"
            for key in ("RAILWAY_DEPLOYMENT_ID", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID", "RAILWAY_ENVIRONMENT_ID"):
                monkeypatch.setenv(key, "11111111-1111-1111-1111-111111111111")
            monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "a" * 40)
            valid = await client.get("/healthz")
            assert valid.json()["deployment"]["status"] == "AVAILABLE"
            assert valid.json()["deployment"]["git_sha"] == "a" * 40
            monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA")
            # No stale health cache may retain previously available provenance.
            assert (await client.get("/healthz")).json()["deployment"]["status"] == "UNAVAILABLE"
    asyncio.run(exercise())
