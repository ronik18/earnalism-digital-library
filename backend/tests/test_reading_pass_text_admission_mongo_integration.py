"""Replica-set coverage for protected-text admission before metered transfer.

These tests exercise the real shared start/transfer handler with the real
ReadingPassService and a disposable MongoDB namespace.  They intentionally do
not use any production title records, users, or sessions.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import os
from urllib.parse import urlparse
import uuid

import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.responses import Response

os.environ.setdefault("JWT_SECRET", "reading-pass-admission-mongo-secret")
os.environ.setdefault("READING_PASS_TOKEN_SECRET", "reading-pass-admission-mongo-token-secret-0123456789")
os.environ.setdefault("READING_PASS_V2_ENABLED", "true")

from backend import server
from backend.api.schemas import ReadingPassSessionStartIn
from backend.domain.reading_pass import canonical_page_records, ensure_utc, segment_manifest
from backend.domain.reading_pass import token_fingerprint
from backend.reading_pass_service import ReadingPassService
from backend.domain.reading_pass import ReadingPassError


pytestmark = pytest.mark.skipif(
    os.environ.get("READER_SEGMENT_MONGO_INTEGRATION") != "1",
    reason="requires the release gate's explicit isolated MongoDB replica set",
)

USER = {"id": "admission-user", "role": "user", "status": "active", "session_id": "admission-auth"}


def _mongo_uri() -> str:
    uri = os.environ.get("MONGODB_URL", "")
    parsed = urlparse(uri)
    if parsed.hostname not in {"127.0.0.1", "localhost"} or "replicaSet=" not in uri:
        raise RuntimeError("reading-pass admission integration requires an explicit loopback replica-set MONGODB_URL")
    return uri


async def _create_indexes(database) -> None:
    await database.reader_content_segments.create_index(
        [("book_slug", 1), ("page_index", 1), ("segmentation_version", 1)], unique=True
    )
    await database.reader_segment_manifests.create_index(
        [("book_slug", 1), ("segmentation_version", 1)], unique=True
    )
    await database.reader_segment_manifests.create_index(
        "book_slug", unique=True, partialFilterExpression={"status": "active"}
    )
    await database.reader_segment_activation_state.create_index("book_slug", unique=True)
    await database.reader_segment_activation_operations.create_index("operation_id", unique=True)
    await database.reading_pass_text_revocation_operations.create_index("operation_id", unique=True)
    await database.users.create_index("id", unique=True)
    await database.reading_pass_sessions.create_index("active_lock", unique=True, sparse=True)
    await database.reading_pass_sessions.create_index("id", unique=True)
    await database.reading_pass_heartbeats.create_index([("session_id", 1), ("idempotency_key", 1)], unique=True)
    await database.reading_pass_heartbeats.create_index([("session_id", 1), ("sequence", 1)], unique=True)
    await database.reading_pass_devices.create_index([("user_id", 1), ("device_id", 1)], unique=True)
    await database.wallet_ledger.create_index("idempotency_key", unique=True)


@asynccontextmanager
async def _isolated_database():
    client = AsyncIOMotorClient(_mongo_uri(), serverSelectionTimeoutMS=5_000)
    hello = await client.admin.command("hello")
    if not hello.get("isWritablePrimary") or not hello.get("setName"):
        client.close()
        raise RuntimeError("reading-pass admission integration requires a writable replica-set primary")
    database = client[f"rpadmit_it_{uuid.uuid4().hex}"]
    previous_db, previous_client, previous_service = server.db, server.client, server.reading_pass_service
    server.db = database
    server.client = client
    server.reading_pass_service = ReadingPassService(
        db=database,
        client=client,
        config=server.READING_PASS_CONFIG,
        token_secret=server.READING_PASS_TOKEN_SECRET,
    )
    try:
        await _create_indexes(database)
        yield database
    finally:
        await client.drop_database(database.name)
        server.db, server.client, server.reading_pass_service = previous_db, previous_client, previous_service
        client.close()


def _records(slug: str, version: str) -> list[dict]:
    return canonical_page_records(
        book_slug=slug,
        segmentation_version=version,
        target_characters=800,
        chapters=[{
            "id": "chapter-001",
            "title": "Fixture",
            "order": 1,
            "content": "".join("<p>" + "fixture word " * 200 + "</p>" for _ in range(10)),
        }],
    )


async def _seed_retained_content(database, slug: str, *, version: str = "admission-fixture-v1") -> dict:
    records = _records(slug, version)
    manifest = {
        "id": str(uuid.uuid4()),
        "book_slug": slug,
        "segmentation_version": version,
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        **segment_manifest(records),
    }
    await database.reader_content_segments.insert_many(records)
    await database.reader_segment_manifests.insert_one(manifest)
    await database.reader_segment_activation_state.insert_one({
        "book_slug": slug,
        "active_segmentation_version": version,
        "generation": 1,
        "created_at": datetime.now(timezone.utc),
    })
    return manifest


async def _start_bound_text_session(database, manifest: dict, slug: str) -> dict:
    await database.users.insert_one({
        "id": USER["id"], "role": "user", "status": "active",
        "reading_seconds_balance": 300, "wallet_seconds": 300,
    })
    return await server.reading_pass_service.start_session(
        user_id=USER["id"], auth_session_id=USER["session_id"],
        device_id="admission-device-0001", device_label="Revocation fixture",
        content_type="text", content_id=slug,
        scope={
            "canonical_page_index": 4,
            "segmentation_version": manifest["segmentation_version"],
            "manifest_version": manifest["version"],
            "authority_activation_generation": 1,
        },
    )


async def _revoke_bound_text(manifest: dict, slug: str, *, operation_id: str) -> dict:
    return await server.reading_pass_service.revoke_text_publication(
        book_slug=slug,
        expected_activation_generation=1,
        expected_segmentation_version=manifest["segmentation_version"],
        expected_manifest_version=manifest["version"],
        operation_id=operation_id,
        reason="fixture withdrawal",
        actor_id="fixture-admin",
    )


async def _rows(collection) -> list[dict]:
    rows = await collection.find({}, {"_id": 0}).to_list(100)
    return json.loads(json.dumps(rows, sort_keys=True, default=str))


def _payload(content_id: str, *, page_index: int = 4, device_id: str = "admission-device-0002"):
    return ReadingPassSessionStartIn(
        device_id=device_id,
        device_label="Admission fixture",
        content_type="text",
        content_id=content_id,
        canonical_page_index=page_index,
    )


@pytest.fixture
def permitted_reader_authority(monkeypatch):
    """Provide isolated authority without changing the shipped all-title hold."""

    async def resolve(slug: str, *, admin_preview: bool = False):
        if not admin_preview and str(slug or "").strip().lower() == "dracula":
            return {"slug": "dracula"}
        return None

    monkeypatch.setattr(server, "_reader_book_access_doc", resolve)


@pytest.mark.parametrize("denied_slug", ["yugalanguriya", "unknown-admission-fixture"])
@pytest.mark.parametrize("transfer", [False, True])
def test_real_handler_denied_start_or_transfer_preserves_existing_session_and_accounting(
    monkeypatch, denied_slug, transfer
):
    async def scenario():
        async with _isolated_database() as database:
            await _seed_retained_content(database, denied_slug)
            await database.users.insert_one({
                "id": USER["id"], "role": "user", "status": "active",
                "reading_seconds_balance": 300, "wallet_seconds": 300,
            })
            # This active session is legitimate fixture state, created before
            # the denied handler operation. A denied start or transfer must
            # leave its lease, accounting, and device intact.
            existing = await server.reading_pass_service.start_session(
                user_id=USER["id"], auth_session_id=USER["session_id"],
                device_id="admission-device-0001", device_label="Existing fixture",
                content_type="text", content_id="permitted-fixture",
                scope={"canonical_page_index": 4, "segmentation_version": "permitted-v1", "manifest_version": "manifest-v1"},
            )
            assert await server._reader_book_access_doc(denied_slug) is None
            before = {
                "users": await _rows(database.users),
                "sessions": await _rows(database.reading_pass_sessions),
                "devices": await _rows(database.reading_pass_devices),
                "audit": await _rows(database.reading_pass_audit),
                "ledger": await _rows(database.wallet_ledger),
            }

            async def forbidden(*_args, **_kwargs):
                pytest.fail("Reader authority denial must occur before retained-manifest access or session transfer")

            monkeypatch.setattr(server, "_active_reader_segment_manifest", forbidden)
            monkeypatch.setattr(server, "_invalidate_user_cache", forbidden)
            monkeypatch.setattr(server.reading_pass_service, "start_session", forbidden)

            response = Response()
            with pytest.raises(server.HTTPException) as denied:
                await server._reading_pass_start(_payload(denied_slug), USER, response, transfer=transfer)
            assert denied.value.status_code == 404
            assert denied.value.detail["code"] == "CONTENT_NOT_AUTHORIZED"
            assert not any(name.lower() == b"set-cookie" for name, _value in response.raw_headers)

            after = {
                "users": await _rows(database.users),
                "sessions": await _rows(database.reading_pass_sessions),
                "devices": await _rows(database.reading_pass_devices),
                "audit": await _rows(database.reading_pass_audit),
                "ledger": await _rows(database.wallet_ledger),
            }
            assert after == before
            retained = await database.reading_pass_sessions.find_one({"id": existing["session_id"]}, {"_id": 0})
            assert retained["status"] == "active"
            assert retained["lease_version"] == 1
            assert retained["content_id"] == "permitted-fixture"

    asyncio.run(scenario())


def test_real_handler_binds_fixture_authority_to_the_canonical_identity(permitted_reader_authority):
    async def scenario():
        async with _isolated_database() as database:
            manifest = await _seed_retained_content(database, "dracula")
            await database.users.insert_one({
                "id": USER["id"], "role": "user", "status": "active",
                "reading_seconds_balance": 300, "wallet_seconds": 300,
            })

            # The public resolver accepts the existing case-normalized alias
            # and returns the canonical controlled identity.  The real handler
            # must bind the lease to that identity, not the request spelling.
            result = await server._reading_pass_start(_payload("Dracula"), USER, Response(), transfer=False)
            assert result["content_id"] == "dracula"
            session = await database.reading_pass_sessions.find_one({"id": result["session_id"]}, {"_id": 0})
            assert session["content_id"] == "dracula"
            assert session["scope"] == {
                "canonical_page_index": 4,
                "segmentation_version": manifest["segmentation_version"],
                "manifest_version": manifest["version"],
                "authority_activation_generation": 1,
            }
            assert await database.reading_pass_audit.count_documents({"event": "metered_session_started"}) == 1

    asyncio.run(scenario())


def test_real_handler_rejects_authorized_fixture_title_without_an_active_canonical_page_before_session_start(
    monkeypatch, permitted_reader_authority
):
    async def scenario():
        async with _isolated_database() as database:
            await database.users.insert_one({
                "id": USER["id"], "role": "user", "status": "active",
                "reading_seconds_balance": 300, "wallet_seconds": 300,
            })
            # The fixture supplies Reader authority, but this disposable
            # database intentionally has no active manifest/page records.
            assert await server._reader_book_access_doc("dracula") is not None
            before = await _rows(database.reading_pass_sessions)
            with pytest.raises(server.HTTPException) as denied:
                await server._reading_pass_start(_payload("dracula"), USER, Response(), transfer=False)
            # Retained source authority alone cannot safely admit a protected
            # page. Without an activation pointer the handler cannot bind the
            # lease to a current immutable publication, so this is an
            # availability failure rather than a claim that the page is gone.
            assert denied.value.status_code == 503
            assert denied.value.detail["code"] == "CONTENT_AUTHORITY_UNAVAILABLE"
            assert await _rows(database.reading_pass_sessions) == before
            assert await database.reading_pass_audit.count_documents({}) == 0

    asyncio.run(scenario())


def test_real_handler_rejects_fixture_title_with_pages_but_no_activation_pointer(permitted_reader_authority):
    async def scenario():
        async with _isolated_database() as database:
            # This is a fixture pre-pointer publication shape: Reader authority
            # and an active immutable manifest/page exist, but no selected
            # generation can bind a new protected lease.  The guard returns an
            # availability error; it does not bootstrap or rewrite history.
            await _seed_retained_content(database, "dracula")
            await database.reader_segment_activation_state.delete_one({"book_slug": "dracula"})
            await database.users.insert_one({
                "id": USER["id"], "role": "user", "status": "active",
                "reading_seconds_balance": 300, "wallet_seconds": 300,
            })
            assert await database.reader_segment_manifests.count_documents(
                {"book_slug": "dracula", "status": "active"}
            ) == 1
            assert await database.reader_content_segments.count_documents({"book_slug": "dracula"}) > 0
            with pytest.raises(server.HTTPException) as denied:
                await server._reading_pass_start(_payload("dracula"), USER, Response(), transfer=False)
            assert denied.value.status_code == 503
            assert denied.value.detail["code"] == "CONTENT_AUTHORITY_UNAVAILABLE"
            assert await database.reading_pass_sessions.count_documents({}) == 0
            assert await database.reader_segment_activation_state.count_documents({}) == 0

    asyncio.run(scenario())


def test_real_mongo_fixed_clock_permitted_authority_checks_always_write_a_fence(monkeypatch):
    async def scenario():
        async with _isolated_database() as database:
            manifest = await _seed_retained_content(database, "fixed-clock-fixture")
            fixed = datetime(2026, 1, 1, tzinfo=timezone.utc)
            await database.reader_segment_activation_state.update_one(
                {"book_slug": "fixed-clock-fixture"},
                {"$set": {"text_authority_last_start_at": fixed}},
            )
            scope = {
                "segmentation_version": manifest["segmentation_version"],
                "manifest_version": manifest["version"],
                "authority_activation_generation": 1,
            }

            async def check(mongo_session):
                await server.reading_pass_service._assert_text_start_authority(
                    mongo_session=mongo_session,
                    content_id="fixed-clock-fixture",
                    scope=scope,
                    now=fixed,
                )

            # Both isolated-Mongo transactions use the same timestamp.  The
            # prior $set-only implementation made the first check a no-op;
            # the fence must provide a real conflict/order point instead.
            await server.reading_pass_service._transaction(check)
            await server.reading_pass_service._transaction(check)
            pointer = await database.reader_segment_activation_state.find_one(
                {"book_slug": "fixed-clock-fixture"}, {"_id": 0}
            )
            assert ensure_utc(pointer["text_authority_last_start_at"]) == fixed
            assert pointer["text_authority_fence"] == 2
            assert pointer["active_segmentation_version"] == manifest["segmentation_version"]
            assert pointer["generation"] == 1

    asyncio.run(scenario())


@pytest.mark.parametrize("content_type, active, playback_state", [
    ("text", True, ""),
    ("audio", True, "playing"),
])
def test_real_mongo_legacy_heartbeat_receipt_is_stale_not_a_replayed_running_lease(
    content_type, active, playback_state
):
    async def scenario():
        async with _isolated_database() as database:
            scope = {}
            if content_type == "text":
                manifest = await _seed_retained_content(database, "legacy-receipt-text")
                content_id = "legacy-receipt-text"
                scope = {
                    "canonical_page_index": 4,
                    "segmentation_version": manifest["segmentation_version"],
                    "manifest_version": manifest["version"],
                    "authority_activation_generation": 1,
                }
            else:
                content_id = "legacy-receipt-audio"
            await database.users.insert_one({
                "id": USER["id"], "role": "user", "status": "active",
                "reading_seconds_balance": 300, "wallet_seconds": 300,
            })
            started = await server.reading_pass_service.start_session(
                user_id=USER["id"], auth_session_id=USER["session_id"],
                device_id=f"legacy-receipt-{content_type}", device_label="Legacy receipt fixture",
                content_type=content_type, content_id=content_id, scope=scope,
            )
            await database.reading_pass_heartbeats.insert_one({
                "id": str(uuid.uuid4()), "session_id": started["session_id"], "user_id": USER["id"],
                "idempotency_key": "released-base-receipt", "sequence": 1, "lease_version": 1,
                "response": {"session_id": started["session_id"], "lease_version": 1, "status": "Running", "deducted_seconds": 5},
            })
            result = await server.reading_pass_service.renew_lease(
                user_id=USER["id"], auth_session_id=USER["session_id"], session_id=started["session_id"],
                lease_token=started["lease_token"], lease_version=1, sequence=1,
                idempotency_key="released-base-receipt", active=active, playback_state=playback_state,
            )
            assert result["status"] == "Stale"
            assert result["legacy_receipt"] is True
            assert "lease_token" not in result
            assert await database.wallet_ledger.count_documents({}) == 0
            assert await database.reading_pass_heartbeats.count_documents({}) == 1

    asyncio.run(scenario())


def test_real_mongo_revocation_caps_settlement_and_preserves_exact_replay(monkeypatch):
    async def scenario():
        async with _isolated_database() as database:
            manifest = await _seed_retained_content(database, "revocation-fixture")
            started = await _start_bound_text_session(database, manifest, "revocation-fixture")
            began = datetime(2026, 1, 1, tzinfo=timezone.utc)
            cutoff = datetime(2026, 1, 1, 0, 0, 11, tzinfo=timezone.utc)
            await database.reading_pass_sessions.update_one(
                {"id": started["session_id"]},
                {"$set": {"last_billed_at": began, "lease_expires_at": began.replace(second=20)}},
            )
            monkeypatch.setattr("backend.reading_pass_service._now", lambda: cutoff)

            first = await _revoke_bound_text(
                manifest, "revocation-fixture", operation_id="real-mongo-revoke-0001"
            )
            duplicate = await _revoke_bound_text(
                manifest, "revocation-fixture", operation_id="real-mongo-revoke-0001"
            )
            assert first["deducted_seconds"] == 11
            assert duplicate["duplicate"] is True
            session = await database.reading_pass_sessions.find_one({"id": started["session_id"]}, {"_id": 0})
            user = await database.users.find_one({"id": USER["id"]}, {"_id": 0})
            ledger = await _rows(database.wallet_ledger)
            transaction = await _rows(database.wallet_transactions)
            state = await database.reader_segment_activation_state.find_one(
                {"book_slug": "revocation-fixture"}, {"_id": 0}
            )
            assert session["status"] == "revoked"
            assert ensure_utc(session["settlement_at"]) == cutoff
            assert ensure_utc(session["billing_cutoff_at"]) == cutoff
            assert "active_lock" not in session
            assert user["reading_seconds_balance"] == 289
            assert len(ledger) == len(transaction) == 1
            assert ledger[0]["debit"] == 11
            assert ledger[0]["metadata"]["billing_cutoff_at"] == cutoff.isoformat()
            assert ensure_utc(state["text_revocation"]["cutoff_at"]) == cutoff

            with pytest.raises(ReadingPassError) as replay:
                await server.reading_pass_service.renew_lease(
                    user_id=USER["id"], auth_session_id=USER["session_id"], session_id=started["session_id"],
                    lease_token=started["lease_token"], lease_version=1, sequence=1,
                    idempotency_key="post-revocation-replay", active=True,
                )
            assert replay.value.code == "LEASE_EXPIRED"
            assert len(await _rows(database.wallet_ledger)) == 1
            stopped = await server.reading_pass_service.end_session(
                user_id=USER["id"], auth_session_id=USER["session_id"], session_id=started["session_id"]
            )
            assert stopped == {"ended": False, "session_id": started["session_id"], "deducted_seconds": 0}
            assert len(await _rows(database.wallet_ledger)) == 1

    asyncio.run(scenario())


def test_real_mongo_revocation_operation_id_is_global_and_schema_absence_refuses_without_writes():
    async def scenario():
        async with _isolated_database() as database:
            first = await _seed_retained_content(database, "operation-id-first")
            second = await _seed_retained_content(database, "operation-id-second")
            await _revoke_bound_text(first, "operation-id-first", operation_id="cross-title-operation-id")
            with pytest.raises(ReadingPassError) as conflict:
                await server.reading_pass_service.revoke_text_publication(
                    book_slug="operation-id-second",
                    expected_activation_generation=1,
                    expected_segmentation_version=second["segmentation_version"],
                    expected_manifest_version=second["version"],
                    operation_id="cross-title-operation-id",
                    reason="different title fixture",
                    actor_id="fixture-admin",
                )
            assert conflict.value.code == "REVOCATION_OPERATION_CONFLICT"
            # The backing MongoDB unique index independently rejects a second
            # operation document for a different title.
            from pymongo.errors import DuplicateKeyError
            with pytest.raises(DuplicateKeyError):
                await database.reading_pass_text_revocation_operations.insert_one({
                    "id": str(uuid.uuid4()), "operation_id": "cross-title-operation-id",
                    "intent": {"book_slug": "operation-id-second"}, "result": {},
                })
            assert await database.reader_segment_activation_state.count_documents(
                {"book_slug": "operation-id-second", "text_revocation": {"$exists": True}}
            ) == 0

            await database.reading_pass_text_revocation_operations.drop_index("operation_id_1")
            await database.reading_pass_text_revocation_operations.create_index(
                "operation_id", unique=True, partialFilterExpression={"approved": True}
            )
            with pytest.raises(ReadingPassError) as partial:
                await _revoke_bound_text(second, "operation-id-second", operation_id="partial-index-refusal")
            assert partial.value.code == "REVOCATION_SCHEMA_UNAVAILABLE"
            assert await database.reading_pass_text_revocation_operations.count_documents(
                {"operation_id": "partial-index-refusal"}
            ) == 0
            assert await database.reader_segment_activation_state.count_documents(
                {"book_slug": "operation-id-second", "text_revocation": {"$exists": True}}
            ) == 0

            await database.reading_pass_text_revocation_operations.drop_index("operation_id_1")
            with pytest.raises(ReadingPassError) as unavailable:
                await server.reading_pass_service.revoke_text_publication(
                    book_slug="operation-id-second",
                    expected_activation_generation=1,
                    expected_segmentation_version=second["segmentation_version"],
                    expected_manifest_version=second["version"],
                    operation_id="schema-missing-operation-id",
                    reason="schema prerequisite fixture",
                    actor_id="fixture-admin",
                )
            assert unavailable.value.code == "REVOCATION_SCHEMA_UNAVAILABLE"
            assert await database.reader_segment_activation_state.count_documents(
                {"book_slug": "operation-id-second", "text_revocation": {"$exists": True}}
            ) == 0

    asyncio.run(scenario())


def test_revoked_current_version_archives_evidence_when_a_replacement_is_separately_promoted():
    async def scenario():
        async with _isolated_database() as database:
            slug = "replacement-publication-fixture"
            current = await _seed_retained_content(database, slug, version="fixture-v1")
            replacement_records = _records(slug, "fixture-v2")
            replacement = {
                "id": str(uuid.uuid4()), "book_slug": slug,
                "segmentation_version": "fixture-v2", "status": "prepared",
                "created_at": datetime.now(timezone.utc), **segment_manifest(replacement_records),
            }
            retained_records = _records(slug, "fixture-v0")
            retained = {
                "id": str(uuid.uuid4()), "book_slug": slug,
                "segmentation_version": "fixture-v0", "status": "archived",
                "created_at": datetime.now(timezone.utc), **segment_manifest(retained_records),
            }
            await database.reader_content_segments.insert_many([*replacement_records, *retained_records])
            await database.reader_segment_manifests.insert_many([replacement, retained])
            now = datetime.now(timezone.utc)
            old_token = "retained-publication-lease-token"
            await database.users.insert_many([
                {"id": USER["id"], "role": "user", "status": "active", "reading_seconds_balance": 300, "wallet_seconds": 300},
                {"id": "retained-user", "role": "user", "status": "active", "reading_seconds_balance": 300, "wallet_seconds": 300},
            ])
            # This pre-existing retained-version lease is deliberately bound
            # to v0, not to the version revoked below.  It must not be
            # reclassified merely because v1 is withdrawn and v2 is selected.
            await database.reading_pass_sessions.insert_one({
                "id": "retained-v0-session", "user_id": "retained-user", "auth_session_id": "retained-auth",
                "device_id": "retained-device", "content_type": "text", "content_id": slug,
                "status": "active", "active_lock": "retained-user", "billing_active": True,
                "lease_token_hash": token_fingerprint(old_token, server.READING_PASS_TOKEN_SECRET),
                "lease_version": 1, "lease_issued_at": now, "last_billed_at": now,
                "lease_expires_at": now.replace(year=now.year + 1), "last_sequence": 0,
                "scope": {"canonical_page_index": 4, "segmentation_version": "fixture-v0", "manifest_version": retained["version"], "authority_activation_generation": 0},
            })
            started = await server.reading_pass_service.start_session(
                user_id=USER["id"], auth_session_id=USER["session_id"], device_id="current-v1-device",
                device_label="Current publication fixture", content_type="text", content_id=slug,
                scope={"canonical_page_index": 4, "segmentation_version": "fixture-v1", "manifest_version": current["version"], "authority_activation_generation": 1},
            )
            await _revoke_bound_text(current, slug, operation_id="replace-revoked-v1")
            promoted = await server.admin_promote_reading_pass_segments(
                slug,
                server.ReadingPassSegmentPromotionIn(
                    target_segmentation_version="fixture-v2", expected_active_segmentation_version="fixture-v1",
                    expected_activation_generation=1, operation_id="promote-replacement-v2",
                ),
                {"email": "fixture@example.test"},
            )
            assert promoted["segmentation_version"] == "fixture-v2"
            state = await database.reader_segment_activation_state.find_one({"book_slug": slug}, {"_id": 0})
            assert state["active_segmentation_version"] == "fixture-v2"
            assert "text_revocation" not in state
            assert state["text_revocation_history"][0]["revocation"]["segmentation_version"] == "fixture-v1"
            # A new v2 lease is permitted through the new pointer; the old v1
            # lease remains terminal, while v0 is still a retained-version
            # session and remains authorizable under its own identity.
            replacement_start = await server.reading_pass_service.start_session(
                user_id=USER["id"], auth_session_id=USER["session_id"], device_id="replacement-v2-device",
                device_label="Replacement publication fixture", content_type="text", content_id=slug,
                scope={"canonical_page_index": 4, "segmentation_version": "fixture-v2", "manifest_version": replacement["version"], "authority_activation_generation": 2},
            )
            assert replacement_start["status"] == "Running"
            assert (await database.reading_pass_sessions.find_one({"id": started["session_id"]}, {"_id": 0}))["status"] == "revoked"
            retained_authorized = await server.reading_pass_service.authorize(
                user_id="retained-user", auth_session_id="retained-auth", session_id="retained-v0-session",
                lease_token=old_token, content_type="text", content_id=slug,
            )
            assert retained_authorized["scope"]["segmentation_version"] == "fixture-v0"
            # A lost revocation response must remain recoverable through the
            # ordinary admin handler after a later, separately permitted
            # promotion. Its durable operation result is historical evidence,
            # never fresh authority over the replacement publication.
            before_replay = {
                name: await _rows(database[name]) for name in (
                    "reader_segment_activation_state", "reading_pass_sessions",
                    "users", "wallet_ledger", "wallet_transactions", "reading_pass_audit",
                    "reading_pass_text_revocation_operations", "reader_segment_manifests",
                    "reader_segment_activation_operations",
                )
            }
            replay = await server.admin_revoke_reading_pass_text_publication(
                slug,
                server.ReadingPassTextPublicationRevocationIn(
                    expected_activation_generation=1,
                    expected_segmentation_version="fixture-v1",
                    expected_manifest_version=current["version"],
                    operation_id="replace-revoked-v1", reason="fixture withdrawal",
                ),
                {"id": "fixture-admin"},
            )
            assert replay["duplicate"] is True
            assert replay["segmentation_version"] == "fixture-v1"
            assert before_replay == {
                name: await _rows(database[name]) for name in before_replay
            }
            with pytest.raises(server.HTTPException) as revoked_rollback:
                await server.admin_promote_reading_pass_segments(
                    slug,
                    server.ReadingPassSegmentPromotionIn(
                        target_segmentation_version="fixture-v1", expected_active_segmentation_version="fixture-v2",
                        expected_activation_generation=2, operation_id="rollback-to-revoked-v1",
                    ),
                    {"email": "fixture@example.test"},
                )
            assert revoked_rollback.value.detail["code"] == "TEXT_PUBLICATION_ALREADY_REVOKED"
            assert before_replay == {
                name: await _rows(database[name]) for name in before_replay
            }
            with pytest.raises(server.HTTPException) as stale_new_operation:
                await server.admin_revoke_reading_pass_text_publication(
                    slug,
                    server.ReadingPassTextPublicationRevocationIn(
                        expected_activation_generation=1,
                        expected_segmentation_version="fixture-v1",
                        expected_manifest_version=current["version"],
                        operation_id="new-operation-against-old-pointer", reason="fixture withdrawal",
                    ),
                    {"id": "fixture-admin"},
                )
            assert stale_new_operation.value.detail["code"] == "STALE_PUBLICATION_AUTHORITY"
            assert before_replay == {
                name: await _rows(database[name]) for name in before_replay
            }

    asyncio.run(scenario())


def test_real_mongo_revocation_commits_after_renewal_read_and_forces_a_retry(monkeypatch):
    async def scenario():
        async with _isolated_database() as database:
            manifest = await _seed_retained_content(database, "race-fixture")
            started = await _start_bound_text_session(database, manifest, "race-fixture")
            began = datetime(2026, 1, 1, tzinfo=timezone.utc)
            cutoff = datetime(2026, 1, 1, 0, 0, 7, tzinfo=timezone.utc)
            await database.reading_pass_sessions.update_one(
                {"id": started["session_id"]},
                {"$set": {"last_billed_at": began, "lease_expires_at": began.replace(second=20)}},
            )
            monkeypatch.setattr("backend.reading_pass_service._now", lambda: cutoff)

            original_client = server.reading_pass_service.client

            class CountingClient:
                def __init__(self):
                    self.starts = 0

                async def start_session(self):
                    self.starts += 1
                    return await original_client.start_session()

            counter = CountingClient()
            server.reading_pass_service.client = counter
            renewal_read = asyncio.Event()
            release_renewal = asyncio.Event()
            original_current_revocation = server.reading_pass_service._current_text_revocation
            paused_once = True

            async def pause_after_unrevoked_read(content_id, mongo_session):
                nonlocal paused_once
                result = await original_current_revocation(content_id, mongo_session)
                if paused_once:
                    paused_once = False
                    renewal_read.set()
                    await release_renewal.wait()
                return result

            monkeypatch.setattr(server.reading_pass_service, "_current_text_revocation", pause_after_unrevoked_read)

            async def renew():
                try:
                    return await server.reading_pass_service.renew_lease(
                        user_id=USER["id"], auth_session_id=USER["session_id"], session_id=started["session_id"],
                        lease_token=started["lease_token"], lease_version=1, sequence=1,
                        idempotency_key="real-mongo-race-heartbeat", active=True,
                    )
                except ReadingPassError as error:
                    return error.code

            renewal = asyncio.create_task(renew())
            await renewal_read.wait()
            # The renewal owns an old snapshot but has not written.  Let the
            # revocation commit first, then release the delayed renewal write.
            # Mongo rejects that stale write and the service opens a fresh
            # transaction, where it observes the terminal lease.
            revoke = await _revoke_bound_text(manifest, "race-fixture", operation_id="real-mongo-race-revoke-first")
            release_renewal.set()
            renewal_outcome = await renewal
            session = await database.reading_pass_sessions.find_one({"id": started["session_id"]}, {"_id": 0})
            ledger = await _rows(database.wallet_ledger)
            user = await database.users.find_one({"id": USER["id"]}, {"_id": 0})
            assert session["status"] == "revoked"
            assert ensure_utc(session["billing_cutoff_at"]) == cutoff
            assert len(ledger) == 1
            assert ledger[0]["debit"] == 7
            assert user["reading_seconds_balance"] == 293
            assert revoke["deducted_seconds"] == 7
            assert renewal_outcome == "LEASE_EXPIRED"
            assert counter.starts >= 3  # renewal, revocation, retried renewal

    asyncio.run(scenario())


def test_real_mongo_renewal_commits_before_revocation_preserves_nonoverlapping_intervals(monkeypatch):
    async def scenario():
        async with _isolated_database() as database:
            manifest = await _seed_retained_content(database, "renew-before-revoke-fixture")
            started = await _start_bound_text_session(database, manifest, "renew-before-revoke-fixture")
            began = datetime(2026, 1, 1, tzinfo=timezone.utc)
            renew_at = datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc)
            cutoff = datetime(2026, 1, 1, 0, 0, 7, tzinfo=timezone.utc)
            await database.reading_pass_sessions.update_one(
                {"id": started["session_id"]},
                {"$set": {"last_billed_at": began, "lease_expires_at": began.replace(second=20)}},
            )
            monkeypatch.setattr("backend.reading_pass_service._now", lambda: renew_at)
            renewed = await server.reading_pass_service.renew_lease(
                user_id=USER["id"], auth_session_id=USER["session_id"], session_id=started["session_id"],
                lease_token=started["lease_token"], lease_version=1, sequence=1,
                idempotency_key="renew-before-revoke", active=True,
            )
            monkeypatch.setattr("backend.reading_pass_service._now", lambda: cutoff)
            revoked = await _revoke_bound_text(
                manifest, "renew-before-revoke-fixture", operation_id="real-mongo-race-renew-first"
            )
            ledger = await _rows(database.wallet_ledger)
            session = await database.reading_pass_sessions.find_one({"id": started["session_id"]}, {"_id": 0})
            assert renewed["deducted_seconds"] == 5
            assert revoked["deducted_seconds"] == 2
            assert sum(row["debit"] for row in ledger) == 7
            assert session["seconds_consumed"] == 7
            assert ensure_utc(session["billing_cutoff_at"]) == cutoff
            assert session["status"] == "revoked"

    asyncio.run(scenario())


def test_real_mongo_stop_revocation_orderings_preserve_one_interval_each(monkeypatch):
    async def conflict_ordering():
        async with _isolated_database() as database:
            manifest = await _seed_retained_content(database, "stop-race-fixture")
            started = await _start_bound_text_session(database, manifest, "stop-race-fixture")
            began = datetime(2026, 1, 1, tzinfo=timezone.utc)
            cutoff = datetime(2026, 1, 1, 0, 0, 6, tzinfo=timezone.utc)
            await database.reading_pass_sessions.update_one(
                {"id": started["session_id"]},
                {"$set": {"last_billed_at": began, "lease_expires_at": began.replace(second=20)}},
            )
            monkeypatch.setattr("backend.reading_pass_service._now", lambda: cutoff)
            original_client = server.reading_pass_service.client

            class CountingClient:
                def __init__(self):
                    self.starts = 0

                async def start_session(self):
                    self.starts += 1
                    return await original_client.start_session()

            counter = CountingClient()
            server.reading_pass_service.client = counter
            stop_ready = asyncio.Event()
            release_stop = asyncio.Event()
            original_settle = server.reading_pass_service._settle_terminal_session
            paused_once = True

            async def pause_stop_before_write(*, reason, **kwargs):
                nonlocal paused_once
                if reason == "user_end" and paused_once:
                    paused_once = False
                    stop_ready.set()
                    await release_stop.wait()
                return await original_settle(reason=reason, **kwargs)

            monkeypatch.setattr(server.reading_pass_service, "_settle_terminal_session", pause_stop_before_write)
            stop = asyncio.create_task(server.reading_pass_service.end_session(
                user_id=USER["id"], auth_session_id=USER["session_id"], session_id=started["session_id"]
            ))
            await stop_ready.wait()
            revoked = await _revoke_bound_text(manifest, "stop-race-fixture", operation_id="stop-race-revoke-first")
            release_stop.set()
            stopped = await stop
            ledger = await _rows(database.wallet_ledger)
            session = await database.reading_pass_sessions.find_one({"id": started["session_id"]}, {"_id": 0})
            assert revoked["deducted_seconds"] == 6
            assert stopped == {"ended": False, "session_id": started["session_id"], "deducted_seconds": 0}
            assert sum(row["debit"] for row in ledger) == 6
            assert session["status"] == "revoked"
            assert counter.starts >= 3

    async def stop_first_ordering():
        async with _isolated_database() as database:
            manifest = await _seed_retained_content(database, "stop-before-revoke-fixture")
            started = await _start_bound_text_session(database, manifest, "stop-before-revoke-fixture")
            began = datetime(2026, 1, 1, tzinfo=timezone.utc)
            stop_at = datetime(2026, 1, 1, 0, 0, 4, tzinfo=timezone.utc)
            cutoff = datetime(2026, 1, 1, 0, 0, 6, tzinfo=timezone.utc)
            await database.reading_pass_sessions.update_one(
                {"id": started["session_id"]},
                {"$set": {"last_billed_at": began, "lease_expires_at": began.replace(second=20)}},
            )
            monkeypatch.setattr("backend.reading_pass_service._now", lambda: stop_at)
            stopped = await server.reading_pass_service.end_session(
                user_id=USER["id"], auth_session_id=USER["session_id"], session_id=started["session_id"]
            )
            monkeypatch.setattr("backend.reading_pass_service._now", lambda: cutoff)
            revoked = await _revoke_bound_text(
                manifest, "stop-before-revoke-fixture", operation_id="stop-race-stop-first"
            )
            ledger = await _rows(database.wallet_ledger)
            session = await database.reading_pass_sessions.find_one({"id": started["session_id"]}, {"_id": 0})
            assert stopped["deducted_seconds"] == 4
            assert revoked["deducted_seconds"] == 0
            assert sum(row["debit"] for row in ledger) == 4
            assert session["status"] == "ended"

    asyncio.run(conflict_ordering())
    asyncio.run(stop_first_ordering())


def test_real_mongo_committed_revocation_with_delayed_unknown_response_retries_only_commit(monkeypatch):
    """Inject a lost acknowledgement after Mongo commits, not a fake commit."""
    async def scenario():
        from pymongo.errors import OperationFailure

        async with _isolated_database() as database:
            slug = "delayed-commit-fixture"
            manifest = await _seed_retained_content(database, slug)
            started = await _start_bound_text_session(database, manifest, slug)
            began = datetime(2026, 1, 1, tzinfo=timezone.utc)
            cutoff = began.replace(second=7)
            await database.reading_pass_sessions.update_one(
                {"id": started["session_id"]},
                {"$set": {"last_billed_at": began, "lease_expires_at": began.replace(second=20)}},
            )
            monkeypatch.setattr("backend.reading_pass_service._now", lambda: cutoff)
            committed = asyncio.Event()
            release_response = asyncio.Event()
            original_client = server.reading_pass_service.client

            class DelayedAcknowledgementClient:
                sessions = 0
                commit_calls = 0

                async def start_session(self):
                    self.sessions += 1
                    session = await original_client.start_session()
                    if self.sessions == 1:
                        original_commit = session.commit_transaction

                        async def delayed_commit():
                            self.commit_calls += 1
                            await original_commit()
                            if self.commit_calls == 1:
                                committed.set()
                                await asyncio.wait_for(release_response.wait(), timeout=5)
                                raise OperationFailure(
                                    "isolated lost commit acknowledgement", code=91,
                                    details={"errorLabels": ["UnknownTransactionCommitResult"]},
                                )

                        monkeypatch.setattr(session, "commit_transaction", delayed_commit)
                    return session

            observed = DelayedAcknowledgementClient()
            server.reading_pass_service.client = observed
            task = asyncio.create_task(_revoke_bound_text(
                manifest, slug, operation_id="delayed-committed-revocation"
            ))
            try:
                await asyncio.wait_for(committed.wait(), timeout=5)
                assert not task.done()
                persisted = await database.reading_pass_text_revocation_operations.find_one(
                    {"operation_id": "delayed-committed-revocation"}, {"_id": 0}
                )
                assert persisted["result"]["deducted_seconds"] == 7
                assert await database.wallet_ledger.count_documents({}) == 1
                monkeypatch.setattr("backend.reading_pass_service._now", lambda: began.replace(second=9))
                with pytest.raises(ReadingPassError) as renewal:
                    await server.reading_pass_service.renew_lease(
                        user_id=USER["id"], auth_session_id=USER["session_id"],
                        session_id=started["session_id"], lease_token=started["lease_token"],
                        lease_version=1, sequence=1, idempotency_key="delayed-revoke-renewal", active=True,
                    )
                assert renewal.value.code == "LEASE_EXPIRED"
            finally:
                release_response.set()
                result = await asyncio.wait_for(task, timeout=5)
            assert observed.commit_calls == 2
            assert result["cutoff_at"] == cutoff.isoformat()
            assert result["deducted_seconds"] == 7
            assert await database.reading_pass_text_revocation_operations.count_documents({}) == 1
            assert await database.wallet_ledger.count_documents({}) == 1
            assert await database.wallet_transactions.count_documents({}) == 1
            session = await database.reading_pass_sessions.find_one({"id": started["session_id"]})
            user = await database.users.find_one({"id": USER["id"]})
            assert session["seconds_consumed"] == 7
            assert user["reading_seconds_balance"] == user["wallet_seconds"] == 293
            assert ensure_utc(session["billing_cutoff_at"]) == cutoff

    asyncio.run(scenario())
