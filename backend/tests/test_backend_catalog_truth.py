from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "catalog-truth-test-secret")

from backend import catalog_truth
from backend import server


def dracula_book(**overrides):
    book = {
        "id": "book-dracula",
        "slug": "dracula",
        "title": "Dracula",
        "author": "Bram Stoker",
        "category_slug": "gothic-fiction",
        "short_description": "A controlled launch classic.",
        "is_published": True,
        "rights_metadata": {
            "rights_tier": "A",
            "verification_status": "approved",
            "blocked_reason": "",
            "source_url": "https://www.gutenberg.org/ebooks/345",
            "source_name": "Project Gutenberg",
            "source_license": "Project Gutenberg License",
        },
        "source_hash": "source-hash",
        "content_hash": "content-hash",
        "provenance_hash": "provenance-hash",
        "qa_status": "QA_PASSED",
        "approved_to_publish": True,
        "publication_status": "LIVE_APPROVED",
        "audiobook_enabled": True,
        "audiobook_assets": {"mp3": "https://cdn.example.com/dracula.mp3"},
        "chapters": [
            {
                "id": "chapter-1",
                "title": "Chapter 1",
                "order": 1,
                "is_preview": True,
                "content": "Reader-facing chapter body should never leak in metadata projection.",
            }
        ],
    }
    book.update(overrides)
    return book


def pipeline_book(**overrides):
    book = {
        "id": "book-kshudhita",
        "slug": "kshudhita-pashan",
        "title": "Kshudhita Pashan",
        "author": "Rabindranath Tagore",
        "category_slug": "gothic-fiction",
        "short_description": "Pipeline-only Bengali gothic candidate.",
        "is_published": True,
        "pipeline_stage": "PIPELINE_ONLY",
        "rights_metadata": {
            "rights_tier": "A",
            "verification_status": "pending",
            "blocked_reason": "",
        },
        "chapters": [{"id": "chapter-1", "content": "Pipeline source text"}],
    }
    book.update(overrides)
    return book


def test_dracula_is_the_only_live_approved_book():
    assert catalog_truth.is_live_approved_book(dracula_book()) is True
    assert catalog_truth.is_live_approved_book(dracula_book(slug="frankenstein")) is False
    assert catalog_truth.is_live_approved_book(dracula_book(rights_metadata={"rights_tier": "B"})) is False


def test_dracula_projection_enables_reader_preview_but_disables_audio():
    projected = catalog_truth.public_book_projection(dracula_book())

    assert projected["publication_status"] == "LIVE_APPROVED"
    assert projected["reader_enabled"] is True
    assert projected["preview_enabled"] is True
    assert projected["reader_url"] == "/reader/dracula"
    assert projected["preview_url"] == "/reader/dracula"
    assert projected["audio_enabled"] is False
    assert projected["audiobook_enabled"] is False
    assert projected["audio_url"] == ""
    assert projected["cta_label"] == "Start Dracula"


def test_projection_removes_private_rights_audio_and_chapter_content():
    projected = catalog_truth.public_book_projection(dracula_book())

    assert "rights_metadata" not in projected
    assert "source_hash" not in projected
    assert "content_hash" not in projected
    assert "provenance_hash" not in projected
    assert "audiobook_assets" not in projected
    assert "audiobook" not in projected
    assert "content" not in projected["chapters"][0]


def test_kshudhita_is_pipeline_only_with_notify_ctas():
    projected = catalog_truth.public_book_projection(pipeline_book())

    assert projected["publication_status"] == "PIPELINE_CANDIDATE"
    assert projected["reader_enabled"] is False
    assert projected["preview_enabled"] is False
    assert projected["audio_enabled"] is False
    assert projected["reader_url"] == ""
    assert projected["preview_url"] == ""
    assert projected["cta_label"] == "Notify Me"
    assert projected["secondary_cta_label"] == "Reading Circle"


def test_unapproved_book_cannot_expose_reader_preview_or_audio():
    book = dracula_book(slug="frankenstein", title="Frankenstein")

    assert catalog_truth.can_expose_reader(book) is False
    assert catalog_truth.can_expose_preview(book) is False
    assert catalog_truth.can_expose_audio(book) is False
    assert catalog_truth.public_book_projection(book)["reader_enabled"] is False


def test_missing_traceability_blocks_live_status(monkeypatch):
    monkeypatch.setattr(catalog_truth, "evidence_for_book", lambda book: {})
    book = dracula_book(source_hash="")

    assert catalog_truth.normalize_book_publication_status(book) != "LIVE_APPROVED"
    assert catalog_truth.can_expose_reader(book) is False


def test_blocked_reason_quarantines_book():
    book = dracula_book(rights_metadata={**dracula_book()["rights_metadata"], "blocked_reason": "unsafe"})

    assert catalog_truth.normalize_book_publication_status(book) == "QUARANTINE"
    assert catalog_truth.can_expose_reader(book) is False


def test_catalog_truth_summary_flags_unapproved_sitemap_entries():
    rows = [
        catalog_truth.catalog_truth_row(dracula_book(), sitemap_urls={"https://theearnalism.com/book/dracula"}),
        catalog_truth.catalog_truth_row(pipeline_book(), sitemap_urls={"https://theearnalism.com/book/kshudhita-pashan"}),
    ]

    summary = catalog_truth.catalog_truth_summary(rows)

    assert summary["live_approved_count"] == 1
    assert summary["dracula_only_live_approved"] is True
    assert summary["pipeline_candidate_count"] == 1
    assert summary["unapproved_sitemap_count"] == 1
    assert "Unapproved sitemap entries detected" in summary["launch_blockers"]


def test_live_approved_mongo_query_preserves_rights_and_search_or():
    query = catalog_truth.live_approved_mongo_query(
        {"$or": [{"title": {"$regex": "Dracula", "$options": "i"}}]}
    )

    assert query["slug"] == {"$in": ["dracula"]}
    assert query["is_published"] is True
    assert query["rights_metadata.rights_tier"] == "A"
    assert query["rights_metadata.verification_status"] == "approved"
    assert "$or" not in query
    assert query["$and"][1]["$or"][0]["title"] == {"$regex": "Dracula", "$options": "i"}


def test_server_controlled_public_query_uses_catalog_truth():
    assert server._controlled_public_book_query() == catalog_truth.live_approved_mongo_query()
    assert server._is_controlled_public_slug("Dracula") is True
    assert server._is_controlled_public_slug("frankenstein") is False


def test_reader_manifest_audio_is_disabled_even_when_assets_exist():
    audio = server._reader_manifest_audio(dracula_book(), "dracula")

    assert audio["enabled"] is False
    assert audio["assets"] == {}
    assert audio["url"] == ""
    assert audio["provider"] == ""


def test_reader_manifest_non_dracula_returns_none():
    result = asyncio.run(server._reader_book_manifest_doc("kshudhita-pashan"))

    assert result is None


def test_public_audiobook_endpoint_404s_non_dracula_without_db_call():
    request = SimpleNamespace(headers={}, method="GET")

    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server._reader_book_audiobook_asset("kshudhita-pashan", "mp3", request))

    assert exc.value.status_code == 404


def test_public_audiobook_endpoint_404s_dracula_when_audio_disabled(monkeypatch):
    class FakeBooks:
        async def find_one(self, query, projection):
            assert query["slug"] == "dracula"
            return dracula_book()

    fake_db = SimpleNamespace(books=FakeBooks())
    monkeypatch.setattr(server, "db", fake_db)
    request = SimpleNamespace(headers={}, method="GET")

    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server._reader_book_audiobook_asset("dracula", "mp3", request))

    assert exc.value.status_code == 404
    assert "Audiobook asset" in exc.value.detail


def test_sitemap_truth_is_dracula_only_for_book_routes():
    sitemap = (catalog_truth.ROOT / "frontend" / "public" / "sitemap.xml").read_text(encoding="utf-8")

    assert "/book/dracula" in sitemap
    assert "/reader/" not in sitemap
    assert "/book/frankenstein" not in sitemap
    assert "/book/kshudhita-pashan" not in sitemap


def test_catalog_truth_rows_keep_audio_false_for_every_status():
    rows = [
        catalog_truth.catalog_truth_row(dracula_book()),
        catalog_truth.catalog_truth_row(pipeline_book()),
        catalog_truth.catalog_truth_row(dracula_book(slug="devdas", title="Devdas")),
    ]

    assert all(row["audio_enabled"] is False for row in rows)
