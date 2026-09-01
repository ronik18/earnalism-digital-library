from __future__ import annotations

import asyncio
import os

import pytest


os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "sprint1-source-cleanup-test-secret")

from backend import catalog_truth, server


APPROVED_AUDIO_SLUGS = set(catalog_truth.AUDIO_ENABLED_SLUGS)
HIDDEN_PROXY_SAMPLES = (
    "bn-066",
    "book-d19e96859f",
    "book-f5d593e1f4",
    "muchiram-gurer-jibanchorit",
    "dsires-baby",
)


def test_live_controlled_artifacts_are_available_and_public_audio_is_fail_closed():
    for slug in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS:
        artifact = catalog_truth.load_controlled_artifact_book(slug)
        assert artifact is not None, slug
        audio = server._reader_manifest_audio(artifact, slug)

        if slug in APPROVED_AUDIO_SLUGS:
            assert audio["enabled"] is True, slug
            assert audio["release_gate"] == "APPROVED", slug
            assert audio["qa_status"] == "QA_PASSED", slug
            # Public reader metadata is intentionally non-playable.  The
            # lease-authorized endpoint is separately covered by the current
            # zero-public-audio contract tests.
            assert audio["assets"] == {}, slug
            assert audio["url"] == "", slug
            continue

        assert audio["enabled"] is False, slug
        assert audio["provider"] == "", slug
        assert audio["voice"] == "", slug
        assert audio["url"] == "", slug
        assert audio["assets"] == {}, slug
        assert audio["release_gate"] == "", slug
        assert audio["qa_status"] == "", slug


def test_historical_excluded_book_is_not_a_runtime_audio_artifact():
    slug = "book-2b9853ec52"
    status = catalog_truth.controlled_artifact_status(slug)

    assert slug in catalog_truth.PUBLIC_CATALOG_EXCLUDED_SLUGS
    assert slug not in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS
    assert slug not in catalog_truth.AUDIO_ENABLED_SLUGS
    assert status["available"] is False
    assert catalog_truth.load_controlled_artifact_book(slug) is None


def test_runtime_artifact_validation_uses_the_selected_controlled_source_only():
    # checksum_manifest.json is historical publication evidence, not the
    # runtime truth gate.  Validate the selected runtime artifacts through the
    # catalog authority; packaged deployment copies are covered separately by
    # test_backend_catalog_truth.py.
    for slug in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS:
        status = catalog_truth.controlled_artifact_status(slug)
        assert status["available"] is True, (slug, status["issues"])
        assert status["reader_issues"] == [], slug
        assert status["audio_issues"] == [], slug


class EmptyBooks:
    async def find_one(self, *_args, **_kwargs):
        return None


class StaleControlledChapterBooks:
    async def find_one(self, *_args, **_kwargs):
        return {
            "slug": "book-edfcf810c5",
            "chapters": [
                {
                    "id": "chapter-001",
                    "title": "ক্ষুধিত পাষাণ",
                    "order": 1,
                    "is_preview": True,
                    "content": "STALE DATABASE TITLE-PAGE WRAPPER",
                }
            ],
        }


async def no_reader_cache(*_args, **_kwargs):
    return None


async def ignore_reader_cache(*_args, **_kwargs):
    return None


def test_public_reader_prefers_canonical_chapter_over_stale_database(monkeypatch):
    monkeypatch.setattr(server, "db", type("DB", (), {"books": StaleControlledChapterBooks()})())
    monkeypatch.setattr(server, "_redis_cache_get", no_reader_cache)
    monkeypatch.setattr(server, "_redis_cache_set", ignore_reader_cache)

    content = asyncio.run(server._reader_chapter_content("book-edfcf810c5", "chapter-001"))
    manifest = asyncio.run(server._reader_book_manifest_doc("book-edfcf810c5"))

    assert content.startswith("<p>গাড়িটি আসিয়া জংশনে থামিলে")
    assert content.endswith("</p>")
    assert "STALE DATABASE TITLE-PAGE WRAPPER" not in content
    assert "<script" not in content.lower()
    assert "javascript:" not in content.lower()
    assert "Wikisource" not in content
    assert "Project Gutenberg" not in content
    assert "https://" not in content
    assert manifest is not None
    assert manifest["chapters"][0]["content_version"] == server._reader_chapter_content_version(
        catalog_truth.load_controlled_artifact_book("book-edfcf810c5", include_content=True)["chapters"][0]
    )


def test_admin_reader_keeps_database_preview_source(monkeypatch):
    monkeypatch.setattr(server, "db", type("DB", (), {"books": StaleControlledChapterBooks()})())
    monkeypatch.setattr(server, "_redis_cache_get", no_reader_cache)
    monkeypatch.setattr(server, "_redis_cache_set", ignore_reader_cache)

    content = asyncio.run(
        server._reader_chapter_content("book-edfcf810c5", "chapter-001", admin_preview=True)
    )

    assert content == "<p>STALE DATABASE TITLE-PAGE WRAPPER</p>"
    assert "<script" not in content.lower()


def test_public_preview_cache_is_bound_to_requested_content_version(monkeypatch):
    book = {
        "slug": "book-edfcf810c5",
        "chapters": [
            {
                "id": "chapter-001",
                "title": "ক্ষুধিত পাষাণ",
                "order": 1,
                "is_preview": True,
            }
        ],
    }
    cache = {}

    async def access_doc(*_args, **_kwargs):
        return book

    async def chapter_content(*_args, **_kwargs):
        return "গাড়িটি আসিয়া জংশনে থামিলে"

    async def cache_get(key):
        return cache.get(key)

    async def cache_set(key, value):
        cache[key] = value

    monkeypatch.setattr(server, "_reader_book_access_doc", access_doc)
    monkeypatch.setattr(server, "_reader_chapter_content", chapter_content)
    monkeypatch.setattr(server, "_public_cache_get", cache_get)
    monkeypatch.setattr(server, "_public_cache_set", cache_set)

    request = server.Request({"type": "http", "method": "GET", "headers": []})
    first = asyncio.run(
        server.reader_get_chapter(
            "book-edfcf810c5",
            "chapter-001",
            request,
            server.Response(),
            v=None,
            principal=None,
        )
    )
    versioned = asyncio.run(
        server.reader_get_chapter(
            "book-edfcf810c5",
            "chapter-001",
            request,
            server.Response(),
            v="canonical-manifest-version",
            principal=None,
        )
    )

    assert first["chapter"]["content_version"] != "canonical-manifest-version"
    assert versioned["chapter"]["content_version"] == "canonical-manifest-version"
    assert len(cache) == 2


@pytest.mark.parametrize("slug", HIDDEN_PROXY_SAMPLES)
def test_hidden_sprint1_audiobook_proxies_return_404(monkeypatch, slug: str):
    monkeypatch.setattr(server, "db", type("DB", (), {"books": EmptyBooks()})())
    request = server.Request({"type": "http", "method": "GET", "headers": []})
    loop = asyncio.new_event_loop()

    try:
        with pytest.raises(server.HTTPException) as exc_info:
            loop.run_until_complete(server._reader_book_audiobook_asset(slug, "mp3", request))
    finally:
        loop.close()

    assert exc_info.value.status_code == 404
