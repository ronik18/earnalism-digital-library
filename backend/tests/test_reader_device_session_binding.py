import asyncio
import copy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request
from starlette.responses import Response

from backend import server


DEVICE = "a" * 64
REFRESH = "isolated-refresh-proof"
USER = {"id": "isolated-user", "email": "reader@example.com", "role": "user", "status": "active", "name": "Reader", "active_user_session_id": "isolated-session", "reading_seconds_balance": 0}


def request(ip="192.0.2.1", device=DEVICE, ua="IsolatedBrowser/1"):
    cookies = f"{server.USER_REFRESH_COOKIE}={REFRESH}"
    if device:
        cookies += f"; {server.USER_DEVICE_COOKIE}={device}"
    return Request({"type": "http", "method": "GET", "path": "/api/users/me", "headers": [(b"user-agent", ua.encode()), (b"cookie", cookies.encode())], "client": (ip, 1234), "server": ("test", 80), "scheme": "https", "query_string": b""})


def session(legacy=False, **changes):
    now = datetime.now(timezone.utc)
    row = {"id": "isolated-session", "user_id": USER["id"], "status": "active", "refresh_token_hash": server._hash_secret(REFRESH), "user_agent": "IsolatedBrowser/1", "idle_expires_at": now + timedelta(minutes=20), "absolute_expires_at": now + timedelta(hours=2), "last_seen_at": now}
    row["device_fingerprint"] = server._legacy_device_fingerprint(request(device="")) if legacy else server._device_fingerprint(request())
    if not legacy:
        row["device_binding_version"] = 1
    row.update(changes)
    return row


def setup(monkeypatch, row, migration_count=1):
    async def find(query, *_args):
        return copy.deepcopy(row) if query.get("refresh_token_hash") == row["refresh_token_hash"] and row["status"] == "active" else None
    updates = AsyncMock(return_value=SimpleNamespace(modified_count=migration_count))
    monkeypatch.setattr(server, "db", SimpleNamespace(user_sessions=SimpleNamespace(find_one=find, update_one=updates)))
    monkeypatch.setattr(server, "_cached_user_doc", AsyncMock(return_value=copy.deepcopy(USER)))
    monkeypatch.setattr(server, "_cached_user_session", AsyncMock(return_value=copy.deepcopy(row)))
    monkeypatch.setattr(server, "_cache_user_session", AsyncMock())
    monkeypatch.setattr(server, "_invalidate_user_cache", AsyncMock())
    return updates


def test_private_device_binding_survives_network_and_language_changes():
    original = request()
    moved = request("198.51.100.2")
    assert server._legacy_device_fingerprint(original) != server._legacy_device_fingerprint(moved)
    assert server._device_fingerprint(original) == server._device_fingerprint(moved)
    assert server._device_fingerprint(original) != server._device_fingerprint(request(device="b" * 64))


@pytest.mark.parametrize("device", ["", "b" * 64, "invalid"])
def test_access_token_alone_or_another_device_cannot_authenticate(monkeypatch, device):
    row = session()
    setup(monkeypatch, row)
    token = server.create_user_token(USER["id"], USER["email"], row["id"], row["device_fingerprint"])
    with pytest.raises(HTTPException) as rejected:
        asyncio.run(server.require_user(request(device=device), HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)))
    assert rejected.value.status_code == 401


def test_authenticated_access_survives_an_ip_change(monkeypatch):
    row = session()
    setup(monkeypatch, row)
    token = server.create_user_token(USER["id"], USER["email"], row["id"], row["device_fingerprint"])
    result = asyncio.run(server.require_user(request("198.51.100.2"), HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)))
    assert result["id"] == USER["id"]


def test_new_login_sets_both_private_cookies_and_binds_the_signed_token(monkeypatch):
    inserted = AsyncMock()
    active = SimpleNamespace(sort=lambda *_args: SimpleNamespace(to_list=AsyncMock(return_value=[])))
    monkeypatch.setattr(server, "db", SimpleNamespace(
        user_sessions=SimpleNamespace(insert_one=inserted, find=lambda *_args: active),
        users=SimpleNamespace(update_one=AsyncMock()),
    ))
    monkeypatch.setattr(server, "_cache_user_session", AsyncMock())
    monkeypatch.setattr(server, "_invalidate_user_cache", AsyncMock())
    response = Response()
    token = asyncio.run(server._create_user_session(USER, request(device=""), response))
    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 2
    assert {cookie.split("=", 1)[0] for cookie in cookies} == {server.USER_REFRESH_COOKIE, server.USER_DEVICE_COOKIE}
    assert all("HttpOnly" in cookie and "Secure" in cookie and "Path=/" in cookie for cookie in cookies)
    device_cookie = next(cookie for cookie in cookies if cookie.startswith(server.USER_DEVICE_COOKIE + "="))
    device_id = device_cookie.split("=", 1)[1].split(";", 1)[0]
    row = inserted.call_args.args[0]
    grant = server.jwt.decode(token, server.JWT_SECRET, algorithms=[server.JWT_ALG])
    assert len(device_id) == 64 and row["device_binding_version"] == 1
    assert row["device_fingerprint"] == server._device_fingerprint(request("198.51.100.2", device=device_id))
    assert grant["sid"] == row["id"] and grant["fp"] == row["device_fingerprint"]


def test_legacy_refresh_proof_migrates_without_requiring_the_old_ip(monkeypatch):
    updates = setup(monkeypatch, session(legacy=True))
    response = Response()
    result = asyncio.run(server._refresh_user_session(REFRESH, request("198.51.100.2", device=""), response))
    assert result and result["user"].id == USER["id"]
    migration = updates.call_args_list[0]
    assert migration.args[0]["device_binding_version"] == {"$ne": 1}
    assert migration.args[1]["$set"]["device_binding_version"] == 1
    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 1 and cookies[0].startswith(server.USER_DEVICE_COOKIE + "=")
    assert "HttpOnly" in cookies[0] and "Secure" in cookies[0]


@pytest.mark.parametrize("kind", ["expired", "revoked", "wrong-browser", "wrong-refresh", "missing-device", "other-device"])
def test_refresh_does_not_recover_invalid_or_foreign_sessions(monkeypatch, kind):
    row = session(legacy=kind in {"expired", "revoked", "wrong-browser", "wrong-refresh"})
    if kind == "expired":
        row["idle_expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    if kind == "revoked":
        row["status"] = "revoked"
    setup(monkeypatch, row)
    req = request(device="" if kind == "missing-device" else "b" * 64 if kind == "other-device" else DEVICE, ua="OtherBrowser" if kind == "wrong-browser" else "IsolatedBrowser/1")
    result = asyncio.run(server._refresh_user_session("wrong-proof" if kind == "wrong-refresh" else REFRESH, req, Response()))
    assert result is None


def test_concurrent_legacy_migration_is_retryable_and_cannot_replace_the_winner(monkeypatch):
    setup(monkeypatch, session(legacy=True), migration_count=0)
    with pytest.raises(HTTPException) as retry:
        asyncio.run(server._refresh_user_session(REFRESH, request(device=""), Response()))
    assert retry.value.status_code == 503
    server._cache_user_session.assert_not_awaited()


def test_cookie_bound_refresh_survives_changed_network(monkeypatch):
    updates = setup(monkeypatch, session())
    result = asyncio.run(server._refresh_user_session(REFRESH, request("198.51.100.2"), Response()))
    assert result
    assert all("device_binding_version" not in call.args[1].get("$set", {}) for call in updates.call_args_list)
