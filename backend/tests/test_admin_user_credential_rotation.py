import asyncio
import importlib
import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

os.environ.setdefault("MONGODB_URL", "mongodb://127.0.0.1:27017/earnalism_credential_rotation")
os.environ.setdefault("JWT_SECRET", "credential-rotation-test-secret")

server = importlib.import_module("backend.server")


def run(coro):
    return asyncio.run(coro)


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, _limit):
        return [dict(row) for row in self.rows]


class Users:
    def __init__(self, row):
        self.row = row

    async def count_documents(self, query):
        return int(all(self.row.get(key) == value for key, value in query.items()))

    async def find_one(self, query, *_args):
        return dict(self.row) if all(self.row.get(key) == value for key, value in query.items()) else None

    async def update_one(self, query, update):
        clauses = query.get("$and", [query])
        for clause in clauses:
            if "$or" in clause:
                if not any(
                    (self.row.get("credential_version") == branch.get("credential_version"))
                    if "credential_version" in branch
                    else ("credential_version" not in self.row)
                    for branch in clause["$or"]
                ):
                    return SimpleNamespace(matched_count=0)
            elif not all(self.row.get(key) == value for key, value in clause.items()):
                return SimpleNamespace(matched_count=0)
        self.row.update(update["$set"])
        for key in update.get("$unset", {}):
            self.row.pop(key, None)
        return SimpleNamespace(matched_count=1)


class Sessions:
    def __init__(self, rows):
        self.rows = rows

    def find(self, query, *_args):
        return Cursor([row for row in self.rows if all(row.get(key) == value for key, value in query.items())])

    async def update_many(self, query, update):
        changed = 0
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                row.update(update["$set"])
                changed += 1
        return SimpleNamespace(modified_count=changed)


class Events:
    def __init__(self):
        self.rows = []

    async def insert_one(self, row):
        self.rows.append(dict(row))


def database(version=0):
    user = {
        "id": "private-user-id",
        "email": "reader@example.com",
        "role": "user",
        "password_hash": server.hash_password("OriginalPass123"),
        "credential_version": version,
        "reading_seconds_balance": 67,
        "wallet_seconds": 67,
        "active_user_session_id": "auth-1",
    }
    sessions = [
        {"id": "auth-1", "user_id": user["id"], "status": "active"},
        {"id": "ended-auth", "user_id": user["id"], "status": "logged_out"},
    ]
    metered_sessions = [{"id": "metered-1", "user_id": user["id"], "status": "ended"}]
    events = Events()
    return user, sessions, metered_sessions, events, SimpleNamespace(
        users=Users(user),
        user_sessions=Sessions(sessions),
        reading_pass_sessions=SimpleNamespace(rows=metered_sessions),
        reader_security_events=events,
    )


def payload(**overrides):
    base = {
        "expected_email": "reader@example.com",
        "expected_credential_version": 0,
        "dry_run": True,
    }
    base.update(overrides)
    return server.AdminUserCredentialRotationIn(**base)


def test_rotation_dry_run_is_non_mutating_and_reports_only_auth_session_scope(monkeypatch):
    user, sessions, metered_sessions, events, db = database()
    monkeypatch.setattr(server, "db", db)
    result = run(server.admin_rotate_user_credentials(user["id"], payload(), {"email": "operator@example.test"}))
    assert result["dry_run"] is True
    assert result["active_auth_session_count"] == 1
    assert result["metered_sessions_untouched"] is True
    assert user["credential_version"] == 0
    assert sessions[0]["status"] == "active"
    assert metered_sessions == [{"id": "metered-1", "user_id": user["id"], "status": "ended"}]
    assert events.rows == []


def test_rotation_is_compare_and_set_and_only_revokes_account_auth_sessions(monkeypatch):
    user, sessions, metered_sessions, events, db = database()
    invalidated = []

    async def invalidate(uid, session_ids=None):
        invalidated.append((uid, session_ids))

    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "_invalidate_user_cache", invalidate)
    result = run(server.admin_rotate_user_credentials(
        user["id"],
        payload(dry_run=False, new_password="ReplacementPass123"),
        {"email": "operator@example.test"},
    ))
    assert result["dry_run"] is False
    assert result["credential_version"] == 1
    assert server.verify_password("ReplacementPass123", user["password_hash"])
    assert user["reading_seconds_balance"] == 67
    assert user["wallet_seconds"] == 67
    assert "active_user_session_id" not in user
    assert sessions[0]["status"] == "revoked"
    assert sessions[1]["status"] == "logged_out"
    assert metered_sessions == [{"id": "metered-1", "user_id": user["id"], "status": "ended"}]
    assert invalidated == [(user["id"], ["auth-1"])]
    assert events.rows[0]["event_type"] == "admin_credential_rotation"
    assert "password" not in events.rows[0]


def test_rotation_rejects_identity_and_version_drift_without_mutation(monkeypatch):
    user, sessions, _metered_sessions, events, db = database(version=2)
    monkeypatch.setattr(server, "db", db)
    with pytest.raises(HTTPException) as exc:
        run(server.admin_rotate_user_credentials(
            user["id"],
            payload(expected_credential_version=0, expected_email="reader@example.com"),
            {"email": "operator@example.test"},
        ))
    assert exc.value.status_code == 409
    assert sessions[0]["status"] == "active"
    assert events.rows == []


def test_rotation_route_is_admin_guarded_and_rejects_reader_tokens(monkeypatch):
    route = next(route for route in server.api.routes if route.path == "/api/admin/users/{uid}/credentials/rotate")
    assert any(dependency.call is server.require_admin for dependency in route.dependant.dependencies)
    monkeypatch.setattr(server.jwt, "decode", lambda *_args, **_kwargs: {"role": "user"})
    with pytest.raises(HTTPException) as exc:
        run(server.require_admin(HTTPAuthorizationCredentials(scheme="Bearer", credentials="reader-token"), None))
    assert exc.value.status_code == 403
