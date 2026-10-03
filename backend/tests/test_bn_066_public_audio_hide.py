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
        return {
            "slug": "book-2b9853ec52",
            "is_published": True,
            "publication_status": "LIVE_APPROVED",
            "approved_to_publish": True,
            "audiobook_enabled": True,
            "audiobook_provider": "historical_mapped_assets",
            "audiobook_assets": {
                "mp3": "https://res.cloudinary.com/demo/video/upload/stale.mp3",
            },
            "audiobook": {
                "provider": "historical_mapped_assets",
                "url": "https://res.cloudinary.com/demo/video/upload/stale.mp3",
            },
        }


async def no_cached_manifest(*_args, **_kwargs):
    return None


async def ignore_cached_manifest(*_args, **_kwargs):
    return None


def test_bn_066_exact_accepted_text_is_available_and_audio_remains_disabled():
    status = catalog_truth.controlled_artifact_status("bn-066")
    artifact = catalog_truth.load_controlled_artifact_book("bn-066", include_content=True)
    assert status["available"] is True
    assert status["self_contained_for_truth_gate"] is True
    assert artifact is not None and len(artifact["chapters"]) == 46
    assert catalog_truth.can_expose_reader(artifact) is True
    assert catalog_truth.can_expose_audio(artifact) is False
    assert server._reader_manifest_audio(artifact, "bn-066")["enabled"] is False


def test_bn_066_reader_manifest_denies_when_release_allowlist_is_missing(monkeypatch):
    # A stale database claim cannot bypass the independently tested allowlist.
    monkeypatch.setattr(server, "_is_controlled_public_slug", lambda _slug: False)
    monkeypatch.setattr(server, "db", SimpleNamespace(books=LegacyAudioBooks()))
    monkeypatch.setattr(server, "_redis_cache_get", no_cached_manifest)
    monkeypatch.setattr(server, "_redis_cache_set", ignore_cached_manifest)
    assert asyncio.run(server._reader_book_manifest_doc("bn-066")) is None


def test_owner_excluded_bengali_title_is_not_reader_or_audio_exposed():
    artifact = catalog_truth.load_controlled_artifact_book("book-2b9853ec52")

    assert artifact is None
    assert "book-2b9853ec52" not in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS


def test_excluded_title_rejects_stale_database_audio(monkeypatch):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=StaleApprovedAudioBooks()))
    monkeypatch.setattr(server, "_redis_cache_get", no_cached_manifest)
    monkeypatch.setattr(server, "_redis_cache_set", ignore_cached_manifest)

    manifest = asyncio.run(server._reader_book_manifest_doc("book-2b9853ec52"))

    assert manifest is None


def test_audio_truth_fails_closed_for_legacy_audio_when_artifact_is_unavailable(monkeypatch):
    slug = "book-2b9853ec52"
    legacy_book = {
        "slug": slug,
        "is_published": True,
        "publication_status": "LIVE_APPROVED",
        "approved_to_publish": True,
        "audiobook_enabled": True,
        "audiobook_provider": "b2",
    }
    monkeypatch.setattr(server, "_controlled_artifact_doc", lambda *_args, **_kwargs: None)

    audio = server._reader_manifest_audio(
        server._reader_audio_truth_doc(legacy_book, slug), slug
    )
    assert audio["enabled"] is False
    assert audio.get("url") in (None, "")


def test_disabled_audio_manifest_stays_disabled_when_qa_status_varies(monkeypatch):
    artifact = catalog_truth.load_controlled_artifact_book("a-ghost-story")
    assert artifact is not None

    monkeypatch.setattr(server, "audio_release_qa_status", lambda _book: "QA_PASSED")
    approved_version = server._reader_manifest_audio(artifact, "a-ghost-story")["version"]
    monkeypatch.setattr(server, "audio_release_qa_status", lambda _book: "REPAIR_REQUIRED")
    repair_version = server._reader_manifest_audio(artifact, "a-ghost-story")["version"]

    assert approved_version == repair_version
    assert server._reader_manifest_audio(artifact, "a-ghost-story")["enabled"] is False


def test_bn_066_legacy_audio_endpoint_fails_closed(monkeypatch):
    monkeypatch.setattr(server, "db", SimpleNamespace(books=LegacyAudioBooks()))
    request = server.Request({"type": "http", "method": "GET", "headers": []})

    with pytest.raises(server.HTTPException) as exc_info:
        asyncio.run(server._reader_book_audiobook_asset("bn-066", "mp3", request))

    assert exc_info.value.status_code == 404


def test_a_ghost_story_and_bn_066_text_release_do_not_admit_audio():
    artifact = catalog_truth.load_controlled_artifact_book("a-ghost-story")

    assert artifact is not None
    assert catalog_truth.can_expose_reader(artifact) is True
    assert catalog_truth.can_expose_audio(artifact) is False
    assert server._reader_manifest_audio(artifact, "a-ghost-story")["enabled"] is False

    bn_066 = catalog_truth.load_controlled_artifact_book("bn-066")
    assert bn_066 is not None
    assert catalog_truth.can_expose_reader(bn_066) is True
    assert catalog_truth.can_expose_audio(bn_066) is False
    assert server._reader_manifest_audio(bn_066, "bn-066")["enabled"] is False


@pytest.mark.parametrize(
    "slug",
    [
        "bn-027",
        "nishkriti",
    ],
)
def test_historical_reconstruction_titles_remain_outside_reader_allowlist(slug):
    artifact = catalog_truth.load_controlled_artifact_book(slug)

    assert slug not in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS
    assert artifact is None


@pytest.mark.parametrize("slug, count", [
    ("alices-adventures-in-wonderland", 12), ("lokrahasya", 16),
    ("mrinalini", 46), ("the-wonderful-wizard-of-oz", 25),
])
def test_exact_reconstruction_text_releases_keep_audio_disabled(slug, count):
    artifact = catalog_truth.load_controlled_artifact_book(slug, include_content=True)
    assert slug in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS
    assert artifact is not None and len(artifact["chapters"]) == count
    assert catalog_truth.can_expose_reader(artifact) is True
    assert catalog_truth.can_expose_audio(artifact) is False
    audio = server._reader_manifest_audio(artifact, slug)
    assert audio["enabled"] is False
    assert audio.get("url") in (None, "")
