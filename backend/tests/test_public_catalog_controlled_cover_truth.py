from __future__ import annotations

import asyncio
import copy
import os
from types import SimpleNamespace

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "public-catalog-cover-truth-test-secret")

from backend import catalog_truth, server


SLUG = "jekyll-and-hyde"


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, *_args, **_kwargs):
        return list(self.docs)


class SameSlugBooks:
    def __init__(self, doc):
        self.doc = doc

    def find(self, _query, _projection=None):
        return FakeCursor([self.doc])

    async def find_one(self, query, _projection=None):
        return self.doc if query.get("slug") == SLUG else None


async def no_cache(*_args, **_kwargs):
    return None


def canonical_jekyll():
    artifact = catalog_truth.load_controlled_artifact_book(
        SLUG,
        include_content=False,
    )
    assert artifact is not None
    assert artifact["cover_image_url"]
    assert artifact["back_cover_image_url"]
    return artifact


def stale_live_mongo_summary():
    stale = copy.deepcopy(canonical_jekyll())
    stale.update(
        {
            "title": "Stale database title",
            "author": "Stale database author",
            "cover_url": "",
            "cover_image_url": "",
            "thumbnail_url": "",
            "back_cover_url": "https://example.com/stale-back-cover.jpg",
            "back_cover_image_url": "https://example.com/stale-back-cover.jpg",
            "back_cover_thumbnail_url": "",
            "audio_enabled": True,
            "audiobook_enabled": True,
            "audiobook_release_gate": "APPROVED",
            "audio_qa_status": "QA_PASSED",
            "audiobook_assets": {
                "mp3": "https://example.com/unapproved-jekyll.mp3",
            },
            "admin_pinned": True,
            "home_shelf_rank": 7,
        }
    )
    return stale


def install_db(monkeypatch, doc):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=SameSlugBooks(doc)))
    monkeypatch.setattr(server, "_public_cache_get", no_cache)
    monkeypatch.setattr(server, "_public_cache_set", no_cache)


def assert_canonical_cover_and_safe_release_truth(book, canonical):
    assert book["slug"] == SLUG
    assert book["title"] == canonical["title"]
    assert book["author"] == canonical["author"]
    assert book["cover_url"] == canonical["cover_url"]
    assert book["cover_image_url"] == canonical["cover_image_url"]
    assert book["thumbnail_url"] == canonical["thumbnail_url"]
    assert book["back_cover_url"] == canonical["back_cover_url"]
    assert book["back_cover_image_url"] == canonical["back_cover_image_url"]
    assert book["back_cover_thumbnail_url"] == canonical["back_cover_thumbnail_url"]
    assert book["reader_enabled"] is True
    assert book["audio_enabled"] is False
    assert book["audiobook_enabled"] is False
    assert book["audio_url"] == ""
    assert book["audiobook_release_gate"] == ""
    assert book["audio_qa_status"] == ""
    assert "audiobook_assets" not in book


def test_public_books_list_prefers_controlled_covers_over_blank_stale_mongo(monkeypatch):
    canonical = canonical_jekyll()
    install_db(monkeypatch, stale_live_mongo_summary())

    result = asyncio.run(server.list_books())
    by_slug = {book["slug"]: book for book in result}

    assert_canonical_cover_and_safe_release_truth(by_slug[SLUG], canonical)


def test_public_book_detail_prefers_controlled_covers_over_blank_stale_mongo(monkeypatch):
    canonical = canonical_jekyll()
    install_db(monkeypatch, stale_live_mongo_summary())

    result = asyncio.run(server.get_book(SLUG))

    assert_canonical_cover_and_safe_release_truth(result, canonical)


def test_controlled_merge_preserves_only_allowlisted_database_editorial_fields():
    canonical = canonical_jekyll()
    stale = stale_live_mongo_summary()

    merged = server._merge_controlled_publication_truth(
        stale,
        canonical,
        slug=SLUG,
    )

    assert merged["admin_pinned"] is True
    assert merged["home_shelf_rank"] == 7
    assert merged["cover_image_url"] == canonical["cover_image_url"]
    assert merged["back_cover_image_url"] == canonical["back_cover_image_url"]
    assert merged["audio_enabled"] is False
    assert merged["audiobook_enabled"] is False
    assert "audiobook_release_gate" not in merged
    assert "audio_qa_status" not in merged


def test_public_catalog_cache_namespace_is_rotated_without_changing_audio_gate():
    cache_key = server._public_cache_key("book_detail", slug=SLUG)

    assert '"catalog_truth": "controlled-covers-v1"' in cache_key
    assert '"truth_gate": "audio-contract-v13"' in cache_key
