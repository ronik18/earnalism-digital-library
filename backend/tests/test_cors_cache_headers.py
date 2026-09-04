from __future__ import annotations

import os

from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware


os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "cors-cache-header-test-secret")

from backend import server


def test_production_cors_has_the_canonical_public_web_origins_without_env_configuration():
    origins = server.resolve_cors_origins("production")

    assert origins == {
        "https://theearnalism.com",
        "https://www.theearnalism.com",
    }


def test_cors_allows_frontend_cache_busting_and_reading_pass_lease_headers():
    cors = next(middleware for middleware in server.app.user_middleware if middleware.cls is CORSMiddleware)
    allowed_headers = {header.lower() for header in cors.kwargs["allow_headers"]}

    assert {
        "cache-control",
        "pragma",
        "x-reading-pass-session",
        "x-reading-pass-lease",
    }.issubset(allowed_headers)


def test_cors_preflight_allows_the_opaque_reading_pass_lease_pair():
    response = TestClient(server.app).options(
        "/api/reading-pass/books/dracula/pages/4",
        headers={
            "Origin": "https://theearnalism.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,x-reading-pass-session,x-reading-pass-lease",
        },
    )

    assert response.status_code == 200
    allowed_headers = {header.strip().lower() for header in response.headers["access-control-allow-headers"].split(",")}
    assert {"authorization", "x-reading-pass-session", "x-reading-pass-lease"}.issubset(allowed_headers)
