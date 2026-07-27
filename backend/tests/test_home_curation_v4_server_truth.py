from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "home-curation-v4-server-truth-test-secret")

from backend import catalog_truth, server


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, *_args, **_kwargs):
        return list(self.docs)


class StaleSummaryBooks:
    def __init__(self, docs):
        self.docs = list(docs)

    def find(self, _query, projection):
        assert "audiobook_assets" not in projection
        assert "audiobook_release_gate" not in projection
        return FakeCursor(self.docs)


async def no_cache(*_args, **_kwargs):
    return None


def test_controlled_truth_replaces_same_slug_summary_and_preserves_only_editorial_fields(monkeypatch):
    stale = {
        "slug": "book-2b9853ec52",
        "title": "Stale title",
        "author": "Stale author",
        "audio_enabled": False,
        "audiobook_enabled": False,
        "cover_image_url": "https://example.com/stale.png",
        "admin_pinned": True,
        "home_shelf_rank": 2,
    }
    artifact = catalog_truth.load_controlled_artifact_book("book-2b9853ec52")
    assert artifact is not None
    monkeypatch.setattr(server, "CONTROLLED_LIVE_BOOK_SLUGS", ("book-2b9853ec52",))
    monkeypatch.setattr(
        server,
        "_controlled_artifact_doc",
        lambda slug, include_content=False: artifact if slug == "book-2b9853ec52" else None,
    )

    resolved = server._home_curation_controlled_truth_docs([stale])

    assert len(resolved) == 1
    assert resolved[0]["title"] == artifact["title"]
    assert resolved[0]["author"] == artifact["author"]
    assert resolved[0]["cover_image_url"] == artifact["cover_image_url"]
    assert catalog_truth.can_expose_audio(resolved[0]) is True
    assert resolved[0]["admin_pinned"] is True
    assert resolved[0]["home_shelf_rank"] == 2


def test_home_curated_route_restores_all_sprint1_readers_and_four_approved_audiobooks(monkeypatch):
    stale_summary = {
        "slug": "book-2b9853ec52",
        "title": "দুই বিঘা জমি",
        "author": "রবীন্দ্রনাথ ঠাকুর",
        "is_published": True,
        "publication_status": "LIVE_APPROVED",
        "approved_to_publish": True,
    }
    monkeypatch.setattr(server, "db", SimpleNamespace(books=StaleSummaryBooks([stale_summary])))
    monkeypatch.setattr(server, "_public_cache_get", no_cache)
    monkeypatch.setattr(server, "_public_cache_set", no_cache)
    monkeypatch.setattr(server, "_redis_cache_get", no_cache)
    monkeypatch.setattr(server, "_redis_cache_set", no_cache)

    payload = asyncio.run(server.get_home_curated())

    assert payload["source"]["sprint1_active_count"] == 32
    assert payload["source"]["reader_enabled_count"] >= 32
    assert payload["source"]["approved_audiobook_count"] == 4
    assert {
        book["slug"] for book in payload["shelves"]["approved_audiobooks"]
    } == {
        "book-2b9853ec52",
        "a-ghost-story",
        "sredni-vashtar",
        "the-open-window",
    }
    by_slug = {
        book["slug"]: book
        for shelf in payload["literary_shelves"]
        for book in [*shelf["visible_books"], *shelf["reserve_books"]]
    }
    by_slug.update(
        {book["slug"]: book for book in payload["shelves"]["approved_audiobooks"]}
    )
    assert by_slug["book-2b9853ec52"]["audiobook_enabled"] is True
    assert (
        by_slug["book-2b9853ec52"]["audiobook_url"]
        == "/api/reader/book/book-2b9853ec52/audiobook"
    )
