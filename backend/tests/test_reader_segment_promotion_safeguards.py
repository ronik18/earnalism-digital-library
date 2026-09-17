from __future__ import annotations

import asyncio
import copy
import hashlib
import os
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "reader-segment-promotion-test-secret")

from backend import server
from backend.domain.reading_pass import canonical_page_records, segment_manifest


def _value(document, path):
    value = document
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _matches(document, query):
    for key, expected in query.items():
        actual = _value(document, key)
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]:
                return False
        elif actual != expected:
            return False
    return True


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, key, direction):
        self.rows.sort(key=lambda row: row.get(key), reverse=direction < 0)
        return self

    async def to_list(self, _limit):
        return copy.deepcopy(self.rows)


class Collection:
    def __init__(self, rows=()):
        self.rows = copy.deepcopy(list(rows))

    async def find_one(self, query, _projection=None, **_kwargs):
        row = next((row for row in self.rows if _matches(row, query)), None)
        return copy.deepcopy(row) if row else None

    def find(self, query, _projection=None, **_kwargs):
        return Cursor([copy.deepcopy(row) for row in self.rows if _matches(row, query)])

    async def insert_one(self, document, **_kwargs):
        self.rows.append(copy.deepcopy(document))
        return SimpleNamespace(inserted_id=document.get("id"))

    async def update_one(self, query, update, upsert=False, **_kwargs):
        row = next((row for row in self.rows if _matches(row, query)), None)
        inserted = False
        if row is None and upsert:
            row = {key: copy.deepcopy(value) for key, value in query.items() if not isinstance(value, dict)}
            self.rows.append(row)
            inserted = True
        if row is None:
            return SimpleNamespace(modified_count=0, matched_count=0)
        changed = False
        for key, value in update.get("$set", {}).items():
            if row.get(key) != value:
                row[key] = copy.deepcopy(value)
                changed = True
        if inserted:
            for key, value in update.get("$setOnInsert", {}).items():
                row[key] = copy.deepcopy(value)
                changed = True
        return SimpleNamespace(modified_count=int(changed), matched_count=1)


class Transaction:
    def __init__(self, lock):
        self.lock = lock

    async def __aenter__(self):
        await self.lock.acquire()
        return self

    async def __aexit__(self, *_args):
        self.lock.release()


class Session:
    def __init__(self, lock):
        self.lock = lock

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def start_transaction(self):
        return Transaction(self.lock)


class Client:
    def __init__(self):
        self.lock = asyncio.Lock()

    async def start_session(self):
        return Session(self.lock)


class UnknownCommitTransaction(Transaction):
    def __init__(self, lock, client):
        super().__init__(lock)
        self.client = client

    async def __aexit__(self, *_args):
        self.lock.release()
        if self.client.unknown_once:
            self.client.unknown_once = False
            raise RuntimeError("UnknownTransactionCommitResult")


class UnknownCommitSession(Session):
    def __init__(self, lock, client):
        super().__init__(lock)
        self.client = client

    def start_transaction(self):
        return UnknownCommitTransaction(self.lock, self.client)


class UnknownCommitClient(Client):
    def __init__(self):
        super().__init__()
        self.unknown_once = True

    async def start_session(self):
        return UnknownCommitSession(self.lock, self)


@dataclass
class Database:
    reader_content_segments: Collection
    reader_segment_manifests: Collection
    reader_segment_activation_state: Collection
    reader_segment_activation_operations: Collection
    reading_pass_audit: Collection


def _versioned_records(version):
    return canonical_page_records(
        book_slug="fixture-book",
        segmentation_version=version,
        target_characters=800,
        chapters=[{"id": "chapter-001", "title": "One", "order": 1, "content": "<p>" + "word " * 1500 + "</p>"}],
    )


def _manifest(version, status):
    records = _versioned_records(version)
    return {"book_slug": "fixture-book", "segmentation_version": version, "status": status, **segment_manifest(records)}


def _database():
    old_version, next_version = "canonical-fixture-v1", "canonical-fixture-v2"
    return Database(
        reader_content_segments=Collection(_versioned_records(old_version) + _versioned_records(next_version)),
        reader_segment_manifests=Collection([_manifest(old_version, "active"), _manifest(next_version, "prepared")]),
        reader_segment_activation_state=Collection([{
            "book_slug": "fixture-book",
            "active_segmentation_version": old_version,
            "generation": 0,
        }]),
        reader_segment_activation_operations=Collection(),
        reading_pass_audit=Collection(),
    )


def _add_matching_title(database, slug, *, pointed=True):
    """Add a second independent immutable fixture title to the model store."""
    source = _database()
    for collection_name in (
        "reader_content_segments",
        "reader_segment_manifests",
        "reader_segment_activation_state",
    ):
        if not pointed and collection_name == "reader_segment_activation_state":
            continue
        destination = getattr(database, collection_name).rows
        for row in getattr(source, collection_name).rows:
            clone = copy.deepcopy(row)
            clone["book_slug"] = slug
            destination.append(clone)
    if not pointed:
        database.reader_segment_manifests.rows = [
            {**row, "status": "prepared"} if row["book_slug"] == slug else row
            for row in database.reader_segment_manifests.rows
        ]


def _payload(target, expected, generation, operation_id):
    return server.ReadingPassSegmentPromotionIn(
        target_segmentation_version=target,
        expected_active_segmentation_version=expected,
        expected_activation_generation=generation,
        operation_id=operation_id,
    )


def test_promotion_is_idempotent_and_stale_requests_cannot_mutate_active_pointer(monkeypatch):
    async def scenario():
        database = _database()
        monkeypatch.setattr(server, "db", database)
        monkeypatch.setattr(server, "client", Client())
        first = _payload("canonical-fixture-v2", "canonical-fixture-v1", 0, "operation-promote-v2")
        before = await server.admin_reading_pass_active_segments("fixture-book", {"email": "fixture@example.test"})
        assert before["segmentation_version"] == "canonical-fixture-v1"
        assert before["activation_generation"] == 0

        # The deterministic transaction lock makes this a real interleaving:
        # one request wins and the other observes the new generation.
        winner, stale = await asyncio.gather(
            server.admin_promote_reading_pass_segments("fixture-book", first, {"email": "fixture@example.test"}),
            _expect_http_conflict(server.admin_promote_reading_pass_segments(
                "fixture-book", _payload("canonical-fixture-v2", "canonical-fixture-v1", 0, "operation-stale-v2"), {"email": "fixture@example.test"}
            )),
        )
        assert winner["segmentation_version"] == "canonical-fixture-v2"
        assert stale.detail["code"] == "STALE_ACTIVE_SEGMENT_VERSION"
        assert (await server.admin_promote_reading_pass_segments("fixture-book", first, {"email": "fixture@example.test"})) == winner
        assert len(database.reading_pass_audit.rows) == 1
        assert database.reader_segment_activation_state.rows[0]["active_segmentation_version"] == "canonical-fixture-v2"
        assert database.reader_segment_activation_state.rows[0]["generation"] == 1
        assert [row["segmentation_version"] for row in database.reader_segment_manifests.rows if row["status"] == "active"] == ["canonical-fixture-v2"]
        after = await server.admin_reading_pass_active_segments("fixture-book", {"email": "fixture@example.test"})
        assert after["segmentation_version"] == "canonical-fixture-v2"
        assert after["activation_generation"] == 1

        rollback = await server.admin_promote_reading_pass_segments(
            "fixture-book", _payload("canonical-fixture-v1", "canonical-fixture-v2", 1, "operation-rollback-v1"), {"email": "fixture@example.test"}
        )
        assert rollback["segmentation_version"] == "canonical-fixture-v1"
        assert rollback["activation_generation"] == 2
        assert [row["segmentation_version"] for row in database.reader_segment_manifests.rows if row["status"] == "active"] == ["canonical-fixture-v1"]

    asyncio.run(scenario())


def test_unknown_commit_is_recovered_only_by_retrying_the_same_operation_id(monkeypatch):
    async def scenario():
        database = _database()
        operation = _payload("canonical-fixture-v2", "canonical-fixture-v1", 0, "operation-uncertain-commit")
        monkeypatch.setattr(server, "db", database)
        monkeypatch.setattr(server, "client", UnknownCommitClient())
        with pytest.raises(RuntimeError, match="UnknownTransactionCommitResult"):
            await server.admin_promote_reading_pass_segments("fixture-book", operation, {"email": "fixture@example.test"})
        assert len(database.reader_segment_activation_operations.rows) == 1
        # The caller never guesses whether the commit applied and never rotates
        # the publication again: the same operation ID returns its durable result.
        recovered = await server.admin_promote_reading_pass_segments("fixture-book", operation, {"email": "fixture@example.test"})
        assert recovered["segmentation_version"] == "canonical-fixture-v2"
        assert len(database.reading_pass_audit.rows) == 1
        assert database.reader_segment_activation_state.rows[0]["generation"] == 1

    asyncio.run(scenario())


def test_explicit_bootstrap_only_initializes_an_unpointed_prepared_candidate(monkeypatch):
    async def scenario():
        database = _database()
        database.reader_content_segments.rows = [
            row for row in database.reader_content_segments.rows
            if row["segmentation_version"] == "canonical-fixture-v2"
        ]
        database.reader_segment_manifests.rows = [_manifest("canonical-fixture-v2", "prepared")]
        database.reader_segment_activation_state.rows = []
        monkeypatch.setattr(server, "db", database)
        monkeypatch.setattr(server, "client", Client())
        payload = server.ReadingPassSegmentBootstrapIn(
            target_segmentation_version="canonical-fixture-v2",
            operation_id="operation-bootstrap-v2",
        )
        first = await server.admin_bootstrap_reading_pass_segments("fixture-book", payload, {"email": "fixture@example.test"})
        assert first["bootstrap"] is True
        assert first["activation_generation"] == 1
        assert await server.admin_bootstrap_reading_pass_segments("fixture-book", payload, {"email": "fixture@example.test"}) == first
        with pytest.raises(server.HTTPException) as second:
            await server.admin_bootstrap_reading_pass_segments(
                "fixture-book",
                server.ReadingPassSegmentBootstrapIn(
                    target_segmentation_version="canonical-fixture-v2",
                    operation_id="operation-bootstrap-again",
                ),
                {"email": "fixture@example.test"},
            )
        assert second.value.detail["code"] == "ACTIVE_SEGMENT_VERSION_EXISTS"
        assert len(database.reading_pass_audit.rows) == 1
        assert [row["segmentation_version"] for row in database.reader_segment_manifests.rows if row["status"] == "active"] == ["canonical-fixture-v2"]

    asyncio.run(scenario())


def test_operation_identity_rejects_cross_title_or_cross_kind_replay(monkeypatch):
    async def scenario():
        database = _database()
        _add_matching_title(database, "fixture-book-b")
        monkeypatch.setattr(server, "db", database)
        monkeypatch.setattr(server, "client", Client())
        operation = _payload("canonical-fixture-v2", "canonical-fixture-v1", 0, "operation-cross-title-promote")
        winner = await server.admin_promote_reading_pass_segments("fixture-book", operation, {"email": "fixture@example.test"})
        assert await server.admin_promote_reading_pass_segments("fixture-book", operation, {"email": "fixture@example.test"}) == winner
        with pytest.raises(server.HTTPException) as cross_title:
            await server.admin_promote_reading_pass_segments("fixture-book-b", operation, {"email": "fixture@example.test"})
        assert cross_title.value.detail["code"] == "ACTIVATION_OPERATION_INTENT_CONFLICT"
        state_b = await server.admin_reading_pass_active_segments("fixture-book-b", {"email": "fixture@example.test"})
        assert state_b["segmentation_version"] == "canonical-fixture-v1"
        assert len(database.reader_segment_activation_operations.rows) == 1
        assert len(database.reading_pass_audit.rows) == 1
        with pytest.raises(server.HTTPException) as changed_intent:
            await server.admin_promote_reading_pass_segments(
                "fixture-book",
                _payload("canonical-fixture-v1", "canonical-fixture-v2", 1, "operation-cross-title-promote"),
                {"email": "fixture@example.test"},
            )
        assert changed_intent.value.detail["code"] == "ACTIVATION_OPERATION_INTENT_CONFLICT"
        with pytest.raises(server.HTTPException) as cross_kind:
            await server.admin_bootstrap_reading_pass_segments(
                "fixture-book", server.ReadingPassSegmentBootstrapIn(
                    target_segmentation_version="canonical-fixture-v2",
                    operation_id="operation-cross-title-promote",
                ), {"email": "fixture@example.test"},
            )
        assert cross_kind.value.detail["code"] == "ACTIVATION_OPERATION_INTENT_CONFLICT"

    asyncio.run(scenario())


def test_bootstrap_operation_identity_rejects_cross_title_replay_and_ambiguous_records(monkeypatch):
    async def scenario():
        database = _database()
        database.reader_content_segments.rows = [
            row for row in database.reader_content_segments.rows
            if row["segmentation_version"] == "canonical-fixture-v2"
        ]
        database.reader_segment_manifests.rows = [_manifest("canonical-fixture-v2", "prepared")]
        database.reader_segment_activation_state.rows = []
        _add_matching_title(database, "fixture-book-b", pointed=False)
        database.reader_content_segments.rows = [
            row for row in database.reader_content_segments.rows
            if row["segmentation_version"] == "canonical-fixture-v2"
        ]
        monkeypatch.setattr(server, "db", database)
        monkeypatch.setattr(server, "client", Client())
        payload = server.ReadingPassSegmentBootstrapIn(
            target_segmentation_version="canonical-fixture-v2", operation_id="operation-cross-title-bootstrap"
        )
        winner = await server.admin_bootstrap_reading_pass_segments("fixture-book", payload, {"email": "fixture@example.test"})
        assert await server.admin_bootstrap_reading_pass_segments("fixture-book", payload, {"email": "fixture@example.test"}) == winner
        with pytest.raises(server.HTTPException) as cross_title:
            await server.admin_bootstrap_reading_pass_segments("fixture-book-b", payload, {"email": "fixture@example.test"})
        assert cross_title.value.detail["code"] == "ACTIVATION_OPERATION_INTENT_CONFLICT"
        assert not any(row["book_slug"] == "fixture-book-b" for row in database.reader_segment_activation_state.rows)
        # A historical record missing a result title is not repaired from a new
        # request and cannot be used as a retry authority.
        database.reader_segment_activation_operations.rows.append({
            "operation_id": "ambiguous-legacy-record",
            "intent_digest": "not-a-verified-legacy-digest",
            "result": {"operation_id": "ambiguous-legacy-record"},
        })
        with pytest.raises(server.HTTPException) as ambiguous:
            await server.admin_bootstrap_reading_pass_segments(
                "fixture-book-b", server.ReadingPassSegmentBootstrapIn(
                    target_segmentation_version="canonical-fixture-v2", operation_id="ambiguous-legacy-record"
                ), {"email": "fixture@example.test"},
            )
        assert ambiguous.value.detail["code"] == "ACTIVATION_OPERATION_INTENT_CONFLICT"

    asyncio.run(scenario())


def test_recovery_requires_consistent_versioned_or_evidenced_legacy_operation_metadata(monkeypatch):
    async def scenario():
        database = _database()
        monkeypatch.setattr(server, "db", database)
        monkeypatch.setattr(server, "client", Client())
        legacy_operation_id = "legacy-evidenced-operation"
        legacy_intent = {"target": "canonical-fixture-v2", "expected": "canonical-fixture-v1", "generation": 0}
        legacy_digest = hashlib.sha256(
            server._json.dumps(legacy_intent, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        legacy_result = {
            "book_slug": "fixture-book", "operation_id": legacy_operation_id,
            "previous_segmentation_version": "canonical-fixture-v1", "segmentation_version": "canonical-fixture-v2",
            "activation_generation": 1, "version": _manifest("canonical-fixture-v2", "prepared")["version"],
            "total_pages": _manifest("canonical-fixture-v2", "prepared")["total_pages"], "activated": True,
        }
        database.reader_segment_activation_operations.rows.append({
            "book_slug": "fixture-book", "operation_id": legacy_operation_id,
            "intent_digest": legacy_digest, "result": legacy_result,
        })
        recovered = await server.admin_promote_reading_pass_segments(
            "fixture-book", _payload("canonical-fixture-v2", "canonical-fixture-v1", 0, legacy_operation_id),
            {"email": "fixture@example.test"},
        )
        assert recovered == legacy_result

        bad_operation_id = "versioned-inconsistent-operation"
        intent = server._reader_segment_operation_intent(
            book_slug="fixture-book", operation_kind="promote", target_segmentation_version="canonical-fixture-v2",
            expected_active_segmentation_version="canonical-fixture-v1", expected_activation_generation=0,
        )
        database.reader_segment_activation_operations.rows.append({
            "book_slug": "fixture-book", "operation_id": bad_operation_id,
            "operation_identity_schema": server._READER_SEGMENT_OPERATION_INTENT_SCHEMA,
            "operation_kind": "promote", "intent": intent,
            "intent_digest": server._reader_segment_operation_digest(intent),
            "result": {**legacy_result, "operation_id": bad_operation_id, "book_slug": "different-book"},
        })
        with pytest.raises(server.HTTPException) as inconsistent:
            await server.admin_promote_reading_pass_segments(
                "fixture-book", _payload("canonical-fixture-v2", "canonical-fixture-v1", 0, bad_operation_id),
                {"email": "fixture@example.test"},
            )
        assert inconsistent.value.detail["code"] == "ACTIVATION_OPERATION_INTENT_CONFLICT"

    asyncio.run(scenario())


async def _expect_http_conflict(coro):
    with pytest.raises(server.HTTPException) as raised:
        await coro
    return raised.value


def test_retained_manifest_integrity_rejects_content_tampering_before_promotion(monkeypatch):
    async def scenario():
        database = _database()
        tampered = next(row for row in database.reader_content_segments.rows if row["segmentation_version"] == "canonical-fixture-v2")
        tampered["content"] = "tampered"
        monkeypatch.setattr(server, "db", database)
        monkeypatch.setattr(server, "client", Client())
        with pytest.raises(server.HTTPException) as raised:
            await server.admin_promote_reading_pass_segments(
                "fixture-book", _payload("canonical-fixture-v2", "canonical-fixture-v1", 0, "operation-tampered-v2"), {"email": "fixture@example.test"}
            )
        assert raised.value.detail["code"] == "SEGMENT_VERSION_INTEGRITY_FAILED"
        assert database.reader_segment_activation_state.rows == [{
            "book_slug": "fixture-book",
            "active_segmentation_version": "canonical-fixture-v1",
            "generation": 0,
        }]
        assert [row["segmentation_version"] for row in database.reader_segment_manifests.rows if row["status"] == "active"] == ["canonical-fixture-v1"]

    asyncio.run(scenario())


def test_legacy_build_activation_flag_is_rejected_before_candidate_resolution():
    async def scenario():
        with pytest.raises(server.HTTPException) as raised:
            await server.admin_build_reading_pass_segments(
                "fixture-book",
                server.ReadingPassSegmentMigrationIn(activate=True, dry_run=False),
                {"email": "fixture@example.test"},
            )
        assert raised.value.status_code == 409
        assert raised.value.detail["code"] == "VERSIONED_PROMOTION_REQUIRED"

    asyncio.run(scenario())


def test_position_write_validates_the_bound_manifest_and_page_before_persisting(monkeypatch):
    async def scenario():
        calls = []

        class Segments:
            async def find_one(self, query, _projection):
                if query.get("page_index") == 4 and query.get("segmentation_version") == "canonical-fixture-v2":
                    return {"chapter_id": "chapter-001"}
                return None

        async def stored(slug, segmentation_version, **_kwargs):
            assert slug == "fixture-book"
            assert segmentation_version == "canonical-fixture-v2"
            return {"version": "fixture-manifest-v2"}

        async def save_position(**kwargs):
            calls.append(kwargs)
            return {"version": 1, "position": kwargs["position"]}

        monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
        monkeypatch.setattr(server, "db", SimpleNamespace(reader_content_segments=Segments()))
        monkeypatch.setattr(server, "_stored_reader_segment_manifest", stored)
        monkeypatch.setattr(server, "reading_pass_service", SimpleNamespace(save_position=save_position))
        payload = server.ReadingPassPositionIn(
            content_type="text", content_id="fixture-book",
            position={"canonical_page_index": 4, "chapter_id": "chapter-001"}, version=0,
            publication_segmentation_version="canonical-fixture-v2",
            publication_manifest_version="fixture-manifest-v2",
        )
        assert (await server.reading_pass_save_position(payload, {"id": "fixture-user"}))["version"] == 1
        assert calls[0]["publication_segmentation_version"] == "canonical-fixture-v2"
        assert calls[0]["publication_manifest_version"] == "fixture-manifest-v2"

        invalid = payload.model_copy(update={"publication_manifest_version": "wrong-manifest"})
        with pytest.raises(server.HTTPException) as rejected:
            await server.reading_pass_save_position(invalid, {"id": "fixture-user"})
        assert rejected.value.status_code == 409
        assert rejected.value.detail["code"] == "PUBLICATION_VERSION_MISMATCH"
        assert len(calls) == 1

    asyncio.run(scenario())
