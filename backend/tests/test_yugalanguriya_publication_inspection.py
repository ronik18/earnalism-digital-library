from __future__ import annotations

import asyncio
import logging
import os
from types import SimpleNamespace

from fastapi.testclient import TestClient
from jose import jwt

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "yugalanguriya-publication-inspection-test-secret")

from backend import server


ROUTE = "/api/admin/reading-pass/yugalanguriya/publication-inspection"
SLUG = "yugalanguriya"


class Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, length):
        return self.rows[:length]


class ReadOnlyCollection:
    def __init__(self, rows=(), *, fail_find_one=False, fail_count=False, block_find_one=False, ignore_query=False):
        self.rows = list(rows)
        self.queries = []
        self.fail_find_one = fail_find_one
        self.fail_count = fail_count
        self.block_find_one = block_find_one
        self.ignore_query = ignore_query
        self._gate = asyncio.Event()

    def _matching_rows(self, query):
        if self.ignore_query:
            return list(self.rows)
        return [row for row in self.rows if all(row.get(key) == value for key, value in query.items())]

    async def find_one(self, query, _projection=None, **kwargs):
        self.queries.append(("find_one", query, kwargs))
        if self.block_find_one:
            await self._gate.wait()
        if self.fail_find_one:
            raise TimeoutError("synthetic sensitive value: should-never-reach-logs")
        return next(iter(self._matching_rows(query)), None)

    def find(self, query, _projection=None, **kwargs):
        self.queries.append(("find", query, kwargs))
        return Cursor(self._matching_rows(query))

    async def count_documents(self, query, **kwargs):
        self.queries.append(("count_documents", query, kwargs))
        if self.fail_count:
            raise TimeoutError("synthetic sensitive value: should-never-reach-logs")
        return len(self._matching_rows(query))

    async def insert_one(self, *_args, **_kwargs):
        raise AssertionError("publication inspector must not write")

    async def update_one(self, *_args, **_kwargs):
        raise AssertionError("publication inspector must not write")

    async def create_index(self, *_args, **_kwargs):
        raise AssertionError("publication inspector must not create indexes")


def fake_db(*, pointer=(), manifests=(), segments=(), sessions=(), pointer_options=None, manifest_options=None):
    return SimpleNamespace(
        reader_segment_activation_state=ReadOnlyCollection(pointer, **(pointer_options or {})),
        reader_segment_manifests=ReadOnlyCollection(manifests, **(manifest_options or {})),
        reader_content_segments=ReadOnlyCollection(segments),
        reading_pass_sessions=ReadOnlyCollection(sessions),
    )


def token(role):
    return jwt.encode({"sub": "test", "email": "test@example.test", "role": role}, server.JWT_SECRET, algorithm=server.JWT_ALG)


def query_options(collection):
    return [options for _method, _query, options in collection.queries]


def test_route_requires_existing_admin_authentication():
    client = TestClient(server.app)
    assert client.get(ROUTE).status_code == 401
    assert client.get(ROUTE, headers={"Authorization": f"Bearer {token('user')}"}).status_code == 403


def test_inspection_is_fixed_scope_bounded_and_read_only(monkeypatch):
    database = fake_db(
        pointer=[{"book_slug": SLUG, "active_segmentation_version": "v-safe", "generation": 2, "secret": "do-not-return"}],
        manifests=[{"book_slug": SLUG, "segmentation_version": "v-safe", "version": "manifest-safe", "status": "active", "total_pages": 13, "body": "do-not-return"}],
        segments=[{"book_slug": SLUG, "segmentation_version": "v-safe", "page_index": 4, "content": "do-not-return"}],
        sessions=[{"content_type": "text", "content_id": SLUG, "status": "active", "user_id": "do-not-return"}],
    )
    monkeypatch.setattr(server, "db", database)

    result = asyncio.run(server._yugalanguriya_publication_inspection())

    assert result["inspection_scope"] == "YUGALANGURIYA_ONLY"
    assert result["identity"]["availability_reason"] == "NOT_IN_CURRENT_CONTROLLED_LIVE_CATALOG"
    assert result["activation_pointer"] == {"status": "PRESENT", "selected_version": "v-safe", "generation": 2, "metadata_status": "OBSERVED"}
    assert result["active_manifest"]["selection_state"] == "SINGLE_ACTIVE_MANIFEST"
    assert result["consistency"]["status"] == "POINTER_MATCHES_ACTIVE_MANIFEST"
    assert result["retained_manifests"]["records"][0]["stored_segment_count"] == 1
    assert result["protected_page"] == {"segmentation_version": "v-safe", "page_index": 4, "status": "OBSERVED", "exists": True}
    assert result["active_text_sessions"]["active_text_session_count"] == 1
    assert result["limitations"]["query_max_time_ms"] == server.YUGALANGURIYA_INSPECTION_QUERY_MAX_TIME_MS
    assert "do-not-return" not in str(result)
    response = TestClient(server.app).get(ROUTE, headers={"Authorization": f"Bearer {token('admin')}"})
    assert response.status_code == 200
    assert "do-not-return" not in response.text
    collections = (database.reader_segment_activation_state, database.reader_segment_manifests, database.reader_content_segments)
    assert all(query.get("book_slug", SLUG) == SLUG for collection in collections for _method, query, _options in collection.queries)
    assert ("count_documents", {"content_type": "text", "content_id": SLUG, "status": "active"}, {"maxTimeMS": server.YUGALANGURIYA_INSPECTION_QUERY_MAX_TIME_MS}) in database.reading_pass_sessions.queries
    assert all(("max_time_ms" in options or "maxTimeMS" in options) for collection in (database.reader_segment_activation_state, database.reader_segment_manifests, database.reader_content_segments) for options in query_options(collection))
    assert TestClient(server.app).get("/api/admin/reading-pass/other/publication-inspection").status_code == 404


def test_retained_bound_and_selected_version_outside_it_are_explicit(monkeypatch):
    manifests = [{"book_slug": SLUG, "segmentation_version": f"v-{index:02d}", "version": f"m-{index}", "status": "archived", "total_pages": 13} for index in range(21)]
    database = fake_db(pointer=[{"book_slug": SLUG, "active_segmentation_version": "missing-version", "generation": 4}], manifests=manifests)
    monkeypatch.setattr(server, "db", database)

    result = asyncio.run(server._yugalanguriya_publication_inspection())

    assert result["complete"] is False
    assert result["retained_manifests"]["truncated"] is True
    assert len(result["retained_manifests"]["records"]) == 20
    assert result["retained_manifests"]["pointer_version_in_returned_records"] == "SELECTED_VERSION_OUTSIDE_RETURNED_BOUND"
    assert result["active_manifest"]["selection_state"] == "ABSENT"
    assert result["protected_page"]["status"] == "ABSENT"
    assert {error["code"] for error in result["errors"]} == {"RESULT_TRUNCATED"}


def test_missing_pointer_and_retained_active_manifest_are_distinct(monkeypatch):
    database = fake_db(manifests=[{"book_slug": SLUG, "segmentation_version": "v-active", "version": "m-active", "status": "active", "total_pages": 13}])
    monkeypatch.setattr(server, "db", database)

    result = asyncio.run(server._yugalanguriya_publication_inspection())

    assert result["activation_pointer"]["status"] == "ABSENT"
    assert result["active_manifest"]["selection_state"] == "SINGLE_ACTIVE_MANIFEST"
    assert result["consistency"]["status"] == "ACTIVE_MANIFEST_WITHOUT_ACTIVATION_STATE"
    assert result["retained_manifests"]["pointer_version_in_returned_records"] == "NO_ACTIVATION_STATE"


def test_non_atomic_multiple_or_mismatched_active_state_is_not_complete(monkeypatch):
    database = fake_db(
        pointer=[{"book_slug": SLUG, "active_segmentation_version": "v-first", "generation": 3}],
        manifests=[
            {"book_slug": SLUG, "segmentation_version": "v-first", "version": "m-first", "status": "active", "total_pages": 13},
            {"book_slug": SLUG, "segmentation_version": "v-second", "version": "m-second", "status": "active", "total_pages": 13},
        ],
    )
    monkeypatch.setattr(server, "db", database)

    result = asyncio.run(server._yugalanguriya_publication_inspection())

    assert result["complete"] is False
    assert result["active_manifest"]["selection_state"] == "MULTIPLE_ACTIVE_MANIFESTS"
    assert result["consistency"]["status"] == "NONATOMIC_MULTIPLE_ACTIVE_MANIFESTS"
    assert {error["code"] for error in result["errors"]} == {"INCONSISTENT_NONATOMIC_STATE"}


def test_malformed_or_overlong_version_is_not_used_as_a_query_key(monkeypatch):
    malformed = "x" * 81
    database = fake_db(
        pointer=[{"book_slug": SLUG, "active_segmentation_version": malformed, "generation": 1}],
        manifests=[{"book_slug": SLUG, "segmentation_version": "v-active", "version": "m-active", "status": "active", "total_pages": 13}],
    )
    monkeypatch.setattr(server, "db", database)

    result = asyncio.run(server._yugalanguriya_publication_inspection())

    assert result["activation_pointer"]["metadata_status"] == "MALFORMED"
    assert result["activation_pointer"]["selected_version"] is None
    assert result["consistency"]["status"] == "MALFORMED_ACTIVATION_STATE"
    assert result["complete"] is False
    assert all(malformed not in query.values() for _method, query, _options in database.reader_content_segments.queries)


def test_partial_failures_are_unknown_and_exception_text_is_not_logged_or_returned(monkeypatch, caplog):
    database = fake_db(sessions=())
    database.reading_pass_sessions.fail_count = True
    monkeypatch.setattr(server, "db", database)
    monkeypatch.setattr(server, "_yugalanguriya_inspection_identity", lambda: (_ for _ in ()).throw(OSError("synthetic sensitive value: package failure")))
    caplog.set_level(logging.WARNING, logger=server.logger.name)

    result = asyncio.run(server._yugalanguriya_publication_inspection())

    assert result["complete"] is False
    assert result["active_text_sessions"] == {"status": "UNKNOWN", "active_text_session_count": None}
    assert {error["component"] for error in result["errors"]} == {"active_text_sessions", "package_identity"}
    assert "synthetic sensitive value" not in str(result)
    assert "synthetic sensitive value" not in caplog.text


def test_overall_deadline_stops_subsequent_reads_without_reporting_zero(monkeypatch):
    database = fake_db(pointer_options={"block_find_one": True})
    monkeypatch.setattr(server, "db", database)
    monkeypatch.setattr(server, "YUGALANGURIYA_INSPECTION_DEADLINE_MS", 1)
    monkeypatch.setattr(server, "YUGALANGURIYA_INSPECTION_QUERY_MAX_TIME_MS", 100)

    result = asyncio.run(server._yugalanguriya_publication_inspection())

    assert result["activation_pointer"]["status"] == "UNKNOWN"
    assert result["active_text_sessions"] == {"status": "UNKNOWN", "active_text_session_count": None}
    assert any(error["code"] == "OVERALL_DEADLINE_EXCEEDED" for error in result["errors"])
    assert database.reader_segment_manifests.queries == []
    assert database.reader_content_segments.queries == []
    assert database.reading_pass_sessions.queries == []
