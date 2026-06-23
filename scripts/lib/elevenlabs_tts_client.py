#!/usr/bin/env python3
"""Guarded ElevenLabs TTS adapter for internal audiobook evaluation.

The adapter defaults to request-body construction only. It reads the API key
from the environment only when execute=True, never logs secrets, and refuses to
write generated audio outside internal/audiobook_lab.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
INTERNAL_AUDIOBOOK_ROOT = ROOT / "internal" / "audiobook_lab"
PUBLIC_PATH_PARTS = {
    ("frontend", "public"),
    ("frontend", "build"),
}
ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsSafetyError(RuntimeError):
    """Raised when a provider call or output path fails a safety gate."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_internal_output_path(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(INTERNAL_AUDIOBOOK_ROOT.resolve())
    except ValueError as exc:
        raise ElevenLabsSafetyError("generated audio output must stay under internal/audiobook_lab") from exc

    relative_parts = resolved.relative_to(ROOT.resolve()).parts
    for index in range(len(relative_parts) - 1):
        if tuple(relative_parts[index : index + 2]) in PUBLIC_PATH_PARTS:
            raise ElevenLabsSafetyError("generated audio output cannot use frontend/public or frontend/build")
    return resolved


@dataclass(frozen=True)
class ElevenLabsSettings:
    provider: str
    voice_id: str
    voice_name: str
    model_id: str
    output_format: str = "mp3_44100_128"
    speed: float = 1.0
    stability: float = 0.5
    similarity_boost: float = 0.75
    style_exaggeration: float = 0.0
    speaker_boost: bool = True
    pronunciation_dictionary_locators: list[dict[str, str]] = field(default_factory=list)
    beta_services_allowed: bool = False
    voice_cloning_allowed: bool = False
    elevenreader_allowed: bool = False

    def safety_blockers(self) -> list[str]:
        blockers: list[str] = []
        if self.provider.lower() != "elevenlabs":
            blockers.append("provider must be elevenlabs")
        if self.beta_services_allowed:
            blockers.append("beta services are not allowed")
        if self.voice_cloning_allowed:
            blockers.append("voice cloning is not allowed")
        if self.elevenreader_allowed:
            blockers.append("ElevenReader is not allowed")
        if not self.voice_id.strip():
            blockers.append("voice_id is required")
        if not self.model_id.strip():
            blockers.append("model_id is required")
        return blockers

    def settings_hash(self) -> str:
        return sha256_text(json.dumps(self.request_settings(), sort_keys=True, ensure_ascii=False))

    def request_settings(self) -> dict[str, Any]:
        return {
            "speed": self.speed,
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style_exaggeration,
            "use_speaker_boost": self.speaker_boost,
        }


def build_tts_request_body(text: str, settings: ElevenLabsSettings) -> dict[str, Any]:
    blockers = settings.safety_blockers()
    if blockers:
        raise ElevenLabsSafetyError("; ".join(blockers))
    body: dict[str, Any] = {
        "text": text,
        "model_id": settings.model_id,
        "voice_settings": settings.request_settings(),
    }
    if settings.pronunciation_dictionary_locators:
        body["pronunciation_dictionary_locators"] = settings.pronunciation_dictionary_locators
    return body


def dry_run_generation_record(
    *,
    chunk_id: str,
    text: str,
    settings: ElevenLabsSettings,
    output_path: Path,
) -> dict[str, Any]:
    output_path = ensure_internal_output_path(output_path)
    body = build_tts_request_body(text, settings)
    return {
        "chunk_id": chunk_id,
        "provider": "ElevenLabs",
        "voice_name": settings.voice_name,
        "voice_id": settings.voice_id,
        "model_id": settings.model_id,
        "output_format": settings.output_format,
        "request_body": body,
        "request_body_hash": sha256_text(json.dumps(body, sort_keys=True, ensure_ascii=False)),
        "settings_hash": settings.settings_hash(),
        "text_hash": sha256_text(text),
        "output_path": str(output_path.relative_to(ROOT)),
        "generation_status": "DRY_RUN_ONLY",
        "provider_api_called": False,
        "audio_hash": "",
        "generated_at": "",
    }


def generate_tts_audio(
    *,
    chunk_id: str,
    text: str,
    settings: ElevenLabsSettings,
    output_path: Path,
    execute: bool = False,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    output_path = ensure_internal_output_path(output_path)
    body = build_tts_request_body(text, settings)
    if not execute:
        return dry_run_generation_record(chunk_id=chunk_id, text=text, settings=settings, output_path=output_path)

    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise ElevenLabsSafetyError("ELEVENLABS_API_KEY is required for execute mode")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{ELEVENLABS_API_BASE}/text-to-speech/{settings.voice_id}?output_format={settings.output_format}"
    request = Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - explicit owner-gated provider call.
            audio_bytes = response.read()
    except HTTPError as exc:
        raise ElevenLabsSafetyError(f"ElevenLabs API request failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise ElevenLabsSafetyError("ElevenLabs API request failed") from exc

    output_path.write_bytes(audio_bytes)
    audio_hash = sha256_file(output_path)
    generated_at = utc_now()
    return {
        "chunk_id": chunk_id,
        "provider": "ElevenLabs",
        "voice_name": settings.voice_name,
        "voice_id": settings.voice_id,
        "model_id": settings.model_id,
        "output_format": settings.output_format,
        "request_body_hash": sha256_text(json.dumps(body, sort_keys=True, ensure_ascii=False)),
        "settings_hash": settings.settings_hash(),
        "text_hash": sha256_text(text),
        "output_path": str(output_path.relative_to(ROOT)),
        "generation_status": "GENERATED_INTERNAL_ONLY",
        "provider_api_called": True,
        "audio_hash": audio_hash,
        "generated_at": generated_at,
    }
