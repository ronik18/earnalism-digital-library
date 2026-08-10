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


def release_sha256(value: Any) -> str:
    """Return a normalized SHA-256 value without an optional scheme prefix."""

    return str(value or "").strip().lower().removeprefix("sha256:")


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
    }


def audiobook_release_qa_blockers(summary: dict[str, Any]) -> list[str]:
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
    return blockers


def audiobook_release_fingerprint(payload: AudiobookReleaseIn) -> str:
    """Create the retry-stable identity for a release request."""

    material = payload.model_dump(exclude={"release_request_id"})
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()
