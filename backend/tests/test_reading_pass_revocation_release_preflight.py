from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

from fastapi.testclient import TestClient
from jose import jwt


os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "reading-pass-release-preflight-test-secret")

from backend import server


ROUTE = "/api/admin/reading-pass/release-preflight"


class Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, length):
        return self.rows[:length]


class ReadOnlyCollection:
    def __init__(self, rows=(), *, fail_find=False):
        self.rows = list(rows)
        self.fail_find = fail_find
        self.queries = []

    @staticmethod
    def _matches(row, query):
        fixed = {key: value for key, value in query.items() if key != "$or"}
        if not all(row.get(key) == value for key, value in fixed.items()):
            return False
        options = query.get("$or")
        return not options or any(all(row.get(key) == value for key, value in option.items()) for option in options)

    def find(self, query, _projection=None, **kwargs):
        self.queries.append((query, kwargs))
        if self.fail_find:
            raise TimeoutError("synthetic sensitive value: must not be returned or logged")
        return Cursor(row for row in self.rows if self._matches(row, query))

    async def insert_one(self, *_args, **_kwargs):
        raise AssertionError("release preflight must not write")

    async def update_one(self, *_args, **_kwargs):
        raise AssertionError("release preflight must not write")

    async def create_index(self, *_args, **_kwargs):
        raise AssertionError("release preflight must not create indexes")


class UnfilteredReadOnlyCollection(ReadOnlyCollection):
    """Simulate a malformed driver result that does not honour the projection."""

    def find(self, query, _projection=None, **kwargs):
        self.queries.append((query, kwargs))
        return Cursor(self.rows)


class ReadOnlyDatabase:
    def __init__(self, *, index_response, pointers=(), manifests=(), fail_command=False):
        self.index_response = index_response
        self.fail_command = fail_command
        self.commands = []
        self.reader_segment_activation_state = ReadOnlyCollection(pointers)
        self.reader_segment_manifests = ReadOnlyCollection(manifests)

    async def command(self, command):
        self.commands.append(command)
        if self.fail_command:
            raise TimeoutError("synthetic sensitive value: must not be returned or logged")
        return self.index_response


def token(role):
    return jwt.encode({"sub": "test", "email": "test@example.test", "role": role}, server.JWT_SECRET, algorithm=server.JWT_ALG)


def exact_index_response(*, cursor_id=0, unique=True, sparse=False, partial_filter=None):
    index = {"name": "secret-index-name", "key": {"operation_id": 1}, "unique": unique}
    if sparse:
        index["sparse"] = True
    if partial_filter is not None:
        index["partialFilterExpression"] = partial_filter
    return {
        "cursor": {
            "id": cursor_id,
            "firstBatch": [index],
        }
    }


def test_route_requires_existing_admin_authentication():
    client = TestClient(server.app)
    assert client.get(ROUTE).status_code == 401
    assert client.get(ROUTE, headers={"Authorization": f"Bearer {token('user')}"}).status_code == 403


def test_preflight_reports_only_safe_complete_metadata_without_writes(monkeypatch):
    database = ReadOnlyDatabase(
        index_response=exact_index_response(),
        pointers=[{"book_slug": "controlled-radharani", "active_segmentation_version": "v-safe", "generation": 3, "secret": "do-not-return"}],
        manifests=[{"book_slug": "controlled-radharani", "segmentation_version": "v-safe", "status": "active", "body": "do-not-return"}],
    )
    monkeypatch.setattr(server, "db", database)

    result = asyncio.run(server._reading_pass_revocation_release_preflight())

    assert result["inspection_scope"] == "READING_PASS_REVOCATION_RELEASE_PRECONDITIONS"
    assert result["complete"] is True
    assert result["revocation_operation_index"] == {"status": "PRESENT_UNIQUE_EXACT", "exact_unique_operation_id_index": True}
    assert result["activation_pointers"]["compatibility"] == "ALL_OBSERVED_POINTERS_MATCH_SINGLE_ACTIVE_MANIFEST"
    assert result["activation_pointers"]["compatible_count"] == 1
    assert database.commands == [{
        "listIndexes": "reading_pass_text_revocation_operations",
        "cursor": {"batchSize": server.READING_PASS_RELEASE_PREFLIGHT_INDEX_BATCH_SIZE},
        "maxTimeMS": server.READING_PASS_RELEASE_PREFLIGHT_QUERY_MAX_TIME_MS,
    }]
    assert database.reader_segment_activation_state.queries[0][0] == {}
    assert database.reader_segment_manifests.queries[0][0] == {
        "status": "active", "$or": [{"book_slug": "controlled-radharani", "segmentation_version": "v-safe"}],
    }
    assert "do-not-return" not in str(result)

    response = TestClient(server.app).get(ROUTE, headers={"Authorization": f"Bearer {token('admin')}"})
    assert response.status_code == 200
    assert "secret-index-name" not in response.text
    assert "do-not-return" not in response.text


def test_partial_index_cursor_and_incompatible_pointer_never_become_a_pass(monkeypatch):
    database = ReadOnlyDatabase(
        index_response=exact_index_response(cursor_id=99),
        pointers=[{"book_slug": "controlled-yugalanguriya", "active_segmentation_version": "v-missing", "generation": 1}],
        manifests=[],
    )
    monkeypatch.setattr(server, "db", database)

    result = asyncio.run(server._reading_pass_revocation_release_preflight())

    assert result["complete"] is False
    assert result["revocation_operation_index"] == {"status": "UNKNOWN", "exact_unique_operation_id_index": None}
    assert result["activation_pointers"]["compatibility"] == "INCOMPLETE_OR_INCONSISTENT_POINTER_MANIFEST_STATE"
    assert result["activation_pointers"]["incompatible_count"] == 1
    assert {error["code"] for error in result["errors"]} == {"INDEX_RESULT_TRUNCATED", "POINTER_ACTIVE_MANIFEST_MISMATCH"}


def test_partial_or_sparse_unique_index_never_establishes_global_operation_idempotency(monkeypatch):
    for response in (
        exact_index_response(sparse=True),
        exact_index_response(partial_filter={"operation_id": {"$type": "string"}}),
    ):
        database = ReadOnlyDatabase(index_response=response)
        monkeypatch.setattr(server, "db", database)

        result = asyncio.run(server._reading_pass_revocation_release_preflight())

        assert result["revocation_operation_index"] == {
            "status": "ABSENT_OR_INCOMPATIBLE",
            "exact_unique_operation_id_index": False,
        }


def test_duplicate_or_truncated_pointer_manifest_evidence_fails_closed(monkeypatch):
    database = ReadOnlyDatabase(
        index_response=exact_index_response(),
        pointers=[
            {"book_slug": "controlled-radharani", "active_segmentation_version": "v-safe", "generation": 3},
            {"book_slug": "controlled-radharani", "active_segmentation_version": "v-other", "generation": 4},
        ],
        manifests=[
            {"book_slug": "controlled-radharani", "segmentation_version": "v-safe", "status": "active"},
        ] * (server.READING_PASS_RELEASE_PREFLIGHT_POINTER_LIMIT + 1),
    )
    monkeypatch.setattr(server, "db", database)

    result = asyncio.run(server._reading_pass_revocation_release_preflight())

    assert result["complete"] is False
    assert result["activation_pointers"]["duplicate_count"] == 1
    assert result["activation_pointers"]["manifest_truncated"] is True
    assert result["activation_pointers"]["compatibility"] == "INCOMPLETE_OR_INCONSISTENT_POINTER_MANIFEST_STATE"
    assert {error["code"] for error in result["errors"]} >= {"DUPLICATE_POINTER_TITLE", "RESULT_TRUNCATED"}


def test_malformed_pointer_or_manifest_evidence_fails_closed(monkeypatch):
    malformed_pointer = ReadOnlyDatabase(
        index_response=exact_index_response(),
        pointers=[{"book_slug": "controlled-radharani", "active_segmentation_version": "bad", "generation": True}],
    )
    monkeypatch.setattr(server, "db", malformed_pointer)

    pointer_result = asyncio.run(server._reading_pass_revocation_release_preflight())

    assert pointer_result["complete"] is False
    assert pointer_result["activation_pointers"]["compatibility"] == "INCOMPLETE_OR_INCONSISTENT_POINTER_MANIFEST_STATE"
    assert any(error == {"component": "activation_pointers", "code": "MALFORMED_POINTER_RECORD"} for error in pointer_result["errors"])

    malformed_manifest = ReadOnlyDatabase(
        index_response=exact_index_response(),
        pointers=[{"book_slug": "controlled-radharani", "active_segmentation_version": "v-safe", "generation": 3}],
    )
    malformed_manifest.reader_segment_manifests = UnfilteredReadOnlyCollection(
        [{"book_slug": "controlled-radharani", "segmentation_version": "bad/", "status": "active"}]
    )
    monkeypatch.setattr(server, "db", malformed_manifest)

    manifest_result = asyncio.run(server._reading_pass_revocation_release_preflight())

    assert manifest_result["complete"] is False
    assert manifest_result["activation_pointers"]["compatibility"] == "INCOMPLETE_OR_INCONSISTENT_POINTER_MANIFEST_STATE"
    assert {error["code"] for error in manifest_result["errors"]} >= {"MALFORMED_MANIFEST_RECORD", "POINTER_ACTIVE_MANIFEST_MISMATCH"}


def test_missing_active_pointers_are_not_compatible_evidence(monkeypatch):
    database = ReadOnlyDatabase(index_response=exact_index_response())
    monkeypatch.setattr(server, "db", database)

    result = asyncio.run(server._reading_pass_revocation_release_preflight())

    assert result["complete"] is False
    assert result["activation_pointers"]["compatibility"] == "NO_ACTIVE_POINTERS_OBSERVED"
    assert any(error == {"component": "activation_pointers", "code": "NO_ACTIVE_POINTERS_OBSERVED"} for error in result["errors"])


def test_read_failure_is_sanitized_and_unknown_not_absent(monkeypatch, caplog):
    database = ReadOnlyDatabase(index_response=exact_index_response(), fail_command=True)
    monkeypatch.setattr(server, "db", database)
    caplog.set_level("WARNING", logger=server.logger.name)

    result = asyncio.run(server._reading_pass_revocation_release_preflight())

    assert result["complete"] is False
    assert result["revocation_operation_index"] == {"status": "UNKNOWN", "exact_unique_operation_id_index": None}
    assert any(error["component"] == "revocation_operation_index" for error in result["errors"])
    assert "synthetic sensitive value" not in str(result)
    assert "synthetic sensitive value" not in caplog.text
