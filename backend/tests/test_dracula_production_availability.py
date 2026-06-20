from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "dracula-availability-test-secret")

from backend import server
from backend import catalog_truth
from scripts import prod_dracula_diagnostic
from scripts import repair_dracula_production_record


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, *_args, **_kwargs):
        return self

    def skip(self, value):
        self.docs = self.docs[int(value or 0) :]
        return self

    def limit(self, value):
        self.docs = self.docs[: int(value or len(self.docs))]
        return self

    async def to_list(self, *_args, **_kwargs):
        return list(self.docs)


class FakeBooks:
    def __init__(self, docs):
        self.docs = list(docs)
        self.mutations = []

    def _matches(self, doc, query):
        slug_filter = query.get("slug")
        if isinstance(slug_filter, dict) and "$in" in slug_filter:
            if doc.get("slug") not in slug_filter["$in"]:
                return False
        elif slug_filter and doc.get("slug") != slug_filter:
            return False
        if query.get("is_published") is True and doc.get("is_published") is not True:
            return False
        chapter_id = query.get("chapters.id")
        if chapter_id and not any(chapter.get("id") == chapter_id for chapter in doc.get("chapters") or []):
            return False
        return True

    def find(self, query, _projection=None):
        return FakeCursor([doc for doc in self.docs if self._matches(doc, query)])

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if self._matches(doc, query):
                if query.get("chapters.id") and projection and "chapters.$" in projection:
                    chapter_id = query["chapters.id"]
                    chapter = next((item for item in doc.get("chapters") or [] if item.get("id") == chapter_id), None)
                    return {"chapters": [chapter]} if chapter else None
                return doc
        return None

    async def count_documents(self, query):
        return len([doc for doc in self.docs if self._matches(doc, query)])


async def noop_cache_get(*_args, **_kwargs):
    return None


async def noop_cache_set(*_args, **_kwargs):
    return None


def install_fake_db(monkeypatch, docs):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=FakeBooks(docs)))
    monkeypatch.setattr(server, "_public_cache_get", noop_cache_get)
    monkeypatch.setattr(server, "_public_cache_set", noop_cache_set)
    monkeypatch.setattr(server, "_redis_cache_get", noop_cache_get)
    monkeypatch.setattr(server, "_redis_cache_set", noop_cache_set)


def test_empty_db_without_artifact_returns_no_fake_dracula(monkeypatch):
    install_fake_db(monkeypatch, [])
    monkeypatch.setattr(server, "load_dracula_artifact_book", lambda **_kwargs: None)

    result = asyncio.run(server.list_books())

    assert result == []


def test_empty_db_with_valid_artifact_returns_dracula_public_projection(monkeypatch):
    install_fake_db(monkeypatch, [])

    result = asyncio.run(server.list_books())

    assert [book["slug"] for book in result] == ["dracula"]
    assert result[0]["reader_enabled"] is True
    assert result[0]["preview_enabled"] is True
    assert result[0]["audio_enabled"] is False
    assert result[0]["audiobook_enabled"] is False


def test_db_missing_dracula_valid_artifact_returns_dracula_in_books(monkeypatch):
    install_fake_db(monkeypatch, [{"slug": "frankenstein", "is_published": True, "title": "Frankenstein"}])

    result = asyncio.run(server.list_books())

    assert [book["slug"] for book in result] == ["dracula"]


def test_incomplete_db_dracula_uses_approved_artifact(monkeypatch):
    install_fake_db(monkeypatch, [{"slug": "dracula", "title": "Dracula", "is_published": True}])

    result = asyncio.run(server.list_books())

    assert [book["slug"] for book in result if book["reader_enabled"]] == ["dracula"]
    assert result[0]["publication_status"] == "LIVE_APPROVED"


def test_db_dracula_without_approval_does_not_become_live_without_artifact(monkeypatch):
    install_fake_db(monkeypatch, [{"slug": "dracula", "title": "Dracula", "is_published": True}])
    monkeypatch.setattr(server, "load_dracula_artifact_book", lambda **_kwargs: None)
    monkeypatch.setattr(catalog_truth, "evidence_for_book", lambda _book: {})

    result = asyncio.run(server.list_books())

    assert result == []


def test_artifact_fallback_is_self_contained_without_legacy_evidence(monkeypatch):
    install_fake_db(monkeypatch, [])
    monkeypatch.setattr(catalog_truth, "evidence_for_book", lambda _book: {})

    books = asyncio.run(server.list_books())
    detail = asyncio.run(server.get_book("dracula"))
    manifest = asyncio.run(server._reader_book_manifest_doc("dracula"))

    assert [book["slug"] for book in books] == ["dracula"]
    assert detail["slug"] == "dracula"
    assert detail["reader_enabled"] is True
    assert detail["preview_enabled"] is True
    assert detail["audio_enabled"] is False
    assert "source_hash" not in detail
    assert "content_hash" not in detail
    assert "provenance_hash" not in detail
    assert manifest is not None
    assert len(manifest["chapters"]) == 27
    assert manifest["audio"]["enabled"] is False
    assert manifest["audio"]["assets"] == {}


def test_books_returns_exactly_one_live_readable_slug(monkeypatch):
    install_fake_db(monkeypatch, [])

    result = asyncio.run(server.list_books())

    live = [book["slug"] for book in result if book.get("reader_enabled")]
    assert live == ["dracula"]


def test_dracula_detail_returns_safe_public_book(monkeypatch):
    install_fake_db(monkeypatch, [])

    result = asyncio.run(server.get_book("dracula"))

    assert result["slug"] == "dracula"
    assert result["reader_enabled"] is True
    assert result["preview_enabled"] is True
    assert result["audio_enabled"] is False
    assert result["audiobook_enabled"] is False
    assert "rights_metadata" not in result
    assert "source_hash" not in result
    assert "content_hash" not in result
    assert "provenance_hash" not in result
    assert "audiobook_assets" not in result


def test_dracula_reader_manifest_returns_27_chapters(monkeypatch):
    install_fake_db(monkeypatch, [])

    manifest = asyncio.run(server._reader_book_manifest_doc("dracula"))

    assert manifest is not None
    assert len(manifest["chapters"]) == 27
    assert manifest["chapters"][0]["is_preview"] is True
    assert manifest["audio"]["enabled"] is False
    assert manifest["audio"]["assets"] == {}


def test_dracula_audiobook_endpoint_returns_404(monkeypatch):
    install_fake_db(monkeypatch, [])
    request = SimpleNamespace(headers={}, method="GET")

    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server._reader_book_audiobook_asset("dracula", "mp3", request))

    assert exc.value.status_code == 404


def test_kshudhita_manifest_remains_hidden(monkeypatch):
    install_fake_db(monkeypatch, [])

    result = asyncio.run(server._reader_book_manifest_doc("kshudhita-pashan"))

    assert result is None


def test_no_non_dracula_audio_fields_appear(monkeypatch):
    install_fake_db(monkeypatch, [])

    result = asyncio.run(server.list_books())

    assert all(book.get("slug") == "dracula" for book in result)
    assert all(book.get("audio_enabled") is False for book in result)
    assert all(not book.get("audio_url") for book in result)


def test_controlled_launch_status_endpoint_is_safe(monkeypatch):
    install_fake_db(monkeypatch, [])

    result = asyncio.run(server.controlled_launch_status())
    serialized = str(result)

    assert result["dracula_book_available"] is True
    assert result["dracula_manifest_available"] is True
    assert result["dracula_source"] == "artifact"
    assert result["audio_enabled_slugs"] == []
    assert "source_hash" not in serialized
    assert "content_hash" not in serialized
    assert "provenance_hash" not in serialized


def test_diagnostic_classifies_empty_books_and_404_detail():
    api = {
        "/healthz": {"status": 200},
        "/books": {"status": 200, "json": []},
        "/books/dracula": {"status": 404},
        "/reader/book/dracula/manifest": {"status": 404},
    }
    db_status = {"configured": False, "ok": False}
    artifact = {"available": True, "reader_manifest_exists": True}

    result = prod_dracula_diagnostic.classify_root_cause(api, db_status, artifact)

    assert result == "DRACULA_MISSING_FROM_DB"


def test_diagnostic_reports_self_contained_artifact_pack():
    artifact = prod_dracula_diagnostic.artifact_readiness()

    assert artifact["artifact_pack_available"] is True
    assert artifact["artifact_pack_self_contained_for_truth_gate"] is True
    assert artifact["fallback_requires_legacy_output_evidence"] is False


def test_diagnostic_holds_if_artifact_requires_legacy_output_evidence():
    api = {
        "/healthz": {"status": 200},
        "/books": {"status": 200, "json": []},
        "/books/dracula": {"status": 404},
        "/reader/book/dracula/manifest": {"status": 404},
    }
    db_status = {"configured": False, "ok": False}
    artifact = {"available": True, "fallback_requires_legacy_output_evidence": True}

    result = prod_dracula_diagnostic.classify_root_cause(api, db_status, artifact)

    assert result == "HOLD_FOR_FIXES"


def test_repair_dry_run_does_not_mutate(tmp_path, monkeypatch):
    monkeypatch.setattr(repair_dracula_production_record, "connect_books_collection", lambda: (None, "test db unavailable"))

    report = repair_dracula_production_record.run_repair(apply=False, output_dir=tmp_path)

    assert report["mutation_performed"] is False
    assert report["mode"] == "dry-run"
    assert (tmp_path / "dracula_repair_dry_run.json").exists()


def test_repair_apply_refuses_without_approved_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(repair_dracula_production_record, "dracula_artifact_status", lambda: {"available": False, "issues": ["missing"]})
    monkeypatch.setattr(repair_dracula_production_record, "safe_dracula_document", lambda: None)

    report = repair_dracula_production_record.run_repair(apply=True, output_dir=tmp_path)

    assert report["mutation_performed"] is False
    assert any("artifact" in blocker.lower() for blocker in report["blockers"])


def test_repair_document_is_dracula_only():
    desired = repair_dracula_production_record.safe_dracula_document()

    assert desired is not None
    assert desired["slug"] == "dracula"
    assert len(desired["chapters"]) == 27
    assert desired["audio_enabled"] is False
    assert desired["audiobook_enabled"] is False
