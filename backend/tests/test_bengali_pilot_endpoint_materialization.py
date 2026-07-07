from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "bengali-endpoint-materialization-test")

from backend import catalog_truth
from backend import server


PILOT_SLUG = "book-2b9853ec52"


def pilot_db_book(**overrides):
    book = {
        "slug": PILOT_SLUG,
        "title": "দুই বিঘা জমি",
        "author": "রবীন্দ্রনাথ ঠাকুর",
        "is_published": True,
        "rights_metadata": {
            "rights_tier": "A",
            "verification_status": "approved",
            "blocked_reason": "",
            "source_url": "https://bn.wikisource.org/wiki/example",
            "source_name": "Bengali Wikisource",
            "source_license": "Public-domain source with compatible transcription license.",
        },
        "qa_status": "QA_PASSED",
        "audiobook_enabled": True,
        "generate_audiobook": False,
        "audiobook_provider": "sarvam",
        "audiobook_voice": "ratan",
        "audio_asset_slug": PILOT_SLUG,
        "audiobook_assets": {
            "mp3": "https://cdn.example.test/book-2b9853ec52.mp3",
            "timestamps": "https://cdn.example.test/book-2b9853ec52_timestamps.json",
            "vtt": "https://cdn.example.test/book-2b9853ec52_highlight.vtt",
            "chapters": "https://cdn.example.test/book-2b9853ec52_chapters.json",
            "meta": "https://cdn.example.test/book-2b9853ec52_meta.json",
        },
        "audiobook": {
            "url": "https://cdn.example.test/book-2b9853ec52.mp3",
            "provider": "sarvam",
            "size": 5_233_965,
            "duration_ms": 327_069,
            "assets": {
                "mp3": "https://cdn.example.test/book-2b9853ec52.mp3",
                "timestamps": "https://cdn.example.test/book-2b9853ec52_timestamps.json",
                "vtt": "https://cdn.example.test/book-2b9853ec52_highlight.vtt",
                "chapters": "https://cdn.example.test/book-2b9853ec52_chapters.json",
                "meta": "https://cdn.example.test/book-2b9853ec52_meta.json",
            },
            "listening_policy_version": "bengali_audiobook_acceptance_v2_92",
            "sync_policy_version": "tiered_sync_acceptance_v1",
            "sync_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
            "sync_granularity": "paragraph_or_stanza",
            "auto_estimated_sync": False,
        },
        "chapters": [
            {
                "id": "chapter-001",
                "title": "দুই বিঘা জমি",
                "order": 1,
                "content": "শুধু বিঘে-দুই ছিল মোর ভুঁই...",
            }
        ],
    }
    book.update(overrides)
    return book


class FakeBooks:
    def __init__(self, doc):
        self.doc = doc
        self.last_query = None

    async def find_one(self, query, _projection):
        self.last_query = query
        return self.doc


def test_pilot_materialization_slug_is_explicit_and_narrow():
    assert PILOT_SLUG in catalog_truth.AUDIO_MATERIALIZATION_SLUGS
    assert PILOT_SLUG in catalog_truth.AUDIO_ENABLED_SLUGS
    assert "book-ac5a71075e" not in catalog_truth.AUDIO_MATERIALIZATION_SLUGS


def test_pilot_endpoint_materializes_with_db_audio_and_controlled_evidence(monkeypatch):
    book = pilot_db_book()
    assert catalog_truth.can_expose_audio({**book, "slug": PILOT_SLUG}) is False

    fake_books = FakeBooks(book)
    monkeypatch.setattr(server, "db", SimpleNamespace(books=fake_books))
    request = SimpleNamespace(headers={}, method="GET")

    response = asyncio.run(server._reader_book_audiobook_asset(PILOT_SLUG, "mp3", request))

    assert response.status_code == 307
    assert response.headers["location"] == "https://cdn.example.test/book-2b9853ec52.mp3"
    assert fake_books.last_query["slug"] == PILOT_SLUG


def test_non_materialized_bengali_audio_remains_hidden(monkeypatch):
    slug = "book-ac5a71075e"
    book = pilot_db_book(slug=slug, audio_asset_slug=slug)
    fake_books = FakeBooks(book)
    monkeypatch.setattr(server, "db", SimpleNamespace(books=fake_books))
    request = SimpleNamespace(headers={}, method="GET")

    with pytest.raises(server.HTTPException) as exc:
        asyncio.run(server._reader_book_audiobook_asset(slug, "mp3", request))

    assert exc.value.status_code == 404


def test_reader_manifest_audio_accepts_paragraph_stanza_sync_for_pilot():
    audio = server._reader_manifest_audio(pilot_db_book(), PILOT_SLUG)

    assert audio["enabled"] is True
    assert audio["provider"] == "sarvam"
    assert audio["url"] == "https://cdn.example.test/book-2b9853ec52.mp3"


def test_estimated_sync_blocks_pilot_audio_exposure():
    book = pilot_db_book(audiobook={**pilot_db_book()["audiobook"], "auto_estimated_sync": True})

    audio = server._reader_manifest_audio(book, PILOT_SLUG)

    assert audio["enabled"] is False
    assert audio["assets"] == {}


def test_unknown_policy_or_sync_tier_blocks_pilot_audio_exposure():
    unknown_policy = pilot_db_book(
        audiobook={**pilot_db_book()["audiobook"], "listening_policy_version": "unknown_policy"}
    )
    unknown_tier = pilot_db_book(
        audiobook={**pilot_db_book()["audiobook"], "sync_tier": "UNKNOWN_SYNC_TIER"}
    )

    assert server._reader_manifest_audio(unknown_policy, PILOT_SLUG)["enabled"] is False
    assert server._reader_manifest_audio(unknown_tier, PILOT_SLUG)["enabled"] is False
