#!/usr/bin/env python3
"""Fail-closed stdlib HTTP adapter for private Google Gemini-TTS generation.

This module prepares source-bound private audition/full-title chunks and calls
the Cloud Text-to-Speech ``text:synthesize`` REST API. It deliberately does
not upload audio, change catalog metadata, approve release gates, or publish.

The provider boundary requires explicit approval and budget environments even
when the caller already uses the paid-stage lock. Generated manifests remain
``QA_REQUIRED`` until the independent Earnalism release pipeline passes them.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MODEL = os.environ.get("EARNALISM_GEMINI_TTS_MODEL", "gemini-2.5-pro-tts")
DEFAULT_VOICE = os.environ.get("EARNALISM_GEMINI_TTS_VOICE", "Charon")
DEFAULT_LANGUAGE = os.environ.get("EARNALISM_GEMINI_TTS_LANGUAGE", "bn-BD")
DEFAULT_REGION = os.environ.get("EARNALISM_GEMINI_TTS_REGION", "global")
DEFAULT_MAX_TEXT_BYTES = int(os.environ.get("EARNALISM_GEMINI_TTS_MAX_TEXT_BYTES", "3600"))
MAX_FIELD_BYTES = 4000
MAX_COMBINED_BYTES = 8000
TIMEOUT_SECONDS = float(os.environ.get("EARNALISM_GEMINI_TTS_HTTP_TIMEOUT_SECONDS", "180"))

REQUIRED_BUDGET_ENVS = (
    "EARNALISM_GEMINI_TTS_ESTIMATED_USD_PER_1K_CHARS",
    "EARNALISM_GEMINI_TTS_MAX_ESTIMATED_USD_PER_TITLE",
    "EARNALISM_GEMINI_TTS_CAMPAIGN_MAX_ESTIMATED_USD",
    "EARNALISM_GEMINI_TTS_PRIOR_CAMPAIGN_USD",
)
REQUIRED_APPROVAL_ENVS = (
    "EARNALISM_APPROVE_GOOGLE_GEMINI_TTS",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED",
)
SUPPORTED_MODELS = {
    "gemini-2.5-pro-tts",
    "gemini-2.5-flash-tts",
    "gemini-2.5-flash-lite-preview-tts",
    "gemini-3.1-flash-tts-preview",
}
SUPPORTED_RELEASE_LANGUAGES = {"bn-BD", "en-IN", "en-US"}
_SESSION_RESERVED_USD = 0.0
_SESSION_RESERVED_BY_TITLE: dict[str, float] = {}


class GeminiTTSBlocked(RuntimeError):
    """A safe, expected fail-closed provider boundary."""


@dataclass(frozen=True)
class GeminiVoice:
    name: str
    model: str = DEFAULT_MODEL
    language_code: str = DEFAULT_LANGUAGE
    output_codec: str = "mp3"


# Keep selection deterministic. These are prebuilt Gemini-TTS voice names, not
# cloned identities. Quality selection still requires title-specific auditions.
GEMINI_VOICES = (
    GeminiVoice("Charon"),
    GeminiVoice("Kore"),
    GeminiVoice("Callirrhoe"),
    GeminiVoice("Aoede"),
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalized_required_text(value: str, field: str) -> str:
    normalized = " ".join(str(value or "").split())
    if not normalized:
        raise GeminiTTSBlocked(f"{field} is required")
    return normalized


def build_title_style_prompt(
    *,
    slug: str,
    title: str,
    author: str,
    language_code: str,
    direction: str,
) -> str:
    """Build a deterministic title-bound prompt without altering the source."""

    slug = _normalized_required_text(slug, "slug")
    title = _normalized_required_text(title, "title")
    author = _normalized_required_text(author, "author")
    direction = _normalized_required_text(direction, "direction")
    if language_code not in SUPPORTED_RELEASE_LANGUAGES:
        raise GeminiTTSBlocked(
            f"Unsupported release language {language_code!r}; expected one of "
            + ", ".join(sorted(SUPPORTED_RELEASE_LANGUAGES))
        )
    language_label = {
        "bn-BD": "Bangla (Bangladesh)",
        "en-IN": "English (India)",
        "en-US": "English (United States)",
    }[language_code]
    prompt = (
        f"Create a premium single-narrator audiobook performance of {title} by {author} "
        f"for Earnalism, in {language_label}. Title key: {slug}. {direction} "
        "Recite only the supplied text, in its exact order. Do not add a title, author, "
        "preface, explanation, sound effect, music, translation, or closing remark. "
        "Preserve every word, punctuation cue, paragraph transition, and intentional "
        "repetition. Keep pronunciation clear, cadence natural, pauses meaningful, joins "
        "smooth, volume uniform, and emotion expressive but restrained."
    )
    if len(prompt.encode("utf-8")) > MAX_FIELD_BYTES:
        raise GeminiTTSBlocked("Title style prompt exceeds the Cloud Gemini-TTS 4,000-byte field limit")
    return prompt


def _max_end_for_utf8_bytes(text: str, start: int, byte_limit: int) -> int:
    low = start + 1
    high = len(text)
    best = start
    while low <= high:
        middle = (low + high) // 2
        if len(text[start:middle].encode("utf-8")) <= byte_limit:
            best = middle
            low = middle + 1
        else:
            high = middle - 1
    return best


def _preferred_boundary(text: str, start: int, hard_end: int) -> int:
    if hard_end >= len(text):
        return hard_end
    minimum = start + max(1, (hard_end - start) // 2)
    window = text[start:hard_end]
    candidates: list[int] = []
    for mark in ("\n\n", "\n", "।", "!", "?", ".", ";", ":", "—", ",", " "):
        index = window.rfind(mark)
        if index >= 0:
            candidates.append(start + index + len(mark))
    usable = [candidate for candidate in candidates if candidate >= minimum]
    return max(usable) if usable else hard_end


def source_bound_chunks(
    source_text: str,
    *,
    expected_source_sha256: str,
    style_prompt: str,
    max_text_bytes: int = DEFAULT_MAX_TEXT_BYTES,
) -> list[dict[str, Any]]:
    """Split source losslessly into deterministic byte-bounded API requests."""

    if not source_text:
        raise GeminiTTSBlocked("source_text is empty")
    actual_source_sha256 = sha256_text(source_text)
    if expected_source_sha256 != actual_source_sha256:
        raise GeminiTTSBlocked("source_text SHA-256 does not match the expected canonical manuscript hash")
    prompt_bytes = len(style_prompt.encode("utf-8"))
    if not style_prompt or prompt_bytes > MAX_FIELD_BYTES:
        raise GeminiTTSBlocked("style_prompt must be non-empty and no more than 4,000 UTF-8 bytes")
    if max_text_bytes <= 0 or max_text_bytes > MAX_FIELD_BYTES:
        raise GeminiTTSBlocked("max_text_bytes must be between 1 and 4,000")

    chunks: list[dict[str, Any]] = []
    start = 0
    while start < len(source_text):
        hard_end = _max_end_for_utf8_bytes(source_text, start, max_text_bytes)
        if hard_end <= start:
            raise GeminiTTSBlocked("Unable to fit the next source character within the configured byte limit")
        end = _preferred_boundary(source_text, start, hard_end)
        text = source_text[start:end]
        text_bytes = len(text.encode("utf-8"))
        if text_bytes > MAX_FIELD_BYTES or text_bytes + prompt_bytes > MAX_COMBINED_BYTES:
            raise GeminiTTSBlocked("A source-bound chunk exceeds Cloud Gemini-TTS request byte limits")
        chunks.append(
            {
                "index": len(chunks),
                "start_char": start,
                "end_char": end,
                "text": text,
                "text_sha256": sha256_text(text),
                "text_bytes": text_bytes,
                "source_text_sha256": actual_source_sha256,
                "style_prompt_sha256": sha256_text(style_prompt),
            }
        )
        start = end
    if "".join(chunk["text"] for chunk in chunks) != source_text:
        raise GeminiTTSBlocked("Source-bound chunk reconstruction failed")
    return chunks


def _parse_explicit_number(name: str, *, allow_zero: bool = False) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise GeminiTTSBlocked(f"{name} must be explicitly set to a numeric value") from exc
    if value < 0 or (value == 0 and not allow_zero):
        qualifier = "zero or greater" if allow_zero else "greater than zero"
        raise GeminiTTSBlocked(f"{name} must be {qualifier}")
    return value


def authorize_and_estimate(
    source_text: str,
    *,
    budget_key: str = "__unscoped__",
    reserve_session: bool = False,
) -> dict[str, float]:
    """Require an explicit paid scope and verify per-title/campaign caps."""

    global _SESSION_RESERVED_USD
    missing_approvals = [
        name
        for name in REQUIRED_APPROVAL_ENVS
        if os.environ.get(name, "").strip().lower() not in {"1", "true", "yes"}
    ]
    if missing_approvals:
        raise GeminiTTSBlocked("Google Gemini-TTS approval is incomplete: " + ", ".join(missing_approvals))
    rate = _parse_explicit_number("EARNALISM_GEMINI_TTS_ESTIMATED_USD_PER_1K_CHARS")
    title_cap = _parse_explicit_number("EARNALISM_GEMINI_TTS_MAX_ESTIMATED_USD_PER_TITLE")
    campaign_cap = _parse_explicit_number("EARNALISM_GEMINI_TTS_CAMPAIGN_MAX_ESTIMATED_USD")
    prior = _parse_explicit_number("EARNALISM_GEMINI_TTS_PRIOR_CAMPAIGN_USD", allow_zero=True)
    estimate = round((len(source_text) / 1000.0) * rate, 6)
    title_reserved = _SESSION_RESERVED_BY_TITLE.get(budget_key, 0.0)
    projected_title = round(title_reserved + estimate, 6)
    projected_campaign = round(prior + _SESSION_RESERVED_USD + estimate, 6)
    if projected_title > title_cap:
        raise GeminiTTSBlocked(
            f"Projected Gemini-TTS title spend {projected_title:.6f} exceeds cap {title_cap:.6f}"
        )
    if projected_campaign > campaign_cap:
        raise GeminiTTSBlocked(
            f"Projected Gemini-TTS campaign spend {projected_campaign:.6f} exceeds cap {campaign_cap:.6f}"
        )
    if reserve_session:
        _SESSION_RESERVED_USD = round(_SESSION_RESERVED_USD + estimate, 6)
        _SESSION_RESERVED_BY_TITLE[budget_key] = projected_title
    return {
        "estimated_usd_per_1k_chars": rate,
        "estimated_title_usd": estimate,
        "session_projected_title_estimated_usd": projected_title,
        "title_cap_usd": title_cap,
        "prior_campaign_estimated_usd": prior,
        "session_reserved_estimated_usd": _SESSION_RESERVED_USD,
        "projected_campaign_estimated_usd": projected_campaign,
        "campaign_cap_usd": campaign_cap,
    }


def _adc_path() -> Path:
    value = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    path = Path(value).expanduser() if value else Path()
    if not value or not path.is_file():
        raise GeminiTTSBlocked("GOOGLE_APPLICATION_CREDENTIALS is missing or unreadable")
    return path


def _load_authorized_user_adc() -> dict[str, Any]:
    try:
        credentials = json.loads(_adc_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GeminiTTSBlocked("Google ADC JSON is unreadable") from exc
    if credentials.get("type") != "authorized_user":
        raise GeminiTTSBlocked("Google Gemini-TTS currently requires authorized_user ADC")
    missing = [
        field
        for field in ("client_id", "client_secret", "refresh_token")
        if not str(credentials.get(field) or "").strip()
    ]
    if missing:
        raise GeminiTTSBlocked("Google authorized_user ADC is missing required fields: " + ", ".join(missing))
    return credentials


def _safe_google_http_error(prefix: str, exc: urllib.error.HTTPError) -> GeminiTTSBlocked:
    error_code = ""
    error_description = ""
    try:
        payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        error = payload.get("error") if isinstance(payload, dict) else {}
        if isinstance(error, dict):
            error_code = str(error.get("status") or error.get("code") or "")
            details = error.get("details") if isinstance(error.get("details"), list) else []
            reasons = [
                str(detail.get("reason") or "")
                for detail in details
                if isinstance(detail, dict) and detail.get("reason")
            ]
            error_description = ",".join(reasons)
        else:
            error_code = str(error or "")
            error_description = str(payload.get("error_description") or "")
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    marker = f" code={error_code}" if error_code else ""
    if "invalid_rapt" in error_description.lower():
        marker += " reason=invalid_rapt; run `gcloud auth application-default login --project=earnalism`"
    elif error_description:
        marker += f" reason={error_description[:80]}"
    return GeminiTTSBlocked(f"{prefix} HTTP {exc.code}:{marker}".rstrip(":"))


def refresh_adc_access_token() -> str:
    credentials = _load_authorized_user_adc()
    body = urllib.parse.urlencode(
        {
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "refresh_token": credentials["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        credentials.get("token_uri") or "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise _safe_google_http_error("Google ADC refresh failed", exc) from exc
    except urllib.error.URLError as exc:
        raise GeminiTTSBlocked(f"Google ADC refresh transport failed: {type(exc.reason).__name__}") from exc
    token = str(payload.get("access_token") or "")
    if not token:
        raise GeminiTTSBlocked("Google ADC refresh returned no access token")
    return token


def _project_id() -> str:
    project = (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GOOGLE_TTS_PROJECT")
        or os.environ.get("GOOGLE_CLOUD_QUOTA_PROJECT")
        or ""
    ).strip()
    if not project:
        raise GeminiTTSBlocked("GOOGLE_CLOUD_PROJECT or GOOGLE_TTS_PROJECT is required")
    return project


def endpoint_for_region(region: str = DEFAULT_REGION) -> str:
    normalized = _normalized_required_text(region, "region").lower()
    host = "texttospeech.googleapis.com" if normalized == "global" else f"{normalized}-texttospeech.googleapis.com"
    return f"https://{host}/v1/text:synthesize"


def _assert_private_output(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    prohibited = (ROOT / "frontend" / "public", ROOT / "frontend" / "build")
    parts = resolved.parts
    contains_frontend_public_tree = any(
        parts[index] == "frontend" and parts[index + 1] in {"public", "build"}
        for index in range(len(parts) - 1)
    )
    if contains_frontend_public_tree or any(
        resolved == base.resolve() or base.resolve() in resolved.parents for base in prohibited
    ):
        raise GeminiTTSBlocked("Gemini-TTS output must remain outside frontend/public and frontend/build")
    return resolved


def _request_audio(
    *,
    access_token: str,
    text: str,
    style_prompt: str,
    voice: str,
    model: str,
    language_code: str,
    region: str,
) -> tuple[bytes, str]:
    if model not in SUPPORTED_MODELS:
        raise GeminiTTSBlocked(f"Unsupported Gemini-TTS model: {model}")
    if language_code not in SUPPORTED_RELEASE_LANGUAGES:
        raise GeminiTTSBlocked(f"Unsupported Gemini-TTS release language: {language_code}")
    endpoint = endpoint_for_region(region)
    request_body = {
        "input": {"prompt": style_prompt, "text": text},
        "voice": {
            "languageCode": language_code,
            "name": _normalized_required_text(voice, "voice"),
            "model_name": model,
        },
        "audioConfig": {"audioEncoding": "MP3"},
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(request_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "x-goog-user-project": _project_id(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise _safe_google_http_error("Cloud Gemini-TTS synthesis failed", exc) from exc
    except urllib.error.URLError as exc:
        raise GeminiTTSBlocked(f"Cloud Gemini-TTS transport failed: {type(exc.reason).__name__}") from exc
    encoded = payload.get("audioContent") or payload.get("audio_content")
    if not isinstance(encoded, str) or not encoded:
        raise GeminiTTSBlocked("Cloud Gemini-TTS response contained no audioContent")
    try:
        audio = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise GeminiTTSBlocked("Cloud Gemini-TTS returned invalid base64 audioContent") from exc
    if len(audio) < 4 or not (audio.startswith(b"ID3") or (audio[0] == 0xFF and audio[1] & 0xE0 == 0xE0)):
        raise GeminiTTSBlocked("Cloud Gemini-TTS response is not recognizable MP3 audio")
    return audio, endpoint


def _atomic_write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(value)
    temporary.replace(path)


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _atomic_write_bytes(path, encoded)


def synthesize(
    text: str,
    out_path: Path,
    *,
    slug: str,
    title: str,
    author: str,
    direction: str,
    voice: str = DEFAULT_VOICE,
    model: str = DEFAULT_MODEL,
    language_code: str = DEFAULT_LANGUAGE,
    region: str = DEFAULT_REGION,
    expected_source_sha256: str | None = None,
) -> dict[str, Any]:
    """Generate one private source-bound MP3 clip after all local gates pass."""

    source_hash = sha256_text(text)
    if expected_source_sha256 is not None and expected_source_sha256 != source_hash:
        raise GeminiTTSBlocked("source_text SHA-256 does not match the expected source hash")
    style_prompt = build_title_style_prompt(
        slug=slug,
        title=title,
        author=author,
        language_code=language_code,
        direction=direction,
    )
    source_bound_chunks(
        text,
        expected_source_sha256=source_hash,
        style_prompt=style_prompt,
        max_text_bytes=MAX_FIELD_BYTES,
    )
    # Reject a known over-budget request before ADC/network. Reserve only after
    # ADC refresh succeeds; after that point an HTTP failure can have uncertain
    # billing and the conservative in-process reservation must remain.
    authorize_and_estimate(text, budget_key=slug)
    destination = _assert_private_output(out_path)
    token = refresh_adc_access_token()
    budget = authorize_and_estimate(text, budget_key=slug, reserve_session=True)
    audio, endpoint = _request_audio(
        access_token=token,
        text=text,
        style_prompt=style_prompt,
        voice=voice,
        model=model,
        language_code=language_code,
        region=region,
    )
    _atomic_write_bytes(destination, audio)
    return {
        "status": "PASS_PRIVATE_QA_REQUIRED",
        "provider": "google_gemini_tts",
        "model": model,
        "voice": voice,
        "language_code": language_code,
        "output_codec": "mp3",
        "endpoint_used": endpoint,
        "source_text_sha256": source_hash,
        "style_prompt_sha256": sha256_text(style_prompt),
        "audio_sha256": sha256_file(destination),
        "audio_size_bytes": destination.stat().st_size,
        "audio_path": str(destination),
        "budget": budget,
        "qa_required": True,
        "release_ready": False,
        "publication_performed": False,
    }


def synthesize_title(
    source_text: str,
    output_dir: Path,
    *,
    slug: str,
    title: str,
    author: str,
    direction: str,
    expected_source_sha256: str,
    voice: str = DEFAULT_VOICE,
    model: str = DEFAULT_MODEL,
    language_code: str = DEFAULT_LANGUAGE,
    region: str = DEFAULT_REGION,
    max_text_bytes: int = DEFAULT_MAX_TEXT_BYTES,
) -> dict[str, Any]:
    """Generate a private chunk package and a hash-bound QA-required manifest."""

    style_prompt = build_title_style_prompt(
        slug=slug,
        title=title,
        author=author,
        language_code=language_code,
        direction=direction,
    )
    chunks = source_bound_chunks(
        source_text,
        expected_source_sha256=expected_source_sha256,
        style_prompt=style_prompt,
        max_text_bytes=max_text_bytes,
    )
    authorize_and_estimate(source_text, budget_key=slug)
    private_dir = _assert_private_output(output_dir)
    token = refresh_adc_access_token()
    budget = authorize_and_estimate(source_text, budget_key=slug, reserve_session=True)
    generated_chunks: list[dict[str, Any]] = []
    endpoint = endpoint_for_region(region)
    for chunk in chunks:
        audio, endpoint = _request_audio(
            access_token=token,
            text=chunk["text"],
            style_prompt=style_prompt,
            voice=voice,
            model=model,
            language_code=language_code,
            region=region,
        )
        audio_path = private_dir / "source_audio" / f"chunk_{chunk['index']:05d}.mp3"
        _atomic_write_bytes(audio_path, audio)
        generated_chunks.append(
            {
                "index": chunk["index"],
                "start_char": chunk["start_char"],
                "end_char": chunk["end_char"],
                "text_sha256": chunk["text_sha256"],
                "text_bytes": chunk["text_bytes"],
                "audio_path": str(audio_path),
                "audio_sha256": sha256_file(audio_path),
                "audio_size_bytes": audio_path.stat().st_size,
            }
        )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "status": "PRIVATE_GENERATED_QA_REQUIRED",
        "generated_at": _iso_now(),
        "slug": slug,
        "title": title,
        "author": author,
        "provider": "google_gemini_tts",
        "model": model,
        "voice": voice,
        "language_code": language_code,
        "region": region,
        "output_codec": "mp3",
        "endpoint_used": endpoint,
        "source_text_sha256": expected_source_sha256,
        "source_character_count": len(source_text),
        "source_utf8_bytes": len(source_text.encode("utf-8")),
        "source_reconstruction_pass": "".join(chunk["text"] for chunk in chunks) == source_text,
        "style_prompt_sha256": sha256_text(style_prompt),
        "chunk_count": len(generated_chunks),
        "chunks": generated_chunks,
        "budget": budget,
        "private_audio_only": True,
        "qa_required": True,
        "release_ready": False,
        "release_gate_mutated": False,
        "upload_performed": False,
        "metadata_mutated": False,
        "publication_performed": False,
    }
    manifest["manifest_payload_sha256"] = sha256_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    manifest_path = private_dir / "google_gemini_tts_manifest.json"
    _atomic_write_json(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    manifest["manifest_file_sha256"] = sha256_file(manifest_path)
    return manifest


def candidate_voices(
    limit: int | None = None,
    *,
    model: str = DEFAULT_MODEL,
    language_code: str = DEFAULT_LANGUAGE,
) -> list[GeminiVoice]:
    voices = [
        GeminiVoice(voice.name, model=model, language_code=language_code, output_codec="mp3")
        for voice in GEMINI_VOICES
    ]
    return voices if limit is None else voices[: max(0, limit)]


def capability_probe() -> dict[str, Any]:
    """Inspect configuration only; never refresh ADC or call the provider."""

    adc_configured = False
    adc_type = ""
    adc_error = ""
    try:
        adc = _load_authorized_user_adc()
        adc_configured = True
        adc_type = str(adc.get("type") or "")
    except GeminiTTSBlocked as exc:
        adc_error = str(exc)
    project_configured = bool(
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GOOGLE_TTS_PROJECT")
        or os.environ.get("GOOGLE_CLOUD_QUOTA_PROJECT")
    )
    budget_envs_present = all(os.environ.get(name, "").strip() for name in REQUIRED_BUDGET_ENVS)
    approvals_present = all(
        os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}
        for name in REQUIRED_APPROVAL_ENVS
    )
    configured = adc_configured and project_configured and budget_envs_present and approvals_present
    return {
        "provider": "google_gemini_tts",
        "credentials_detected": adc_configured,
        "adc_type": adc_type,
        "auth_status": "configured_not_refreshed" if adc_configured else "missing_or_invalid_configuration",
        "project_configured": project_configured,
        "budget_envs_present": budget_envs_present,
        "approvals_present": approvals_present,
        "available_for_private_generation": configured,
        "endpoint_used": endpoint_for_region(),
        "models": sorted(SUPPORTED_MODELS),
        "voices_listed": [voice.name for voice in GEMINI_VOICES],
        "release_languages": sorted(SUPPORTED_RELEASE_LANGUAGES),
        "sample_synthesis_succeeded": False,
        "error_message_redacted": adc_error,
        "retryable": not configured,
        "exact_next_fix": (
            ""
            if configured
            else "Repair authorized-user ADC, set a Google Cloud project, and provide explicit Gemini-TTS approval and budget envs."
        ),
        "network_probe_performed": False,
        "qa_required": True,
        "release_ready": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Private fail-closed Google Gemini-TTS adapter")
    parser.add_argument("--probe", action="store_true", help="Inspect configuration only; never refresh ADC")
    parser.add_argument("--source-text-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--slug", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--author", default="")
    parser.add_argument("--direction", default="")
    parser.add_argument("--source-sha256", default="")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=sorted(SUPPORTED_MODELS))
    parser.add_argument("--language-code", default=DEFAULT_LANGUAGE, choices=sorted(SUPPORTED_RELEASE_LANGUAGES))
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--max-text-bytes", type=int, default=DEFAULT_MAX_TEXT_BYTES)
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(capability_probe(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    required = {
        "--source-text-path": args.source_text_path,
        "--output-dir": args.output_dir,
        "--slug": args.slug,
        "--title": args.title,
        "--author": args.author,
        "--direction": args.direction,
        "--source-sha256": args.source_sha256,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        parser.error("generation requires " + ", ".join(missing))
    try:
        source_text = args.source_text_path.read_text(encoding="utf-8")
        manifest = synthesize_title(
            source_text,
            args.output_dir,
            slug=args.slug,
            title=args.title,
            author=args.author,
            direction=args.direction,
            expected_source_sha256=args.source_sha256,
            voice=args.voice,
            model=args.model,
            language_code=args.language_code,
            region=args.region,
            max_text_bytes=args.max_text_bytes,
        )
    except (OSError, GeminiTTSBlocked) as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "provider": "google_gemini_tts",
                    "reason": str(exc),
                    "release_ready": False,
                    "publication_performed": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "manifest_path": manifest["manifest_path"],
                "manifest_file_sha256": manifest["manifest_file_sha256"],
                "chunk_count": manifest["chunk_count"],
                "estimated_title_usd": manifest["budget"]["estimated_title_usd"],
                "qa_required": True,
                "release_ready": False,
                "publication_performed": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
