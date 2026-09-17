"""Replica-set integration coverage for versioned Reader publication promotion.

These tests are intentionally opt-in.  The release gate enables them only
after it has started and verified its loopback MongoDB replica set.  They use
the real Motor driver and a unique disposable namespace; the model tests in
``test_reader_segment_promotion_safeguards.py`` remain separate coverage.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace
from urllib.parse import urlparse
import uuid

import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.requests import Request
from starlette.responses import Response

os.environ.setdefault("JWT_SECRET", "reader-segment-mongo-integration-secret")
os.environ.setdefault("READING_PASS_TOKEN_SECRET", "reader-segment-mongo-integration-token-secret-0123456789")
os.environ.setdefault("READING_PASS_V2_ENABLED", "true")

from backend import server
from backend.api.schemas import ReadingPassPositionIn
from backend.domain.reading_pass import canonical_page_records, segment_manifest, token_fingerprint
from backend.reading_pass_service import ReadingPassService


pytestmark = pytest.mark.skipif(
    os.environ.get("READER_SEGMENT_MONGO_INTEGRATION") != "1",
    reason="requires the release gate's explicit isolated MongoDB replica set",
)


def _mongo_uri() -> str:
    uri = os.environ.get("MONGODB_URL", "")
    parsed = urlparse(uri)
    if parsed.hostname not in {"127.0.0.1", "localhost"} or "replicaSet=" not in uri:
        raise RuntimeError("reader segment Mongo integration requires an explicit loopback replica-set MONGODB_URL")
    return uri


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


async def _seed_title(database, slug: str, *, pointed: bool = True) -> dict:
    versions = ("canonical-fixture-v1", "canonical-fixture-v2")
    manifests = []
    for index, version in enumerate(versions):
        records = _records(slug, version)
        manifest = {
            "id": str(uuid.uuid4()),
            "book_slug": slug,
            "segmentation_version": version,
            "status": "active" if pointed and index == 0 else "prepared",
            "created_at": datetime.now(timezone.utc),
            **segment_manifest(records),
        }
        await database.reader_content_segments.insert_many(records)
        manifests.append(manifest)
    await database.reader_segment_manifests.insert_many(manifests)
    if pointed:
        await database.reader_segment_activation_state.insert_one({
            "book_slug": slug,
            "active_segmentation_version": versions[0],
            "generation": 0,
            "created_at": datetime.now(timezone.utc),
        })
    return {version: manifest for version, manifest in zip(versions, manifests)}


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
    await database.reading_pass_positions.create_index(
        [("user_id", 1), ("content_type", 1), ("content_id", 1)], unique=True
    )


@asynccontextmanager
async def _isolated_database():
    uri = _mongo_uri()
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5_000)
    hello = await client.admin.command("hello")
    if not hello.get("isWritablePrimary") or not hello.get("setName"):
        client.close()
        raise RuntimeError("reader segment Mongo integration requires a writable replica-set primary")
    # MongoDB database names are capped at 63 bytes; retain a clear test-only
    # prefix while leaving ample unique entropy for concurrent CI jobs.
    namespace = f"rpseg_it_{uuid.uuid4().hex}"
    database = client[namespace]
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
        await client.drop_database(namespace)
        server.db, server.client, server.reading_pass_service = previous_db, previous_client, previous_service
        client.close()


def _promotion(target: str, expected: str, generation: int, operation_id: str):
    return server.ReadingPassSegmentPromotionIn(
        target_segmentation_version=target,
        expected_active_segmentation_version=expected,
        expected_activation_generation=generation,
        operation_id=operation_id,
    )


async def _http_code(coro):
    try:
        return "result", await coro
    except server.HTTPException as exc:
        return "http", exc.detail["code"]


def test_real_mongo_rejects_cross_title_and_cross_kind_replay_and_recovers_same_intent():
    async def scenario():
        async with _isolated_database() as database:
            await _seed_title(database, "fixture-book-a")
            await _seed_title(database, "fixture-book-b")
            payload = _promotion("canonical-fixture-v2", "canonical-fixture-v1", 0, "mongo-cross-title-promote")
            first = await server.admin_promote_reading_pass_segments("fixture-book-a", payload, {"email": "fixture@example.test"})
            retry = await server.admin_promote_reading_pass_segments("fixture-book-a", payload, {"email": "fixture@example.test"})
            assert retry == first
            kind, cross_title = await _http_code(
                server.admin_promote_reading_pass_segments("fixture-book-b", payload, {"email": "fixture@example.test"})
            )
            assert (kind, cross_title) == ("http", "ACTIVATION_OPERATION_INTENT_CONFLICT")
            kind, cross_kind = await _http_code(
                server.admin_bootstrap_reading_pass_segments(
                    "fixture-book-b",
                    server.ReadingPassSegmentBootstrapIn(
                        target_segmentation_version="canonical-fixture-v2", operation_id="mongo-cross-title-promote"
                    ),
                    {"email": "fixture@example.test"},
                )
            )
            assert (kind, cross_kind) == ("http", "ACTIVATION_OPERATION_INTENT_CONFLICT")
            state_a = await database.reader_segment_activation_state.find_one({"book_slug": "fixture-book-a"}, {"_id": 0})
            state_b = await database.reader_segment_activation_state.find_one({"book_slug": "fixture-book-b"}, {"_id": 0})
            assert state_a["active_segmentation_version"] == "canonical-fixture-v2"
            assert state_b["active_segmentation_version"] == "canonical-fixture-v1"
            assert await database.reading_pass_audit.count_documents({"book_slug": "fixture-book-b"}) == 0
            assert await database.reader_segment_activation_operations.count_documents({}) == 1

    asyncio.run(scenario())


def test_real_mongo_serializes_concurrent_promoters_retries_bootstraps_and_stale_rollback(monkeypatch):
    async def scenario():
        async with _isolated_database() as database:
            await _seed_title(database, "fixture-book")
            original_runner = server._run_reader_segment_activation_transaction
            barrier = asyncio.Barrier(2)
            seen_tasks = set()

            async def coordinated_runner(callback, **kwargs):
                async def coordinated(session):
                    task = id(asyncio.current_task())
                    if task not in seen_tasks:
                        seen_tasks.add(task)
                        await barrier.wait()
                    return await callback(session)
                return await original_runner(coordinated, **kwargs)

            monkeypatch.setattr(server, "_run_reader_segment_activation_transaction", coordinated_runner)
            first = _promotion("canonical-fixture-v2", "canonical-fixture-v1", 0, "mongo-concurrent-promote-a")
            second = _promotion("canonical-fixture-v2", "canonical-fixture-v1", 0, "mongo-concurrent-promote-b")
            outcomes = await asyncio.gather(
                _http_code(server.admin_promote_reading_pass_segments("fixture-book", first, {"email": "fixture@example.test"})),
                _http_code(server.admin_promote_reading_pass_segments("fixture-book", second, {"email": "fixture@example.test"})),
            )
            assert sorted(kind for kind, _value in outcomes) == ["http", "result"]
            assert next(value for kind, value in outcomes if kind == "http") == "STALE_ACTIVE_SEGMENT_VERSION"
            state = await database.reader_segment_activation_state.find_one({"book_slug": "fixture-book"}, {"_id": 0})
            assert state["active_segmentation_version"] == "canonical-fixture-v2"
            assert state["generation"] == 1

            # A pair of same-ID retries is allowed to recover one durable result,
            # not to perform two state transitions.
            winning_operation_id = next(value for kind, value in outcomes if kind == "result")["operation_id"]
            winning_payload = first if winning_operation_id == first.operation_id else second
            retry_outcomes = await asyncio.gather(
                _http_code(server.admin_promote_reading_pass_segments(
                    "fixture-book",
                    winning_payload,
                    {"email": "fixture@example.test"},
                )),
                _http_code(server.admin_promote_reading_pass_segments(
                    "fixture-book",
                    winning_payload,
                    {"email": "fixture@example.test"},
                )),
            )
            assert retry_outcomes[0] == retry_outcomes[1]
            assert retry_outcomes[0][0] == "result"

            # These two requests begin before either can see the durable
            # operation record.  The global operation-id index may therefore
            # reject one final insert; that loser must recover the exact same
            # result rather than leak a duplicate-key error or transition twice.
            await _seed_title(database, "same-id-book")
            same_id_payload = _promotion(
                "canonical-fixture-v2", "canonical-fixture-v1", 0, "mongo-concurrent-same-id"
            )
            same_id_outcomes = await asyncio.gather(
                _http_code(server.admin_promote_reading_pass_segments(
                    "same-id-book", same_id_payload, {"email": "fixture@example.test"}
                )),
                _http_code(server.admin_promote_reading_pass_segments(
                    "same-id-book", same_id_payload, {"email": "fixture@example.test"}
                )),
            )
            assert [kind for kind, _value in same_id_outcomes] == ["result", "result"]
            assert same_id_outcomes[0][1] == same_id_outcomes[1][1]
            same_id_state = await database.reader_segment_activation_state.find_one(
                {"book_slug": "same-id-book"}, {"_id": 0}
            )
            assert same_id_state["generation"] == 1
            assert await database.reader_segment_activation_operations.count_documents(
                {"operation_id": "mongo-concurrent-same-id"}
            ) == 1

            monkeypatch.setattr(server, "_run_reader_segment_activation_transaction", original_runner)
            rollback = await server.admin_promote_reading_pass_segments(
                "fixture-book", _promotion("canonical-fixture-v1", "canonical-fixture-v2", 1, "mongo-rollback"), {"email": "fixture@example.test"}
            )
            assert rollback["activation_generation"] == 2
            kind, stale = await _http_code(
                server.admin_promote_reading_pass_segments(
                    "fixture-book", _promotion("canonical-fixture-v2", "canonical-fixture-v1", 1, "mongo-stale-after-rollback"), {"email": "fixture@example.test"}
                )
            )
            assert (kind, stale) == ("http", "STALE_ACTIVE_SEGMENT_VERSION")

            await _seed_title(database, "bootstrap-book", pointed=False)
            bootstrap_barrier = asyncio.Barrier(2)
            bootstrap_seen = set()

            async def bootstrap_runner(callback, **kwargs):
                async def coordinated(session):
                    task = id(asyncio.current_task())
                    if task not in bootstrap_seen:
                        bootstrap_seen.add(task)
                        await bootstrap_barrier.wait()
                    return await callback(session)
                return await original_runner(coordinated, **kwargs)

            monkeypatch.setattr(server, "_run_reader_segment_activation_transaction", bootstrap_runner)
            bootstrap_outcomes = await asyncio.gather(
                _http_code(server.admin_bootstrap_reading_pass_segments("bootstrap-book", server.ReadingPassSegmentBootstrapIn(target_segmentation_version="canonical-fixture-v2", operation_id="mongo-bootstrap-a"), {"email": "fixture@example.test"})),
                _http_code(server.admin_bootstrap_reading_pass_segments("bootstrap-book", server.ReadingPassSegmentBootstrapIn(target_segmentation_version="canonical-fixture-v2", operation_id="mongo-bootstrap-b"), {"email": "fixture@example.test"})),
            )
            assert sorted(kind for kind, _value in bootstrap_outcomes) == ["http", "result"]
            assert next(value for kind, value in bootstrap_outcomes if kind == "http") == "ACTIVE_SEGMENT_VERSION_EXISTS"

    asyncio.run(scenario())


def test_real_mongo_aborts_intermediate_write_and_retains_bound_session_page_and_position(monkeypatch):
    async def scenario():
        async with _isolated_database() as database:
            manifests = await _seed_title(database, "fixture-book")
            original_record = server._record_reader_segment_activation_operation

            async def fail_after_audit(_document, *, mongo_session):
                raise RuntimeError("injected-after-audit-before-operation-record")

            monkeypatch.setattr(server, "_record_reader_segment_activation_operation", fail_after_audit)
            payload = _promotion("canonical-fixture-v2", "canonical-fixture-v1", 0, "mongo-atomic-abort")
            with pytest.raises(RuntimeError, match="injected-after-audit"):
                await server.admin_promote_reading_pass_segments("fixture-book", payload, {"email": "fixture@example.test"})
            state = await database.reader_segment_activation_state.find_one({"book_slug": "fixture-book"}, {"_id": 0})
            assert state["active_segmentation_version"] == "canonical-fixture-v1"
            assert state["generation"] == 0
            assert await database.reading_pass_audit.count_documents({}) == 0
            assert await database.reader_segment_activation_operations.count_documents({}) == 0
            active = await database.reader_segment_manifests.find_one({"book_slug": "fixture-book", "status": "active"}, {"_id": 0})
            assert active["segmentation_version"] == "canonical-fixture-v1"

            # This is deliberately injected response loss after a real MongoDB
            # commit, not an observed database transport failure.
            monkeypatch.setattr(server, "_record_reader_segment_activation_operation", original_record)
            original_runner = server._run_reader_segment_activation_transaction
            lost_once = True

            async def lose_committed_response(callback, **kwargs):
                nonlocal lost_once
                result = await original_runner(callback, **kwargs)
                if lost_once:
                    lost_once = False
                    raise RuntimeError("injected-response-lost-after-commit")
                return result

            monkeypatch.setattr(server, "_run_reader_segment_activation_transaction", lose_committed_response)
            recovery_payload = _promotion("canonical-fixture-v2", "canonical-fixture-v1", 0, "mongo-lost-response")
            with pytest.raises(RuntimeError, match="injected-response-lost-after-commit"):
                await server.admin_promote_reading_pass_segments("fixture-book", recovery_payload, {"email": "fixture@example.test"})
            monkeypatch.setattr(server, "_run_reader_segment_activation_transaction", original_runner)
            recovered = await server.admin_promote_reading_pass_segments("fixture-book", recovery_payload, {"email": "fixture@example.test"})
            assert recovered["segmentation_version"] == "canonical-fixture-v2"
            assert await database.reader_segment_activation_operations.count_documents({"operation_id": "mongo-lost-response"}) == 1

            # A session and position explicitly bound to the retained v1
            # publication remain coherent after v2 becomes active.
            old_manifest = manifests["canonical-fixture-v1"]
            now = datetime.now(timezone.utc)
            lease_token = "fixture-lease-token"
            await database.users.insert_one({"id": "fixture-user", "role": "user", "status": "active", "reading_seconds_balance": 300, "wallet_seconds": 300})
            await database.user_sessions.insert_one({"id": "fixture-auth", "user_id": "fixture-user", "status": "active", "idle_expires_at": now + timedelta(minutes=5), "absolute_expires_at": now + timedelta(minutes=5)})
            await database.reading_pass_sessions.insert_one({
                "id": "fixture-metered", "user_id": "fixture-user", "auth_session_id": "fixture-auth", "status": "active",
                "content_type": "text", "content_id": "fixture-book", "lease_token_hash": token_fingerprint(lease_token, server.READING_PASS_TOKEN_SECRET),
                "lease_expires_at": now + timedelta(minutes=5),
                "scope": {"segmentation_version": "canonical-fixture-v1", "manifest_version": old_manifest["version"]},
            })

            async def fixture_book(_slug):
                return {"slug": "fixture-book", "chapters": [{"id": "chapter-001", "title": "Fixture", "order": 1}]}

            monkeypatch.setattr(server, "_reader_book_access_doc", fixture_book)
            request = Request({"type": "http", "headers": [(b"x-reading-pass-session", b"fixture-metered"), (b"x-reading-pass-lease", lease_token.encode())]})
            page = await server.reading_pass_book_page("fixture-book", 4, request, Response(), {"id": "fixture-user", "role": "user", "status": "active", "session_id": "fixture-auth"})
            assert page["segmentation_version"] == "canonical-fixture-v1"
            saved = await server.reading_pass_save_position(
                ReadingPassPositionIn(
                    content_type="text", content_id="fixture-book", position={"canonical_page_index": 4, "chapter_id": page["chapter_id"]}, version=0,
                    publication_segmentation_version="canonical-fixture-v1", publication_manifest_version=old_manifest["version"],
                ),
                {"id": "fixture-user"},
            )
            assert saved["position"]["segmentation_version"] == "canonical-fixture-v1"
            position = await server.reading_pass_get_position("text", "fixture-book", {"id": "fixture-user"})
            assert position["publication_version_compatibility"] == "retained_nonactive"

    asyncio.run(scenario())
