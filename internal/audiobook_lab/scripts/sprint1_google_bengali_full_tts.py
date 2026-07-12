#!/usr/bin/env python3
"""Generate one lock-safe, private Google Bengali full-book TTS candidate."""

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Optional, Protocol


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "internal" / "audiobook_lab" / "scripts"
HOOK_DIR = ROOT / "internal" / "audiobook_lab" / "scripts" / "factory_hooks"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(HOOK_DIR))

from bengali_tts_provider_bakeoff import google_safe_tts_text  # noqa: E402
from common import normalize_text, sha256_file, sha256_text  # noqa: E402
from tts_hook import chunk_text, concat_chunks, prepared_text_source_terms  # noqa: E402


PROVIDER = "google"
MODEL = "google-cloud-texttospeech"
LANGUAGE_CODE = "bn-IN"
STYLE_PROFILE = "literary_warm_pacing"
TEXT_PREP = "google_safe_tts_text_v1"
SPEAKING_RATE = 0.94
DEFAULT_MAX_CHARS = 1400
GOOGLE_MAX_INPUT_BYTES = 4500
LOCK_REL = Path("internal/earnalism_intelligence/locks/paid_tts.lock")
MANIFEST_NAME = "google_bengali_full_tts_manifest.json"
MANIFEST_HASH_NAME = f"{MANIFEST_NAME}.sha256"
SOURCE_COPY_NAME = "sanitized_manuscript.txt"
CHUNK_DIR_NAME = "chunks"

TRUE_GATES = (
    "EARNALISM_APPROVE_GOOGLE_FULL_TTS",
    "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS",
    "EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED",
)
SCOPED_GATES = {
    "EARNALISM_BENGALI_TTS_PROVIDER": PROVIDER,
}
MONEY_ENVS = (
    "EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS",
    "EARNALISM_GOOGLE_TTS_FULL_MAX_ESTIMATED_USD",
    "EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE",
    "EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD",
    "SPRINT1_MAX_USD_PER_TITLE",
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD",
    "MAX_TTS_BUDGET_USD",
)
FATAL_FLAGS = (
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "list_reading_rhythm_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VOICE_RE = re.compile(r"^bn-IN-[A-Za-z0-9][A-Za-z0-9-]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GoogleProvider(Protocol):
    """Narrow provider boundary so tests never import or call Google."""

    def available_voice_names(self, language_code: str) -> set[str]: ...

    def synthesize(self, *, text: str, voice: str, language_code: str) -> bytes: ...


class GoogleCloudProvider:
    def __init__(self) -> None:
        from google.cloud import texttospeech  # noqa: PLC0415

        self._texttospeech = texttospeech
        self._client = texttospeech.TextToSpeechClient()

    def available_voice_names(self, language_code: str) -> set[str]:
        response = self._client.list_voices(language_code=language_code)
        return {str(voice.name) for voice in response.voices if getattr(voice, "name", "")}

    def synthesize(self, *, text: str, voice: str, language_code: str) -> bytes:
        tts = self._texttospeech
        response = self._client.synthesize_speech(
            input=tts.SynthesisInput(text=text),
            voice=tts.VoiceSelectionParams(language_code=language_code, name=voice),
            audio_config=tts.AudioConfig(
                audio_encoding=tts.AudioEncoding.MP3,
                speaking_rate=SPEAKING_RATE,
                pitch=0.0,
            ),
        )
        return bytes(response.audio_content or b"")


@dataclass(frozen=True)
class RunConfig:
    asset_root: Path
    slug: str
    voice: str
    manuscript_path: Path
    run_dir: Path
    representative_evidence_path: Path
    expected_manuscript_sha256: str
    prior_title_estimated_spend_usd: float
    prior_sprint_estimated_spend_usd: float
    lock_path: Optional[Path] = None
    max_chars: int = DEFAULT_MAX_CHARS


@dataclass
class PreparedRun:
    config: RunConfig
    manuscript: str
    manuscript_bytes: bytes
    chunks: list[dict[str, Any]]
    evidence_sha256: str
    budget: dict[str, Any]
    attempt_fingerprint: str
    blockers: list[str]

    def report(self) -> dict[str, Any]:
        return {
            "slug": self.config.slug,
            "provider": PROVIDER,
            "model": MODEL,
            "voice": self.config.voice,
            "language_code": LANGUAGE_CODE,
            "source_sha256": sha256_text(self.manuscript) if self.manuscript else "",
            "source_characters": len(self.manuscript),
            "source_utf8_bytes": len(self.manuscript_bytes),
            "chunk_count": len(self.chunks),
            "max_characters_per_chunk": self.config.max_chars,
            "representative_evidence_sha256": self.evidence_sha256,
            "attempt_fingerprint": self.attempt_fingerprint,
            "budget": self.budget,
            "blockers": list(self.blockers),
            "provider_calls_ran": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        }


@dataclass
class LockLease:
    original_bytes: bytes
    original_sha256: str
    restored: bool = False


def _resolve(path: Path, asset_root: Path) -> Path:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = asset_root / candidate
    return candidate.resolve(strict=False)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _stable_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, separators=(",", ": ")) + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, payload: bytes, *, run_dir: Path) -> None:
    resolved_parent = path.parent.resolve(strict=False)
    if not _is_within(resolved_parent, run_dir.resolve(strict=False)):
        raise RuntimeError(f"Refusing non-private output path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _decimal_env(environ: Mapping[str, str], name: str, blockers: list[str]) -> Optional[Decimal]:
    raw = str(environ.get(name, "")).strip()
    if not raw:
        blockers.append(f"{name} is required")
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        blockers.append(f"{name} must be a finite positive number")
        return None
    if not value.is_finite() or value <= 0:
        blockers.append(f"{name} must be a finite positive number")
        return None
    return value


def budget_report(
    billable_text: str,
    *,
    prior_title_estimated_spend_usd: float,
    prior_sprint_estimated_spend_usd: float,
    environ: Mapping[str, str],
) -> dict[str, Any]:
    blockers: list[str] = []
    values = {name: _decimal_env(environ, name, blockers) for name in MONEY_ENVS}
    try:
        prior_title = Decimal(str(prior_title_estimated_spend_usd))
        prior_sprint = Decimal(str(prior_sprint_estimated_spend_usd))
    except InvalidOperation:
        prior_title = Decimal("NaN")
        prior_sprint = Decimal("NaN")
    if not prior_title.is_finite() or prior_title < 0:
        blockers.append("prior title estimated spend must be finite and non-negative")
    if not prior_sprint.is_finite() or prior_sprint < 0:
        blockers.append("prior sprint estimated spend must be finite and non-negative")
    if prior_title.is_finite() and prior_sprint.is_finite() and prior_title > prior_sprint:
        blockers.append("prior title estimated spend cannot exceed prior sprint estimated spend")

    rate = values["EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS"]
    estimate = Decimal(len(billable_text)) / Decimal(1000) * rate if rate is not None else Decimal(0)
    title_total = prior_title + estimate if prior_title.is_finite() else Decimal(0)
    sprint_total = prior_sprint + estimate if prior_sprint.is_finite() else Decimal(0)

    google_cap = values["EARNALISM_GOOGLE_TTS_FULL_MAX_ESTIMATED_USD"]
    campaign_title_cap = values["EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE"]
    campaign_cap = values["EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD"]
    title_cap = values["SPRINT1_MAX_USD_PER_TITLE"]
    sprint_cap = values["SPRINT1_TOTAL_AUDIO_BUDGET_USD"]
    global_cap = values["MAX_TTS_BUDGET_USD"]
    if google_cap is not None and estimate > google_cap:
        blockers.append("estimated Google TTS spend exceeds the full-TTS sub-cap")
    if campaign_title_cap is not None and title_total > campaign_title_cap:
        blockers.append("estimated title spend exceeds EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE")
    if campaign_cap is not None and sprint_total > campaign_cap:
        blockers.append("estimated sprint spend exceeds EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD")
    if title_cap is not None and title_total > title_cap:
        blockers.append("estimated title spend exceeds SPRINT1_MAX_USD_PER_TITLE")
    if sprint_cap is not None and sprint_total > sprint_cap:
        blockers.append("estimated sprint spend exceeds SPRINT1_TOTAL_AUDIO_BUDGET_USD")
    if global_cap is not None and sprint_total > global_cap:
        blockers.append("estimated sprint spend exceeds MAX_TTS_BUDGET_USD")

    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "estimated_google_tts_usd": _money(estimate),
        "prior_title_estimated_spend_usd": _money(prior_title) if prior_title.is_finite() else None,
        "estimated_title_total_usd": _money(title_total),
        "prior_sprint_estimated_spend_usd": _money(prior_sprint) if prior_sprint.is_finite() else None,
        "estimated_sprint_total_usd": _money(sprint_total),
        "google_full_tts_cap_usd": _money(google_cap) if google_cap is not None else None,
        "campaign_per_title_cap_usd": (
            _money(campaign_title_cap) if campaign_title_cap is not None else None
        ),
        "campaign_cap_usd": _money(campaign_cap) if campaign_cap is not None else None,
        "title_cap_usd": _money(title_cap) if title_cap is not None else None,
        "sprint_cap_usd": _money(sprint_cap) if sprint_cap is not None else None,
        "max_tts_budget_usd": _money(global_cap) if global_cap is not None else None,
        "estimated_usd_per_1k_characters": _money(rate) if rate is not None else None,
        "billable_characters": len(billable_text),
        "blockers": blockers,
    }


def runtime_gate_errors(config: RunConfig, environ: Mapping[str, str]) -> list[str]:
    errors = [
        f"{name}=true is required"
        for name in TRUE_GATES
        if environ.get(name, "").strip().lower() != "true"
    ]
    errors.extend(
        f"{name} must equal {expected}"
        for name, expected in SCOPED_GATES.items()
        if environ.get(name, "").strip().lower() != expected.lower()
    )
    if environ.get("EARNALISM_BENGALI_FULL_PILOT_SLUG", "").strip() != config.slug:
        errors.append(f"EARNALISM_BENGALI_FULL_PILOT_SLUG must equal {config.slug}")
    if environ.get("EARNALISM_BENGALI_TTS_VOICE", "").strip() != config.voice:
        errors.append(f"EARNALISM_BENGALI_TTS_VOICE must equal {config.voice}")
    for name in ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT"):
        if not environ.get(name, "").strip():
            errors.append(f"{name} is required")
    return errors


def private_run_dir_errors(config: RunConfig) -> list[str]:
    asset_root = config.asset_root.resolve(strict=False)
    original = config.run_dir.expanduser()
    if not original.is_absolute():
        original = asset_root / original
    run_dir = _resolve(config.run_dir, asset_root)
    if original.is_symlink():
        return ["run directory must not be a symlink"]
    if run_dir == asset_root / "internal" / "audiobook_lab":
        return ["run directory must be below internal/audiobook_lab, not the lab root"]
    if _is_within(run_dir, asset_root):
        private_root = (asset_root / "internal" / "audiobook_lab").resolve(strict=False)
        if not _is_within(run_dir, private_root):
            return ["repo-local run directory must be below internal/audiobook_lab"]
    else:
        temporary_root = Path(tempfile.gettempdir()).resolve(strict=False)
        if not _is_within(run_dir, temporary_root):
            return ["external run directory must be below the operating-system temporary directory"]
    if run_dir.exists() and not run_dir.is_dir():
        return ["run directory exists but is not a directory"]
    reserved = [run_dir / MANIFEST_NAME, run_dir / MANIFEST_HASH_NAME, run_dir / CHUNK_DIR_NAME]
    manuscript_path = _resolve(config.manuscript_path, asset_root)
    source_copy = run_dir / SOURCE_COPY_NAME
    if source_copy.resolve(strict=False) != manuscript_path:
        reserved.append(source_copy)
    if any(path.exists() or path.is_symlink() for path in reserved):
        return ["run directory contains prior Google full-TTS output"]
    final_audio = run_dir / private_audio_name(config.slug, config.voice)
    if final_audio.exists() or final_audio.is_symlink():
        return ["run directory contains prior final audio"]
    return []


def lock_path_scope_errors(config: RunConfig) -> list[str]:
    asset_root = config.asset_root.resolve(strict=False)
    raw_path = (config.lock_path or LOCK_REL).expanduser()
    if not raw_path.is_absolute():
        raw_path = asset_root / raw_path
    if raw_path.is_symlink():
        return ["paid TTS lock path must not be a symlink"]
    lock_path = raw_path.resolve(strict=False)
    expected_repo_lock = (asset_root / LOCK_REL).resolve(strict=False)
    if _is_within(lock_path, asset_root):
        if lock_path != expected_repo_lock:
            return ["repo-local paid TTS lock must be internal/earnalism_intelligence/locks/paid_tts.lock"]
    elif not _is_within(lock_path, Path(tempfile.gettempdir()).resolve(strict=False)):
        return ["external paid TTS lock must be below the operating-system temporary directory"]
    return []


def _read_manuscript(config: RunConfig, blockers: list[str]) -> tuple[str, bytes]:
    path = _resolve(config.manuscript_path, config.asset_root.resolve(strict=False))
    if not path.is_file() or path.is_symlink():
        blockers.append("sanitized manuscript must be a regular, non-symlink file")
        return "", b""
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        blockers.append(f"sanitized manuscript must be readable UTF-8: {exc}")
        return "", b""
    if text.startswith("\ufeff"):
        blockers.append("sanitized manuscript must not contain a UTF-8 BOM")
    if not text.strip():
        blockers.append("sanitized manuscript is empty")
    if "\x00" in text or any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        blockers.append("sanitized manuscript contains forbidden control characters")
    if not re.search(r"[\u0980-\u09ff]", text):
        blockers.append("sanitized manuscript contains no Bengali text")
    source_terms = prepared_text_source_terms(text)
    if source_terms:
        blockers.append("sanitized manuscript still contains source terms: " + ", ".join(source_terms))
    if re.search(r"<[^>]+>", text):
        blockers.append("sanitized manuscript must be plain text without markup")
    actual_sha256 = sha256_text(text)
    if not SHA256_RE.fullmatch(config.expected_manuscript_sha256):
        blockers.append("expected manuscript SHA-256 must be 64 lowercase hexadecimal characters")
    elif actual_sha256 != config.expected_manuscript_sha256:
        blockers.append("sanitized manuscript SHA-256 does not match the approved hash")
    return text, raw


def _representative_evidence_errors(config: RunConfig) -> tuple[list[str], str]:
    path = _resolve(config.representative_evidence_path, config.asset_root.resolve(strict=False))
    if not path.is_file() or path.is_symlink():
        return ["representative evidence must be a regular, non-symlink JSON file"], ""
    try:
        raw = path.read_bytes()
        evidence = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"representative evidence is unreadable or invalid: {exc}"], ""
    errors: list[str] = []
    evidence_slug = evidence.get("slug") or evidence.get("pilot_candidate_selected") or evidence.get("passage_slug")
    if evidence_slug != config.slug:
        errors.append("representative evidence slug does not match")
    if str(evidence.get("provider") or "").strip().lower() != PROVIDER:
        errors.append("representative evidence provider must be google")
    if str(evidence.get("voice") or "").strip() != config.voice:
        errors.append("representative evidence voice does not match")
    scores = evidence.get("scores") if isinstance(evidence.get("scores"), dict) else {}
    score = evidence.get(
        "representative_score",
        evidence.get("overall_listening_score", scores.get("overall_listening_score")),
    )
    confidence = evidence.get("confidence", evidence.get("confidence_score", scores.get("confidence_score")))
    try:
        parsed_score = float(score)
        if not math.isfinite(parsed_score) or parsed_score < 9.2:
            errors.append("representative listening score must be at least 9.2")
    except (TypeError, ValueError):
        errors.append("representative listening score is missing or invalid")
    try:
        parsed_confidence = float(confidence)
        if not math.isfinite(parsed_confidence) or parsed_confidence < 0.90:
            errors.append("representative confidence must be at least 0.90")
    except (TypeError, ValueError):
        errors.append("representative confidence is missing or invalid")
    status_pass = (
        str(evidence.get("status") or "").upper() == "PASS"
        or evidence.get("representative_passed_9_2") is True
    )
    if not status_pass:
        errors.append("representative evidence status is not PASS")
    if str(evidence.get("model") or "") != MODEL:
        errors.append(f"representative evidence model must equal {MODEL}")
    evidence_style = evidence.get("best_style_profile") or evidence.get("style_profile")
    if evidence_style != STYLE_PROFILE:
        errors.append(f"representative evidence style must equal {STYLE_PROFILE}")
    if evidence.get("blockers"):
        errors.append("representative evidence contains blockers")
    raw_flags = (
        evidence.get("fatal_flags")
        or evidence.get("fatal_flags_required")
        or evidence.get("judge_flags")
        or {}
    )
    if isinstance(raw_flags, dict):
        flagged = [str(name) for name, value in raw_flags.items() if bool(value)]
    elif isinstance(raw_flags, list):
        flagged = [str(name) for name in raw_flags if name]
    else:
        flagged = ["invalid_fatal_flags"]
    if flagged:
        errors.append("representative evidence has fatal flags: " + ", ".join(flagged))
    return errors, hashlib.sha256(raw).hexdigest()


def _parse_available_lock(raw: bytes) -> tuple[dict[str, Any], list[str]]:
    try:
        lock = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, [f"paid TTS lock is unreadable or invalid: {exc}"]
    if not isinstance(lock, dict):
        return {}, ["paid TTS lock must contain a JSON object"]
    errors: list[str] = []
    if lock.get("status") != "active":
        errors.append("paid TTS lock status must be active")
    if lock.get("current_holder") != "none":
        errors.append("paid TTS lock already has a holder")
    if lock.get("allowed_next_holders") != []:
        errors.append("paid TTS lock allowed_next_holders must be empty")
    return lock, errors


def _lock_errors(lock_path: Path) -> list[str]:
    if not lock_path.is_file() or lock_path.is_symlink():
        return ["paid TTS lock must be a regular, non-symlink file"]
    try:
        _, errors = _parse_available_lock(lock_path.read_bytes())
    except OSError as exc:
        return [f"paid TTS lock is unreadable or invalid: {exc}"]
    return errors


def _validate_chunks(manuscript: str, max_chars: int, blockers: list[str]) -> list[dict[str, Any]]:
    if max_chars <= 0 or max_chars > DEFAULT_MAX_CHARS:
        blockers.append(f"max characters per chunk must be between 1 and {DEFAULT_MAX_CHARS}")
        return []
    source_chunks = chunk_text(manuscript, max_chars=max_chars) if manuscript else []
    chunks: list[dict[str, Any]] = []
    for source_chunk in source_chunks:
        source_text = str(source_chunk.get("text") or "")
        tts_text = google_safe_tts_text(source_text)
        chunks.append(
            {
                **source_chunk,
                "tts_text": tts_text,
                "tts_text_hash": sha256_text(tts_text),
            }
        )
    if not chunks:
        blockers.append("sentence-safe chunking produced no chunks")
        return []
    rebuilt = " ".join(str(chunk["text"]) for chunk in chunks)
    if re.sub(r"\s+", " ", rebuilt).strip() != re.sub(r"\s+", " ", manuscript).strip():
        blockers.append("sentence-safe chunks do not preserve the sanitized manuscript")
    expected_indexes = list(range(len(chunks)))
    if [chunk.get("index") for chunk in chunks] != expected_indexes:
        blockers.append("sentence-safe chunk indexes are not contiguous and ordered")
    for chunk in chunks:
        source_text = str(chunk.get("text") or "")
        tts_text = str(chunk.get("tts_text") or "")
        if len(source_text) > max_chars:
            blockers.append(f"chunk {chunk.get('index')} exceeds the character cap")
        if not tts_text:
            blockers.append(f"chunk {chunk.get('index')} has empty prepared TTS text")
        if normalize_text(tts_text) != normalize_text(source_text):
            blockers.append(f"chunk {chunk.get('index')} TTS preparation changes manuscript content")
        if len(tts_text.encode("utf-8")) > GOOGLE_MAX_INPUT_BYTES:
            blockers.append(f"chunk {chunk.get('index')} exceeds the Google UTF-8 byte cap")
        if chunk.get("text_hash") != sha256_text(source_text):
            blockers.append(f"chunk {chunk.get('index')} has a non-deterministic text hash")
    return chunks


def attempt_fingerprint(
    config: RunConfig,
    manuscript: str,
    chunks: list[dict[str, Any]],
    evidence_sha256: str,
) -> str:
    payload = {
        "schema": 1,
        "slug": config.slug,
        "provider": PROVIDER,
        "model": MODEL,
        "voice": config.voice,
        "language_code": LANGUAGE_CODE,
        "style_profile": STYLE_PROFILE,
        "text_prep": TEXT_PREP,
        "speaking_rate": SPEAKING_RATE,
        "source_sha256": sha256_text(manuscript),
        "representative_evidence_sha256": evidence_sha256,
        "max_characters_per_chunk": config.max_chars,
        "chunk_text_sha256": [chunk["text_hash"] for chunk in chunks],
        "chunk_tts_text_sha256": [chunk["tts_text_hash"] for chunk in chunks],
    }
    return hashlib.sha256(_stable_json_bytes(payload)).hexdigest()


def prepare_run(config: RunConfig, environ: Optional[Mapping[str, str]] = None) -> PreparedRun:
    environ = os.environ if environ is None else environ
    blockers: list[str] = []
    if not SLUG_RE.fullmatch(config.slug):
        blockers.append("slug must contain only lowercase ASCII letters, numbers, and single hyphens")
    if not VOICE_RE.fullmatch(config.voice):
        blockers.append("voice must be an explicit bn-IN Google voice name")
    if (
        not math.isfinite(config.prior_title_estimated_spend_usd)
        or config.prior_title_estimated_spend_usd < 0
    ):
        blockers.append("prior title estimated spend must be finite and non-negative")
    if (
        not math.isfinite(config.prior_sprint_estimated_spend_usd)
        or config.prior_sprint_estimated_spend_usd < 0
    ):
        blockers.append("prior sprint estimated spend must be finite and non-negative")
    blockers.extend(private_run_dir_errors(config))
    blockers.extend(runtime_gate_errors(config, environ))
    manuscript, manuscript_bytes = _read_manuscript(config, blockers)
    evidence_errors, evidence_sha256 = _representative_evidence_errors(config)
    blockers.extend(evidence_errors)
    chunks = _validate_chunks(manuscript, config.max_chars, blockers)
    billable_text = "".join(str(chunk.get("tts_text") or "") for chunk in chunks) if chunks else manuscript
    budget = budget_report(
        billable_text,
        prior_title_estimated_spend_usd=config.prior_title_estimated_spend_usd,
        prior_sprint_estimated_spend_usd=config.prior_sprint_estimated_spend_usd,
        environ=environ,
    )
    blockers.extend(budget["blockers"])
    lock_path = _resolve(config.lock_path or LOCK_REL, config.asset_root.resolve(strict=False))
    blockers.extend(lock_path_scope_errors(config))
    blockers.extend(_lock_errors(lock_path))
    fingerprint = (
        attempt_fingerprint(config, manuscript, chunks, evidence_sha256)
        if manuscript and chunks
        else ""
    )
    return PreparedRun(
        config=config,
        manuscript=manuscript,
        manuscript_bytes=manuscript_bytes,
        chunks=chunks,
        evidence_sha256=evidence_sha256,
        budget=budget,
        attempt_fingerprint=fingerprint,
        blockers=list(dict.fromkeys(blockers)),
    )


def _acquired_lock_payload(original: dict[str, Any], prepared: PreparedRun) -> dict[str, Any]:
    payload = dict(original)
    payload.update(
        {
            "status": "active",
            "current_holder": f"sprint1_google_bengali_full_tts:{prepared.config.slug}",
            "allowed_next_holders": [],
            "allowed_slugs": [prepared.config.slug],
            "approved_scope": (
                "One private Google Bengali full-book TTS candidate only; no upload, publication, "
                "public path, or release mutation."
            ),
            "google_bengali_full_tts_scope": {
                "slug": prepared.config.slug,
                "voice": prepared.config.voice,
                "style_profile": STYLE_PROFILE,
                "text_prep": TEXT_PREP,
                "speaking_rate": SPEAKING_RATE,
                "source_sha256": sha256_text(prepared.manuscript),
                "attempt_fingerprint": prepared.attempt_fingerprint,
                "estimated_google_tts_usd": prepared.budget["estimated_google_tts_usd"],
                "no_upload": True,
                "no_publication": True,
                "no_public_write": True,
                "no_release_mutation": True,
            },
            "stop_conditions": [
                "any approval, credential, source, representative, path, or budget gate fails",
                "the selected Google Bengali voice is unavailable",
                "any provider chunk is empty",
                "any upload, public write, publication, fallback, or release mutation is attempted",
            ],
        }
    )
    return payload


def _write_locked_bytes(handle: Any, payload: bytes) -> None:
    handle.seek(0)
    handle.write(payload)
    handle.truncate()
    handle.flush()
    os.fsync(handle.fileno())


@contextmanager
def paid_tts_lock(lock_path: Path, prepared: PreparedRun) -> Iterator[LockLease]:
    with lock_path.open("r+b") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("paid TTS lock is held by another process") from exc
        original = handle.read()
        lease = LockLease(original_bytes=original, original_sha256=hashlib.sha256(original).hexdigest())
        original_payload, errors = _parse_available_lock(original)
        if errors:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            raise RuntimeError("; ".join(errors))
        try:
            _write_locked_bytes(handle, _stable_json_bytes(_acquired_lock_payload(original_payload, prepared)))
            yield lease
        finally:
            _write_locked_bytes(handle, original)
            handle.seek(0)
            lease.restored = handle.read() == original
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            if not lease.restored:
                raise RuntimeError("paid TTS lock bytes were not restored")


def private_audio_name(slug: str, voice: str) -> str:
    return f"{slug}_{voice.lower()}_private_full.mp3"


def _default_concat(chunk_paths: list[Path], final_audio: Path) -> dict[str, Any]:
    return concat_chunks(chunk_paths, final_audio)


def _manifest(
    prepared: PreparedRun,
    chunk_records: list[dict[str, Any]],
    final_audio: Path,
) -> dict[str, Any]:
    config = prepared.config
    return {
        "schema_version": 1,
        "slug": config.slug,
        "provider": PROVIDER,
        "model": MODEL,
        "voice": config.voice,
        "language_code": LANGUAGE_CODE,
        "style_profile": STYLE_PROFILE,
        "text_prep": TEXT_PREP,
        "speaking_rate": SPEAKING_RATE,
        "source": {
            "file": SOURCE_COPY_NAME,
            "sha256": sha256_text(prepared.manuscript),
            "characters": len(prepared.manuscript),
            "utf8_bytes": len(prepared.manuscript_bytes),
        },
        "representative_evidence_sha256": prepared.evidence_sha256,
        "attempt_fingerprint": prepared.attempt_fingerprint,
        "chunking": {
            "utility": "factory_hooks.tts_hook.chunk_text",
            "max_characters": config.max_chars,
            "max_utf8_bytes": GOOGLE_MAX_INPUT_BYTES,
            "chunk_count": len(chunk_records),
        },
        "chunks": chunk_records,
        "final_audio": {
            "file": final_audio.name,
            "sha256": sha256_file(final_audio),
            "bytes": final_audio.stat().st_size,
        },
        "budget": prepared.budget,
        "actual_provider_billing": "NOT_REPORTED",
        "quality_status": "PRIVATE_QA_REQUIRED",
        "fallback_tts_used": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_gate_mutated": False,
        "public_audio_approved": False,
    }


def run(
    config: RunConfig,
    *,
    execute: bool = False,
    environ: Optional[Mapping[str, str]] = None,
    provider_factory: Optional[Callable[[], GoogleProvider]] = None,
    concat_fn: Optional[Callable[[list[Path], Path], dict[str, Any]]] = None,
) -> dict[str, Any]:
    environ = os.environ if environ is None else environ
    prepared = prepare_run(config, environ)
    result = prepared.report()
    if prepared.blockers:
        result["status"] = "BLOCKED_PREFLIGHT"
        return result
    if not execute:
        result["status"] = "PREFLIGHT_PASS"
        return result

    run_dir = _resolve(config.run_dir, config.asset_root.resolve(strict=False))
    manuscript_path = _resolve(config.manuscript_path, config.asset_root.resolve(strict=False))
    lock_path = _resolve(config.lock_path or LOCK_REL, config.asset_root.resolve(strict=False))
    provider_call_count = 0
    lease: Optional[LockLease] = None
    provider_factory = provider_factory or GoogleCloudProvider
    concat_fn = concat_fn or _default_concat
    try:
        with paid_tts_lock(lock_path, prepared) as lease:
            if manuscript_path.read_bytes() != prepared.manuscript_bytes:
                raise RuntimeError("sanitized manuscript changed after preflight")
            path_errors = private_run_dir_errors(config)
            if path_errors:
                raise RuntimeError("; ".join(path_errors))
            lock_scope_errors = lock_path_scope_errors(config)
            if lock_scope_errors:
                raise RuntimeError("; ".join(lock_scope_errors))
            run_dir.mkdir(parents=True, exist_ok=True)
            source_copy = run_dir / SOURCE_COPY_NAME
            if source_copy.resolve(strict=False) != manuscript_path:
                _atomic_write(source_copy, prepared.manuscript_bytes, run_dir=run_dir)

            provider = provider_factory()
            provider_call_count += 1
            available = provider.available_voice_names(LANGUAGE_CODE)
            if config.voice not in available:
                raise RuntimeError(f"selected Google Bengali voice is unavailable: {config.voice}")

            chunk_dir = run_dir / CHUNK_DIR_NAME
            chunk_dir.mkdir(parents=True, exist_ok=False)
            chunk_paths: list[Path] = []
            chunk_records: list[dict[str, Any]] = []
            for chunk in prepared.chunks:
                provider_call_count += 1
                audio = provider.synthesize(
                    text=chunk["tts_text"],
                    voice=config.voice,
                    language_code=LANGUAGE_CODE,
                )
                if not audio:
                    raise RuntimeError(f"Google returned empty audio for chunk {chunk['index']}")
                target = chunk_dir / f"chunk_{chunk['index']:04d}.mp3"
                _atomic_write(target, audio, run_dir=run_dir)
                chunk_paths.append(target)
                chunk_records.append(
                    {
                        "index": chunk["index"],
                        "file": f"{CHUNK_DIR_NAME}/{target.name}",
                        "text_sha256": chunk["text_hash"],
                        "text_characters": len(chunk["text"]),
                        "text_utf8_bytes": len(chunk["text"].encode("utf-8")),
                        "tts_text_sha256": chunk["tts_text_hash"],
                        "tts_text_characters": len(chunk["tts_text"]),
                        "tts_text_utf8_bytes": len(chunk["tts_text"].encode("utf-8")),
                        "audio_sha256": sha256_file(target),
                        "audio_bytes": target.stat().st_size,
                    }
                )

            final_audio = run_dir / private_audio_name(config.slug, config.voice)
            concat_result = concat_fn(chunk_paths, final_audio)
            if not concat_result.get("ok") or not final_audio.is_file() or final_audio.stat().st_size <= 0:
                reason = concat_result.get("error") or "invalid final audio"
                raise RuntimeError(f"private chunk concatenation failed: {reason}")
            manifest_bytes = _stable_json_bytes(_manifest(prepared, chunk_records, final_audio))
            _atomic_write(run_dir / MANIFEST_NAME, manifest_bytes, run_dir=run_dir)
            manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
            _atomic_write(
                run_dir / MANIFEST_HASH_NAME,
                f"{manifest_sha256}  {MANIFEST_NAME}\n".encode("ascii"),
                run_dir=run_dir,
            )
        result.update(
            {
                "status": "PRIVATE_FULL_TTS_PASS_QA_REQUIRED",
                "provider_calls_ran": provider_call_count > 0,
                "provider_call_count": provider_call_count,
                "run_dir": str(run_dir),
                "manifest": str(run_dir / MANIFEST_NAME),
                "manifest_sha256": manifest_sha256,
                "final_audio": str(final_audio),
                "final_audio_sha256": sha256_file(final_audio),
                "generated_chunk_count": len(chunk_records),
                "lock_sha256_before": lease.original_sha256 if lease else "",
                "lock_restored": bool(lease and lease.restored),
            }
        )
    except Exception as exc:  # noqa: BLE001
        result.update(
            {
                "status": "FULL_TTS_BLOCKED",
                "provider_calls_ran": provider_call_count > 0,
                "provider_call_count": provider_call_count,
                "lock_sha256_before": lease.original_sha256 if lease else "",
                "lock_restored": bool(lease and lease.restored),
                "errors": [f"{type(exc).__name__}: {exc}"],
            }
        )
    return result


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--manuscript", dest="manuscript_path", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--representative-evidence", dest="representative_evidence_path", type=Path, required=True)
    parser.add_argument("--expected-manuscript-sha256", required=True)
    parser.add_argument("--prior-title-estimated-spend-usd", type=float, required=True)
    parser.add_argument("--prior-sprint-estimated-spend-usd", type=float, required=True)
    parser.add_argument("--lock-path", type=Path)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    config = RunConfig(
        asset_root=args.asset_root,
        slug=args.slug,
        voice=args.voice,
        manuscript_path=args.manuscript_path,
        run_dir=args.run_dir,
        representative_evidence_path=args.representative_evidence_path,
        expected_manuscript_sha256=args.expected_manuscript_sha256,
        prior_title_estimated_spend_usd=args.prior_title_estimated_spend_usd,
        prior_sprint_estimated_spend_usd=args.prior_sprint_estimated_spend_usd,
        lock_path=args.lock_path,
        max_chars=args.max_chars,
    )
    result = run(config, execute=args.execute)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PREFLIGHT_PASS", "PRIVATE_FULL_TTS_PASS_QA_REQUIRED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
