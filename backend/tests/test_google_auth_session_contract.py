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
