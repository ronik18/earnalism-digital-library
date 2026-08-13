import os
import json
from copy import deepcopy
from pathlib import Path


os.environ.setdefault("MONGODB_URL", "mongodb://127.0.0.1:27017/earnalism_test")
os.environ.setdefault("JWT_SECRET", "test-only-release-conveyor-secret")


from backend.server import (
    AudiobookReleaseIn,
    _audiobook_release_fingerprint,
    _audiobook_release_qa_blockers,
    _audiobook_release_qa_summary,
)
from backend.domain.audiobook_release import (
    ACCESSIBILITY_EXCEPTION_DECISION,
    ACCESSIBILITY_EXCEPTION_SCHEMA,
    audiobook_accessibility_exception_sha256,
)


AUDIO_SHA256 = "a" * 64
ATTEMPT_FINGERPRINT = "c" * 64


def complete_qa(**overrides):
    qa = {
        "asr_manuscript_score": 0.99,
        "coverage": 0.995,
        "first_span_score": 0.98,
        "last_span_score": 0.98,
        "overall_score": 9.1,
        "confidence": 0.94,
        "fatal_flags": {},
        "blockers": [],
        "ordered_content_integrity": True,
        "attempt_fingerprint": ATTEMPT_FINGERPRINT,
        "audio_sha256": AUDIO_SHA256,
        "accessibility": {
            "voiceover_status": "PASS",
            "talkback_status": "PASS",
            "keyboard_controls_status": "PASS",
            "chapter_navigation_status": "PASS",
            "pause_resume_recovery_status": "PASS",
        },
    }
    qa.update(overrides)
    return qa


def accessibility_exception(*, confidence=0.94):
    exception = {
        "schema_version": ACCESSIBILITY_EXCEPTION_SCHEMA,
        "title_slug": "example",
        "candidate_fingerprint": ATTEMPT_FINGERPRINT,
        "audio_sha256": AUDIO_SHA256,
        "owner_name": "Example Owner",
        "owner_role": "Product owner",
        "decision": ACCESSIBILITY_EXCEPTION_DECISION,
        "accepted_residual_risk": True,
        "reason": "Compatible physical assistive-technology devices are temporarily unavailable.",
        "confidence": confidence,
        "voiceover_status": "NOT_TESTED",
        "talkback_status": "NOT_TESTED",
        "waived_checks": ["voiceover_physical_device", "talkback_physical_device"],
        "other_release_gates_waived": False,
        "recorded_at": "2026-08-13T00:00:00Z",
    }
    exception["exception_sha256"] = audiobook_accessibility_exception_sha256(exception)
    return exception


def test_release_qa_summary_normalizes_notebook_fields():
    summary = _audiobook_release_qa_summary(complete_qa())

    assert not _audiobook_release_qa_blockers(
        summary,
        title_slug="example",
        audio_sha256=AUDIO_SHA256,
        attempt_fingerprint=ATTEMPT_FINGERPRINT,
    )
    assert summary["sync_tier"] == "AUDIO_ONLY_NO_SYNC"


def test_checksum_bound_accessibility_exception_preserves_not_tested_truth():
    accessibility = deepcopy(complete_qa()["accessibility"])
    accessibility.update(
        {
            "voiceover_status": "NOT_TESTED",
            "talkback_status": "NOT_TESTED",
            "policy_exception": accessibility_exception(),
        }
    )
    summary = _audiobook_release_qa_summary(complete_qa(accessibility=accessibility))

    assert not _audiobook_release_qa_blockers(
        summary,
        title_slug="example",
        audio_sha256=AUDIO_SHA256,
        attempt_fingerprint=ATTEMPT_FINGERPRINT,
    )
    assert summary["accessibility"]["voiceover_status"] == "NOT_TESTED"
    assert summary["accessibility"]["talkback_status"] == "NOT_TESTED"
    assert summary["accessibility"]["policy_exception"]["other_release_gates_waived"] is False


def test_accessibility_exception_fails_closed_on_checksum_or_candidate_mismatch():
    exception = accessibility_exception()
    exception["exception_sha256"] = "0" * 64
    accessibility = {
        **complete_qa()["accessibility"],
        "voiceover_status": "NOT_TESTED",
        "talkback_status": "NOT_TESTED",
        "policy_exception": exception,
    }
    summary = _audiobook_release_qa_summary(complete_qa(accessibility=accessibility))

    blockers = _audiobook_release_qa_blockers(
        summary,
        title_slug="different-title",
        audio_sha256="d" * 64,
        attempt_fingerprint="e" * 64,
    )

    assert "Accessibility exception checksum is invalid." in blockers
    assert "Accessibility exception is not bound to the release title." in blockers
    assert "Accessibility exception is not bound to the release audio checksum." in blockers
    assert "Accessibility exception is not bound to the release attempt fingerprint." in blockers


def test_accessibility_exception_does_not_waive_objective_or_browser_gates():
    accessibility = {
        **complete_qa()["accessibility"],
        "voiceover_status": "NOT_TESTED",
        "talkback_status": "NOT_TESTED",
        "keyboard_controls_status": "FAIL",
        "policy_exception": accessibility_exception(),
    }
    summary = _audiobook_release_qa_summary(
        complete_qa(asr_manuscript_score=0.8, accessibility=accessibility)
    )

    blockers = _audiobook_release_qa_blockers(
        summary,
        title_slug="example",
        audio_sha256=AUDIO_SHA256,
        attempt_fingerprint=ATTEMPT_FINGERPRINT,
    )

    assert "ASR manuscript score must be at least 0.97." in blockers
    assert "Keyboard audiobook controls must pass." in blockers


def test_accessibility_exception_rejects_any_other_gate_waiver():
    exception = accessibility_exception()
    exception["other_release_gates_waived"] = True
    exception["exception_sha256"] = audiobook_accessibility_exception_sha256(exception)
    accessibility = {
        **complete_qa()["accessibility"],
        "voiceover_status": "NOT_TESTED",
        "talkback_status": "NOT_TESTED",
        "policy_exception": exception,
    }
    summary = _audiobook_release_qa_summary(complete_qa(accessibility=accessibility))

    blockers = _audiobook_release_qa_blockers(
        summary,
        title_slug="example",
        audio_sha256=AUDIO_SHA256,
        attempt_fingerprint=ATTEMPT_FINGERPRINT,
    )

    assert "Accessibility exception cannot waive any other release gate." in blockers


def test_dracula_owner_exception_artifact_is_checksum_bound_and_release_compatible():
    exception_path = (
        Path(__file__).resolve().parents[2]
        / "internal"
        / "earnalism_intelligence"
        / "dracula_accessibility_policy_exception_20260813.json"
    )
    exception = json.loads(exception_path.read_text(encoding="utf-8"))
    accessibility = {
        **complete_qa()["accessibility"],
        "voiceover_status": "NOT_TESTED",
        "talkback_status": "NOT_TESTED",
        "policy_exception": exception,
    }
    qa = complete_qa(
        confidence=0.92,
        attempt_fingerprint=exception["candidate_fingerprint"],
        audio_sha256=exception["audio_sha256"],
        accessibility=accessibility,
    )
    summary = _audiobook_release_qa_summary(qa)

    assert exception["exception_sha256"] == audiobook_accessibility_exception_sha256(exception)
    assert not _audiobook_release_qa_blockers(
        summary,
        title_slug="dracula",
        audio_sha256=exception["audio_sha256"],
        attempt_fingerprint=exception["candidate_fingerprint"],
    )
    assert summary["accessibility"]["voiceover_status"] == "NOT_TESTED"
    assert summary["accessibility"]["talkback_status"] == "NOT_TESTED"


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
