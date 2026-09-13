"""Canonical reader-only identities that must never enter audio generation."""
from __future__ import annotations

import json
from pathlib import Path

_CONFIG = Path(__file__).resolve().parent / "data" / "controlled_launch.json"
READER_ONLY_AUDIO_EXCLUDED_SLUGS = frozenset(
    str(value).strip().lower()
    for value in json.loads(_CONFIG.read_text(encoding="utf-8")).get("reader_only_audio_excluded_slugs", [])
    if str(value).strip()
)


class ReaderOnlyAudioExcluded(ValueError):
    pass


def require_audio_candidate(slug: str) -> None:
    if str(slug).strip().lower() in READER_ONLY_AUDIO_EXCLUDED_SLUGS:
        raise ReaderOnlyAudioExcluded(f"{slug} is reader-only and excluded from audiobook/TTS generation")
