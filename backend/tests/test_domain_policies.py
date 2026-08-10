from datetime import datetime, timedelta, timezone

from backend.api.schemas import AudiobookReleaseIn
from backend.domain.audiobook_release import (
    audiobook_release_fingerprint,
    audiobook_release_qa_blockers,
    audiobook_release_qa_summary,
    release_sha256,
)
from backend.domain.catalog import canonical_category_slug, normalize_text, slugify
from backend.domain.reading_billing import billable_reading_seconds, should_reset_reading_clock


def test_release_policy_is_available_without_server_import():
    assert release_sha256(" SHA256:ABC ") == "abc"
    summary = audiobook_release_qa_summary({})
    assert audiobook_release_qa_blockers(summary)
    payload = AudiobookReleaseIn(
        audio_object_key="audiobooks/example/example.mp3",
        audio_sha256="a" * 64,
        audio_size_bytes=100,
        duration_seconds=1.0,
        manuscript_sha256="b" * 64,
        provider="kokoro",
        model="hexgrad/Kokoro-82M",
        voice="bm_george",
        qa={"asr_score": 0.99},
        owner_public_release_intent=True,
    )
    assert len(audiobook_release_fingerprint(payload)) == 64


def test_reading_billing_policy_is_parameterized_and_pulse_limited():
    now = datetime(2026, 5, 31, 10, 0, tzinfo=timezone.utc)
    kwargs = {
        "heartbeat_tick_seconds": 30,
        "heartbeat_early_grace_seconds": 5,
        "session_idle_grace_seconds": 120,
    }
    assert billable_reading_seconds(now - timedelta(seconds=31), now, **kwargs) == 30
    assert billable_reading_seconds(now - timedelta(minutes=30), now, **kwargs) == 0
    assert should_reset_reading_clock(now - timedelta(minutes=30), now, session_idle_grace_seconds=120)


def test_catalog_policy_normalizes_text_and_legacy_categories():
    assert normalize_text("e\u0301") == "é"
    assert slugify("A Book: Redux") == "a-book-redux"
    assert canonical_category_slug("classic literature") == "literary-fiction"
