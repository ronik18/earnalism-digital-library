"""Regression coverage for the frontend-compatible reading-time contract.

These tests deliberately call the real ``/reading/*`` route handlers with an
isolated async Mongo-shaped double.  That keeps payment and billing coverage
deterministic while still exercising the production credit, session, pulse,
CAS debit, and ledger code paths.  No provider calls or live database writes
are made.
"""

import asyncio
import copy
import importlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class FakeResult:
    def __init__(self, modified_count=0, matched_count=0, upserted_id=None):
        self.modified_count = modified_count
        self.matched_count = matched_count
        self.upserted_id = upserted_id


class FakeCursor:
    def __init__(self, documents):
        self.documents = [copy.deepcopy(document) for document in documents]

    def sort(self, field, direction):
        self.documents.sort(key=lambda document: _get_path(document, field) or 0, reverse=direction < 0)
        return self

    async def to_list(self, length):
        await asyncio.sleep(0)
        return copy.deepcopy(self.documents[:length])


def _get_path(document, path):
    value = document
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _set_path(document, path, value):
    parts = path.split(".")
    target = document
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def _unset_path(document, path):
    parts = path.split(".")
    target = document
    for part in parts[:-1]:
        if not isinstance(target, dict) or part not in target:
            return
        target = target[part]
    if isinstance(target, dict):
        target.pop(parts[-1], None)


def _matches(document, query):
    for key, expected in query.items():
        actual = _get_path(document, key)
        if isinstance(expected, dict):
            if "$ne" in expected and actual == expected["$ne"]:
                return False
            if "$nin" in expected and actual in expected["$nin"]:
                return False
            if "$in" in expected and actual not in expected["$in"]:
                return False
            continue
        if actual != expected:
            return False
    return True


def _apply_update(document, update, *, inserting=False):
    before = copy.deepcopy(document)
    for operator, changes in update.items():
        if operator == "$set" or (operator == "$setOnInsert" and inserting):
            for key, value in changes.items():
                _set_path(document, key, copy.deepcopy(value))
        elif operator == "$inc":
            for key, value in changes.items():
                _set_path(document, key, (_get_path(document, key) or 0) + value)
        elif operator == "$unset":
            for key in changes:
                _unset_path(document, key)
        else:
            raise AssertionError(f"Unsupported fake Mongo operator: {operator}")
    return before != document


class FakeCollection:
    def __init__(self, documents=None):
        self.documents = [copy.deepcopy(document) for document in (documents or [])]

    async def find_one(self, query, projection=None):
        await asyncio.sleep(0)
        for document in self.documents:
            if _matches(document, query):
                return copy.deepcopy(document)
        return None

    def find(self, query, projection=None):
        return FakeCursor([document for document in self.documents if _matches(document, query)])

    async def update_one(self, query, update, upsert=False):
        # Yield before matching so simultaneous pulse requests exercise the
        # same compare-and-set boundary as the production update.
        await asyncio.sleep(0)
        for document in self.documents:
            if _matches(document, query):
                changed = _apply_update(document, update)
                return FakeResult(int(changed), 1)
        if not upsert:
            return FakeResult()
        document = {}
        for key, value in query.items():
            if not isinstance(value, dict):
                _set_path(document, key, copy.deepcopy(value))
        _apply_update(document, update, inserting=True)
        self.documents.append(document)
        return FakeResult(1, 0, document.get("id"))

    async def update_many(self, query, update):
        await asyncio.sleep(0)
        modified = 0
        matched = 0
        for document in self.documents:
            if _matches(document, query):
                matched += 1
                modified += int(_apply_update(document, update))
        return FakeResult(modified, matched)

    async def insert_one(self, document):
        await asyncio.sleep(0)
        self.documents.append(copy.deepcopy(document))
        return SimpleNamespace(inserted_id=document.get("id"))


class FakeDB:
    def __init__(self, user):
        self.users = FakeCollection([user])
        self.user_sessions = FakeCollection()
        self.topup_intents = FakeCollection()
        self.wallet_ledger = FakeCollection()
        self.wallet_transactions = FakeCollection()
        self.wallet_integrity_alerts = FakeCollection()


def _load_server(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-reading-invariants-32")
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    return importlib.import_module("server")


def _install_isolated_state(monkeypatch, server, balance=0):
    user = {
        "id": "reading-invariant-user",
        "email": "reader@example.test",
        "role": "user",
        "status": "active",
        "reading_seconds_balance": balance,
        "wallet_seconds": balance,
    }
    database = FakeDB(user)
    monkeypatch.setattr(server, "db", database)

    async def book_access(slug, **_kwargs):
        return {"id": slug, "slug": slug, "title": "Fixture Reader"}

    async def wallet_cache(user_id):
        document = await database.users.find_one({"id": user_id}) or {}
        return int(document.get("reading_seconds_balance", 0) or 0)

    async def no_op(*_args, **_kwargs):
        return None

    monkeypatch.setattr(server, "_reader_book_access_doc", book_access)
    monkeypatch.setattr(server, "_cached_user_wallet_seconds", wallet_cache)

    async def user_doc(user_id):
        return await database.users.find_one({"id": user_id})

    async def user_session(session_id, user_id=None):
        query = {"id": session_id}
        if user_id:
            query["user_id"] = user_id
        return await database.user_sessions.find_one(query)

    monkeypatch.setattr(server, "_cached_user_doc", user_doc)
    monkeypatch.setattr(server, "_cached_user_session", user_session)
    monkeypatch.setattr(server, "_cache_user_session", no_op)
    monkeypatch.setattr(server, "_invalidate_user_cache", no_op)
    monkeypatch.setattr(server, "_set_user_wallet_cache", no_op)
    monkeypatch.setattr(server, "_flag_wallet_divergence", no_op)
    return database, database.users.documents[0]


def _principal(session_id):
    return {
        "id": "reading-invariant-user",
        "role": "user",
        "status": "active",
        "session_id": session_id,
    }


def _request(user_agent):
    return SimpleNamespace(headers={"user-agent": user_agent}, client=SimpleNamespace(host="127.0.0.1"))


def _run(awaitable):
    return asyncio.run(awaitable)


def _credit(database, server, minutes=1):
    intent = {
        "id": f"intent-{minutes}-{len(database.topup_intents.documents)}",
        "user_id": "reading-invariant-user",
        "pack_id": "test-pack",
        "minutes": minutes,
        "status": "created",
        "created_at": server.now_iso(),
        "expires_at": server.topup_intent_expires_at(),
    }
    database.topup_intents.documents.append(copy.deepcopy(intent))
    return _run(server._credit_wallet_for_intent(intent, f"payment-{intent['id']}", "webhook"))


def _make_next_pulse_billable(database):
    active = database.users.documents[0]["active_reading_session"]
    active["last_debit_at"] = datetime.now(timezone.utc) - timedelta(seconds=31)


def _start_reading_session(server, principal, session_id):
    payload = server.ReaderSessionStartIn(
        session_id=session_id,
        book_id="fixture-book",
        book_slug="fixture-book",
        chapter_id="chapter-1",
    )
    return _run(server.reading_session_start_v2(payload, _request(principal["session_id"]), principal))


def _pulse(server, principal, session_id):
    payload = server.ReadingPulseIn(session_id=session_id, visible=True, idle=False)
    return _run(server.reading_pulse(payload, principal))


def _ledger_totals(database):
    credit = sum(row.get("credit", 0) for row in database.wallet_ledger.documents)
    debit = sum(row.get("debit", 0) for row in database.wallet_ledger.documents)
    return credit, debit


def test_frontend_reading_routes_are_the_routes_under_regression_test(monkeypatch):
    server = _load_server(monkeypatch)
    routes = {route.path for route in server.api.routes}
    assert {"/api/reading/session/start", "/api/reading/pulse", "/api/reading/session/end"} <= routes


def test_payment_credit_reads_through_reading_routes_to_exact_wallet_empty(monkeypatch):
    server = _load_server(monkeypatch)
    database, user = _install_isolated_state(monkeypatch, server)
    principal = _principal("auth-device-a")

    credited = _credit(database, server, minutes=1)
    assert credited["status"] == "credited"
    assert user["reading_seconds_balance"] == 60

    _start_reading_session(server, principal, "reading-session-a")
    _make_next_pulse_billable(database)
    first = _pulse(server, principal, "reading-session-a")
    _make_next_pulse_billable(database)
    second = _pulse(server, principal, "reading-session-a")
    third = _pulse(server, principal, "reading-session-a")

    assert first["deducted_seconds"] == 30
    assert second["deducted_seconds"] == 30
    assert second["wallet_seconds"] == 0
    assert second["status"] == "wallet_empty"
    assert third == {"success": False, "status": "wallet_empty", "wallet_seconds": 0}
    assert user["reading_seconds_balance"] == 0
    assert user["reading_seconds_balance"] >= 0


def test_second_device_replaces_old_reading_session_before_it_can_bill(monkeypatch):
    server = _load_server(monkeypatch)
    database, user = _install_isolated_state(monkeypatch, server)
    _credit(database, server, minutes=2)
    request_a = _request("Device A")
    response_a = server.Response()
    token_a = _run(server._create_user_session(user, request_a, response_a))
    credentials_a = server.HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_a)
    device_a = _run(server.optional_principal(request_a, credentials_a))
    assert device_a and device_a["session_id"]

    _start_reading_session(server, device_a, "reading-session-a")

    request_b = _request("Device B")
    response_b = server.Response()
    token_b = _run(server._create_user_session(user, request_b, response_b))
    credentials_b = server.HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_b)
    old_device = _run(server.optional_principal(request_a, credentials_a))
    device_b = _run(server.optional_principal(request_b, credentials_b))
    assert old_device is None
    assert device_b and device_b["session_id"] != device_a["session_id"]

    _start_reading_session(server, device_b, "reading-session-b")
    old_device_reading = _pulse(server, old_device, "reading-session-a")
    assert old_device_reading == {"success": False, "status": "session_invalid"}
    assert user["reading_seconds_balance"] == 120

    _make_next_pulse_billable(database)
    new_device = _pulse(server, device_b, "reading-session-b")
    assert new_device["deducted_seconds"] == 30
    assert new_device["status"] == "low_balance"
    assert user["reading_seconds_balance"] == 90


def test_concurrent_reading_pulses_create_exactly_one_debit(monkeypatch):
    server = _load_server(monkeypatch)
    database, user = _install_isolated_state(monkeypatch, server)
    _credit(database, server, minutes=1)
    principal = _principal("auth-device-a")
    _start_reading_session(server, principal, "reading-session-a")
    _make_next_pulse_billable(database)

    payload = server.ReadingPulseIn(session_id="reading-session-a", visible=True, idle=False)

    async def send_two_pulses():
        return await asyncio.gather(
            server.reading_pulse(payload, principal),
            server.reading_pulse(payload, principal),
        )

    results = _run(send_two_pulses())
    assert sorted(result["deducted_seconds"] for result in results) == [0, 30]
    assert sum(result["deducted_seconds"] for result in results) == 30
    assert user["reading_seconds_balance"] == 30
    assert len([row for row in database.wallet_ledger.documents if row["action"] == "reading_debit"]) == 1


def test_wallet_ledger_balance_equals_credits_minus_debits_and_never_negative(monkeypatch):
    server = _load_server(monkeypatch)
    database, user = _install_isolated_state(monkeypatch, server)
    principal = _principal("auth-device-a")
    _credit(database, server, minutes=1)
    _start_reading_session(server, principal, "reading-session-a")

    for _ in range(3):
        _make_next_pulse_billable(database)
        _pulse(server, principal, "reading-session-a")

    credits, debits = _ledger_totals(database)
    assert credits == 60
    assert debits == 60
    assert user["reading_seconds_balance"] == credits - debits
    assert user["reading_seconds_balance"] >= 0
    assert all(row["balance_after"] >= 0 for row in database.wallet_ledger.documents)
