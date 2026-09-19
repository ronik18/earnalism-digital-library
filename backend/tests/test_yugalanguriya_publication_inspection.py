from __future__ import annotations

import asyncio
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
    def __init__(self, rows=(), *, fail_find_one=False, fail_count=False):
        self.rows = list(rows)
        self.queries = []
        self.fail_find_one = fail_find_one
        self.fail_count = fail_count

    async def find_one(self, query, _projection=None):
        self.queries.append(("find_one", query))
        if self.fail_find_one:
            raise TimeoutError("synthetic internal failure")
        return next((row for row in self.rows if all(row.get(k) == v for k, v in query.items())), None)

    def find(self, query, _projection=None):
        self.queries.append(("find", query))
        return Cursor([row for row in self.rows if all(row.get(k) == v for k, v in query.items())])

    async def count_documents(self, query):
        self.queries.append(("count_documents", query))
        if self.fail_count:
            raise TimeoutError("synthetic internal failure")
        return sum(1 for row in self.rows if all(row.get(k) == v for k, v in query.items()))

    async def insert_one(self, *_args, **_kwargs):
        raise AssertionError("publication inspector must not write")

    async def update_one(self, *_args, **_kwargs):
        raise AssertionError("publication inspector must not write")

    async def create_index(self, *_args, **_kwargs):
        raise AssertionError("publication inspector must not create indexes")


def fake_db(*, pointer=(), manifests=(), segments=(), sessions=()):
    return SimpleNamespace(
        reader_segment_activation_state=ReadOnlyCollection(pointer),
        reader_segment_manifests=ReadOnlyCollection(manifests),
        reader_content_segments=ReadOnlyCollection(segments),
        reading_pass_sessions=ReadOnlyCollection(sessions),
    )


def token(role):
    return jwt.encode({"sub": "test", "email": "test@example.test", "role": role}, server.JWT_SECRET, algorithm=server.JWT_ALG)


def test_route_requires_existing_admin_authentication():
    client = TestClient(server.app)
    assert client.get(ROUTE).status_code == 401
    assert client.get(ROUTE, headers={"Authorization": f"Bearer {token('user')}"}).status_code == 403


def test_inspection_is_fixed_scope_allowlisted_and_read_only(monkeypatch):
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
    assert result["activation_pointer"]["status"] == "PRESENT"
    assert result["retained_manifests"]["records"][0]["stored_segment_count"] == 1
    assert result["protected_page"] == {"page_index": 4, "status": "OBSERVED", "exists": True}
    assert result["active_text_sessions"]["active_text_session_count"] == 1
    assert "do-not-return" not in str(result)
    response = TestClient(server.app).get(ROUTE, headers={"Authorization": f"Bearer {token('admin')}"})
    assert response.status_code == 200
    assert "do-not-return" not in response.text
    assert all(query.get("book_slug", SLUG) == SLUG for collection in (database.reader_segment_activation_state, database.reader_segment_manifests, database.reader_content_segments) for _method, query in collection.queries)
    assert ("count_documents", {"content_type": "text", "content_id": SLUG, "status": "active"}) in database.reading_pass_sessions.queries
    assert TestClient(server.app).get("/api/admin/reading-pass/other/publication-inspection").status_code == 404


def test_retained_inconsistent_and_oversized_results_are_explicit(monkeypatch):
    manifests = [{"book_slug": SLUG, "segmentation_version": f"v-{index}", "version": f"m-{index}", "status": "archived", "total_pages": 13} for index in range(21)]
    database = fake_db(pointer=[{"book_slug": SLUG, "active_segmentation_version": "missing-version", "generation": 4}], manifests=manifests)
    monkeypatch.setattr(server, "db", database)

    result = asyncio.run(server._yugalanguriya_publication_inspection())

    assert result["complete"] is False
    assert result["retained_manifests"]["truncated"] is True
    assert len(result["retained_manifests"]["records"]) == 20
    assert result["retained_manifests"]["pointer_version_in_returned_records"] is False
    assert result["protected_page"] == {"page_index": 4, "status": "OBSERVED", "exists": False}
    assert {error["code"] for error in result["errors"]} == {"RESULT_TRUNCATED"}


def test_partial_failures_are_unknown_not_false_empty_success(monkeypatch):
    database = fake_db(sessions=())
    database.reading_pass_sessions.fail_count = True
    monkeypatch.setattr(server, "db", database)
    monkeypatch.setattr(server, "_yugalanguriya_inspection_identity", lambda: (_ for _ in ()).throw(OSError("synthetic package failure")))

    result = asyncio.run(server._yugalanguriya_publication_inspection())

    assert result["complete"] is False
    assert result["active_text_sessions"] == {"status": "UNKNOWN", "active_text_session_count": None}
    assert {error["component"] for error in result["errors"]} == {"active_text_sessions", "package_identity"}
    assert "synthetic internal failure" not in str(result)
    assert "synthetic package failure" not in str(result)
