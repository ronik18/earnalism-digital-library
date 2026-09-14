import asyncio
import copy
import importlib
import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

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


def matches(row, query):
    if "$and" in query:
        return all(matches(row, clause) for clause in query["$and"])
    if "$or" in query:
        return any(matches(row, clause) for clause in query["$or"])
    for key, value in query.items():
        if isinstance(value, dict) and "$exists" in value:
            if (key in row) != bool(value["$exists"]):
                return False
        elif row.get(key) != value:
            return False
    return True


class Users:
    def __init__(self, row):
        self.row = row

    async def count_documents(self, query, **_kwargs):
        return int(matches(self.row, query))

    async def find_one(self, query, *_args, **_kwargs):
        return dict(self.row) if matches(self.row, query) else None

    async def update_one(self, query, update, **_kwargs):
        if not matches(self.row, query):
            return SimpleNamespace(matched_count=0)
        self.row.update(update["$set"])
        for key in update.get("$unset", {}):
            self.row.pop(key, None)
        return SimpleNamespace(matched_count=1)


class Sessions:
    def __init__(self, rows, *, fail_update=False):
        self.rows = rows
        self.fail_update = fail_update

    def find(self, query, *_args, **_kwargs):
        return Cursor([row for row in self.rows if matches(row, query)])

    async def update_many(self, query, update, **_kwargs):
        if self.fail_update:
            raise RuntimeError("revocation storage unavailable")
        changed = 0
        for row in self.rows:
            if matches(row, query):
                row.update(update["$set"])
                changed += 1
        return SimpleNamespace(modified_count=changed)


class Events:
    def __init__(self, *, fail_insert=False):
        self.rows = []
        self.fail_insert = fail_insert

    async def insert_one(self, row, **_kwargs):
        if self.fail_insert:
            raise RuntimeError("audit storage unavailable")
        self.rows.append(dict(row))


class Operations:
    def __init__(self):
        self.rows = []

    async def find_one(self, query, *_args, **_kwargs):
        for row in self.rows:
            if matches(row, query):
                return dict(row)
        return None

    async def insert_one(self, row, **_kwargs):
        if any(existing.get("operation_id") == row.get("operation_id") for existing in self.rows):
            raise server.DuplicateKeyError("duplicate operation")
        self.rows.append(dict(row))

    async def update_one(self, query, update, **_kwargs):
        for row in self.rows:
            if matches(row, query):
                row.update(update.get("$set", {}))
                return SimpleNamespace(matched_count=1)
        return SimpleNamespace(matched_count=0)


class Transaction:
    def __init__(self, database):
        self.database = database
        self.snapshot = None

    async def __aenter__(self):
        self.snapshot = copy.deepcopy({
            "user": self.database.users.row,
            "sessions": self.database.user_sessions.rows,
            "events": self.database.reader_security_events.rows,
            "operations": self.database.credential_rotation_operations.rows,
        })
        return self

    async def __aexit__(self, exc_type, *_args):
        if exc_type:
            self.database.users.row.clear()
            self.database.users.row.update(self.snapshot["user"])
            self.database.user_sessions.rows[:] = self.snapshot["sessions"]
            self.database.reader_security_events.rows[:] = self.snapshot["events"]
            self.database.credential_rotation_operations.rows[:] = self.snapshot["operations"]
        return False


class Session:
    def __init__(self, database):
        self.database = database

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def start_transaction(self):
        return Transaction(self.database)


class Client:
    def __init__(self, database):
        self.database = database

    async def start_session(self):
        return Session(self.database)


def database(version=0, *, fail_revocation=False, fail_audit=False):
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
    events = Events(fail_insert=fail_audit)
    db = SimpleNamespace(
        users=Users(user),
        user_sessions=Sessions(sessions, fail_update=fail_revocation),
        reading_pass_sessions=SimpleNamespace(rows=metered_sessions),
        reader_security_events=events,
        credential_rotation_operations=Operations(),
    )
    return user, sessions, metered_sessions, events, db, Client(db)


def payload(**overrides):
    base = {
        "expected_email": "reader@example.com",
        "expected_credential_version": 0,
        "operation_id": "rotation-operation-0001",
        "dry_run": True,
    }
    base.update(overrides)
    return server.AdminUserCredentialRotationIn(**base)


def test_rotation_dry_run_is_non_mutating_and_reports_only_auth_session_scope(monkeypatch):
    user, sessions, metered_sessions, events, db, client = database()
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "client", client)
    result = run(server.admin_rotate_user_credentials(user["id"], payload(), {"email": "operator@example.test"}))
    assert result["dry_run"] is True
    assert result["active_auth_session_count"] == 1
    assert result["metered_sessions_untouched"] is True
    assert user["credential_version"] == 0
    assert sessions[0]["status"] == "active"
    assert metered_sessions == [{"id": "metered-1", "user_id": user["id"], "status": "ended"}]
    assert events.rows == []


def test_rotation_is_compare_and_set_and_only_revokes_account_auth_sessions(monkeypatch):
    user, sessions, metered_sessions, events, db, client = database()
    invalidated = []

    async def invalidate(uid, session_ids=None):
        invalidated.append((uid, session_ids))

    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "client", client)
    monkeypatch.setattr(server, "_invalidate_user_cache_strict", invalidate)
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
    user, sessions, _metered_sessions, events, db, client = database(version=2)
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "client", client)
    with pytest.raises(HTTPException) as exc:
        run(server.admin_rotate_user_credentials(
            user["id"],
            payload(
                expected_credential_version=0,
                expected_email="reader@example.com",
                dry_run=False,
                new_password="ReplacementPass123",
            ),
            {"email": "operator@example.test"},
        ))
    assert exc.value.status_code == 409
    assert sessions[0]["status"] == "active"
    assert events.rows == []


@pytest.mark.parametrize("failure", ["revocation", "audit"])
def test_rotation_database_failures_roll_back_all_credential_changes(monkeypatch, failure):
    user, sessions, _metered_sessions, events, db, client = database(
        fail_revocation=failure == "revocation",
        fail_audit=failure == "audit",
    )
    original_hash = user["password_hash"]
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "client", client)

    with pytest.raises(HTTPException) as exc:
        run(server.admin_rotate_user_credentials(
            user["id"],
            payload(dry_run=False, new_password="ReplacementPass123"),
            {"email": "operator@example.test"},
        ))

    assert exc.value.status_code == 503
    assert user["password_hash"] == original_hash
    assert user["credential_version"] == 0
    assert user["active_user_session_id"] == "auth-1"
    assert sessions[0]["status"] == "active"
    assert events.rows == []
    assert db.credential_rotation_operations.rows == []


def test_rotation_cache_failure_is_resumable_without_another_password_rotation(monkeypatch):
    user, sessions, _metered_sessions, events, db, client = database()
    invalidation_calls = []

    async def fail_cache(*_args, **_kwargs):
        invalidation_calls.append("failed")
        raise RuntimeError("cache unavailable")

    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "client", client)
    monkeypatch.setattr(server, "_invalidate_user_cache_strict", fail_cache)
    with pytest.raises(HTTPException) as exc:
        run(server.admin_rotate_user_credentials(
            user["id"],
            payload(dry_run=False, new_password="ReplacementPass123"),
            {"email": "operator@example.test"},
        ))

    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "CREDENTIAL_ROTATION_CLEANUP_PENDING"
    committed_hash = user["password_hash"]
    assert user["credential_version"] == 1
    assert sessions[0]["status"] == "revoked"
    assert len(events.rows) == 1
    assert db.credential_rotation_operations.rows[0]["state"] == "cache_invalidation_pending"

    async def complete_cache(*_args, **_kwargs):
        invalidation_calls.append("completed")

    monkeypatch.setattr(server, "_invalidate_user_cache_strict", complete_cache)
    result = run(server.admin_rotate_user_credentials(
        user["id"],
        payload(dry_run=False, new_password=None),
        {"email": "operator@example.test"},
    ))

    assert result["resumed"] is True
    assert result["cleanup_state"] == "complete"
    assert user["password_hash"] == committed_hash
    assert user["credential_version"] == 1
    assert len(events.rows) == 1
    assert invalidation_calls == ["failed", "completed"]
    assert db.credential_rotation_operations.rows[0]["state"] == "complete"


def test_rotation_interleaving_does_not_report_success_until_auth_cache_is_cleared(monkeypatch):
    user, sessions, _metered_sessions, _events, db, client = database()
    auth_cache = {"auth-1": {"status": "active", "user_id": user["id"]}}
    observed = []

    async def strict_cache_invalidation(uid, session_ids=None):
        # Simulate a refresh interleaving with the finalization boundary: the
        # old cache is removed before this operation becomes complete, and the
        # backing session is already revoked by the committed transaction.
        observed.append((uid, list(session_ids or []), sessions[0]["status"]))
        auth_cache.clear()
        assert sessions[0]["status"] == "revoked"
        assert "auth-1" not in auth_cache

    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "client", client)
    monkeypatch.setattr(server, "_invalidate_user_cache_strict", strict_cache_invalidation)
    result = run(server.admin_rotate_user_credentials(
        user["id"],
        payload(dry_run=False, new_password="ReplacementPass123"),
        {"email": "operator@example.test"},
    ))

    assert result["cleanup_state"] == "complete"
    assert observed == [(user["id"], ["auth-1"], "revoked")]
    assert db.credential_rotation_operations.rows[0]["state"] == "complete"


def test_rotation_http_route_reuses_the_dry_run_operation_id(monkeypatch):
    user, _sessions, _metered_sessions, _events, db, mongo_client = database()

    async def strict_cache_invalidation(*_args, **_kwargs):
        return None

    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "client", mongo_client)
    monkeypatch.setattr(server, "_invalidate_user_cache_strict", strict_cache_invalidation)
    server.app.dependency_overrides[server.require_admin] = lambda: {"email": "operator@example.test", "role": "admin"}
    try:
        http = TestClient(server.app)
        dry = http.post(f"/api/admin/users/{user['id']}/credentials/rotate", json={
            "expected_email": user["email"],
            "dry_run": True,
        })
        assert dry.status_code == 200
        operation_id = dry.json()["operation_id"]
        credential_version = dry.json()["credential_version"]
        applied = http.post(f"/api/admin/users/{user['id']}/credentials/rotate", json={
            "expected_email": user["email"],
            "expected_credential_version": credential_version,
            "operation_id": operation_id,
            "dry_run": False,
            "new_password": "ReplacementPass123",
        })
    finally:
        server.app.dependency_overrides.pop(server.require_admin, None)

    assert applied.status_code == 200
    assert applied.json()["operation_id"] == operation_id
    assert applied.json()["cleanup_state"] == "complete"


def test_rotation_execution_requires_the_version_returned_by_dry_run(monkeypatch):
    user, _sessions, _metered_sessions, _events, db, client = database()
    monkeypatch.setattr(server, "db", db)
    monkeypatch.setattr(server, "client", client)
    with pytest.raises(HTTPException) as exc:
        run(server.admin_rotate_user_credentials(
            user["id"],
            server.AdminUserCredentialRotationIn(
                expected_email=user["email"],
                operation_id="rotation-operation-0001",
                dry_run=False,
                new_password="ReplacementPass123",
            ),
            {"email": "operator@example.test"},
        ))
    assert exc.value.status_code == 400


def test_rotation_route_is_admin_guarded_and_rejects_reader_tokens(monkeypatch):
    route = next(route for route in server.api.routes if route.path == "/api/admin/users/{uid}/credentials/rotate")
    assert any(dependency.call is server.require_admin for dependency in route.dependant.dependencies)
    monkeypatch.setattr(server.jwt, "decode", lambda *_args, **_kwargs: {"role": "user"})
    with pytest.raises(HTTPException) as exc:
        run(server.require_admin(HTTPAuthorizationCredentials(scheme="Bearer", credentials="reader-token"), None))
    assert exc.value.status_code == 403
