from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path

import pytest


os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "sprint1-source-cleanup-test-secret")

from backend import catalog_truth, server


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "internal" / "audiobook_lab" / "sprint1_publication" / "sprint1_publication_matrix.json"
PACKET_ROOTS = (
    ROOT / "backend" / "data" / "controlled_publications",
    ROOT / "data" / "controlled_publications",
)
APPROVED_AUDIO_SLUGS = {"book-2b9853ec52", "a-ghost-story", "sredni-vashtar", "the-open-window"}
CLEANED_METADATA_SLUGS = {
    "alices-adventures-in-wonderland",
    "nishkriti",
    "book-f5d593e1f4",
    "muchiram-gurer-jibanchorit",
}
HIDDEN_PROXY_SAMPLES = (
    "bn-066",
    "book-d19e96859f",
    "book-f5d593e1f4",
    "muchiram-gurer-jibanchorit",
    "dsires-baby",
)
APPROVED_MP3_SUFFIXES = {
    "book-2b9853ec52": "book-2b9853ec52_mp3_a974819392d7.mp3",
    "a-ghost-story": "a-ghost-story_mp3_c0e52985ee1e.mp3",
    "sredni-vashtar": "sredni-vashtar_mp3_2b328a80b906.mp3",
    "the-open-window": "the-open-window_mp3_b23e6720a243.mp3",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def active_sprint1_slugs() -> list[str]:
    rows = read_json(MATRIX)["titles"]
    return [row["slug"] for row in rows if row.get("sprint1_audio_target") is True]


def packet_paths(slug: str, filename: str) -> list[Path]:
    return [path for root in PACKET_ROOTS if (path := root / slug / filename).exists()]


def assert_checksum_manifest(packet: Path) -> None:
    manifest = read_json(packet / "checksum_manifest.json")
    for entry in manifest["files"]:
        if entry["file"] == "checksum_manifest.json":
            continue
        artifact = packet / entry["file"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["sha256"]


def test_active_sprint1_manifest_audio_truth_is_fail_closed_except_approved_titles():
    slugs = active_sprint1_slugs()

    assert len(slugs) == 32
    for slug in slugs:
        artifact = catalog_truth.load_controlled_artifact_book(slug)
        assert artifact is not None, slug
        audio = server._reader_manifest_audio(artifact, slug)

        if slug in APPROVED_AUDIO_SLUGS:
            assert audio["enabled"] is True, slug
            assert audio["release_gate"] == "APPROVED", slug
            assert audio["qa_status"] == "QA_PASSED", slug
            assert audio["assets"]["mp3"] == f"/api/reader/book/{slug}/audiobook", slug
            continue

        assert audio["enabled"] is False, slug
        assert audio["provider"] == "", slug
        assert audio["voice"] == "", slug
        assert audio["url"] == "", slug
        assert audio["assets"] == {}, slug
        assert audio["release_gate"] == "", slug
        assert audio["qa_status"] == "", slug


def test_hidden_sprint1_runtime_sources_have_no_direct_audio_urls():
    for slug in set(active_sprint1_slugs()) - APPROVED_AUDIO_SLUGS:
        public_books = packet_paths(slug, "public_book.json")
        assert public_books, slug
        for path in public_books:
            book = read_json(path)
            audio_source = json.dumps(
                {
                    "audio_url": book.get("audio_url", ""),
                    "audioUrl": book.get("audioUrl", ""),
                    "audiobook_assets": book.get("audiobook_assets", {}),
                    "audiobook": book.get("audiobook", {}),
                },
                sort_keys=True,
            ).lower()
            assert "res.cloudinary.com" not in audio_source, path
            assert "backblazeb2.com" not in audio_source, path
            assert "/audio/" not in audio_source, path


def test_cleaned_sprint1_metadata_is_explicitly_audio_hidden():
    for slug in CLEANED_METADATA_SLUGS:
        public_books = packet_paths(slug, "public_book.json")
        assert public_books, slug
        for path in public_books:
            book = read_json(path)
            assert book["audio_enabled"] is False, path
            assert book["audiobook_enabled"] is False, path
            assert book["generate_audiobook"] is False, path
            assert book["audiobook_provider"] == "", path
            assert book["audiobook_voice"] == "", path
            assert book["audio_asset_slug"] == "", path
            assert book["audiobook_assets"] == {}, path
            assert book["audiobook"] == {}, path


@pytest.mark.parametrize("slug", ("book-f5d593e1f4", "muchiram-gurer-jibanchorit"))
def test_stale_historical_audio_approval_is_failed_closed(slug: str):
    for path in packet_paths(slug, "approval_evidence.json"):
        evidence = read_json(path)
        assert evidence["audio_public_release"] == "PUBLIC_AUDIO_RELEASE_BLOCKED_QA_REQUIRED"
        assert evidence["audiobook_enabled"] is False


def test_current_approved_packages_are_unchanged_and_evidence_gated():
    for slug, expected_suffix in APPROVED_MP3_SUFFIXES.items():
        for path in packet_paths(slug, "public_book.json"):
            book = read_json(path)
            assert book["audio_enabled"] is True, path
            assert book["audiobook_enabled"] is True, path
            assert book["audiobook_assets"]["mp3"].endswith(expected_suffix), path
            assert_checksum_manifest(path.parent)

        artifact = catalog_truth.load_controlled_artifact_book(slug)
        assert artifact is not None
        audio = server._reader_manifest_audio(artifact, slug)
        assert audio["enabled"] is True
        assert audio["release_gate"] == "APPROVED"
        assert audio["qa_status"] == "QA_PASSED"


def test_changed_packet_checksums_match():
    for slug in CLEANED_METADATA_SLUGS:
        for root in PACKET_ROOTS:
            packet = root / slug
            if (packet / "checksum_manifest.json").exists():
                assert_checksum_manifest(packet)


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

    assert content.startswith("গাড়িটি আসিয়া জংশনে থামিলে")
    assert "STALE DATABASE TITLE-PAGE WRAPPER" not in content
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

    assert content == "STALE DATABASE TITLE-PAGE WRAPPER"


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
