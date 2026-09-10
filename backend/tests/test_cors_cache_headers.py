from __future__ import annotations

import os
from types import SimpleNamespace

from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware


os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "cors-cache-header-test-secret")
# This module runs in its own process before the JavaScript PR regression.
# The parent launcher is UAT-configured; keep its loopback services but assert
# the production CORS allowlist without changing the running UAT server.
os.environ["ENVIRONMENT"] = "production"
os.environ.pop("CORS_ORIGINS", None)
os.environ.pop("FRONTEND_URL", None)
os.environ["READING_PASS_V2_ENABLED"] = "false"

from backend import server


class _EmptyBooksCursor:
    def sort(self, *_args):
        return self

    async def to_list(self, _limit):
        return []


class _EmptyBooksCollection:
    def find(self, *_args, **_kwargs):
        return _EmptyBooksCursor()


class _VaryRespectingCache:
    def __init__(self):
        self._entries = []

    @staticmethod
    def _request_key(headers, vary_tokens):
        normalized = {name.lower(): value for name, value in headers.items()}
        return tuple((token.lower(), normalized.get(token.lower(), "")) for token in vary_tokens)

    def store(self, headers, request_headers):
        vary_tokens = [
            token.strip()
            for value in headers.get_list("vary")
            for token in value.split(",")
            if token.strip()
        ]
        if any(token == "*" for token in vary_tokens):
            return
        self._entries.append((vary_tokens, self._request_key(request_headers, vary_tokens)))

    def hit(self, request_headers):
        return any(
            self._request_key(request_headers, vary_tokens) == stored_key
            for vary_tokens, stored_key in self._entries
        )


def _public_books_client(monkeypatch):
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(books=_EmptyBooksCollection()),
    )

    async def _cache_miss(_key):
        return None

    async def _cache_set(_key, _value):
        return None

    monkeypatch.setattr(server, "_public_cache_get", _cache_miss)
    monkeypatch.setattr(server, "_public_cache_set", _cache_set)
    return TestClient(server.app)


def _vary_tokens(response):
    return [
        token.strip().lower()
        for value in response.headers.get_list("vary")
        for token in value.split(",")
        if token.strip()
    ]


def _public_request_headers(origin=None):
    headers = {"Accept-Encoding": "gzip"}
    if origin is not None:
        headers["Origin"] = origin
    return headers


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


def test_public_catalogue_cors_and_cache_contract_for_each_origin(monkeypatch):
    client = _public_books_client(monkeypatch)
    cases = [
        (None, None, None),
        ("https://theearnalism.com", "https://theearnalism.com", "true"),
        ("https://www.theearnalism.com", "https://www.theearnalism.com", "true"),
        ("https://unapproved.example", None, "true"),
    ]

    for origin, expected_acao, expected_credentials in cases:
        response = client.get("/api/books", headers=_public_request_headers(origin))

        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert response.headers["cache-control"].startswith("public")
        assert response.headers["content-encoding"] == "gzip"
        assert response.headers.get("access-control-allow-origin") == expected_acao
        assert response.headers.get("access-control-allow-credentials") == expected_credentials
        vary_tokens = _vary_tokens(response)
        assert vary_tokens.count("origin") == 1
        assert "accept-encoding" in vary_tokens


def test_vary_respecting_cache_keeps_origin_variants_separate(monkeypatch):
    client = _public_books_client(monkeypatch)
    originless = _public_request_headers()
    apex = _public_request_headers("https://theearnalism.com")
    www = _public_request_headers("https://www.theearnalism.com")
    unapproved = _public_request_headers("https://unapproved.example")

    cache = _VaryRespectingCache()
    cache.store(client.get("/api/books", headers=originless).headers, originless)
    assert not cache.hit(apex)

    cache = _VaryRespectingCache()
    cache.store(client.get("/api/books", headers=apex).headers, apex)
    assert cache.hit(apex)
    assert not cache.hit(originless)
    assert not cache.hit(www)
    assert not cache.hit(unapproved)

    cache = _VaryRespectingCache()
    cache.store(client.get("/api/books", headers=unapproved).headers, unapproved)
    assert not cache.hit(apex)


class _SyntheticHeaders:
    def __init__(self, vary_values):
        self._vary_values = vary_values

    def get_list(self, name):
        return self._vary_values if name.lower() == "vary" else []


def test_vary_wildcard_is_never_reused():
    cache = _VaryRespectingCache()
    cache.store(_SyntheticHeaders(["*"]), _public_request_headers("https://theearnalism.com"))

    assert not cache.hit(_public_request_headers("https://theearnalism.com"))


def test_vary_origin_merge_preserves_existing_dimensions_and_wildcard():
    merged = server._merge_vary_origin([
        (b"Vary", b"Accept-Encoding, oRiGiN"),
        (b"vary", b"Accept-Language"),
        (b"x-unrelated", b"unchanged"),
    ])

    assert merged == [
        (b"x-unrelated", b"unchanged"),
        (b"vary", b"Accept-Encoding, oRiGiN, Accept-Language"),
    ]
    wildcard = [(b"vary", b"*"), (b"Vary", b"Accept-Encoding")]
    assert server._merge_vary_origin(wildcard) == wildcard


def test_public_cache_vary_does_not_apply_to_authenticated_or_no_store_responses(monkeypatch):
    client = _public_books_client(monkeypatch)
    authenticated = client.get(
        "/api/books",
        headers={
            **_public_request_headers("https://theearnalism.com"),
            "Authorization": "Bearer private-token",
        },
    )

    assert authenticated.status_code == 200
    assert "cache-control" not in authenticated.headers
    assert _vary_tokens(authenticated).count("origin") == 1
    assert not server._is_public_anonymous_cacheable_response(
        "GET",
        "/api/books",
        200,
        "Bearer private-token",
    )
    assert not server._cache_control_is_publicly_cacheable([
        (b"cache-control", b"no-store"),
    ])
