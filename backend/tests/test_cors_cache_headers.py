from __future__ import annotations

import os

from starlette.middleware.cors import CORSMiddleware


os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "cors-cache-header-test-secret")

from backend import server


def test_cors_allows_frontend_cache_busting_headers():
    cors = next(middleware for middleware in server.app.user_middleware if middleware.cls is CORSMiddleware)
    allowed_headers = {header.lower() for header in cors.kwargs["allow_headers"]}

    assert {"cache-control", "pragma"}.issubset(allowed_headers)
