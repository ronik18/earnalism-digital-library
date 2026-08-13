"""Audiobook release-policy normalization and deterministic receipts.

This module intentionally contains no database, storage, or HTTP dependencies.
Keeping these rules pure makes release decisions easy to test and prevents
transport concerns from changing publication behavior.
"""

import hashlib
import json
import math
from typing import Any, Dict, Optional

try:
    from backend.api.schemas import AudiobookReleaseIn
except ImportError:  # pragma: no cover - supports uvicorn from backend/
    from api.schemas import AudiobookReleaseIn


ACCESSIBILITY_EXCEPTION_SCHEMA = "earnalism.audiobook_accessibility_exception.v1"
ACCESSIBILITY_PASS = "PASS"
ACCESSIBILITY_NOT_TESTED = "NOT_TESTED"
ACCESSIBILITY_EXCEPTION_DECISION = "OWNER_ACCEPTED_RESIDUAL_RISK"
ACCESSIBILITY_EXCEPTION_CHECKS = {
    "talkback_physical_device",
    "voiceover_physical_device",
}
ACCESSIBILITY_REQUIRED_BROWSER_CHECKS = {
    "keyboard_controls_status": "Keyboard audiobook controls must pass.",
    "chapter_navigation_status": "Chapter navigation must pass.",
    "pause_resume_recovery_status": "Pause/resume recovery must pass.",
}


def release_sha256(value: Any) -> str:
    """Return a normalized SHA-256 value without an optional scheme prefix."""

    return str(value or "").strip().lower().removeprefix("sha256:")


def _normalized_accessibility_status(value: Any) -> str:
    return str(value or "").strip().upper().replace(" ", "_")


def _accessibility_exception_material(value: Optional[Dict[str, Any]]) -> dict[str, Any]:
    """Return the canonical, checksum-bound owner exception material."""

    exception = value if isinstance(value, dict) else {}
    waived_checks = exception.get("waived_checks") or []
    if isinstance(waived_checks, str):
        waived_checks = [waived_checks]
    return {
        "schema_version": str(exception.get("schema_version") or "").strip(),
        "title_slug": str(exception.get("title_slug") or "").strip().lower(),
        "candidate_fingerprint": release_sha256(exception.get("candidate_fingerprint")),
        "audio_sha256": release_sha256(exception.get("audio_sha256")),
        "owner_name": str(exception.get("owner_name") or "").strip(),
        "owner_role": str(exception.get("owner_role") or "").strip(),
        "decision": str(exception.get("decision") or "").strip().upper(),
        "accepted_residual_risk": exception.get("accepted_residual_risk") is True,
        "reason": str(exception.get("reason") or "").strip(),
        "confidence": exception.get("confidence"),
        "voiceover_status": _normalized_accessibility_status(exception.get("voiceover_status")),
        "talkback_status": _normalized_accessibility_status(exception.get("talkback_status")),
        "waived_checks": sorted({str(item).strip().lower() for item in waived_checks if str(item).strip()}),
        "other_release_gates_waived": exception.get("other_release_gates_waived") is True,
        "recorded_at": str(exception.get("recorded_at") or "").strip(),
    }


def audiobook_accessibility_exception_sha256(value: Optional[Dict[str, Any]]) -> str:
    """Hash an accessibility exception without trusting its claimed digest."""

    material = _accessibility_exception_material(value)
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def audiobook_release_qa_summary(value: Optional[Dict[str, Any]]) -> dict[str, Any]:
    """Normalize notebook QA into one compact, fail-closed release receipt."""

    qa = value if isinstance(value, dict) else {}

    def score(*keys: str) -> Optional[float]:
        for key in keys:
            raw = qa.get(key)
            if raw is None:
                continue
            try:
                number = float(raw)
            except (TypeError, ValueError):
                continue
            if math.isfinite(number):
                return number
        return None

    fatal_flags = qa.get("fatal_flags") or qa.get("fatal_red_flags") or {}
    if isinstance(fatal_flags, dict):
        fatal_flags = [str(key) for key, active in fatal_flags.items() if active is True]
    elif isinstance(fatal_flags, str):
        fatal_flags = [fatal_flags] if fatal_flags.strip() else []
    else:
        fatal_flags = [str(item) for item in fatal_flags if str(item).strip()]

    blockers = qa.get("blockers") or []
    if isinstance(blockers, str):
        blockers = [blockers] if blockers.strip() else []
    else:
        blockers = [str(item) for item in blockers if str(item).strip()]

    accessibility = qa.get("accessibility") if isinstance(qa.get("accessibility"), dict) else {}
    policy_exception = (
        accessibility.get("policy_exception")
        if isinstance(accessibility.get("policy_exception"), dict)
        else {}
    )

    return {
        "asr_score": score("asr_score", "asr_manuscript_score", "similarity"),
        "coverage": score("coverage", "asr_coverage"),
        "first_span_score": score("first_span_score", "first_word_score"),
        "last_span_score": score("last_span_score", "last_word_score"),
        "listening_score": score("listening_score", "overall_score", "overall"),
        "listening_confidence": score("listening_confidence", "confidence"),
        "fatal_flags": sorted(set(fatal_flags)),
        "blockers": sorted(set(blockers)),
        "ordered_content_integrity": qa.get(
            "ordered_content_integrity",
            qa.get("no_missing_duplicated_reordered_content"),
        ),
        "sync_tier": str(qa.get("sync_tier") or "AUDIO_ONLY_NO_SYNC").strip().upper(),
        "attempt_fingerprint": release_sha256(qa.get("attempt_fingerprint")),
        "audio_sha256": release_sha256(qa.get("audio_sha256")),
        "accessibility": {
            "voiceover_status": _normalized_accessibility_status(accessibility.get("voiceover_status")),
            "talkback_status": _normalized_accessibility_status(accessibility.get("talkback_status")),
            "keyboard_controls_status": _normalized_accessibility_status(
                accessibility.get("keyboard_controls_status")
            ),
            "chapter_navigation_status": _normalized_accessibility_status(
                accessibility.get("chapter_navigation_status")
            ),
            "pause_resume_recovery_status": _normalized_accessibility_status(
                accessibility.get("pause_resume_recovery_status")
            ),
            "policy_exception": {
                **_accessibility_exception_material(policy_exception),
                "exception_sha256": release_sha256(policy_exception.get("exception_sha256")),
            }
            if policy_exception
            else {},
        },
    }


def audiobook_release_qa_blockers(
    summary: dict[str, Any],
    *,
    title_slug: str = "",
    audio_sha256: str = "",
    attempt_fingerprint: str = "",
) -> list[str]:
    """Return objective blockers for the controlled audiobook release gate."""

    required = {
        "asr_score": (0.97, "ASR manuscript score must be at least 0.97."),
        "coverage": (0.98, "ASR/source coverage must be at least 0.98."),
        "first_span_score": (0.95, "The first audio span must match the manuscript."),
        "last_span_score": (0.95, "The last audio span must match the manuscript."),
        "listening_score": (8.9, "Full-title listening score must be at least 8.9."),
        "listening_confidence": (0.90, "Listening QA confidence must be at least 0.90."),
    }
    blockers = [
        message
        for key, (minimum, message) in required.items()
        if summary.get(key) is None or summary[key] < minimum
    ]
    if summary.get("ordered_content_integrity") is not True:
        blockers.append("Ordered manuscript content integrity must pass.")
    if summary.get("fatal_flags"):
        blockers.append("Fatal listening QA flags must be empty.")
    if summary.get("blockers"):
        blockers.append("The release receipt must contain no unresolved blockers.")

    accessibility = summary.get("accessibility") if isinstance(summary.get("accessibility"), dict) else {}
    for field, message in ACCESSIBILITY_REQUIRED_BROWSER_CHECKS.items():
        if accessibility.get(field) != ACCESSIBILITY_PASS:
            blockers.append(message)

    screen_reader_statuses = {
        "voiceover_physical_device": accessibility.get("voiceover_status"),
        "talkback_physical_device": accessibility.get("talkback_status"),
    }
    invalid_statuses = {
        check: status
        for check, status in screen_reader_statuses.items()
        if status not in {ACCESSIBILITY_PASS, ACCESSIBILITY_NOT_TESTED}
    }
    if invalid_statuses:
        blockers.append("VoiceOver and TalkBack status must be PASS or NOT_TESTED.")

    deferred_checks = {
        check for check, status in screen_reader_statuses.items() if status == ACCESSIBILITY_NOT_TESTED
    }
    exception = accessibility.get("policy_exception") if isinstance(accessibility.get("policy_exception"), dict) else {}
    if deferred_checks:
        expected_title_slug = str(title_slug or "").strip().lower()
        expected_audio_sha256 = release_sha256(audio_sha256 or summary.get("audio_sha256"))
        expected_fingerprint = release_sha256(attempt_fingerprint or summary.get("attempt_fingerprint"))
        exception_confidence = score_from_value(exception.get("confidence"))
        listening_confidence = score_from_value(summary.get("listening_confidence"))

        if exception.get("schema_version") != ACCESSIBILITY_EXCEPTION_SCHEMA:
            blockers.append("Accessibility exception schema is missing or unsupported.")
        if exception.get("decision") != ACCESSIBILITY_EXCEPTION_DECISION:
            blockers.append("Accessibility exception must record owner-accepted residual risk.")
        if exception.get("accepted_residual_risk") is not True:
            blockers.append("Accessibility residual risk acceptance is missing.")
        if not exception.get("owner_name") or not exception.get("owner_role"):
            blockers.append("Accessibility exception must identify the owner and role.")
        if not exception.get("reason") or not exception.get("recorded_at"):
            blockers.append("Accessibility exception reason and recorded timestamp are required.")
        if not expected_title_slug or exception.get("title_slug") != expected_title_slug:
            blockers.append("Accessibility exception is not bound to the release title.")
        if exception.get("other_release_gates_waived") is not False:
            blockers.append("Accessibility exception cannot waive any other release gate.")
        if set(exception.get("waived_checks") or []) != deferred_checks:
            blockers.append("Accessibility exception scope must exactly match the NOT_TESTED checks.")
        if exception.get("voiceover_status") != screen_reader_statuses["voiceover_physical_device"]:
            blockers.append("Accessibility exception VoiceOver status does not match the release receipt.")
        if exception.get("talkback_status") != screen_reader_statuses["talkback_physical_device"]:
            blockers.append("Accessibility exception TalkBack status does not match the release receipt.")
        if not expected_audio_sha256 or exception.get("audio_sha256") != expected_audio_sha256:
            blockers.append("Accessibility exception is not bound to the release audio checksum.")
        if not expected_fingerprint or exception.get("candidate_fingerprint") != expected_fingerprint:
            blockers.append("Accessibility exception is not bound to the release attempt fingerprint.")
        if exception_confidence is None or exception_confidence < 0.90:
            blockers.append("Accessibility exception confidence must be at least 0.90.")
        if listening_confidence is None or exception_confidence != listening_confidence:
            blockers.append("Accessibility exception confidence must match listening QA confidence.")
        expected_exception_sha256 = audiobook_accessibility_exception_sha256(exception)
        if exception.get("exception_sha256") != expected_exception_sha256:
            blockers.append("Accessibility exception checksum is invalid.")
    elif exception:
        blockers.append("Accessibility exception is present but no screen-reader check is NOT_TESTED.")
    return blockers


def score_from_value(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def audiobook_release_fingerprint(payload: AudiobookReleaseIn) -> str:
    """Create the retry-stable identity for a release request."""

    material = payload.model_dump(exclude={"release_request_id"})
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()
