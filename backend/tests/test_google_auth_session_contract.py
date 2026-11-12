"""Google verification remains the authority for the frontend session response."""
import asyncio
import importlib
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

os.environ.setdefault("MONGODB_URL", "mongodb://127.0.0.1:27017/earnalism_auth_safety")
os.environ.setdefault("JWT_SECRET", "generated-fixture-secret-for-isolated-auth-tests-only")
server = importlib.import_module("backend.server")


def request():
    return Request({"type": "http", "method": "POST", "path": "/api/auth/google", "headers": [], "client": ("127.0.0.1", 1234)})


@pytest.fixture
def setup(monkeypatch):
    record = {"id": "fixture-reader", "name": "Fixture Reader", "email": "reader@example.com", "role": "user", "status": "active", "reading_seconds_balance": 0, "created_at": "2026-01-01T00:00:00Z"}
    users = SimpleNamespace(find_one=AsyncMock(return_value=record), insert_one=AsyncMock())
    issue = AsyncMock(return_value="generated-fixture-session")
    monkeypatch.setattr(server, "GOOGLE_CLIENT_ID", "fixture-client")
    monkeypatch.setattr(server, "db", SimpleNamespace(users=users))
    monkeypatch.setattr(server, "_verify_google_credential", lambda _: {"email": record["email"], "name": record["name"]})
    monkeypatch.setattr(server, "_create_user_session", issue)
    return record, users, issue


def test_verified_existing_identity_returns_authoritative_user_and_token(setup):
    record, users, issue = setup
    result = asyncio.run(server.auth_google(server.GoogleAuthIn(credential="fixture"), request(), Response()))
    assert result.token == "generated-fixture-session"
    assert result.user.id == record["id"]
    assert result.user.email == record["email"]
    issue.assert_awaited_once()
    users.insert_one.assert_not_awaited()


def test_blocked_identity_does_not_receive_session(setup):
    record, _, issue = setup
    record["status"] = "blocked"
    with pytest.raises(HTTPException) as error:
        asyncio.run(server.auth_google(server.GoogleAuthIn(credential="fixture"), request(), Response()))
    assert error.value.status_code == 403
    issue.assert_not_awaited()


def test_invalid_credential_does_not_query_or_issue_session(setup, monkeypatch):
    _, users, issue = setup
    def invalid(_):
        raise ValueError("invalid fixture")
    monkeypatch.setattr(server, "_verify_google_credential", invalid)
    with pytest.raises(HTTPException) as error:
        asyncio.run(server.auth_google(server.GoogleAuthIn(credential="invalid"), request(), Response()))
    assert error.value.status_code == 401
    users.find_one.assert_not_awaited()
    issue.assert_not_awaited()


def test_unconfigured_provider_fails_closed(setup, monkeypatch):
    _, users, issue = setup
    monkeypatch.setattr(server, "GOOGLE_CLIENT_ID", "")
    with pytest.raises(HTTPException) as error:
        asyncio.run(server.auth_google(server.GoogleAuthIn(credential="fixture"), request(), Response()))
    assert error.value.status_code == 503
    users.find_one.assert_not_awaited()
    issue.assert_not_awaited()


@pytest.mark.parametrize("role", ["admin", "owner", "", None])
def test_google_non_reader_identity_cannot_issue_reader_session(setup, role):
    record, users, issue = setup
    record["role"] = role
    with pytest.raises(HTTPException) as error:
        asyncio.run(server.auth_google(server.GoogleAuthIn(credential="fixture"), request(), Response()))
    assert error.value.status_code == 403
    issue.assert_not_awaited()
    users.insert_one.assert_not_awaited()


@pytest.mark.parametrize("role", ["admin", "owner", None])
def test_reader_session_issuer_rejects_wrong_role_before_any_write(monkeypatch, role):
    monkeypatch.setattr(server, "db", object())
    with pytest.raises(HTTPException) as error:
        asyncio.run(server._create_user_session({"role": role}, request(), Response()))
    assert error.value.status_code == 403


@pytest.mark.parametrize("role", ["admin", "owner", None, "user"])
def test_optional_and_required_identity_agree_without_retagging_cached_account(monkeypatch, role):
    from datetime import datetime, timezone, timedelta
    from fastapi.security import HTTPAuthorizationCredentials
    now = datetime.now(timezone.utc)
    record = {"id": "fixture-reader", "role": role, "status": "active", "reading_seconds_balance": 0,
              "active_user_session_id": "fixture-session"}
    session = {"status": "active", "idle_expires_at": now + timedelta(hours=1),
               "absolute_expires_at": now + timedelta(hours=2), "last_seen_at": now}
    lookup = AsyncMock(return_value=session)
    monkeypatch.setattr(server, "_cached_user_doc", AsyncMock(return_value=record))
    monkeypatch.setattr(server, "_cached_user_session", lookup)
    monkeypatch.setattr(server, "SESSION_TOUCH_INTERVAL_SECONDS", 60)
    monkeypatch.setattr(server, "_device_fingerprint", lambda _: "fixture-fp")
    monkeypatch.setattr(server.jwt, "decode", lambda *a, **kw: {"role": "user", "sub": record["id"],
        "sid": "fixture-session", "fp": "fixture-fp"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="synthetic-only")
    before = dict(record)
    optional = asyncio.run(server.optional_principal(request(), creds))
    assert record == before
    if role == "user":
        assert optional["role"] == "user" and optional["reading_seconds_balance"] == 0
        assert optional is not record
        required = asyncio.run(server.require_user(request(), creds))
        assert required["id"] == optional["id"]
    else:
        assert optional is None
        lookup.assert_not_awaited()
        with pytest.raises(HTTPException) as error:
            asyncio.run(server.require_user(request(), creds))
        assert error.value.status_code == 403
