from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "a-ghost-story-routability-test-secret")

from backend import catalog_truth
from backend import server


class EmptyBooks:
    async def find_one(self, *_args, **_kwargs):
        return None


async def noop_cache_get(*_args, **_kwargs):
    return None


async def noop_cache_set(*_args, **_kwargs):
    return None


def test_a_ghost_story_controlled_artifact_has_release_gated_audio():
    status = catalog_truth.controlled_artifact_status("a-ghost-story")
    artifact = catalog_truth.load_controlled_artifact_book("a-ghost-story", include_content=True)

    assert status["available"] is True
    assert status["self_contained_for_truth_gate"] is True
    assert status["audio_enabled"] is True
    assert status["audiobook_enabled"] is True
    assert artifact is not None
    assert artifact["slug"] == "a-ghost-story"
    assert artifact["title"] == "A Ghost Story"
    assert artifact["audio_enabled"] is True
    assert artifact["audiobook_enabled"] is True
    assert artifact["generate_audiobook"] is True
    assert artifact["audiobook_assets"]["mp3"].startswith("https://s3.us-west-004.backblazeb2.com/")
    assert artifact["audiobook"]["provider"] == "google"
    assert catalog_truth.can_expose_audio(artifact) is True
    assert artifact["chapters"][0]["content"].startswith("I took a large room")


def test_a_ghost_story_public_detail_falls_back_without_leaking_storage_assets(monkeypatch):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=EmptyBooks()))
    monkeypatch.setattr(server, "_public_cache_get", noop_cache_get)
    monkeypatch.setattr(server, "_public_cache_set", noop_cache_set)

    result = asyncio.run(server.get_book("a-ghost-story"))
    dumped = server.PublicBookOut.model_validate(result).model_dump()

    assert dumped["slug"] == "a-ghost-story"
    assert dumped["title"] == "A Ghost Story"
    assert dumped["reader_enabled"] is True
    assert dumped["reader_url"] == "/reader/a-ghost-story"
    assert dumped["audio_enabled"] is False
    assert dumped["audiobook_enabled"] is False
    assert dumped["audio_url"] == ""
    assert dumped["audio_status"] == "NOT_AVAILABLE"
    assert dumped["cta_label"] == "Read"
    assert "audiobook_assets" not in result
    assert "audiobook" not in result
    assert "content" not in dumped["chapters"][0]


def test_a_ghost_story_reader_manifest_has_content_and_approved_audio(monkeypatch):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=EmptyBooks()))

    manifest = asyncio.run(server._reader_book_manifest_doc("a-ghost-story"))

    assert manifest is not None
    assert manifest["book"]["slug"] == "a-ghost-story"
    assert manifest["book"]["reader_enabled"] is True
    assert manifest["audio"]["enabled"] is True
    assert manifest["audio"]["provider"] == "google"
    assert manifest["audio"]["voice"] == "en-GB-Studio-C"
    assert manifest["audio"]["release_gate"] == "APPROVED"
    assert manifest["audio"]["qa_status"] == "QA_PASSED"
    assert manifest["audio"]["url"] == "/api/reader/book/a-ghost-story/audiobook"
    assert manifest["audio"]["assets"]["mp3"] == "/api/reader/book/a-ghost-story/audiobook"
    assert manifest["audio"]["sync_mode"] == "section_following"
    assert len(manifest["chapters"]) == 1
    chapter = manifest["chapters"][0]
    assert chapter["id"] == "chapter-001"
    assert chapter["title"] == "A Ghost Story"
    assert chapter["is_preview"] is True
    assert chapter["word_count"] == 2450
    assert chapter["reading_minutes"] == 11
    assert chapter["processing_status"] == "ready"
    assert chapter["content_url"].startswith("/api/reader/chapter/a-ghost-story/chapter-001?v=")
