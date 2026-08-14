from datetime import datetime, timedelta, timezone
import html
import re

import pytest
from pydantic import ValidationError

from backend.api.schemas import ReadingPassPreviewActivationIn

from backend.domain.reading_pass import (
    PUBLIC_AUDIO_PREVIEW_SECONDS,
    ReadingPassConfig,
    canonical_segment_chapter_title,
    canonicalize_segment_manifest_chapters,
    canonical_page_records,
    public_audio_position,
    public_text_page,
    segment_manifest,
    server_billable_seconds,
)


def test_preview_boundaries_are_canonical_and_fixed():
    assert [public_text_page(index) for index in range(1, 5)] == [True, True, True, False]
    assert public_audio_position(0)
    assert public_audio_position(179.999)
    assert not public_audio_position(PUBLIC_AUDIO_PREVIEW_SECONDS)
    assert not public_audio_position(999)


def test_canonical_pages_do_not_depend_on_viewport_or_font_settings():
    chapters = [
        {
            "id": "chapter-001",
            "title": "One",
            "order": 1,
            "content": "".join(f"<p>Paragraph {index} {'word ' * 120}</p>" for index in range(12)),
        }
    ]
    first = canonical_page_records(book_slug="fixture", chapters=chapters, target_characters=1200)
    second = canonical_page_records(book_slug="fixture", chapters=chapters, target_characters=1200)
    assert first == second
    assert len(first) > 3
    assert [row["page_index"] for row in first] == list(range(1, len(first) + 1))
    assert [row["is_public_preview"] for row in first[:4]] == [True, True, True, False]
    assert segment_manifest(first)["total_pages"] == len(first)


def test_reading_pass_titles_follow_controlled_reader_truth():
    stored = [
        {
            "chapter_id": "chapter-001",
            "chapter_title": "CHAPTER I. STALE SUBTITLE",
            "chapter_order": 1,
        },
        {
            "chapter_id": "chapter-002",
            "chapter_title": "CHAPTER II. STALE SUBTITLE",
            "chapter_order": 2,
        },
    ]
    controlled = [
        {"id": "chapter-001", "title": "CHAPTER I"},
        {"id": "chapter-002", "title": "CHAPTER II"},
    ]

    reconciled = canonicalize_segment_manifest_chapters(stored, controlled)

    assert [chapter["chapter_title"] for chapter in reconciled] == [
        "CHAPTER I",
        "CHAPTER II",
    ]
    assert canonical_segment_chapter_title(
        controlled,
        "chapter-002",
        "stale",
    ) == "CHAPTER II"
    assert canonical_segment_chapter_title(
        controlled,
        "chapter-missing",
        "Fallback",
    ) == "Fallback"


def test_canonical_segmentation_preserves_prose_outside_recognized_blocks():
    source = "Preface words<div><p>First paragraph.</p><p>Second paragraph.</p>Closing words</div>"
    records = canonical_page_records(
        book_slug="fixture",
        chapters=[{"id": "chapter-001", "title": "One", "content": source}],
    )
    rendered = " ".join(row["content"] for row in records)
    plain = html.unescape(re.sub(r"<[^>]+>", " ", rendered))
    assert re.sub(r"\s+", " ", plain).strip() == (
        "Preface words First paragraph. Second paragraph. Closing words"
    )


def test_server_billing_ignores_client_elapsed_and_caps_at_old_lease():
    config = ReadingPassConfig()
    started = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert server_billable_seconds(
        last_billed_at=started,
        lease_expires_at=started + timedelta(seconds=20),
        now=started + timedelta(days=1),
        active=True,
        config=config,
    ) == 20
    assert server_billable_seconds(
        last_billed_at=started,
        lease_expires_at=started + timedelta(seconds=20),
        now=started + timedelta(seconds=10),
        active=False,
        config=config,
    ) == 0


def test_reading_pass_config_rejects_weak_or_reinterpreted_boundaries():
    with pytest.raises(ValueError):
        ReadingPassConfig(public_text_pages=4)
    with pytest.raises(ValueError):
        ReadingPassConfig(public_audio_seconds=181)
    with pytest.raises(ValueError):
        ReadingPassConfig(heartbeat_seconds=10, maximum_lease_seconds=5)


def test_preview_activation_contract_requires_hashes_and_bounded_duration():
    valid = {
        "version": "sha256-" + "a" * 64,
        "duration_seconds": 180,
        "sha256": "a" * 64,
        "source_sha256": "b" * 64,
        "bytes": 2_000_000,
        "store": "private_audio",
        "bucket": "audio",
        "key": f"previews/book/{'a' * 64}/book.preview-180s.mp3",
        "version_id": "immutable-object-version-1",
    }
    assert ReadingPassPreviewActivationIn(**valid).activate is False
    with pytest.raises(ValidationError):
        ReadingPassPreviewActivationIn(**{**valid, "duration_seconds": 181})
    with pytest.raises(ValidationError):
        ReadingPassPreviewActivationIn(**{**valid, "sha256": "not-a-hash"})
    with pytest.raises(ValidationError):
        ReadingPassPreviewActivationIn(**{**valid, "version_id": ""})
