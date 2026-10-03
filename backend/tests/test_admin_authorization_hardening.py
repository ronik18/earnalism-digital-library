import asyncio
import importlib
import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

os.environ.setdefault("JWT_SECRET", "admin-authorization-hardening-test-secret")
os.environ.setdefault("MONGODB_URL", "mongodb://127.0.0.1:27017/earnalism_admin_authz_test")
server = importlib.import_module("backend.server")


class Users:
    def __init__(self, rows):
        self.rows = rows

    async def find_one(self, query, *_args, **_kwargs):
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                return dict(row)
        return None


def run(coro):
    return asyncio.run(coro)


def credentials_for(user_id, role="admin"):
    token = server.jwt.encode(
        {"sub": user_id, "email": "claimed@example.test", "role": role, "type": "access"},
        server.JWT_SECRET,
        algorithm=server.JWT_ALG,
    )
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def request():
    return Request({"type": "http", "headers": [], "method": "GET", "path": "/"})


def test_password_login_rejects_normal_user(monkeypatch):
    user = {
        "id": "reader-1",
        "email": "reader@example.com",
        "role": "user",
        "password_hash": "stored",
    }
    monkeypatch.setattr(server, "db", SimpleNamespace(users=Users([user])))
    monkeypatch.setattr(server, "verify_password", lambda _password, _hash: True)

    with pytest.raises(HTTPException) as exc:
        run(server.login(server.LoginIn(email=user["email"], password="password")))

    assert exc.value.status_code == 403


def test_forged_admin_claim_for_user_cannot_access_admin_or_optional_admin_path(monkeypatch):
    user = {"id": "reader-1", "email": "reader@example.com", "role": "user", "status": "active"}
    monkeypatch.setattr(server, "db", SimpleNamespace(users=Users([user])))
    creds = credentials_for(user["id"], role="admin")

    with pytest.raises(HTTPException) as exc:
        run(server.require_admin(creds, None))
    assert exc.value.status_code == 403
    assert run(server.optional_principal(request(), creds)) is None


@pytest.mark.parametrize("status_field", [
    {"status": "blocked"},
    {"status": "disabled"},
    {"status": "inactive"},
    {"is_active": False},
    {"admin_active": False},
])
def test_disabled_or_invalidated_admin_loses_existing_token(monkeypatch, status_field):
    admin = {"id": "admin-1", "email": "admin@example.com", "role": "admin", **status_field}
    monkeypatch.setattr(server, "db", SimpleNamespace(users=Users([admin])))
    creds = credentials_for(admin["id"])

    with pytest.raises(HTTPException) as exc:
        run(server.require_admin(creds, None))
    assert exc.value.status_code == 403
    assert run(server.optional_principal(request(), creds)) is None


def test_active_admin_preserves_legitimate_access(monkeypatch):
    admin = {"id": "admin-1", "email": "admin@example.com", "role": "admin", "status": "active"}
    monkeypatch.setattr(server, "db", SimpleNamespace(users=Users([admin])))
    creds = credentials_for(admin["id"])

    principal = run(server.require_admin(creds, None))
    assert principal["id"] == admin["id"]
    assert principal["email"] == admin["email"]
    assert principal["role"] == "admin"
    assert run(server.optional_principal(request(), creds))["id"] == admin["id"]
