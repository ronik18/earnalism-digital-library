#!/usr/bin/env python3
"""Bounded Sarvam Saaras REST speech-to-text adapter.

Audio is split into deterministic sub-30-second temporary WAV clips. Provider
audio is never retained, errors are redacted, and returned word timestamps are
offset back onto the source file timeline.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import requests


DEFAULT_ENDPOINT = os.environ.get("SARVAM_STT_ENDPOINT", "https://api.sarvam.ai/speech-to-text")
DEFAULT_MODEL = os.environ.get("SARVAM_STT_MODEL", "saaras:v3")
DEFAULT_LANGUAGE = os.environ.get("SARVAM_STT_LANGUAGE", "bn-IN")
DEFAULT_MODE = os.environ.get("SARVAM_STT_MODE", "transcribe")
CLIP_SECONDS = 29.0
REQUIRED_APPROVAL_ENVS = (
    "EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS",
    "EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF",
    "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS",
    "EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED",
)
REQUIRED_BUDGET_ENVS = (
    "EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD",
    "EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE",
)


def require_paid_campaign_approval() -> dict[str, float]:
    """Fail closed at the provider boundary when campaign approval is absent."""
    missing = [name for name in REQUIRED_APPROVAL_ENVS if os.environ.get(name, "").strip().lower() != "true"]
    budgets: dict[str, float] = {}
    for name in REQUIRED_BUDGET_ENVS:
        raw = os.environ.get(name, "").strip()
        try:
            value = float(raw)
        except ValueError:
            value = 0.0
        if value <= 0:
            missing.append(name)
        else:
            budgets[name] = value
    if missing:
        raise RuntimeError("Paid Bengali campaign approval is incomplete: " + ", ".join(sorted(missing)))
    return budgets


def validate_campaign_budget(*, title_estimate_usd: float, campaign_cumulative_usd: float) -> None:
    budgets = require_paid_campaign_approval()
    title_cap = budgets["EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE"]
    campaign_cap = budgets["EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD"]
    if title_estimate_usd > title_cap:
        raise RuntimeError(
            f"Estimated title work {title_estimate_usd:.4f} exceeds approved per-title cap {title_cap:.4f}"
        )
    if campaign_cumulative_usd > campaign_cap:
        raise RuntimeError(
            f"Estimated campaign work {campaign_cumulative_usd:.4f} exceeds approved campaign cap {campaign_cap:.4f}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
        capture_output=True,
        check=True,
    )
    return float(result.stdout.strip())


def prepare_clips(path: Path, directory: Path, *, clip_seconds: float = CLIP_SECONDS) -> list[dict[str, Any]]:
    duration = audio_duration(path)
    clips: list[dict[str, Any]] = []
    offset = 0.0
    index = 0
    while offset < duration - 0.05:
        clip = directory / f"clip_{index:03d}.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{offset:.3f}",
                "-t",
                f"{clip_seconds:.3f}",
                "-i",
                str(path),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(clip),
            ],
            check=True,
        )
        if not clip.is_file() or clip.stat().st_size <= 44:
            raise RuntimeError(f"Sarvam ASR clip creation failed at offset {offset:.3f}")
        clips.append(
            {
                "index": index,
                "path": clip,
                "offset_seconds": round(offset, 3),
                "sha256": sha256_file(clip),
            }
        )
        offset += clip_seconds
        index += 1
    return clips


def _timestamp_candidates(timestamps: dict[str, Any]) -> list[tuple[list[Any], list[Any], list[Any]]]:
    candidates: list[tuple[list[Any], list[Any], list[Any]]] = []
    raw_words = timestamps.get("words") if isinstance(timestamps.get("words"), list) else []
    starts = timestamps.get("start_time_seconds") if isinstance(timestamps.get("start_time_seconds"), list) else []
    ends = timestamps.get("end_time_seconds") if isinstance(timestamps.get("end_time_seconds"), list) else []
    if raw_words or starts or ends:
        if not (len(raw_words) == len(starts) == len(ends)):
            raise RuntimeError("Sarvam ASR returned inconsistent timestamp arrays")
        candidates.append((raw_words, starts, ends))
    nested = timestamps.get("timestamps")
    if isinstance(nested, dict):
        candidates.extend(_timestamp_candidates(nested))
    return candidates


def timestamp_words(payload: dict[str, Any], *, offset_seconds: float) -> list[dict[str, Any]]:
    timestamps = payload.get("timestamps") if isinstance(payload.get("timestamps"), dict) else {}
    candidates = _timestamp_candidates(timestamps)
    if not candidates:
        return []
    raw_words, starts, ends = max(candidates, key=lambda item: len(item[0]))
    # A single sentence-sized token per clip is measured segment timing, not a
    # word timestamp. Never promote it to the release word-sync field.
    if raw_words and sum(str(item).count(" ") for item in raw_words) > len(raw_words):
        raise RuntimeError("Sarvam ASR returned segment timestamps instead of word timestamps")
    words: list[dict[str, Any]] = []
    for word, start, end in zip(raw_words, starts, ends):
        token = str(word or "").strip()
        if not token:
            continue
        words.append(
            {
                "word": token,
                "start": round(float(start) + offset_seconds, 3),
                "end": round(float(end) + offset_seconds, 3),
            }
        )
    return words


def transcribe_rest(
    path: Path,
    *,
    model: str = DEFAULT_MODEL,
    language: str = DEFAULT_LANGUAGE,
    mode: str = DEFAULT_MODE,
    with_timestamps: bool = True,
    timeout: float = 180.0,
    request_gap_seconds: float = 0.25,
) -> dict[str, Any]:
    require_paid_campaign_approval()
    api_key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY is required")
    transcripts: list[str] = []
    words: list[dict[str, Any]] = []
    request_ids: list[str] = []
    clip_evidence: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="earnalism-sarvam-stt-") as raw:
        clips = prepare_clips(path, Path(raw))
        for position, clip in enumerate(clips):
            clip_path = Path(clip["path"])
            with clip_path.open("rb") as handle:
                response = requests.post(
                    DEFAULT_ENDPOINT,
                    headers={"api-subscription-key": api_key},
                    files={"file": (clip_path.name, handle, "audio/wav")},
                    data={
                        "model": model,
                        "language_code": language,
                        "mode": mode,
                        "with_timestamps": "true" if with_timestamps else "false",
                    },
                    timeout=timeout,
                )
            if response.status_code >= 400:
                retry_after = response.headers.get("retry-after", "")
                raise RuntimeError(
                    f"Sarvam ASR HTTP {response.status_code}"
                    + (f" retry-after={retry_after}" if retry_after else "")
                )
            payload = response.json()
            transcript = str(payload.get("transcript") or "").strip()
            if not transcript:
                raise RuntimeError(f"Sarvam ASR returned an empty transcript for clip {position}")
            transcripts.append(transcript)
            if with_timestamps:
                clip_words = timestamp_words(payload, offset_seconds=float(clip["offset_seconds"]))
                if not clip_words:
                    raise RuntimeError(f"Sarvam ASR returned no word timestamps for clip {position}")
                words.extend(clip_words)
            request_id = str(payload.get("request_id") or "")
            if request_id:
                request_ids.append(request_id)
            clip_evidence.append(
                {
                    "index": position,
                    "offset_seconds": clip["offset_seconds"],
                    "sha256": clip["sha256"],
                    "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
                    "word_timestamp_count": len(clip_words) if with_timestamps else 0,
                }
            )
            if position + 1 < len(clips):
                time.sleep(max(float(request_gap_seconds), 0.0))
    text = " ".join(transcripts).strip()
    return {
        "text": text,
        "words": words,
        "provider": "sarvam",
        "model": model,
        "language": language,
        "mode": mode,
        "transport": "rest",
        "with_timestamps": with_timestamps,
        "timestamp_granularity": "word" if with_timestamps else "none",
        "request_count": len(clip_evidence),
        "request_id_hashes": [hashlib.sha256(value.encode("utf-8")).hexdigest() for value in request_ids],
        "clips": clip_evidence,
    }
