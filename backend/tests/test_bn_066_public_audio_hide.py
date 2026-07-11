from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "bn-066-public-audio-hide-test-secret")

from backend import catalog_truth
from backend import server


class EmptyBooks:
    async def find_one(self, *_args, **_kwargs):
        return None


class LegacyAudioBooks:
    async def find_one(self, *_args, **_kwargs):
        return {
            "slug": "bn-066",
            "is_published": True,
            "publication_status": "LIVE_APPROVED",
            "approved_to_publish": True,
            "audiobook_enabled": True,
            "audiobook_provider": "b2",
            "audiobook_assets": {
                "mp3": "https://s3.us-west-004.backblazeb2.com/earnalism-audiobooks/bn-066.mp3",
            },
        }


async def no_cached_manifest(*_args, **_kwargs):
    return None


async def ignore_cached_manifest(*_args, **_kwargs):
    return None


def test_bn_066_artifact_remains_reader_live_and_audio_hidden():
    status = catalog_truth.controlled_artifact_status("bn-066")
    artifact = catalog_truth.load_controlled_artifact_book("bn-066", include_content=True)

    assert status["available"] is True
    assert status["self_contained_for_truth_gate"] is True
    assert artifact is not None
    assert catalog_truth.can_expose_reader(artifact) is True
    assert catalog_truth.can_expose_audio(artifact) is False
    assert artifact["audiobook_enabled"] is False
    assert artifact["generate_audiobook"] is False
    assert artifact["audiobook_provider"] == ""
    assert artifact["audiobook_voice"] == ""
    assert artifact["audiobook_assets"] == {}
    assert artifact["audiobook"] == {}
    assert artifact["chapters"]


def test_bn_066_reader_manifest_fails_closed_without_losing_reader(monkeypatch):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=EmptyBooks()))
    monkeypatch.setattr(server, "_redis_cache_get", no_cached_manifest)
    monkeypatch.setattr(server, "_redis_cache_set", ignore_cached_manifest)

    manifest = asyncio.run(server._reader_book_manifest_doc("bn-066"))

    assert manifest is not None
    assert manifest["book"]["slug"] == "bn-066"
    assert manifest["book"]["reader_enabled"] is True
    assert manifest["chapters"]
    assert manifest["audio"]["enabled"] is False
    assert manifest["audio"]["assets"] == {}
    assert manifest["audio"]["url"] == ""
    assert manifest["audio"]["provider"] == ""
    assert manifest["audio"]["voice"] == ""
    assert manifest["audio"]["release_gate"] == ""
    assert manifest["audio"]["qa_status"] == ""


def test_approved_bengali_pilot_still_exposes_evidence_gated_audio():
    artifact = catalog_truth.load_controlled_artifact_book("book-2b9853ec52")

    assert artifact is not None
    assert catalog_truth.can_expose_audio(artifact) is True
    audio = server._reader_manifest_audio(artifact, "book-2b9853ec52")
    assert audio["enabled"] is True
    assert audio["release_gate"] == "APPROVED"
    assert audio["qa_status"] == "QA_PASSED"
    assert audio["assets"]["mp3"]


def test_bn_066_legacy_audio_endpoint_fails_closed(monkeypatch):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=LegacyAudioBooks()))
    request = server.Request({"type": "http", "method": "GET", "headers": []})

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(server._reader_book_audiobook_asset("bn-066", "mp3", request))

    assert exc_info.value.status_code == 404


def test_a_ghost_story_remains_reader_first_audio_hidden():
    artifact = catalog_truth.load_controlled_artifact_book("a-ghost-story")

    assert artifact is not None
    assert catalog_truth.can_expose_reader(artifact) is True
    assert catalog_truth.can_expose_audio(artifact) is False
    assert server._reader_manifest_audio(artifact, "a-ghost-story")["enabled"] is False
