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


class StaleApprovedAudioBooks:
    async def find_one(self, *_args, **_kwargs):
        book = catalog_truth.load_controlled_artifact_book("book-2b9853ec52", include_content=True)
        assert book is not None
        book["audiobook_provider"] = "historical_mapped_assets"
        book["audiobook_voice"] = ""
        book["audiobook_assets"] = {
            "mp3": "https://res.cloudinary.com/demo/video/upload/stale.mp3",
        }
        book["audiobook"] = {
            "provider": "historical_mapped_assets",
            "url": "https://res.cloudinary.com/demo/video/upload/stale.mp3",
        }
        return book


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
    assert artifact["cover_image_url"].endswith("book-2b9853ec52_front_1600x2400.png")
    assert artifact["back_cover_image_url"].endswith("book-2b9853ec52_back_1600x2400.png")
    assert artifact["audiobook_provider"] == "b2"
    assert artifact["audiobook_voice"] == "ratan"
    assert artifact["audiobook_assets"]["mp3"].startswith(
        "https://s3.us-west-004.backblazeb2.com/earnalism-audiobooks/"
    )
    audio = server._reader_manifest_audio(artifact, "book-2b9853ec52")
    assert audio["enabled"] is True
    assert audio["release_gate"] == "APPROVED"
    assert audio["qa_status"] == "QA_PASSED"
    assert audio["provider"] == "b2"
    assert audio["voice"] == "ratan"
    assert audio["assets"]["mp3"] == "/api/reader/book/book-2b9853ec52/audiobook"
    assert audio["assets"]["timestamps"] == "/api/reader/book/book-2b9853ec52/audiobook/timestamps"
    assert audio["url"] == "/api/reader/book/book-2b9853ec52/audiobook"
    assert audio["size"] == 5_233_965
    assert audio["duration_ms"] == 327_069


def test_approved_manifest_prefers_controlled_artifact_over_stale_database_audio(monkeypatch):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=StaleApprovedAudioBooks()))
    monkeypatch.setattr(server, "_redis_cache_get", no_cached_manifest)
    monkeypatch.setattr(server, "_redis_cache_set", ignore_cached_manifest)

    manifest = asyncio.run(server._reader_book_manifest_doc("book-2b9853ec52"))

    assert manifest is not None
    assert manifest["audio"]["enabled"] is True
    assert manifest["audio"]["provider"] == "b2"
    assert manifest["audio"]["voice"] == "ratan"
    assert manifest["audio"]["url"] == "/api/reader/book/book-2b9853ec52/audiobook"
    assert "cloudinary.com" not in str(manifest["audio"])


def test_approved_audio_truth_fails_closed_when_artifact_is_unavailable(monkeypatch):
    artifact = catalog_truth.load_controlled_artifact_book("book-2b9853ec52")
    assert artifact is not None
    monkeypatch.setattr(server, "_controlled_artifact_doc", lambda *_args, **_kwargs: None)

    assert server._reader_audio_truth_doc(artifact, "book-2b9853ec52") is None


def test_approved_audio_version_changes_with_release_qa_semantics(monkeypatch):
    artifact = catalog_truth.load_controlled_artifact_book("book-2b9853ec52")
    assert artifact is not None

    monkeypatch.setattr(server, "audio_release_qa_status", lambda _book: "QA_PASSED")
    approved_version = server._reader_manifest_audio(artifact, "book-2b9853ec52")["version"]
    monkeypatch.setattr(server, "audio_release_qa_status", lambda _book: "REPAIR_REQUIRED")
    repair_version = server._reader_manifest_audio(artifact, "book-2b9853ec52")["version"]

    assert approved_version != repair_version


def test_bn_066_legacy_audio_endpoint_fails_closed(monkeypatch):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=LegacyAudioBooks()))
    request = server.Request({"type": "http", "method": "GET", "headers": []})

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(server._reader_book_audiobook_asset("bn-066", "mp3", request))

    assert exc_info.value.status_code == 404


def test_a_ghost_story_release_does_not_change_bn_066_fail_closed_policy():
    artifact = catalog_truth.load_controlled_artifact_book("a-ghost-story")

    assert artifact is not None
    assert catalog_truth.can_expose_reader(artifact) is True
    assert catalog_truth.can_expose_audio(artifact) is True
    assert server._reader_manifest_audio(artifact, "a-ghost-story")["enabled"] is True

    bn_066 = catalog_truth.load_controlled_artifact_book("bn-066")
    assert bn_066 is not None
    assert catalog_truth.can_expose_audio(bn_066) is False
    assert server._reader_manifest_audio(bn_066, "bn-066")["enabled"] is False


@pytest.mark.parametrize(
    "slug",
    [
        "alices-adventures-in-wonderland",
        "bn-027",
        "lokrahasya",
        "mrinalini",
        "nishkriti",
        "the-wonderful-wizard-of-oz",
    ],
)
def test_historical_reconstruction_audio_fails_closed(slug):
    artifact = catalog_truth.load_controlled_artifact_book(slug)

    assert artifact is not None
    assert catalog_truth.can_expose_reader(artifact) is True
    assert catalog_truth.can_expose_audio(artifact) is False
    audio = server._reader_manifest_audio(artifact, slug)
    assert audio["enabled"] is False
    assert audio["assets"] == {}
    assert audio["url"] == ""
    assert audio["release_gate"] == ""
    assert audio["qa_status"] == ""
