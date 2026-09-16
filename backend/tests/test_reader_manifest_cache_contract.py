from __future__ import annotations

import os

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "reader-manifest-cache-test-secret")

from backend import server


@pytest.fixture
def manifest_client(monkeypatch):
    wallets = {"reader-a": 600, "reader-b": 120}
    principals = {
        "reader-a": {"id": "reader-a", "role": "user", "status": "active"},
        "reader-b": {"id": "reader-b", "role": "user", "status": "active"},
        "blocked": {"id": "reader-a", "role": "user", "status": "blocked"},
        "admin": {"id": "admin", "role": "admin"},
    }

    async def principal(request: Request):
        # Isolate principal resolution; exercise the actual route and middleware.
        return principals.get(request.headers.get("authorization", "").removeprefix("Bearer "))

    async def manifest(slug, *, admin_preview=False):
        return {"version": "unchanged-edition", "book": {"slug": slug}, "chapters": []}

    async def wallet(user_id):
        return wallets[user_id]

    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", False)
    monkeypatch.setattr(server, "_reader_book_manifest_doc", manifest)
    monkeypatch.setattr(server, "_cached_user_wallet_seconds", wallet)
    monkeypatch.setitem(server.app.dependency_overrides, server.optional_principal, principal)
    client = TestClient(server.app)
    try:
        yield client, wallets
    finally:
        client.close()


def assert_private_response(response):
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert "etag" not in response.headers
    assert response.headers["x-reader-manifest-version"] == "unchanged-edition"
    vary = {
        value.strip().lower()
        for header in response.headers.get_list("vary")
        for value in header.split(",")
    }
    assert {"authorization", "cookie"}.issubset(vary)


@pytest.mark.parametrize("principal", [None, "reader-a", "reader-b", "blocked", "admin"])
def test_manifest_is_not_cacheable_for_any_principal(manifest_client, principal):
    client, _wallets = manifest_client
    headers = {"Origin": "https://theearnalism.com"}
    if principal:
        headers["Authorization"] = f"Bearer {principal}"
    response = client.get("/api/reader/book/test-edition/manifest", headers=headers)

    assert_private_response(response)
    assert response.json()["access"]["authenticated"] is (principal is not None)


def test_old_edition_etag_cannot_reuse_guest_account_or_wallet_payload(manifest_client):
    client, wallets = manifest_client
    url = "/api/reader/book/test-edition/manifest"
    stale_headers = {"If-None-Match": 'W/"reader-manifest-unchanged-edition"'}

    def fetch(principal=None, *, preview=False):
        headers = dict(stale_headers)
        if principal:
            headers["Authorization"] = f"Bearer {principal}"
        response = client.get(url + ("?preview=admin" if preview else ""), headers=headers)
        assert_private_response(response)
        return response.json()["access"]

    guest = fetch()
    assert guest["role"] == "guest"
    assert guest["wallet_seconds"] == 0
    assert guest["can_read_paid"] is False

    first = fetch("reader-a")
    assert first["role"] == "user"
    assert first["wallet_seconds"] == 600
    assert first["can_read_paid"] is True

    assert fetch("reader-b")["wallet_seconds"] == 120
    wallets["reader-b"] = 0
    exhausted = fetch("reader-b")
    assert exhausted["wallet_seconds"] == 0
    assert exhausted["can_read_paid"] is False

    blocked = fetch("blocked")
    assert blocked["status"] == "blocked"
    assert blocked["wallet_seconds"] == 0
    assert blocked["can_read_paid"] is False

    admin = fetch("admin", preview=True)
    assert admin["role"] == "admin"
    assert admin["admin_preview"] is True
    assert admin["can_read_paid"] is True

    assert fetch() == guest
