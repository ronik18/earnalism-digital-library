#!/usr/bin/env python3
"""Sarvam Bengali TTS adapter for Earnalism provider bakeoffs.

The adapter intentionally exposes only the small surface required by the
audition bakeoff: deterministic voice enumeration, credential detection, and
single-clip synthesis. It never logs or returns secret values.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


DEFAULT_ENDPOINT = os.environ.get("SARVAM_TTS_ENDPOINT", "https://api.sarvam.ai/text-to-speech")
DEFAULT_MODEL = os.environ.get("SARVAM_TTS_MODEL", "bulbul:v3")
DEFAULT_LANGUAGE = os.environ.get("SARVAM_TTS_LANGUAGE", "bn-IN")
DEFAULT_CODEC = os.environ.get("SARVAM_TTS_OUTPUT_CODEC", "wav")
TIMEOUT_SECONDS = float(os.environ.get("SARVAM_TTS_TIMEOUT_SECONDS", "120"))


@dataclass(frozen=True)
class SarvamVoice:
    speaker: str
    model: str = DEFAULT_MODEL
    language_code: str = DEFAULT_LANGUAGE
    output_codec: str = DEFAULT_CODEC


SARVAM_VOICES = [
    SarvamVoice("aditya"),
    SarvamVoice("ritu"),
    SarvamVoice("ashutosh"),
    SarvamVoice("priya"),
    SarvamVoice("neha"),
    SarvamVoice("rahul"),
    SarvamVoice("pooja"),
    SarvamVoice("rohan"),
    SarvamVoice("simran"),
    SarvamVoice("kavya"),
    SarvamVoice("amit"),
    SarvamVoice("dev"),
    SarvamVoice("ishita"),
    SarvamVoice("shreya"),
    SarvamVoice("ratan"),
    SarvamVoice("varun"),
    SarvamVoice("manan"),
    SarvamVoice("sumit"),
    SarvamVoice("roopa"),
    SarvamVoice("kabir"),
    SarvamVoice("aayan"),
    SarvamVoice("shubh"),
    SarvamVoice("advait"),
    SarvamVoice("anand"),
    SarvamVoice("tanya"),
    SarvamVoice("tarun"),
    SarvamVoice("sunny"),
    SarvamVoice("mani"),
    SarvamVoice("gokul"),
    SarvamVoice("vijay"),
    SarvamVoice("shruti"),
    SarvamVoice("suhani"),
    SarvamVoice("mohit"),
    SarvamVoice("kavitha"),
    SarvamVoice("rehan"),
    SarvamVoice("soham"),
    SarvamVoice("rupali"),
    SarvamVoice("niharika"),
]


def key_detected() -> bool:
    return bool(os.environ.get("SARVAM_API_KEY"))


def candidate_voices(limit: int | None = None) -> list[SarvamVoice]:
    if limit is None:
        return list(SARVAM_VOICES)
    return list(SARVAM_VOICES[: max(0, limit)])


def capability_probe() -> dict[str, Any]:
    detected = key_detected()
    return {
        "provider": "sarvam",
        "credentials_detected": detected,
        "auth_status": "detected" if detected else "missing",
        "endpoint_used": DEFAULT_ENDPOINT,
        "region": "",
        "voices_listed": [voice.speaker for voice in SARVAM_VOICES],
        "bengali_voices_detected": [voice.speaker for voice in SARVAM_VOICES],
        "sample_synthesis_succeeded": False,
        "error_message_redacted": "" if detected else "SARVAM_API_KEY missing",
        "retryable": not detected,
        "exact_next_fix": "" if detected else "Set SARVAM_API_KEY in the execution environment.",
        "style_control": False,
    }


def _extract_audio_bytes(payload: dict[str, Any]) -> bytes:
    candidates: list[Any] = []
    for key in ("audio", "audioContent", "audio_content"):
        if payload.get(key):
            candidates.append(payload[key])
    if isinstance(payload.get("audios"), list):
        candidates.extend(payload["audios"])
    for value in candidates:
        if isinstance(value, dict):
            for key in ("audio", "audioContent", "audio_content"):
                if value.get(key):
                    value = value[key]
                    break
        if isinstance(value, str):
            return base64.b64decode(value)
    raise RuntimeError(f"Sarvam TTS response did not contain recognized audio fields: {sorted(payload.keys())}")


def synthesize(text: str, out_path: Path, *, speaker: str, model: str = DEFAULT_MODEL, language_code: str = DEFAULT_LANGUAGE, output_codec: str = DEFAULT_CODEC) -> dict[str, Any]:
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY missing")
    request_body = {
        "text": text,
        "target_language_code": language_code,
        "model": model,
        "speaker": speaker,
        "pace": float(os.environ.get("SARVAM_TTS_PACE", "0.88")),
        "speech_sample_rate": int(os.environ.get("SARVAM_TTS_SAMPLE_RATE", "22050")),
        "enable_preprocessing": True,
        "output_audio_codec": output_codec,
    }
    if not model.startswith("bulbul:v3"):
        request_body["pitch"] = float(os.environ.get("SARVAM_TTS_PITCH", "0.0"))
        request_body["loudness"] = float(os.environ.get("SARVAM_TTS_LOUDNESS", "1.0"))
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json",
    }
    response = requests.post(DEFAULT_ENDPOINT, headers=headers, data=json.dumps(request_body), timeout=TIMEOUT_SECONDS)
    if response.status_code >= 400:
        body = response.text[:500] if response.text else ""
        raise RuntimeError(f"Sarvam TTS HTTP {response.status_code}: {body}")
    payload = response.json()
    audio_bytes = _extract_audio_bytes(payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio_bytes)
    if out_path.stat().st_size <= 0:
        raise RuntimeError("Sarvam TTS produced an empty audio file")
    return {
        "status": "PASS",
        "model": model,
        "speaker": speaker,
        "language_code": language_code,
        "endpoint_used": DEFAULT_ENDPOINT,
        "output_codec": output_codec,
    }
