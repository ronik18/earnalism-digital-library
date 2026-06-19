import asyncio
import importlib
import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.responses import Response

os.environ.setdefault("MONGODB_URL", "mongodb://127.0.0.1:27017/earnalism_auth_safety")
os.environ.setdefault("JWT_SECRET", "auth-safety-test-secret")

server = importlib.import_module("backend.server")


class FakeUsers:
    def __init__(self, doc):
        self.doc = doc

    async def find_one(self, *_args, **_kwargs):
        return self.doc


def run(coro):
    return asyncio.run(coro)


def user_doc(**overrides):
    doc = {
        "id": "user-1",
        "name": "Legacy Reader",
        "email": "reader@example.com",
        "role": "user",
        "status": "active",
        "auth_provider": "email",
        "password_hash": server.hash_password("CorrectPass123"),
        "reading_seconds_balance": 0,
        "created_at": "2026-01-01T00:00:00Z",
    }
    doc.update(overrides)
    return doc


def login_payload(password="wrong-password"):
    return server.UserLoginIn(email="reader@example.com", password=password)


def test_verify_password_returns_false_for_missing_or_malformed_hashes():
    assert server.verify_password("anything", None) is False
    assert server.verify_password("anything", "") is False
    assert server.verify_password("anything", "not-a-bcrypt-hash") is False


def test_verify_password_still_accepts_valid_bcrypt_hash():
    password_hash = server.hash_password("CorrectPass123")
    assert server.verify_password("CorrectPass123", password_hash) is True
    assert server.verify_password("WrongPass123", password_hash) is False


def test_user_login_with_malformed_email_password_hash_returns_401(monkeypatch):
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(users=FakeUsers(user_doc(password_hash="not-a-bcrypt-hash"))),
    )

    with pytest.raises(HTTPException) as exc:
        run(server.user_login(login_payload(), None, Response()))

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid email or password"


def test_user_login_with_social_account_without_password_returns_actionable_403(monkeypatch):
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(users=FakeUsers(user_doc(auth_provider="google", password_hash=""))),
    )

    with pytest.raises(HTTPException) as exc:
        run(server.user_login(login_payload(), None, Response()))

    assert exc.value.status_code == 403
    assert "does not have a password credential" in exc.value.detail
    assert "sales@reoenterprise.org" in exc.value.detail
