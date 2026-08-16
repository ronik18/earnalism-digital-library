from __future__ import annotations

import asyncio
import copy
import os
from types import SimpleNamespace

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "public-catalog-cover-truth-test-secret")

from backend import catalog_truth, server


SLUG = "jekyll-and-hyde"
GIFT_SLUG = "the-gift-of-the-magi"


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


async def no_cache_write(*_args, **_kwargs):
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


def test_controlled_merge_accepts_only_server_owned_conveyor_audio_release():
    canonical = canonical_jekyll()
    released = stale_live_mongo_summary()
    released.update(
        {
            "audio_enabled": True,
            "audiobook_enabled": True,
            "generate_audiobook": True,
            "audio_status": "AVAILABLE",
            "audiobook_release_gate": "APPROVED",
            "audio_qa_status": "QA_PASSED",
            "audiobook_provider": "kokoro",
            "audiobook_voice": "bm_george",
            "audiobook_assets": {
                "mp3": "https://s3.us-west-004.backblazeb2.com/private/released.mp3",
            },
            "audiobook": {
                "release_gate": "APPROVED",
                "qa_status": "QA_PASSED",
                "assets": {"mp3": "b2://private/released.mp3"},
            },
            "audiobook_release_conveyor": {
                "schema_version": server.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
                "reader_release_approved": True,
                "audio_release_approved": True,
                "audio_public_release": "APPROVED",
                "audio_qa_status": "QA_PASSED",
                "audio_sha256": "a" * 64,
            },
        }
    )

    merged = server._merge_controlled_publication_truth(released, canonical, slug=SLUG)
    public = server.public_book_projection(merged)

    assert merged["cover_image_url"] == canonical["cover_image_url"]
    assert public["audio_enabled"] is True
    assert public["audiobook_enabled"] is True
    assert public["audio_url"] == f"/api/reader/book/{SLUG}/audiobook"
    assert public["audiobook_release_gate"] == "APPROVED"
    assert public["audio_qa_status"] == "QA_PASSED"


def test_audiobook_release_uses_validated_controlled_reader_truth_for_legacy_shell():
    canonical = catalog_truth.load_controlled_artifact_book(
        "gitanjali",
        include_content=False,
    )
    assert canonical is not None
    legacy_shell = {
        "slug": "gitanjali",
        "title": "Gitanjali",
        "is_published": False,
        "audiobook_enabled": False,
        "chapters": [{"title": "Legacy shell chapter"}],
    }

    resolved = server._audiobook_release_reader_truth(legacy_shell, "gitanjali")

    assert resolved["is_published"] is True
    assert resolved["approved_to_publish"] is True
    assert resolved["publication_status"] == "LIVE_APPROVED"
    assert resolved["qa_status"] == "QA_PASSED"
    assert resolved["cover_image_url"]
    assert len(resolved["chapters"]) == 104
    assert resolved["audiobook_manuscript_sha256"] == (
        "6a14b35ae1ea3d6cc37bb384ca0f96b1f98bb6ddf1ba9f6c535ab3d1f3e442ca"
    )
    assert resolved["audio_enabled"] is False
    assert resolved["audiobook_enabled"] is False
    assert server.rights_publish_blockers(resolved) == []


def test_audiobook_release_falls_back_to_database_when_no_controlled_artifact(monkeypatch):
    database_book = {"slug": "ordinary-book", "is_published": True}
    monkeypatch.setattr(server, "load_controlled_artifact_book", lambda *_args, **_kwargs: None)

    assert server._audiobook_release_reader_truth(database_book, "ordinary-book") is database_book


def test_controlled_reader_audio_truth_merges_exact_server_owned_release(monkeypatch):
    canonical = canonical_jekyll()
    released = stale_live_mongo_summary()
    released.update(
        {
            "audio_enabled": True,
            "audiobook_enabled": True,
            "generate_audiobook": True,
            "audio_status": "AVAILABLE",
            "audiobook_release_gate": "APPROVED",
            "audio_qa_status": "QA_PASSED",
            "audiobook_provider": "kokoro",
            "audiobook_voice": "bm_george",
            "audiobook_assets": {"mp3": "b2://private/released.mp3"},
            "audiobook_release_conveyor": {
                "schema_version": server.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
                "reader_release_approved": True,
                "audio_release_approved": True,
                "audio_public_release": "APPROVED",
                "audio_qa_status": "QA_PASSED",
                "audio_sha256": "a" * 64,
            },
        }
    )
    monkeypatch.setattr(server, "_controlled_artifact_doc", lambda *_args, **_kwargs: canonical)

    resolved = server._reader_audio_truth_doc(released, SLUG)

    assert resolved is not None
    assert resolved["audio_enabled"] is True
    assert resolved["audiobook_enabled"] is True
    assert resolved["audiobook_release_gate"] == "APPROVED"


def test_controlled_reader_manifest_resolves_generic_server_owned_release(monkeypatch):
    released = stale_live_mongo_summary()
    released.update(
        {
            "audio_enabled": True,
            "audiobook_enabled": True,
            "generate_audiobook": True,
            "audio_status": "AVAILABLE",
            "audiobook_release_gate": "APPROVED",
            "audio_qa_status": "QA_PASSED",
            "audiobook_provider": "kokoro",
            "audiobook_voice": "af_heart",
            "audiobook_assets": {
                "mp3": "https://s3.us-west-004.backblazeb2.com/private/released.mp3",
            },
            "audiobook_release_conveyor": {
                "schema_version": server.AUDIOBOOK_RELEASE_CONVEYOR_SCHEMA,
                "reader_release_approved": True,
                "audio_release_approved": True,
                "audio_public_release": "APPROVED",
                "audio_qa_status": "QA_PASSED",
                "audio_sha256": "b" * 64,
            },
        }
    )
    monkeypatch.setattr(server, "db", SimpleNamespace(books=SameSlugBooks(released)))
    monkeypatch.setattr(server, "_redis_cache_get", no_cache)
    monkeypatch.setattr(server, "_redis_cache_set", no_cache_write)

    manifest = asyncio.run(server._reader_book_manifest_doc(SLUG))

    assert manifest is not None
    assert manifest["book"]["audio_enabled"] is True
    assert manifest["book"]["audiobook_enabled"] is True
    assert manifest["book"]["audio_url"] == f"/api/reader/book/{SLUG}/audiobook"
    assert manifest["audio"]["enabled"] is True
    assert manifest["audio"]["provider"] == "kokoro"
    assert manifest["audio"]["voice"] == "af_heart"
    assert manifest["audio"]["assets"]["mp3"] == f"/api/reader/book/{SLUG}/audiobook"


def test_public_catalog_cache_namespace_is_rotated_without_changing_audio_gate():
    cache_key = server._public_cache_key("book_detail", slug=SLUG)

    assert '"catalog_truth": "controlled-covers-v1"' in cache_key
    assert '"truth_gate": "audio-contract-v16"' in cache_key


def test_reader_catalog_cache_namespaces_rotate_with_public_catalog_truth(monkeypatch):
    seen = []

    async def capture_cache_key(namespace, key):
        seen.append((namespace, key))
        return {"cached": True}

    async def fixed_generation():
        return 37

    monkeypatch.setattr(server, "_redis_cache_get", capture_cache_key)
    monkeypatch.setattr(server, "_reader_content_cache_generation_value", fixed_generation)

    assert asyncio.run(server._reader_book_access_doc(SLUG)) == {"cached": True}
    assert asyncio.run(server._reader_book_manifest_doc(SLUG)) == {"cached": True}

    assert seen == [
        (
            "reader-content",
            "book-access:audio-contract-v16:controlled-covers-v1:37:public:jekyll-and-hyde",
        ),
        (
            "reader-manifest",
            "book-manifest:audio-contract-v16:controlled-covers-v1:chapter-index.v1:37:public:jekyll-and-hyde",
        ),
    ]


def test_gift_reader_manifest_uses_exact_canonical_covers_and_keeps_audio_hidden(monkeypatch):
    canonical = catalog_truth.load_controlled_artifact_book(
        GIFT_SLUG,
        include_content=True,
    )
    assert canonical is not None
    monkeypatch.setattr(server, "db", SimpleNamespace(books=SameSlugBooks({})))
    monkeypatch.setattr(server, "_redis_cache_get", no_cache)
    monkeypatch.setattr(server, "_redis_cache_set", no_cache_write)

    manifest = asyncio.run(server._reader_book_manifest_doc(GIFT_SLUG))

    assert manifest is not None
    assert manifest["book"]["slug"] == GIFT_SLUG
    assert manifest["book"]["title"] == canonical["title"] == "The Gift of the Magi"
    assert manifest["book"]["author"] == canonical["author"] == "O. Henry"
    assert manifest["book"]["cover_url"] == canonical["cover_url"]
    assert manifest["book"]["cover_image_url"] == canonical["cover_image_url"]
    assert manifest["book"]["back_cover_url"] == canonical["back_cover_url"]
    assert manifest["book"]["back_cover_image_url"] == canonical["back_cover_image_url"]
    assert manifest["book"]["audio_enabled"] is False
    assert manifest["book"]["audiobook_enabled"] is False
    assert manifest["audio"]["enabled"] is False
    assert manifest["audio"]["assets"] == {}
    assert manifest["audio"]["url"] == ""


def test_reader_manifest_ignores_pre_catalog_truth_namespace_entry(monkeypatch):
    canonical = catalog_truth.load_controlled_artifact_book(
        GIFT_SLUG,
        include_content=True,
    )
    assert canonical is not None
    monkeypatch.setattr(server, "db", SimpleNamespace(books=SameSlugBooks({})))
    stale_key = "book-manifest:audio-contract-v13:562:public:the-gift-of-the-magi"
    stale_manifest = {
        "book": {
            "slug": GIFT_SLUG,
            "title": "Stale cached title",
            "cover_url": "https://example.com/stale-front.jpg",
            "back_cover_url": "https://example.com/stale-back.jpg",
        }
    }
    seen = []

    async def seeded_cache(namespace, key):
        seen.append((namespace, key))
        return stale_manifest if key == stale_key else None

    async def fixed_generation():
        return 562

    monkeypatch.setattr(server, "_redis_cache_get", seeded_cache)
    monkeypatch.setattr(server, "_redis_cache_set", no_cache_write)
    monkeypatch.setattr(server, "_reader_content_cache_generation_value", fixed_generation)

    manifest = asyncio.run(server._reader_book_manifest_doc(GIFT_SLUG))

    assert manifest is not None
    assert seen == [
        (
            "reader-manifest",
            "book-manifest:audio-contract-v16:controlled-covers-v1:chapter-index.v1:562:public:the-gift-of-the-magi",
        )
    ]
    assert seen[0][1] != stale_key
    assert manifest["book"]["title"] == canonical["title"]
    assert manifest["book"]["cover_url"] == canonical["cover_url"]
    assert manifest["book"]["back_cover_url"] == canonical["back_cover_url"]
    assert manifest["audio"]["enabled"] is False
