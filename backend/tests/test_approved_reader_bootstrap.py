import asyncio
import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from starlette.responses import Response

from backend import server
from backend.tests.test_reader_segment_promotion_safeguards import Collection, Client


SLUG = "a-horseman-in-the-sky"
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


def setup(monkeypatch):
    plan = json.loads(PLAN_PATH.read_text())
    plan["titles"] = [row for row in plan["titles"] if row["slug"] == SLUG]
    original_read = server.read_json_file
    monkeypatch.setattr(server, "read_json_file", lambda path: copy.deepcopy(plan) if Path(path) == PLAN_PATH else original_read(path))
    monkeypatch.setattr(server, "READING_PASS_V2_ENABLED", True)
    monkeypatch.setattr(server, "ENVIRONMENT", "production")
    database = Database()
    monkeypatch.setattr(server, "db", database)
    monkeypatch.setattr(server, "client", Client())
    book = server._controlled_artifact_doc(SLUG, include_content=True)
    assert book and book["chapters"]
    monkeypatch.setattr(server, "_reader_book_access_doc", AsyncMock(return_value=book))
    content = {chapter["id"]: chapter["content"] for chapter in book["chapters"]}
    monkeypatch.setattr(server, "_reader_chapter_content", AsyncMock(side_effect=lambda slug, chapter_id: content[chapter_id]))
    return database, plan


def test_exact_approved_source_initializes_once_and_real_manifest_is_readable(monkeypatch):
    database, _plan = setup(monkeypatch)

    async def run():
        first = await server._initialize_authorized_reader_release()
        manifest = await server.reading_pass_book_manifest(SLUG, Response())
        retained = copy.deepcopy(database.reader_content_segments.rows)
        second = await server._initialize_authorized_reader_release()
        return first, manifest, retained, second

    first, manifest, retained, second = asyncio.run(run())
    assert first[0]["status"] == "INITIALIZED"
    assert manifest["book_slug"] == SLUG and manifest["total_pages"] > 3
    assert manifest["version"] == first[0]["version"]
    assert all(row["content"].strip() and row["created_by"] == ACTOR for row in retained)
    assert database.reader_content_segments.rows == retained
    assert second == [{"slug": SLUG, "status": "PRESERVED_EXISTING_POINTER"}]
    assert len(database.reader_segment_activation_operations.rows) == 1
    assert database.reading_pass_audit.rows[0]["actor"] == ACTOR


@pytest.mark.parametrize("existing", ["active", "pointer", "revoked", "archived", "operator-prepared"])
def test_existing_versions_and_revocation_history_remain_unchanged(monkeypatch, existing):
    database, _plan = setup(monkeypatch)
    if existing in {"pointer", "revoked"}:
        database.reader_segment_activation_state.rows.append({"book_slug": SLUG, "generation": 7, "text_revocation": {"reason": "retained"}})
    else:
        database.reader_segment_manifests.rows.append({"book_slug": SLUG, "segmentation_version": "original-approved-version", "status": "prepared" if existing == "operator-prepared" else existing, "created_by": "admin:original"})
    before = copy.deepcopy(database.__dict__)
    results = asyncio.run(server._initialize_authorized_reader_release())
    assert results[0]["status"].startswith("PRESERVED_")
    for key, old in before.items():
        assert getattr(database, key).rows == old.rows


@pytest.mark.parametrize("hold", ["changed-decision", "revoked-decision", "conflicting-index", "incomplete-source", "unreleased-title"])
def test_missing_authority_or_integrity_cannot_create_pages_or_pointer(monkeypatch, hold):
    database, plan = setup(monkeypatch)
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
