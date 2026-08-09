import os


os.environ.setdefault("MONGODB_URL", "mongodb://127.0.0.1:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "test-only-release-conveyor-secret")


from backend.server import (
    AudiobookReleaseIn,
    _audiobook_release_fingerprint,
    _audiobook_release_qa_blockers,
    _audiobook_release_qa_summary,
)


def test_release_qa_summary_normalizes_notebook_fields():
    summary = _audiobook_release_qa_summary(
        {
            "asr_manuscript_score": 0.99,
            "coverage": 0.995,
            "first_span_score": 0.98,
            "last_span_score": 0.98,
            "overall_score": 9.1,
            "confidence": 0.94,
            "fatal_flags": {},
            "blockers": [],
            "ordered_content_integrity": True,
        }
    )

    assert not _audiobook_release_qa_blockers(summary)
    assert summary["sync_tier"] == "AUDIO_ONLY_NO_SYNC"


def test_release_qa_summary_fails_closed_when_required_values_are_missing():
    blockers = _audiobook_release_qa_blockers(_audiobook_release_qa_summary({}))

    assert len(blockers) >= 6


def test_release_fingerprint_is_stable_and_excludes_request_id():
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
        release_request_id="first-request",
    )
    retry = payload.model_copy(update={"release_request_id": "retry-request"})

    assert _audiobook_release_fingerprint(payload) == _audiobook_release_fingerprint(retry)
