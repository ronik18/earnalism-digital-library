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
    await database.reading_pass_text_revocation_operations.create_index("operation_id", unique=True)
    await database.users.create_index("id", unique=True)
    await database.reading_pass_sessions.create_index("active_lock", unique=True, sparse=True)
    await database.reading_pass_sessions.create_index("id", unique=True)
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


def test_real_handler_uses_actual_reader_authority_and_binds_the_canonical_identity():
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


def test_real_handler_rejects_authorized_title_without_an_active_canonical_page_before_session_start(monkeypatch):
    async def scenario():
        async with _isolated_database() as database:
            await database.users.insert_one({
                "id": USER["id"], "role": "user", "status": "active",
                "reading_seconds_balance": 300, "wallet_seconds": 300,
            })
            # Dracula is current Reader authority, but this disposable
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


@pytest.mark.parametrize("first", ["renew", "revoke"])
def test_real_mongo_renewal_revocation_race_has_one_debit_and_no_running_replay(monkeypatch, first):
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

            async def renew():
                try:
                    return await server.reading_pass_service.renew_lease(
                        user_id=USER["id"], auth_session_id=USER["session_id"], session_id=started["session_id"],
                        lease_token=started["lease_token"], lease_version=1, sequence=1,
                        idempotency_key="real-mongo-race-heartbeat", active=True,
                    )
                except ReadingPassError as error:
                    return error.code

            revoke = _revoke_bound_text(manifest, "race-fixture", operation_id=f"real-mongo-race-{first}-0001")
            outcomes = await asyncio.gather(*( [renew(), revoke] if first == "renew" else [revoke, renew()] ))
            session = await database.reading_pass_sessions.find_one({"id": started["session_id"]}, {"_id": 0})
            ledger = await _rows(database.wallet_ledger)
            user = await database.users.find_one({"id": USER["id"]}, {"_id": 0})
            assert session["status"] == "revoked"
            assert ensure_utc(session["billing_cutoff_at"]) == cutoff
            assert len(ledger) == 1
            assert ledger[0]["debit"] == 7
            assert user["reading_seconds_balance"] == 293
            assert any(isinstance(outcome, dict) or outcome in {"LEASE_EXPIRED", "CONTENT_REVOKED"} for outcome in outcomes)

    asyncio.run(scenario())
