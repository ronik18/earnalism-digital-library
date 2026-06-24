#!/usr/bin/env python3
"""Opt-in ElevenLabs API generation for internal full-chapter audiobook QA.

Default mode is dry-run. Generate mode is deliberately fenced by explicit CLI
mode, environment switches, provider evidence, cost controls, and internal-only
path checks. The script writes manifests and QA evidence, but never approves
public audio or production use.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tts_provider_internal_eval_review import (  # noqa: E402
    ELIGIBLE_INTERNAL_EVAL_ONLY,
    PRODUCTION_BLOCKED,
    review_provider_candidates,
    selected_provider_decision,
)


INTERNAL_AUDIOBOOK_ROOT = ROOT / "internal" / "audiobook_lab"
PUBLIC_AUDIO_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
HOLD_SYNC_QA_REQUIRED = "HOLD_SYNC_QA_REQUIRED"
ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}
PUBLIC_PATHS = (ROOT / "frontend" / "public", ROOT / "frontend" / "build")


class GenerationSafetyError(RuntimeError):
    """Raised when an API generation safety gate is not satisfied."""


@dataclass(frozen=True)
class ManualChunk:
    chunk_id: str
    text: str
    sentence_ids: list[str]
    audio_filename: str
    estimated_duration_seconds: float | None
    manifest_text_hash: str
    manifest_settings_hash: str
    chunk_text_path: Path

    @property
    def text_hash(self) -> str:
        return sha256_text(self.text)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "unknown"


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, ensure_ascii=False))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def chapter_dir(book_slug: str, language: str, chapter: int | str) -> Path:
    return INTERNAL_AUDIOBOOK_ROOT / safe_slug(book_slug) / language.lower() / f"chapter-{int(chapter)}"


def ensure_internal_path(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(INTERNAL_AUDIOBOOK_ROOT.resolve())
    except ValueError as exc:
        raise GenerationSafetyError(f"{label} must stay under internal/audiobook_lab") from exc
    for public_path in PUBLIC_PATHS:
        try:
            resolved.relative_to(public_path.resolve())
        except ValueError:
            continue
        raise GenerationSafetyError(f"{label} must not be under {relative_path(public_path)}")
    return resolved


def reject_public_audio_files() -> list[str]:
    found: list[str] = []
    for public_path in PUBLIC_PATHS:
        if not public_path.exists():
            continue
        for path in public_path.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                found.append(relative_path(path))
    return sorted(found)


def voice_settings_for_request(config: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("voice_settings")
    if not isinstance(settings, dict):
        raise GenerationSafetyError("voice_settings must be present in API generation config")
    allowed = ("stability", "similarity_boost", "style", "speed", "use_speaker_boost")
    return {key: settings[key] for key in allowed if key in settings}


def settings_hash(config: dict[str, Any]) -> str:
    payload = {
        "provider": config.get("provider"),
        "voice_name": config.get("voice_name"),
        "voice_id": config.get("voice_id"),
        "model_id": config.get("model_id"),
        "output_format": config.get("output_format"),
        "language_code": config.get("language_code"),
        "voice_settings": voice_settings_for_request(config),
        "beta_services_used": config.get("beta_services_used"),
        "voice_cloning_used": config.get("voice_cloning_used"),
        "elevenreader_used": config.get("elevenreader_used"),
    }
    return sha256_json(payload)


def require_config_safety(config: dict[str, Any]) -> None:
    blockers: list[str] = []
    if str(config.get("provider", "")).lower() != "elevenlabs":
        blockers.append("provider must be elevenlabs")
    if config.get("voice_name") != "Rachel":
        blockers.append("voice_name must be Rachel")
    if config.get("voice_id") != "21m00Tcm4TlvDq8ikWAM":
        blockers.append("voice_id must be 21m00Tcm4TlvDq8ikWAM")
    if config.get("model_id") != "eleven_multilingual_v2":
        blockers.append("model_id must be eleven_multilingual_v2")
    if config.get("output_format") != "mp3_44100_192":
        blockers.append("output_format must be mp3_44100_192")
    if bool(config.get("beta_services_used")):
        blockers.append("beta_services_used must be false")
    if bool(config.get("voice_cloning_used")):
        blockers.append("voice_cloning_used must be false")
    if bool(config.get("elevenreader_used")):
        blockers.append("elevenreader_used must be false")
    if config.get("production_status") != PRODUCTION_BLOCKED:
        blockers.append("production_status must remain PRODUCTION_BLOCKED")
    if bool(config.get("public_audio_allowed")):
        blockers.append("public_audio_allowed must be false")
    voice_settings_for_request(config)
    if blockers:
        raise GenerationSafetyError("; ".join(blockers))


def require_provider_internal_eval_gate() -> dict[str, Any]:
    decisions = review_provider_candidates()
    decision = selected_provider_decision("elevenlabs", decisions)
    if decision.internal_generation_status != ELIGIBLE_INTERNAL_EVAL_ONLY:
        raise GenerationSafetyError(
            "ElevenLabs provider evidence must be ELIGIBLE_INTERNAL_EVAL_ONLY before API generation"
        )
    if decision.public_production_status != PRODUCTION_BLOCKED:
        raise GenerationSafetyError("ElevenLabs production status must remain PRODUCTION_BLOCKED")
    return {
        "provider_id": decision.provider.get("provider_id"),
        "decision_status": decision.decision_status,
        "internal_eval_status": decision.internal_eval_status,
        "internal_generation_status": decision.internal_generation_status,
        "public_production_status": decision.public_production_status,
        "owner_evidence_path": decision.provider.get("owner_evidence_path"),
    }


def load_manual_chunks(sample_dir: Path, selector: str, max_chunks: int | None) -> list[ManualChunk]:
    manual_dir = sample_dir / "manual_elevenlabs_chunks"
    expected_path = manual_dir / "expected_audio_filenames.json"
    if not expected_path.exists():
        raise FileNotFoundError(f"expected_audio_filenames.json not found: {relative_path(expected_path)}")
    expected = load_json(expected_path)
    expected_chunks = expected.get("chunks", [])
    if not isinstance(expected_chunks, list) or not expected_chunks:
        raise GenerationSafetyError("expected_audio_filenames.json must contain a non-empty chunks list")

    selected_payloads = expected_chunks[:3] if selector == "first3" else expected_chunks
    if max_chunks is not None:
        selected_payloads = selected_payloads[: max(0, max_chunks)]
    chunks: list[ManualChunk] = []
    for payload in selected_payloads:
        chunk_id = str(payload.get("chunk_id", "")).strip()
        if not re.fullmatch(r"c\d{3}", chunk_id):
            raise GenerationSafetyError(f"invalid chunk_id in expected manifest: {chunk_id}")
        text_path = ROOT / str(payload.get("chunk_text_path", ""))
        text_path = ensure_internal_path(text_path, f"{chunk_id} chunk text path")
        if not text_path.exists():
            raise FileNotFoundError(f"manual chunk text not found: {relative_path(text_path)}")
        audio_filename = str(payload.get("audio_filename") or f"dracula-chapter-1-elevenlabs-rachel-{chunk_id}.mp3")
        if Path(audio_filename).name != audio_filename or Path(audio_filename).suffix.lower() not in AUDIO_EXTENSIONS:
            raise GenerationSafetyError(f"invalid audio filename for {chunk_id}")
        chunks.append(
            ManualChunk(
                chunk_id=chunk_id,
                text=text_path.read_text(encoding="utf-8").strip(),
                sentence_ids=[str(item) for item in payload.get("sentence_ids", [])],
                audio_filename=audio_filename,
                estimated_duration_seconds=payload.get("estimated_duration_seconds"),
                manifest_text_hash=str(payload.get("text_hash") or ""),
                manifest_settings_hash=str(payload.get("settings_hash") or ""),
                chunk_text_path=text_path,
            )
        )
    return chunks


def output_audio_path(output_dir: Path, chunk: ManualChunk) -> Path:
    return ensure_internal_path(output_dir / chunk.audio_filename, f"{chunk.chunk_id} generated audio output path")


def load_existing_generation_records(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = load_json(path)
    records = payload.get("chunks", [])
    if not isinstance(records, list):
        return {}
    return {str(record.get("chunk_id")): record for record in records if isinstance(record, dict)}


def existing_cache_record(
    *,
    chunk: ManualChunk,
    generation_manifest_path: Path,
    output_path: Path,
    current_settings_hash: str,
) -> dict[str, Any] | None:
    record = load_existing_generation_records(generation_manifest_path).get(chunk.chunk_id)
    if not record:
        return None
    if record.get("text_hash") != chunk.text_hash or record.get("settings_hash") != current_settings_hash:
        return None
    if not output_path.exists():
        return None
    return record


def build_request_body(
    *,
    chunk: ManualChunk,
    previous_chunk: ManualChunk | None,
    next_chunk: ManualChunk | None,
    config: dict[str, Any],
    previous_request_id: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "text": chunk.text,
        "model_id": config["model_id"],
        "voice_settings": voice_settings_for_request(config),
    }
    if config.get("language_code"):
        body["language_code"] = config["language_code"]
    if previous_chunk:
        body["previous_text"] = previous_chunk.text
    if next_chunk:
        body["next_text"] = next_chunk.text
    if previous_request_id:
        body["previous_request_ids"] = [previous_request_id]
    locators = config.get("pronunciation_dictionary_locators")
    if isinstance(locators, list) and locators:
        body["pronunciation_dictionary_locators"] = locators
    return body


def post_with_timestamps(
    *,
    api_key: str,
    voice_id: str,
    output_format: str,
    body: dict[str, Any],
    timeout_seconds: int = 180,
    urlopen_fn: Callable[..., Any] = urlopen,
) -> tuple[bytes, dict[str, Any], str | None]:
    url = f"{ELEVENLABS_API_BASE}/text-to-speech/{quote(voice_id)}/with-timestamps?output_format={quote(output_format)}"
    request = Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen_fn(request, timeout=timeout_seconds) as response:  # nosec B310 - owner-gated provider call.
            raw = response.read()
            response_headers = getattr(response, "headers", {})
    except HTTPError as exc:
        raise GenerationSafetyError(f"ElevenLabs with-timestamps request failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise GenerationSafetyError("ElevenLabs with-timestamps request failed") from exc
    payload = json.loads(raw.decode("utf-8"))
    audio_base64 = payload.get("audio_base64")
    if not isinstance(audio_base64, str) or not audio_base64:
        raise GenerationSafetyError("ElevenLabs with-timestamps response did not include audio_base64")
    audio_bytes = base64.b64decode(audio_base64)
    request_id = None
    for key in ("request-id", "x-request-id", "xi-request-id"):
        getter = getattr(response_headers, "get", None)
        if callable(getter):
            request_id = getter(key)
        if request_id:
            break
    return audio_bytes, payload, request_id


def alignment_arrays(payload: dict[str, Any]) -> tuple[list[str], list[float], list[float]]:
    alignment = payload.get("normalized_alignment") or payload.get("alignment") or {}
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    if not isinstance(chars, list) or not isinstance(starts, list) or not isinstance(ends, list):
        return [], [], []
    usable = min(len(chars), len(starts), len(ends))
    return [str(item) for item in chars[:usable]], [float(item) for item in starts[:usable]], [float(item) for item in ends[:usable]]


def timing_for_text(
    *,
    chunk_text: str,
    sentence_text: str,
    alignment_payload: dict[str, Any] | None,
    cursor: int,
) -> tuple[int | None, int | None, int]:
    if not sentence_text or not alignment_payload:
        return None, None, cursor
    chars, starts, ends = alignment_arrays(alignment_payload)
    if not chars:
        return None, None, cursor
    joined = "".join(chars)
    search_text = sentence_text.strip()
    index = joined.find(search_text, cursor)
    if index < 0:
        index = chunk_text.find(search_text, cursor)
    if index < 0:
        return None, None, cursor
    end_index = min(index + len(search_text) - 1, len(ends) - 1)
    start_ms = int(round(starts[index] * 1000))
    end_ms = int(round(ends[end_index] * 1000))
    return start_ms, end_ms, index + len(search_text)


def build_sync_manifest(
    *,
    book_slug: str,
    language: str,
    chapter: int,
    sample_dir: Path,
    chunks: list[ManualChunk],
    generation_records: list[dict[str, Any]],
) -> dict[str, Any]:
    sentence_map_path = sample_dir / "sentence_map.json"
    sentence_map = load_json(sentence_map_path) if sentence_map_path.exists() else {}
    by_chunk = {record["chunk_id"]: record for record in generation_records}
    items: list[dict[str, Any]] = []
    for chunk in chunks:
        record = by_chunk.get(chunk.chunk_id, {})
        alignment_payload = None
        alignment_path_value = record.get("alignment_path")
        if alignment_path_value:
            alignment_path = ROOT / alignment_path_value
            if alignment_path.exists():
                alignment_payload = load_json(alignment_path)
        cursor = 0
        for sentence_id in chunk.sentence_ids:
            sentence = sentence_map.get(sentence_id, {}) if isinstance(sentence_map, dict) else {}
            narration_text = str(sentence.get("narration_text") or "")
            source_text = str(sentence.get("source_text") or "")
            decision = str(sentence.get("narration_decision") or "speak")
            spoken = decision not in {"metadata_only", "silence_pause"} and bool(narration_text.strip())
            start_ms, end_ms, cursor = timing_for_text(
                chunk_text=chunk.text,
                sentence_text=narration_text,
                alignment_payload=alignment_payload if spoken else None,
                cursor=cursor,
            )
            timing_source = "elevenlabs_character_alignment" if start_ms is not None else "placeholder_api_alignment_required"
            if not spoken:
                timing_source = "metadata_or_pause_no_spoken_audio"
            items.append(
                {
                    "text_fragment_id": f"{safe_slug(book_slug)}-chapter-{chapter:03d}-{sentence_id}",
                    "sentence_id": sentence_id,
                    "chapter": chapter,
                    "language": language.lower(),
                    "text": narration_text if spoken else source_text,
                    "source_text": source_text,
                    "narration_decision": decision,
                    "narration_mode": sentence.get("narration_mode") or "premium_audiobook",
                    "chunk_id": chunk.chunk_id,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "timing_source": timing_source,
                    "sync_level": "sentence",
                    "sync_status": HOLD_SYNC_QA_REQUIRED,
                    "audio_hash": record.get("audio_hash") or "sha256:placeholder-no-audio-generated",
                    "public": False,
                }
            )
    return {
        "generated_by": "scripts/elevenlabs_full_chapter_generate.py",
        "generated_at": utc_now(),
        "book_slug": safe_slug(book_slug),
        "chapter": chapter,
        "language": language.lower(),
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "timing_source": "elevenlabs_with_timestamps_or_placeholder",
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
        "items": items,
    }


def write_cost_reports(sample_dir: Path, result: dict[str, Any]) -> None:
    cost_json = {
        "generated_by": "scripts/elevenlabs_full_chapter_generate.py",
        "generated_at": utc_now(),
        "mode": result["mode"],
        "chunk_selector": result["chunk_selector"],
        "chunk_count": result["chunk_count"],
        "total_characters": result["total_characters"],
        "estimated_generation_scope": result["estimated_generation_scope"],
        "generated_chunk_count": result["generated_chunk_count"],
        "skipped_cached_chunk_count": result["skipped_cached_chunk_count"],
        "failed_chunk_count": result["failed_chunk_count"],
        "no_full_book_generation": True,
        "full_book_generation_allowed": False,
        "full_chapter_generation_allowed": result["chunk_selector"] == "all",
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "production_status": PRODUCTION_BLOCKED,
        "audio_output_root": result["output_dir"],
        "api_key_persisted": False,
    }
    write_json(sample_dir / "generation_cost_control_report.json", cost_json)
    md = "\n".join(
        [
            "# ElevenLabs Dracula Generation Cost-Control Report",
            "",
            f"- Mode: `{result['mode']}`",
            f"- Chunk selector: `{result['chunk_selector']}`",
            f"- Chunk count: `{result['chunk_count']}`",
            f"- Total characters: `{result['total_characters']}`",
            f"- Generated chunks: `{result['generated_chunk_count']}`",
            f"- Skipped cached chunks: `{result['skipped_cached_chunk_count']}`",
            f"- Failed chunks: `{result['failed_chunk_count']}`",
            "- Full-book generation: `false`",
            "- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
            "- Production: `PRODUCTION_BLOCKED`",
            "- API key persisted: `false`",
            "",
        ]
    )
    (sample_dir / "generation_cost_control_report.md").write_text(md, encoding="utf-8")
    (ROOT / "ELEVENLABS_DRACULA_GENERATION_COST_CONTROL_REPORT.md").write_text(md, encoding="utf-8")


def write_qa_reports(sample_dir: Path, result: dict[str, Any]) -> None:
    internal_report = "\n".join(
        [
            "# ElevenLabs Dracula Full Chapter Internal Report",
            "",
            "## API Automation Status",
            "",
            f"- Mode: `{result['mode']}`",
            f"- Endpoint: `POST /v1/text-to-speech/:voice_id/with-timestamps`",
            f"- Voice: `Rachel / 21m00Tcm4TlvDq8ikWAM`",
            f"- Model: `eleven_multilingual_v2`",
            f"- Output format: `mp3_44100_192`",
            f"- Chunk selector: `{result['chunk_selector']}`",
            f"- Chunks considered: `{result['chunk_count']}`",
            f"- Total characters: `{result['total_characters']}`",
            "- Public audio: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
            "- Production: `PRODUCTION_BLOCKED`",
            "- Listen Now CTA allowed: `false`",
            "- AudioObject metadata allowed: `false`",
            "- Full-book generation allowed: `false`",
            "",
        ]
    )
    qa_scorecard = "\n".join(
        [
            "# ElevenLabs Dracula Full Chapter QA Scorecard",
            "",
            "- Decision: `HOLD_OWNER_LISTENING_QA_REQUIRED`",
            "- Human listening QA score: `not filled`",
            "- Sync QA score: `not filled`",
            "- Public release: `PUBLIC_AUDIO_RELEASE_BLOCKED`",
            "- Production approved: `false`",
            "- No Listen Now CTA",
            "- No AudioObject metadata",
            "- Generated audio remains internal only.",
            "",
        ]
    )
    sync_report = "\n".join(
        [
            "# ElevenLabs Dracula Full Chapter Sync QA Report",
            "",
            f"- Sync status: `{HOLD_SYNC_QA_REQUIRED}`",
            f"- Character alignment manifest: `{result['character_alignment_manifest_path']}`",
            f"- Sync manifest: `{result['sync_manifest_path']}`",
            "- Sentence-level timing must be owner/QA reviewed before any public release.",
            "- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.",
            "- Production remains `PRODUCTION_BLOCKED`.",
            "",
        ]
    )
    targets = {
        ROOT / "ELEVENLABS_DRACULA_FULL_CHAPTER_INTERNAL_REPORT.md": internal_report,
        sample_dir / "ELEVENLABS_DRACULA_FULL_CHAPTER_INTERNAL_REPORT.md": internal_report,
        ROOT / "ELEVENLABS_DRACULA_FULL_CHAPTER_QA_SCORECARD.md": qa_scorecard,
        sample_dir / "ELEVENLABS_DRACULA_FULL_CHAPTER_QA_SCORECARD.md": qa_scorecard,
        ROOT / "ELEVENLABS_DRACULA_FULL_CHAPTER_SYNC_QA_REPORT.md": sync_report,
        sample_dir / "ELEVENLABS_DRACULA_FULL_CHAPTER_SYNC_QA_REPORT.md": sync_report,
    }
    for path, text in targets.items():
        path.write_text(text, encoding="utf-8")


def build_character_alignment_manifest(
    *,
    book_slug: str,
    language: str,
    chapter: int,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generated_by": "scripts/elevenlabs_full_chapter_generate.py",
        "generated_at": utc_now(),
        "book_slug": safe_slug(book_slug),
        "language": language.lower(),
        "chapter": chapter,
        "provider": "ElevenLabs",
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
        "chunks": [
            {
                "chunk_id": record["chunk_id"],
                "text_hash": record["text_hash"],
                "settings_hash": record["settings_hash"],
                "alignment_status": record.get("alignment_status", "PLACEHOLDER_PENDING_GENERATION"),
                "alignment_path": record.get("alignment_path", ""),
                "request_id": record.get("request_id", ""),
                "public": False,
            }
            for record in records
        ],
    }


def build_full_audio_manifest(
    *,
    book_slug: str,
    language: str,
    chapter: int,
    records: list[dict[str, Any]],
    chunk_selector: str,
) -> dict[str, Any]:
    generated = [record for record in records if record.get("generation_status") == "GENERATED_INTERNAL_ONLY"]
    return {
        "generated_by": "scripts/elevenlabs_full_chapter_generate.py",
        "generated_at": utc_now(),
        "book_slug": safe_slug(book_slug),
        "language": language.lower(),
        "chapter": chapter,
        "provider": "ElevenLabs",
        "voice": "Rachel",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "audio_status": "INTERNAL_FULL_CHAPTER_ONLY" if chunk_selector == "all" else "INTERNAL_SAMPLE_ONLY",
        "generation_status": "DRY_RUN_READY" if not generated else "GENERATED_INTERNAL_ONLY_HOLD_QA",
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "chunk_count": len(records),
        "generated_chunk_count": len(generated),
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
        "production_approved": False,
        "listen_now_cta_allowed": False,
        "audio_object_metadata_allowed": False,
        "full_book_generation_allowed": False,
        "chunks": [
            {
                "chunk_id": record["chunk_id"],
                "audio_path": record.get("audio_path", ""),
                "audio_hash": record.get("audio_hash", ""),
                "generation_status": record.get("generation_status"),
                "public": False,
            }
            for record in records
        ],
    }


def require_generate_gates(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    public_audio = reject_public_audio_files()
    if public_audio:
        raise GenerationSafetyError("public audio files are present under frontend/public or frontend/build")
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise GenerationSafetyError("ELEVENLABS_API_KEY is required for generate mode")
    if os.environ.get("EARNALISM_ALLOW_ELEVENLABS_GENERATION") != "true":
        raise GenerationSafetyError("EARNALISM_ALLOW_ELEVENLABS_GENERATION must be exactly true for generate mode")
    if args.chunks == "all":
        if not args.force:
            raise GenerationSafetyError("--chunks all requires --force")
        if os.environ.get("EARNALISM_ALLOW_FULL_CHAPTER_AUDIO_GENERATION") != "true":
            raise GenerationSafetyError(
                "EARNALISM_ALLOW_FULL_CHAPTER_AUDIO_GENERATION must be exactly true for all-chunk generation"
            )
    if args.chunks != "first3" and args.max_chunks is None:
        raise GenerationSafetyError("generate mode requires --max-chunks unless --chunks first3 is used")
    require_config_safety(config)
    provider_gate = require_provider_internal_eval_gate()
    return {"api_key": api_key, "provider_gate": provider_gate}


def run_generation(
    *,
    book_slug: str,
    language: str,
    chapter: int | str,
    mode: str = "dry-run",
    chunks: str = "first3",
    max_chunks: int | None = None,
    force: bool = False,
    output_dir: Path | None = None,
    config_path: Path | None = None,
    urlopen_fn: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    chapter_number = int(chapter)
    sample_dir = chapter_dir(book_slug, language, chapter_number)
    config_path = config_path or sample_dir / "elevenlabs_api_generation_config.json"
    config = load_json(config_path)
    require_config_safety(config)

    output_dir = output_dir or sample_dir / "generated_audio"
    output_dir = ensure_internal_path(output_dir, "generated audio output directory")
    alignment_dir = ensure_internal_path(sample_dir / "generated_alignment", "generated alignment output directory")
    generation_manifest_path = sample_dir / "chunk_generation_manifest.json"
    chunks_to_process = load_manual_chunks(sample_dir, chunks, max_chunks)
    current_settings_hash = settings_hash(config)
    generate_gate: dict[str, Any] = {"provider_gate": {"status": "not_required_for_dry_run"}}
    if mode == "generate":
        namespace = argparse.Namespace(chunks=chunks, max_chunks=max_chunks, force=force)
        generate_gate = require_generate_gates(namespace, config)

    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    generated_count = 0
    skipped_count = 0
    previous_request_id: str | None = None

    for index, chunk in enumerate(chunks_to_process):
        previous_chunk = chunks_to_process[index - 1] if index > 0 else None
        next_chunk = chunks_to_process[index + 1] if index + 1 < len(chunks_to_process) else None
        audio_path = output_audio_path(output_dir, chunk)
        alignment_path = ensure_internal_path(alignment_dir / f"{chunk.chunk_id}.json", f"{chunk.chunk_id} alignment path")
        request_body = build_request_body(
            chunk=chunk,
            previous_chunk=previous_chunk,
            next_chunk=next_chunk,
            config=config,
            previous_request_id=previous_request_id,
        )
        base_record: dict[str, Any] = {
            "chunk_id": chunk.chunk_id,
            "provider": "ElevenLabs",
            "voice_name": config["voice_name"],
            "voice_id": config["voice_id"],
            "model_id": config["model_id"],
            "output_format": config["output_format"],
            "language_code": config.get("language_code", ""),
            "text_hash": chunk.text_hash,
            "manifest_text_hash": chunk.manifest_text_hash,
            "settings_hash": current_settings_hash,
            "manifest_settings_hash": chunk.manifest_settings_hash,
            "request_body_hash": sha256_json(request_body),
            "request_endpoint": "POST /v1/text-to-speech/:voice_id/with-timestamps",
            "character_count": len(chunk.text),
            "estimated_duration_seconds": chunk.estimated_duration_seconds,
            "chunk_text_path": relative_path(chunk.chunk_text_path),
            "audio_path": relative_path(audio_path),
            "alignment_path": "",
            "provider_api_called": False,
            "public": False,
            "public_audio_allowed": False,
            "production_status": PRODUCTION_BLOCKED,
            "audio_hash": "",
            "generated_at": "",
            "request_id": "",
        }
        cached = None if force else existing_cache_record(
            chunk=chunk,
            generation_manifest_path=generation_manifest_path,
            output_path=audio_path,
            current_settings_hash=current_settings_hash,
        )
        if cached:
            skipped_count += 1
            record = {**base_record, **cached}
            record["generation_status"] = "SKIPPED_CACHED_INTERNAL_AUDIO"
            record["provider_api_called"] = False
            if audio_path.exists():
                record["audio_hash"] = sha256_file(audio_path)
            if alignment_path.exists():
                record["alignment_path"] = relative_path(alignment_path)
                record["alignment_status"] = "CACHED_ALIGNMENT_PRESENT"
            records.append(record)
            previous_request_id = str(record.get("request_id") or "") or previous_request_id
            continue

        if mode == "dry-run":
            records.append(
                {
                    **base_record,
                    "generation_status": "DRY_RUN_ONLY",
                    "alignment_status": "PLACEHOLDER_PENDING_GENERATION",
                    "provider_api_called": False,
                }
            )
            continue

        if audio_path.exists() and not force:
            failures.append({"chunk_id": chunk.chunk_id, "error": f"{relative_path(audio_path)} exists; pass --force to overwrite"})
            records.append(
                {
                    **base_record,
                    "generation_status": "BLOCKED_EXISTING_AUDIO_REQUIRES_FORCE",
                    "alignment_status": "NO_ALIGNMENT_BLOCKED_EXISTING_AUDIO",
                    "provider_api_called": False,
                    "failure": f"{relative_path(audio_path)} exists; pass --force to overwrite",
                }
            )
            break

        try:
            audio_bytes, alignment_payload, request_id = post_with_timestamps(
                api_key=generate_gate["api_key"],
                voice_id=config["voice_id"],
                output_format=config["output_format"],
                body=request_body,
                urlopen_fn=urlopen_fn,
            )
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_bytes(audio_bytes)
            alignment_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(alignment_path, alignment_payload)
            generated_count += 1
            previous_request_id = request_id
            records.append(
                {
                    **base_record,
                    "generation_status": "GENERATED_INTERNAL_ONLY",
                    "alignment_status": "ELEVENLABS_ALIGNMENT_RECORDED",
                    "alignment_path": relative_path(alignment_path),
                    "provider_api_called": True,
                    "audio_hash": sha256_file(audio_path),
                    "generated_at": utc_now(),
                    "request_id": request_id or "",
                }
            )
        except Exception as exc:
            failures.append({"chunk_id": chunk.chunk_id, "error": str(exc)})
            records.append(
                {
                    **base_record,
                    "generation_status": "FAILED_INTERNAL_GENERATION",
                    "alignment_status": "NO_ALIGNMENT_FAILED_GENERATION",
                    "provider_api_called": mode == "generate",
                    "failure": str(exc),
                }
            )
            if not force:
                break

    total_characters = sum(len(chunk.text) for chunk in chunks_to_process)
    result: dict[str, Any] = {
        "status": "DRY_RUN_READY" if mode == "dry-run" else ("GENERATED_INTERNAL_ONLY_HOLD_QA" if generated_count else "GENERATE_ATTEMPT_COMPLETE"),
        "mode": mode,
        "book_slug": safe_slug(book_slug),
        "language": language.lower(),
        "chapter": chapter_number,
        "chunk_selector": chunks,
        "chunk_count": len(chunks_to_process),
        "total_characters": total_characters,
        "estimated_generation_scope": "first 3 chunks" if chunks == "first3" else "full Chapter 1 chunks only",
        "generated_chunk_count": generated_count,
        "skipped_cached_chunk_count": skipped_count,
        "failed_chunk_count": len(failures),
        "failures": failures,
        "output_dir": relative_path(output_dir),
        "provider_gate": generate_gate.get("provider_gate"),
        "production_status": PRODUCTION_BLOCKED,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "full_book_generation_allowed": False,
    }

    generation_manifest = {
        "generated_by": "scripts/elevenlabs_full_chapter_generate.py",
        "generated_at": utc_now(),
        "mode": mode,
        "book_slug": safe_slug(book_slug),
        "language": language.lower(),
        "chapter": chapter_number,
        "provider": "ElevenLabs",
        "voice": config["voice_name"],
        "voice_id": config["voice_id"],
        "model_id": config["model_id"],
        "output_format": config["output_format"],
        "sync_status": HOLD_SYNC_QA_REQUIRED,
        "public_audio_release": PUBLIC_AUDIO_RELEASE_BLOCKED,
        "public_audio_allowed": False,
        "production_status": PRODUCTION_BLOCKED,
        "chunks": records,
    }
    write_json(generation_manifest_path, generation_manifest)

    character_alignment_manifest = build_character_alignment_manifest(
        book_slug=book_slug,
        language=language,
        chapter=chapter_number,
        records=records,
    )
    character_alignment_path = sample_dir / "character_alignment_manifest.json"
    write_json(character_alignment_path, character_alignment_manifest)

    sync_manifest = build_sync_manifest(
        book_slug=book_slug,
        language=language,
        chapter=chapter_number,
        sample_dir=sample_dir,
        chunks=chunks_to_process,
        generation_records=records,
    )
    sync_path = sample_dir / "sync_manifest.json"
    write_json(sync_path, sync_manifest)

    full_audio_manifest = build_full_audio_manifest(
        book_slug=book_slug,
        language=language,
        chapter=chapter_number,
        records=records,
        chunk_selector=chunks,
    )
    full_audio_path = sample_dir / "full_chapter_audio_manifest.json"
    write_json(full_audio_path, full_audio_manifest)

    result.update(
        {
            "chunk_generation_manifest_path": relative_path(generation_manifest_path),
            "character_alignment_manifest_path": relative_path(character_alignment_path),
            "sync_manifest_path": relative_path(sync_path),
            "full_chapter_audio_manifest_path": relative_path(full_audio_path),
            "generation_cost_control_report_path": relative_path(sample_dir / "generation_cost_control_report.json"),
        }
    )
    write_cost_reports(sample_dir, result)
    write_qa_reports(sample_dir, result)
    if failures and mode == "generate":
        raise GenerationSafetyError("one or more ElevenLabs generation chunks failed")
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book-slug", required=True)
    parser.add_argument("--language", default="en")
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--mode", choices=("dry-run", "generate"), default="dry-run")
    parser.add_argument("--chunks", choices=("first3", "all"), default="first3")
    parser.add_argument("--max-chunks", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("internal/audiobook_lab/dracula/en/chapter-1/generated_audio"),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("internal/audiobook_lab/dracula/en/chapter-1/elevenlabs_api_generation_config.json"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run_generation(
            book_slug=args.book_slug,
            language=args.language,
            chapter=args.chapter,
            mode=args.mode,
            chunks=args.chunks,
            max_chunks=args.max_chunks,
            force=args.force,
            output_dir=(ROOT / args.output_dir if not args.output_dir.is_absolute() else args.output_dir),
            config_path=(ROOT / args.config if not args.config.is_absolute() else args.config),
        )
    except GenerationSafetyError as exc:
        print(f"BLOCKED_ELEVENLABS_GENERATION: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"FAILED_ELEVENLABS_GENERATION_PIPELINE: {exc}", file=sys.stderr)
        return 1
    print(
        "ELEVENLABS_API_PIPELINE "
        f"status={result['status']} mode={result['mode']} chunks={result['chunk_selector']} "
        f"chunk_count={result['chunk_count']} total_characters={result['total_characters']} "
        f"generated={result['generated_chunk_count']} skipped_cached={result['skipped_cached_chunk_count']} "
        f"failed={result['failed_chunk_count']} public_audio_allowed=false sync_status={HOLD_SYNC_QA_REQUIRED}"
    )
    print(f"chunk_generation_manifest={result['chunk_generation_manifest_path']}")
    print(f"sync_manifest={result['sync_manifest_path']}")
    print(f"cost_control_report={result['generation_cost_control_report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
