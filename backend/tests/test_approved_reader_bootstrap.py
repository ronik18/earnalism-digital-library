import asyncio
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from starlette.responses import Response
from starlette.requests import Request

from backend import server
from backend.tests.test_reader_segment_promotion_safeguards import Collection, Client


SLUG = "a-horseman-in-the-sky"
NEW_RELEASE_SLUGS = ("dracula", "book-edfcf810c5")
RELEASE_SLUGS = (SLUG, *NEW_RELEASE_SLUGS)
ACTOR = "system:owner-authorized-reader-bootstrap-v1"
PLAN_PATH = Path(server.__file__).parent / "data" / "approved_reader_bootstrap.json"


class IndexedCollection(Collection):
    def __init__(self, keys, partial=None):
        super().__init__()
        self.indexes = {str(i): {"key": key, "unique": True, **({"partialFilterExpression": part} if part else {})} for i, (key, part) in enumerate(keys)}

    async def index_information(self):
        return self.indexes

    async def create_index(self, keys, **options):
        self.indexes[str(len(self.indexes))] = {"key": keys, **options}

    async def insert_many(self, documents, **_kwargs):
        self.rows.extend(copy.deepcopy(documents))


class Database:
    def __init__(self):
        self.reader_content_segments = IndexedCollection([([("book_slug", 1), ("page_index", 1), ("segmentation_version", 1)], None)])
        self.reader_segment_manifests = IndexedCollection([([("book_slug", 1), ("segmentation_version", 1)], None), ([("book_slug", 1)], {"status": "active"})])
        self.reader_segment_activation_state = IndexedCollection([([("book_slug", 1)], None)])
        self.reader_segment_activation_operations = IndexedCollection([([("operation_id", 1)], None)])
        self.reading_pass_audit = Collection()

    def __getitem__(self, key):
        return getattr(self, key)


def setup(monkeypatch, slug=SLUG):
    plan = json.loads(PLAN_PATH.read_text())
    plan["titles"] = [row for row in plan["titles"] if row["slug"] == slug]
    assert len(plan["titles"]) == 1
    record, _components = server._release_rights_artifact(slug)
    assert record and record.get("decision_id")
    assert plan["titles"][0]["decision_id"] == record["decision_id"]
    assert plan["titles"][0]["record_sha256"] == server.record_sha256(record)
    original_read = server.read_json_file
    monkeypatch.setattr(server, "read_json_file", lambda path: copy.deepcopy(plan) if Path(path) == PLAN_PATH else original_read(path))
    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
    monkeypatch.setattr(server, "ENVIRONMENT", "production")
    database = Database()
    monkeypatch.setattr(server, "db", database)
    monkeypatch.setattr(server, "client", Client())
    book = server._controlled_artifact_doc(slug, include_content=True)
    assert book and book["chapters"]
    monkeypatch.setattr(server, "_reader_book_access_doc", AsyncMock(return_value=book))
    content = {chapter["id"]: chapter["content"] for chapter in book["chapters"]}
    monkeypatch.setattr(server, "_reader_chapter_content", AsyncMock(side_effect=lambda slug, chapter_id: content[chapter_id]))
    return database, plan


def test_persisted_plan_exactly_matches_approved_scope_and_registered_decisions():
    plan = json.loads(PLAN_PATH.read_text())
    titles = plan["titles"]
    assert len(titles) == 26
    assert len({entry["slug"] for entry in titles}) == len(titles)
    assert {entry["slug"] for entry in titles} == set(server.CONTROLLED_LIVE_BOOK_SLUGS)
    accepted, revoked = server.load_production_registry()
    for entry in titles:
        record, _components = server._release_rights_artifact(entry["slug"])
        assert record and entry["decision_id"] == record["decision_id"]
        assert entry["record_sha256"] == server.record_sha256(record)
        assert accepted[entry["decision_id"]] == entry["record_sha256"]
        assert entry["decision_id"] not in revoked


@pytest.mark.parametrize("slug", RELEASE_SLUGS)
def test_exact_approved_source_initializes_once_and_real_manifest_is_readable(monkeypatch, slug):
    database, _plan = setup(monkeypatch, slug)

    async def run():
        first = await server._initialize_authorized_reader_release()
        manifest = await server.reading_pass_book_manifest(slug, Response())
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
        previews = [await server.reading_pass_book_page(slug, index, request, Response(), principal=None)
                    for index in (1, 3)]
        with pytest.raises(server.HTTPException) as protected:
            await server.reading_pass_book_page(slug, 4, request, Response(), principal=None)
        assert protected.value.status_code == 401
        assert protected.value.detail["code"] == "AUTH_REQUIRED"
        retained = copy.deepcopy(database.reader_content_segments.rows)
        second = await server._initialize_authorized_reader_release()
        return first, manifest, previews, retained, second

    first, manifest, previews, retained, second = asyncio.run(run())
    assert first[0]["status"] == "INITIALIZED"
    assert manifest["book_slug"] == slug and manifest["total_pages"] > 3
    assert manifest["version"] == first[0]["version"]
    assert manifest["public_preview_pages"] == 3
    assert [chapter["chapter_id"] for chapter in manifest["chapters"]] == [
        chapter["id"] for chapter in server._reader_book_access_doc.return_value["chapters"]]
    for page in previews:
        assert page["book_slug"] == slug and page["is_preview"] is True
        assert page["manifest_version"] == manifest["version"]
        assert page["segmentation_version"] == manifest["segmentation_version"]
        assert page["content"].strip()
        assert hashlib.sha256(page["content"].encode()).hexdigest() == page["content_sha256"]
    assert all(row["content"].strip() and row["created_by"] == ACTOR for row in retained)
    assert [row["page_index"] for row in retained] == list(range(1, manifest["total_pages"] + 1))
    assert all(hashlib.sha256(row["content"].encode()).hexdigest() == row["content_sha256"] for row in retained)
    assert database.reader_content_segments.rows == retained
    assert second == [{"slug": slug, "status": "PRESERVED_EXISTING_POINTER"}]
    assert len(database.reader_segment_activation_operations.rows) == 1
    assert database.reading_pass_audit.rows[0]["actor"] == ACTOR


@pytest.mark.parametrize("existing", ["active", "pointer", "revoked", "archived", "operator-prepared"])
@pytest.mark.parametrize("slug", RELEASE_SLUGS)
def test_existing_versions_and_revocation_history_remain_unchanged(monkeypatch, existing, slug):
    database, _plan = setup(monkeypatch, slug)
    if existing in {"pointer", "revoked"}:
        database.reader_segment_activation_state.rows.append({"book_slug": slug, "generation": 7, "text_revocation": {"reason": "retained"}})
    else:
        database.reader_segment_manifests.rows.append({"book_slug": slug, "segmentation_version": "original-approved-version", "status": "prepared" if existing == "operator-prepared" else existing, "created_by": "admin:original"})
    before = copy.deepcopy(database.__dict__)
    results = asyncio.run(server._initialize_authorized_reader_release())
    assert results[0]["status"].startswith("PRESERVED_")
    for key, old in before.items():
        assert getattr(database, key).rows == old.rows


@pytest.mark.parametrize("hold", ["changed-decision", "revoked-decision", "conflicting-index", "incomplete-source", "unreleased-title"])
@pytest.mark.parametrize("slug", RELEASE_SLUGS)
def test_missing_authority_or_integrity_cannot_create_pages_or_pointer(monkeypatch, hold, slug):
    database, plan = setup(monkeypatch, slug)
    entry = plan["titles"][0]
    if hold == "changed-decision":
        entry["record_sha256"] = "0" * 64
    elif hold == "revoked-decision":
        accepted, _revoked = server.load_production_registry()
        monkeypatch.setattr(server, "load_production_registry", lambda: (accepted, frozenset({entry["decision_id"]})))
    elif hold == "conflicting-index":
        database.reader_segment_activation_state.indexes = {}
        database.reader_segment_activation_state.create_index = AsyncMock(side_effect=RuntimeError("synthetic uniqueness conflict"))
    elif hold == "incomplete-source":
        server._reader_book_access_doc.return_value = None
    else:
        entry["slug"] = "frankenstein"
    result = asyncio.run(server._initialize_authorized_reader_release())
    assert result[0]["status"].startswith("HELD")
    assert not database.reader_content_segments.rows
    assert not database.reader_segment_activation_state.rows
    assert not database.reader_segment_activation_operations.rows


@pytest.mark.parametrize("slug", NEW_RELEASE_SLUGS)
def test_omitted_plan_entry_does_not_initialize_an_absent_candidate(monkeypatch, slug):
    database, plan = setup(monkeypatch, slug)
    plan["titles"] = []

    async def run():
        assert await server._initialize_authorized_reader_release() == []
        with pytest.raises(server.HTTPException) as absent:
            await server.reading_pass_book_manifest(slug, Response())
        assert absent.value.status_code == 503
        assert absent.value.detail["code"] == "SEGMENTS_NOT_READY"

    asyncio.run(run())
    assert not database.reader_content_segments.rows
    assert not database.reader_segment_manifests.rows
    assert not database.reader_segment_activation_state.rows
    assert not database.reader_segment_activation_operations.rows


def test_disabled_reading_pass_does_not_initialize_anything(monkeypatch):
    database, _plan = setup(monkeypatch)
    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", False)
    assert asyncio.run(server._initialize_authorized_reader_release()) == []
    assert not database.reader_content_segments.rows


def test_uat_seed_and_preview_environments_are_not_initialized(monkeypatch):
    database, _plan = setup(monkeypatch)
    monkeypatch.setattr(server, "ENVIRONMENT", "uat")
    assert asyncio.run(server._initialize_authorized_reader_release()) == []
    assert not database.reader_content_segments.rows


def test_missing_unique_index_is_installed_without_changing_existing_indexes_or_history(monkeypatch):
    database, _plan = setup(monkeypatch)
    collection = database.reader_segment_activation_state
    collection.indexes = {"retained_history_lookup": {"key": [("retained_history_id", 1)], "unique": False}}
    collection.rows.append({"book_slug": "another-retained-title", "generation": 9})
    before = copy.deepcopy(collection.rows)
    first = asyncio.run(server._initialize_authorized_reader_release())
    assert first[0]["status"] == "INITIALIZED"
    assert collection.rows[:1] == before
    assert collection.indexes["retained_history_lookup"] == {"key": [("retained_history_id", 1)], "unique": False}
    assert any(index["key"] == [("book_slug", 1)] and index["unique"] is True for index in collection.indexes.values())
