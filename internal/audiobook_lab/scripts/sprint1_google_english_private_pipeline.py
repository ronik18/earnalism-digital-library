#!/usr/bin/env python3
"""Generate one hash-bound English Google TTS candidate in private storage only."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shlex
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

from tts_hook import chunk_text as factory_chunk_text  # noqa: E402


PIPELINE_SCHEMA = "earnalism.google_english_private_pipeline.v1"
INPUT_SCHEMA = "earnalism.google_english_private_input.v1"
LISTENING_SCHEMA = "earnalism.google_english_private_listening_evidence.v1"
POLICY_MIN_LISTENING_SCORE = 9.3
POLICY_MIN_LISTENING_CONFIDENCE = 0.90
GOOGLE_SAFE_INPUT_BYTES = 4500
MODES = ("audition", "full")
PASSAGE_IDS = ("opening", "middle", "dialogue_or_risk", "ending")
FATAL_LISTENING_FLAGS = (
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "list_reading_rhythm_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
    "placeholder_audio_detected",
)
APPROVAL_ENV_BY_MODE = {
    "audition": "EARNALISM_APPROVE_GOOGLE_ENGLISH_PRIVATE_AUDITION",
    "full": "EARNALISM_APPROVE_GOOGLE_ENGLISH_PRIVATE_FULL",
}
PRIVATE_REPO_OUTPUT_ROOT = ROOT / "internal/audiobook_lab/private_runs"
FORBIDDEN_OUTPUT_COMPONENTS = {
    "build",
    "dist",
    "frontend",
    "public",
    "release",
    "releases",
    "static",
    "uploads",
}
BOILERPLATE_MARKERS = (
    "*** start of this project gutenberg",
    "*** end of this project gutenberg",
    "project gutenberg literary archive foundation",
    "www.gutenberg.org",
    "this ebook is for the use of anyone anywhere",
    "repository license",
    "source repository",
)


class PipelineError(RuntimeError):
    """A fail-closed pipeline decision with a stable CLI status."""

    def __init__(
        self,
        status: str,
        message: str,
        *,
        exit_code: int = 2,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.exit_code = exit_code
        self.details = details or {}

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "error": str(self), **self.details}


class TTSProvider(Protocol):
    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        language_code: str,
        speaking_rate: float,
        pitch: float,
    ) -> bytes:
        raise NotImplementedError


@dataclass(frozen=True)
class PipelineConfig:
    mode: str
    source_path: Path
    manifest_path: Path
    lock_path: Path
    private_output_dir: Path
    voice: str
    usd_per_million_chars: float
    run_budget_usd: float
    title_budget_usd: float
    sprint_budget_usd: float
    title_spend_usd: float = 0.0
    sprint_spend_usd: float = 0.0
    language_code: str | None = None
    audition_evidence_path: Path | None = None
    minimum_listening_score: float = 9.3
    minimum_listening_confidence: float = 0.90
    max_passage_chars: int = 1200
    max_chunk_chars: int = 1600
    speaking_rate: float = 0.94
    pitch: float = 0.0
    project_id: str | None = None
    execute: bool = False


@dataclass(frozen=True)
class SourceBundle:
    slug: str
    title: str
    author: str
    source_text: str
    source_bytes: bytes
    source_sha256: str
    manifest: dict[str, Any]
    manifest_bytes: bytes
    manifest_sha256: str


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    temporary.write_bytes(payload)
    if mode is not None:
        os.chmod(temporary, mode)
    os.replace(temporary, path)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_bytes(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )
        + b"\n",
    )


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_private_output_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    forbidden = sorted(
        {part.lower() for part in resolved.parts} & FORBIDDEN_OUTPUT_COMPONENTS
    )
    if forbidden:
        raise PipelineError(
            "BLOCKED_NON_PRIVATE_OUTPUT",
            "Private output path contains a public or release-facing component",
            details={
                "private_output_dir": str(resolved),
                "forbidden_components": forbidden,
            },
        )
    if resolved == ROOT or (
        is_within(resolved, ROOT) and not is_within(resolved, PRIVATE_REPO_OUTPUT_ROOT)
    ):
        raise PipelineError(
            "BLOCKED_NON_PRIVATE_OUTPUT",
            "Repository outputs are allowed only under internal/audiobook_lab/private_runs",
            details={"private_output_dir": str(resolved)},
        )
    return resolved


def nested_value(payload: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        value: Any = payload
        for key in path:
            if not isinstance(value, dict) or key not in value:
                break
            value = value[key]
        else:
            return value
    return None


def commercial_use_allowed(value: Any) -> bool:
    if value is True:
        return True
    return str(value or "").strip().lower() in {
        "allowed",
        "approved",
        "commercial_use_allowed",
        "true",
        "yes",
    }


def load_source_bundle(source_path: Path, manifest_path: Path) -> SourceBundle:
    source_bytes = source_path.expanduser().resolve().read_bytes()
    try:
        source_text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PipelineError(
            "BLOCKED_SOURCE_ENCODING", "Sanitized source must be valid UTF-8"
        ) from exc
    if not source_text.strip():
        raise PipelineError("BLOCKED_EMPTY_SOURCE", "Sanitized source is empty")
    if "\x00" in source_text:
        raise PipelineError(
            "BLOCKED_SOURCE_SANITATION", "Sanitized source contains NUL bytes"
        )
    lowered = source_text.lower()
    markers = [marker for marker in BOILERPLATE_MARKERS if marker in lowered]
    if markers:
        raise PipelineError(
            "BLOCKED_SOURCE_SANITATION",
            "Reader-facing source still contains repository or license boilerplate",
            details={"markers": markers},
        )

    manifest_bytes = manifest_path.expanduser().resolve().read_bytes()
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PipelineError(
            "BLOCKED_INPUT_MANIFEST", "Input manifest must be valid UTF-8 JSON"
        ) from exc
    if not isinstance(manifest, dict) or isinstance(manifest.get("books"), list):
        raise PipelineError(
            "BLOCKED_INPUT_MANIFEST", "Input manifest must describe exactly one title"
        )

    source_sha256 = sha256_bytes(source_bytes)
    declared_hash = str(
        nested_value(
            manifest,
            ("sanitized_source_sha256",),
            ("sanitized_source", "sha256"),
            ("source", "sanitized_sha256"),
        )
        or ""
    ).lower()
    if declared_hash != source_sha256:
        raise PipelineError(
            "BLOCKED_SOURCE_HASH_MISMATCH",
            "Sanitized source bytes do not match the input manifest",
            details={"declared_sha256": declared_hash, "actual_sha256": source_sha256},
        )

    sanitization_status = str(
        nested_value(manifest, ("sanitization_status",), ("sanitization", "status"))
        or ""
    ).upper()
    rights_status = str(
        nested_value(manifest, ("rights_status",), ("rights", "status")) or ""
    ).upper()
    commercial = nested_value(
        manifest,
        ("commercial_use_allowed",),
        ("rights", "commercial_use_allowed"),
        ("rights", "commercial_use"),
    )
    if sanitization_status != "PASS":
        raise PipelineError(
            "BLOCKED_SOURCE_SANITATION",
            "Input manifest sanitization_status must be PASS",
        )
    if rights_status != "PASS" or not commercial_use_allowed(commercial):
        raise PipelineError(
            "BLOCKED_RIGHTS",
            "Input manifest must contain PASS rights and explicit commercial-use clearance",
        )

    slug = str(manifest.get("slug") or "").strip()
    title = str(manifest.get("title") or "").strip()
    author = str(manifest.get("author") or "").strip()
    language = (
        str(manifest.get("language") or manifest.get("language_code") or "")
        .strip()
        .lower()
    )
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise PipelineError(
            "BLOCKED_INPUT_MANIFEST", "Input manifest slug is missing or invalid"
        )
    if not title:
        raise PipelineError(
            "BLOCKED_INPUT_MANIFEST", "Input manifest title is required"
        )
    if language not in {"en", "eng", "english"} and not language.startswith("en-"):
        raise PipelineError(
            "BLOCKED_NON_ENGLISH_TITLE", "This pipeline accepts one English title only"
        )

    return SourceBundle(
        slug=slug,
        title=title,
        author=author,
        source_text=source_text,
        source_bytes=source_bytes,
        source_sha256=source_sha256,
        manifest=manifest,
        manifest_bytes=manifest_bytes,
        manifest_sha256=sha256_bytes(manifest_bytes),
    )


def english_language_code(voice: str, explicit: str | None = None) -> str:
    match = re.match(r"^(en-[A-Z]{2})-", voice)
    if not match:
        raise PipelineError(
            "BLOCKED_GOOGLE_VOICE",
            "Google voice must be an English voice name such as en-GB-Studio-C",
        )
    derived = match.group(1)
    if explicit and explicit != derived:
        raise PipelineError(
            "BLOCKED_GOOGLE_VOICE",
            "--language-code must match the locale encoded in --voice",
            details={"voice_locale": derived, "language_code": explicit},
        )
    return explicit or derived


def sentence_units(text: str) -> list[str]:
    flattened = re.sub(r"\s+", " ", text or "").strip()
    sentences = [
        item.strip() for item in re.split(r"(?<=[.!?])\s+", flattened) if item.strip()
    ]
    if len(sentences) < 4:
        sentences = [
            item.strip()
            for item in re.split(r"(?<=[.!?;:])\s+", flattened)
            if item.strip()
        ]
    if len(sentences) < 4:
        raise PipelineError(
            "BLOCKED_UNREPRESENTATIVE_SOURCE",
            "Source needs at least four sentence or clause units for representative auditioning",
        )
    return sentences


def joined_with_limit(
    sentences: list[str], indexes: list[int], max_chars: int
) -> tuple[str, set[int]]:
    selected: list[str] = []
    used: set[int] = set()
    for index in indexes:
        sentence = sentences[index]
        if selected and len(" ".join([*selected, sentence])) > max_chars:
            break
        if not selected and len(sentence) > max_chars:
            sentence = (
                sentence[:max_chars].rsplit(" ", 1)[0].strip() or sentence[:max_chars]
            )
        selected.append(sentence)
        used.add(index)
    return " ".join(selected).strip(), used


def contextual_risk_passage(
    sentences: list[str],
    risk_index: int,
    max_chars: int,
    reserved: set[int],
) -> tuple[str, list[int]]:
    """Keep a risky sentence in prose context so the audition is representative."""
    target_chars = min(max_chars, 400)
    selected = {risk_index}
    left = risk_index - 1
    right = risk_index + 1
    while True:
        current = " ".join(sentences[index] for index in sorted(selected))
        if len(current) >= target_chars:
            return current, sorted(selected)
        candidates = []
        if left >= 0 and left not in reserved:
            candidates.append(left)
        if right < len(sentences) and right not in reserved:
            candidates.append(right)
        if not candidates:
            return current, sorted(selected)
        added = False
        for index in candidates:
            proposed = " ".join(
                sentences[item] for item in sorted({*selected, index})
            )
            if len(proposed) <= max_chars:
                selected.add(index)
                added = True
            if index == left:
                left -= 1
            if index == right:
                right += 1
            if len(proposed) >= target_chars:
                break
        if not added:
            return current, sorted(selected)


def select_representative_passages(
    text: str, max_chars: int = 1200
) -> list[dict[str, Any]]:
    if max_chars < 200:
        raise PipelineError("BLOCKED_CONFIG", "max_passage_chars must be at least 200")
    sentences = sentence_units(text)
    count = len(sentences)
    window = min(4, max(1, count // 10))

    opening_text, opening_used = joined_with_limit(
        sentences, list(range(window)), max_chars
    )
    ending_indexes = list(range(count - window, count))
    ending_text, ending_used = joined_with_limit(sentences, ending_indexes, max_chars)

    middle_start = max(window, min(count - window - 1, count // 2 - window // 2))
    middle_indexes = list(
        range(middle_start, min(count - window, middle_start + window))
    )
    if not middle_indexes:
        middle_indexes = [count // 2]
    middle_text, middle_used = joined_with_limit(sentences, middle_indexes, max_chars)

    reserved = opening_used | middle_used | ending_used

    def risk_score(item: tuple[int, str]) -> tuple[int, int, int]:
        index, sentence = item
        dialogue = sum(
            sentence.count(mark)
            for mark in ('"', "\u201c", "\u201d", "\u2018", "\u2019")
        )
        punctuation = sum(
            sentence.count(mark) for mark in ("?", "!", ";", ":", "\u2014", ",")
        )
        return (
            dialogue * 20 + punctuation * 3 + min(len(sentence), 400) // 20,
            -abs(index - count // 2),
            -index,
        )

    eligible = [
        (index, sentence)
        for index, sentence in enumerate(sentences)
        if index not in reserved
    ]
    candidates = eligible or list(enumerate(sentences))
    risk_index, _risk_sentence = max(candidates, key=risk_score)
    risk_text, risk_context_indexes = contextual_risk_passage(
        sentences, risk_index, max_chars, reserved
    )
    if len(risk_text) > max_chars:
        risk_text = (
            risk_text[:max_chars].rsplit(" ", 1)[0].strip() or risk_text[:max_chars]
        )

    passages = [
        ("opening", opening_text),
        ("middle", middle_text),
        ("dialogue_or_risk", risk_text),
        ("ending", ending_text),
    ]
    if any(not passage_text for _, passage_text in passages):
        raise PipelineError(
            "BLOCKED_UNREPRESENTATIVE_SOURCE",
            "Representative passage selection produced an empty passage",
        )
    hashes = [sha256_text(passage_text) for _, passage_text in passages]
    if len(set(hashes)) != len(PASSAGE_IDS):
        raise PipelineError(
            "BLOCKED_UNREPRESENTATIVE_SOURCE",
            "Representative passages are not distinct",
        )
    return [
        {
            "passage_id": passage_id,
            "text": passage_text,
            "text_sha256": sha256_text(passage_text),
            "characters": len(passage_text),
            **(
                {
                    "source_sentence_index": risk_index,
                    "source_sentence_indexes": risk_context_indexes,
                }
                if passage_id == "dialogue_or_risk"
                else {}
            ),
        }
        for passage_id, passage_text in passages
    ]


def full_generation_chunks(text: str, max_chars: int = 1600) -> list[dict[str, Any]]:
    if max_chars < 500 or max_chars > 4500:
        raise PipelineError(
            "BLOCKED_CONFIG", "max_chunk_chars must be between 500 and 4500"
        )
    chunks = factory_chunk_text(text, max_chars=max_chars)
    if not chunks:
        raise PipelineError(
            "BLOCKED_EMPTY_SOURCE", "Source produced no full-generation chunks"
        )
    rebuilt = re.sub(r"\s+", " ", " ".join(item["text"] for item in chunks)).strip()
    expected = re.sub(r"\s+", " ", text).strip()
    if rebuilt != expected:
        raise PipelineError(
            "BLOCKED_SOURCE_PRESERVATION",
            "Sentence-safe chunks do not preserve sanitized source text",
        )
    return [
        {
            "chunk_id": f"chunk_{int(item['index']):04d}",
            "index": int(item["index"]),
            "text": item["text"],
            "text_sha256": item["text_hash"],
            "characters": len(item["text"]),
        }
        for item in chunks
    ]


def validate_google_unit_sizes(units: list[dict[str, Any]]) -> None:
    oversized = [
        item.get("passage_id") or item.get("chunk_id")
        for item in units
        if len(str(item["text"]).encode("utf-8")) > GOOGLE_SAFE_INPUT_BYTES
    ]
    if oversized:
        raise PipelineError(
            "BLOCKED_GOOGLE_INPUT_LIMIT",
            "One or more TTS units exceed the private pipeline's Google byte safety limit",
            details={
                "limit_bytes": GOOGLE_SAFE_INPUT_BYTES,
                "oversized_units": oversized,
            },
        )


def validate_money(name: str, value: float, *, allow_zero: bool) -> None:
    if not math.isfinite(value) or value < 0 or (not allow_zero and value == 0):
        qualifier = "non-negative" if allow_zero else "greater than zero"
        raise PipelineError("BLOCKED_CONFIG", f"{name} must be finite and {qualifier}")


def budget_check(config: PipelineConfig, character_count: int) -> dict[str, Any]:
    validate_money(
        "usd_per_million_chars", config.usd_per_million_chars, allow_zero=False
    )
    validate_money("run_budget_usd", config.run_budget_usd, allow_zero=False)
    validate_money("title_budget_usd", config.title_budget_usd, allow_zero=False)
    validate_money("sprint_budget_usd", config.sprint_budget_usd, allow_zero=False)
    validate_money("title_spend_usd", config.title_spend_usd, allow_zero=True)
    validate_money("sprint_spend_usd", config.sprint_spend_usd, allow_zero=True)
    estimate = round(character_count / 1_000_000 * config.usd_per_million_chars, 6)
    projected_title = round(config.title_spend_usd + estimate, 6)
    projected_sprint = round(config.sprint_spend_usd + estimate, 6)
    blockers: list[str] = []
    if estimate > config.run_budget_usd:
        blockers.append("estimated run cost exceeds run budget")
    if projected_title > config.title_budget_usd:
        blockers.append("projected title spend exceeds title budget")
    if projected_sprint > config.sprint_budget_usd:
        blockers.append("projected sprint spend exceeds sprint budget")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "billable_characters": character_count,
        "usd_per_million_chars": config.usd_per_million_chars,
        "estimated_run_usd": estimate,
        "run_budget_usd": config.run_budget_usd,
        "prior_title_spend_usd": config.title_spend_usd,
        "projected_title_spend_usd": projected_title,
        "title_budget_usd": config.title_budget_usd,
        "prior_sprint_spend_usd": config.sprint_spend_usd,
        "projected_sprint_spend_usd": projected_sprint,
        "sprint_budget_usd": config.sprint_budget_usd,
        "blockers": blockers,
    }


def attempt_fingerprint(
    *,
    mode: str,
    source_sha256: str,
    manifest_sha256: str,
    voice: str,
    language_code: str,
    speaking_rate: float,
    pitch: float,
    units: list[dict[str, Any]],
) -> str:
    payload = {
        "schema": PIPELINE_SCHEMA,
        "mode": mode,
        "provider": "google",
        "source_sha256": source_sha256,
        "manifest_sha256": manifest_sha256,
        "voice": voice,
        "language_code": language_code,
        "speaking_rate": speaking_rate,
        "pitch": pitch,
        "unit_hashes": [item["text_sha256"] for item in units],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def attempt_state_path(output_dir: Path, slug: str, fingerprint: str) -> Path:
    return output_dir / slug / "attempts" / f"{fingerprint}.json"


def reject_duplicate_attempt(path: Path, fingerprint: str) -> None:
    if not path.exists():
        return
    try:
        prior = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PipelineError(
            "BLOCKED_ATTEMPT_LEDGER", "Existing private attempt state is unreadable"
        ) from exc
    if (
        prior.get("attempt_fingerprint") == fingerprint
        and prior.get("provider_calls_ran") is True
    ):
        raise PipelineError(
            "BLOCKED_DUPLICATE_FINGERPRINT",
            "This exact source, manifest, voice, settings, and mode already reached the provider",
            exit_code=4,
            details={
                "attempt_fingerprint": fingerprint,
                "prior_status": prior.get("status"),
            },
        )


def validate_paid_lock(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PipelineError(
            "BLOCKED_PAID_LOCK", "Paid lock must be valid UTF-8 JSON"
        ) from exc
    if not isinstance(payload, dict) or payload.get("status") != "active":
        raise PipelineError("BLOCKED_PAID_LOCK", "Paid lock must remain active")
    if payload.get("current_holder") != "none":
        raise PipelineError("BLOCKED_PAID_LOCK", "Paid lock already has a holder")
    if payload.get("allowed_next_holders", []) != []:
        raise PipelineError(
            "BLOCKED_PAID_LOCK", "Paid lock allowed_next_holders must be empty"
        )
    return payload


def acquired_lock_payload(
    original: dict[str, Any],
    *,
    config: PipelineConfig,
    bundle: SourceBundle,
    fingerprint: str,
    budget: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(original)
    payload.update(
        {
            "current_holder": f"sprint1_google_english_private_pipeline:{bundle.slug}:{config.mode}",
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "allowed_slugs": [bundle.slug],
            "budget_cap_usd": config.run_budget_usd,
            "approved_scope": (
                f"Private Google English {config.mode} only; voice {config.voice}; fingerprint {fingerprint}; "
                "no upload, publication, release mutation, or public output."
            ),
            "estimated_cost_usd": budget["estimated_run_usd"],
            "stop_conditions": [
                "Any approval, source, manifest, rights, lock, or budget gate fails",
                "The fingerprint already reached the provider",
                "Full mode lacks passing hash-bound representative listening evidence",
                "Any output path is public or release-facing",
                "Any upload, publication, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def approval_errors(
    config: PipelineConfig, *, require_google_project: bool = True
) -> list[str]:
    if not config.execute:
        return []
    errors: list[str] = []
    approval_env = APPROVAL_ENV_BY_MODE[config.mode]
    if os.environ.get(approval_env, "").strip().lower() != "true":
        errors.append(f"{approval_env}=true is required")
    if (
        os.environ.get("EARNALISM_STOP_ON_BUDGET_EXCEEDED", "").strip().lower()
        != "true"
    ):
        errors.append("EARNALISM_STOP_ON_BUDGET_EXCEEDED=true is required")
    if require_google_project and not (
        config.project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
    ):
        errors.append("GOOGLE_CLOUD_PROJECT or --project-id is required")
    return errors


def evidence_sample_map(evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    samples = evidence.get("samples")
    if not isinstance(samples, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        passage_id = str(sample.get("passage_id") or "")
        if passage_id and passage_id not in result:
            result[passage_id] = sample
    return result


def validate_audition_evidence(
    path: Path | None,
    *,
    config: PipelineConfig,
    bundle: SourceBundle,
    output_dir: Path,
    language_code: str,
    passages: list[dict[str, Any]],
) -> dict[str, Any]:
    if path is None:
        raise PipelineError(
            "BLOCKED_AUDITION_EVIDENCE",
            "Full mode requires --audition-evidence from this pipeline's representative audition",
            exit_code=5,
        )
    evidence_path = path.expanduser().resolve()
    if not is_within(evidence_path, output_dir):
        raise PipelineError(
            "BLOCKED_AUDITION_EVIDENCE",
            "Audition evidence must remain inside private output",
        )
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PipelineError(
            "BLOCKED_AUDITION_EVIDENCE", "Audition evidence is missing or invalid"
        ) from exc

    expected_fingerprint = attempt_fingerprint(
        mode="audition",
        source_sha256=bundle.source_sha256,
        manifest_sha256=bundle.manifest_sha256,
        voice=config.voice,
        language_code=language_code,
        speaking_rate=config.speaking_rate,
        pitch=config.pitch,
        units=passages,
    )
    binding_errors: list[str] = []
    expected_fields = {
        "schema_version": LISTENING_SCHEMA,
        "status": "PASS",
        "slug": bundle.slug,
        "provider": "google",
        "voice": config.voice,
        "language_code": language_code,
        "source_sha256": bundle.source_sha256,
        "input_manifest_sha256": bundle.manifest_sha256,
        "audition_fingerprint": expected_fingerprint,
        "private_output_only": True,
        "provider_calls_ran": True,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
    }
    for field, expected in expected_fields.items():
        if evidence.get(field) != expected:
            binding_errors.append(f"{field} must equal {expected!r}")

    audition_manifest_value = str(evidence.get("audition_manifest_path") or "")
    audition_manifest_path = (
        Path(audition_manifest_value).expanduser().resolve()
        if audition_manifest_value
        else Path()
    )
    if (
        not audition_manifest_value
        or not is_within(audition_manifest_path, output_dir)
        or not audition_manifest_path.is_file()
    ):
        binding_errors.append(
            "audition_manifest_path must reference a private audition manifest"
        )
    else:
        audition_manifest_bytes = audition_manifest_path.read_bytes()
        if sha256_bytes(audition_manifest_bytes) != evidence.get(
            "audition_manifest_sha256"
        ):
            binding_errors.append("audition manifest hash mismatch")
        try:
            audition_manifest = json.loads(audition_manifest_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError):
            binding_errors.append("audition manifest is invalid")
        else:
            if audition_manifest.get("attempt_fingerprint") != expected_fingerprint:
                binding_errors.append("audition manifest fingerprint mismatch")
            if (
                audition_manifest.get("status")
                != "AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED"
            ):
                binding_errors.append(
                    "audition manifest status is not listening-review-ready"
                )
            if audition_manifest.get("mode") != "audition":
                binding_errors.append("audition manifest mode is invalid")
            if audition_manifest.get("provider_calls_ran") is not True:
                binding_errors.append("audition manifest does not prove provider calls")
            if audition_manifest.get("private_output_only") is not True:
                binding_errors.append("audition manifest is not private-output-only")
            for mutation_field in (
                "upload_performed",
                "publication_performed",
                "release_mutation_performed",
            ):
                if audition_manifest.get(mutation_field) is not False:
                    binding_errors.append(
                        f"audition manifest {mutation_field} must be false"
                    )

    samples = evidence_sample_map(evidence)
    expected_passages = {item["passage_id"]: item for item in passages}
    if set(samples) != set(PASSAGE_IDS):
        binding_errors.append(
            "evidence must contain exactly opening, middle, dialogue_or_risk, and ending"
        )
    sample_blockers: list[str] = []
    for passage_id in PASSAGE_IDS:
        sample = samples.get(passage_id)
        passage = expected_passages[passage_id]
        if not sample:
            continue
        if sample.get("source_text_sha256") != passage["text_sha256"]:
            sample_blockers.append(f"{passage_id}: source text hash mismatch")
        try:
            score = float(sample.get("overall_listening_score"))
            confidence = float(sample.get("confidence_score"))
        except (TypeError, ValueError):
            sample_blockers.append(
                f"{passage_id}: listening score and confidence are required"
            )
            continue
        if not math.isfinite(score) or not 0 <= score <= 10:
            sample_blockers.append(
                f"{passage_id}: listening score must be finite and between 0 and 10"
            )
            continue
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            sample_blockers.append(
                f"{passage_id}: confidence must be finite and between 0 and 1"
            )
            continue
        if score < config.minimum_listening_score:
            sample_blockers.append(
                f"{passage_id}: listening score {score} below {config.minimum_listening_score}"
            )
        if confidence < config.minimum_listening_confidence:
            sample_blockers.append(
                f"{passage_id}: confidence {confidence} below {config.minimum_listening_confidence}"
            )
        fatal_flags = sample.get("fatal_flags") or []
        judge_flags = sample.get("judge_flags") or {}
        if fatal_flags:
            sample_blockers.append(f"{passage_id}: fatal listening flags present")
        if isinstance(judge_flags, dict) and any(
            judge_flags.get(flag) is True for flag in FATAL_LISTENING_FLAGS
        ):
            sample_blockers.append(f"{passage_id}: fatal listening flag is true")
        audio_value = str(sample.get("audio_path") or "")
        audio_path = Path(audio_value).expanduser().resolve() if audio_value else Path()
        if (
            not audio_value
            or not is_within(audio_path, output_dir)
            or not audio_path.is_file()
        ):
            sample_blockers.append(f"{passage_id}: private audition audio is missing")
        elif sha256_bytes(audio_path.read_bytes()) != sample.get("audio_sha256"):
            sample_blockers.append(f"{passage_id}: audition audio hash mismatch")

    blockers = [*binding_errors, *sample_blockers]
    if blockers:
        raise PipelineError(
            "BLOCKED_AUDITION_EVIDENCE",
            "Representative listening-audition evidence is incomplete, stale, or below policy",
            exit_code=5,
            details={"blockers": blockers},
        )
    return {**evidence, "evidence_sha256": sha256_bytes(evidence_path.read_bytes())}


class GoogleCloudTTSProvider:
    def __init__(self, project_id: str | None = None) -> None:
        from google.cloud import texttospeech  # noqa: PLC0415

        self.texttospeech = texttospeech
        self.client = texttospeech.TextToSpeechClient()
        self.project_id = project_id

    def ensure_voice(self, *, voice: str, language_code: str) -> None:
        available = {
            item.name
            for item in self.client.list_voices(language_code=language_code).voices
        }
        if voice not in available:
            raise RuntimeError(f"Selected Google voice is unavailable: {voice}")

    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        language_code: str,
        speaking_rate: float,
        pitch: float,
    ) -> bytes:
        response = self.client.synthesize_speech(
            input=self.texttospeech.SynthesisInput(text=text),
            voice=self.texttospeech.VoiceSelectionParams(
                language_code=language_code, name=voice
            ),
            audio_config=self.texttospeech.AudioConfig(
                audio_encoding=self.texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=pitch,
            ),
        )
        return bytes(response.audio_content)


ProviderFactory = Callable[[PipelineConfig], TTSProvider]


def default_provider_factory(config: PipelineConfig) -> TTSProvider:
    return GoogleCloudTTSProvider(
        config.project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
    )


def private_run_dir(output_dir: Path, slug: str, mode: str, fingerprint: str) -> Path:
    return output_dir / slug / mode / fingerprint[:16]


def provider_unit_records(
    mode: str, units: list[dict[str, Any]], run_dir: Path
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for unit in units:
        unit_id = unit["passage_id"] if mode == "audition" else unit["chunk_id"]
        records.append(
            {
                "unit_id": unit_id,
                "text": unit["text"],
                "text_sha256": unit["text_sha256"],
                "characters": unit["characters"],
                "audio_path": str(run_dir / "audio" / f"{unit_id}.mp3"),
            }
        )
    return records


def listening_template(
    *,
    config: PipelineConfig,
    bundle: SourceBundle,
    language_code: str,
    fingerprint: str,
    records: list[dict[str, Any]],
    audition_manifest_path: Path,
    audition_manifest_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": LISTENING_SCHEMA,
        "status": "PENDING_LISTENING_REVIEW",
        "slug": bundle.slug,
        "title": bundle.title,
        "provider": "google",
        "voice": config.voice,
        "language_code": language_code,
        "source_sha256": bundle.source_sha256,
        "input_manifest_sha256": bundle.manifest_sha256,
        "audition_fingerprint": fingerprint,
        "audition_manifest_path": str(audition_manifest_path),
        "audition_manifest_sha256": audition_manifest_sha256,
        "minimum_listening_score": config.minimum_listening_score,
        "minimum_listening_confidence": config.minimum_listening_confidence,
        "required_passages": list(PASSAGE_IDS),
        "fatal_flags_required_false": list(FATAL_LISTENING_FLAGS),
        "private_output_only": True,
        "provider_calls_ran": True,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "samples": [
            {
                "passage_id": record["unit_id"],
                "source_text_sha256": record["text_sha256"],
                "audio_path": record["audio_path"],
                "audio_sha256": record["audio_sha256"],
                "overall_listening_score": None,
                "confidence_score": None,
                "fatal_flags": [],
                "judge_flags": {flag: False for flag in FATAL_LISTENING_FLAGS},
                "review_notes": "",
            }
            for record in records
        ],
    }


def next_command(
    config: PipelineConfig,
    evidence_path: Path | None = None,
    *,
    title_spend_usd: float | None = None,
    sprint_spend_usd: float | None = None,
) -> str:
    script = Path(__file__).resolve()
    mode = "full" if evidence_path else config.mode
    parts = [
        sys.executable,
        str(script),
        mode,
        "--sanitized-source",
        str(config.source_path),
        "--input-manifest",
        str(config.manifest_path),
        "--paid-lock",
        str(config.lock_path),
        "--private-output-dir",
        str(config.private_output_dir),
        "--voice",
        config.voice,
        "--usd-per-million-chars",
        str(config.usd_per_million_chars),
        "--run-budget-usd",
        str(config.run_budget_usd),
        "--title-budget-usd",
        str(config.title_budget_usd),
        "--title-spend-usd",
        str(config.title_spend_usd if title_spend_usd is None else title_spend_usd),
        "--sprint-budget-usd",
        str(config.sprint_budget_usd),
        "--sprint-spend-usd",
        str(config.sprint_spend_usd if sprint_spend_usd is None else sprint_spend_usd),
    ]
    if config.language_code:
        parts.extend(["--language-code", config.language_code])
    if config.project_id:
        parts.extend(["--project-id", config.project_id])
    if evidence_path:
        parts.extend(["--audition-evidence", str(evidence_path)])
    parts.append("--execute")
    return " ".join(shlex.quote(part) for part in parts)


def validate_config(config: PipelineConfig) -> None:
    if config.mode not in MODES:
        raise PipelineError("BLOCKED_CONFIG", f"mode must be one of {', '.join(MODES)}")
    if config.mode == "audition" and config.audition_evidence_path is not None:
        raise PipelineError(
            "BLOCKED_CONFIG", "--audition-evidence applies only to full mode"
        )
    if not 0.25 <= config.speaking_rate <= 4.0:
        raise PipelineError(
            "BLOCKED_CONFIG", "speaking_rate must be between 0.25 and 4.0"
        )
    if not -20.0 <= config.pitch <= 20.0:
        raise PipelineError("BLOCKED_CONFIG", "pitch must be between -20 and 20")
    if not POLICY_MIN_LISTENING_SCORE <= config.minimum_listening_score <= 10:
        raise PipelineError(
            "BLOCKED_CONFIG",
            f"minimum_listening_score must be between {POLICY_MIN_LISTENING_SCORE} and 10",
        )
    if not POLICY_MIN_LISTENING_CONFIDENCE <= config.minimum_listening_confidence <= 1:
        raise PipelineError(
            "BLOCKED_CONFIG",
            "minimum_listening_confidence must be between 0.9 and 1",
        )


def run_pipeline(
    config: PipelineConfig,
    *,
    provider_factory: ProviderFactory | None = None,
) -> dict[str, Any]:
    validate_config(config)
    output_dir = validate_private_output_dir(config.private_output_dir)
    bundle = load_source_bundle(config.source_path, config.manifest_path)
    language_code = english_language_code(config.voice, config.language_code)
    passages = select_representative_passages(
        bundle.source_text, config.max_passage_chars
    )
    audition_evidence: dict[str, Any] | None = None
    if config.mode == "audition":
        units = passages
    else:
        audition_evidence = validate_audition_evidence(
            config.audition_evidence_path,
            config=config,
            bundle=bundle,
            output_dir=output_dir,
            language_code=language_code,
            passages=passages,
        )
        units = full_generation_chunks(bundle.source_text, config.max_chunk_chars)

    validate_google_unit_sizes(units)
    budget = budget_check(config, sum(int(item["characters"]) for item in units))
    if budget["status"] != "PASS":
        raise PipelineError(
            "BLOCKED_BUDGET",
            "Paid Google TTS budget gate failed before provider construction",
            exit_code=3,
            details={"budget": budget, "provider_calls_ran": False},
        )
    runtime_errors = approval_errors(
        config, require_google_project=provider_factory is None
    )
    if runtime_errors:
        raise PipelineError(
            "BLOCKED_RUNTIME_GATES",
            "Explicit paid runtime approval is incomplete",
            details={"errors": runtime_errors, "provider_calls_ran": False},
        )

    fingerprint = attempt_fingerprint(
        mode=config.mode,
        source_sha256=bundle.source_sha256,
        manifest_sha256=bundle.manifest_sha256,
        voice=config.voice,
        language_code=language_code,
        speaking_rate=config.speaking_rate,
        pitch=config.pitch,
        units=units,
    )
    state_path = attempt_state_path(output_dir, bundle.slug, fingerprint)
    reject_duplicate_attempt(state_path, fingerprint)
    preflight = {
        "schema_version": PIPELINE_SCHEMA,
        "status": f"{config.mode.upper()}_PREFLIGHT_PASS",
        "mode": config.mode,
        "slug": bundle.slug,
        "title": bundle.title,
        "author": bundle.author,
        "provider": "google",
        "voice": config.voice,
        "language_code": language_code,
        "speaking_rate": config.speaking_rate,
        "pitch": config.pitch,
        "source_sha256": bundle.source_sha256,
        "input_manifest_sha256": bundle.manifest_sha256,
        "input_schema": bundle.manifest.get("schema_version"),
        "attempt_fingerprint": fingerprint,
        "unit_count": len(units),
        "unit_hashes": [item["text_sha256"] for item in units],
        "representative_passages": [
            {key: value for key, value in item.items() if key != "text"}
            for item in passages
        ],
        "budget": budget,
        "audition_evidence_sha256": (audition_evidence or {}).get("evidence_sha256"),
        "private_output_only": True,
        "public_release_approved": False,
        "provider_calls_ran": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "paid_lock_touched": False,
    }
    if not config.execute:
        return {**preflight, "next_exact_command": next_command(config)}

    original_lock = config.lock_path.expanduser().resolve().read_bytes()
    parsed_lock = validate_paid_lock(original_lock)
    run_dir = private_run_dir(output_dir, bundle.slug, config.mode, fingerprint)
    manifest_name = (
        "audition_manifest.json"
        if config.mode == "audition"
        else "full_generation_manifest.json"
    )
    result_manifest_path = run_dir / manifest_name
    records = provider_unit_records(config.mode, units, run_dir)
    started_at = iso_now()
    attempt_state = {
        "schema_version": PIPELINE_SCHEMA,
        "status": "PROVIDER_READY_PENDING_FIRST_SYNTHESIS",
        "mode": config.mode,
        "slug": bundle.slug,
        "provider": "google",
        "voice": config.voice,
        "source_sha256": bundle.source_sha256,
        "input_manifest_sha256": bundle.manifest_sha256,
        "attempt_fingerprint": fingerprint,
        "provider_calls_ran": False,
        "started_at": started_at,
        "private_output_only": True,
    }
    acquired = acquired_lock_payload(
        parsed_lock,
        config=config,
        bundle=bundle,
        fingerprint=fingerprint,
        budget=budget,
    )
    lock_sha256_before = sha256_bytes(original_lock)
    execution_error: Exception | None = None
    synthesis_calls = 0
    provider_calls_ran = False
    try:
        atomic_write_bytes(
            config.lock_path.expanduser().resolve(),
            json.dumps(acquired, ensure_ascii=False, indent=2, sort_keys=True).encode(
                "utf-8"
            )
            + b"\n",
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(run_dir / "sanitized_source.txt", bundle.source_bytes)
        atomic_write_bytes(run_dir / "input_manifest.json", bundle.manifest_bytes)
        atomic_write_json(state_path, attempt_state)
        provider = (provider_factory or default_provider_factory)(config)
        ensure_voice = getattr(provider, "ensure_voice", None)
        if callable(ensure_voice):
            ensure_voice(voice=config.voice, language_code=language_code)
        for record in records:
            if not provider_calls_ran:
                provider_calls_ran = True
                attempt_state.update(
                    {"status": "PROVIDER_CALL_STARTED", "provider_calls_ran": True}
                )
                atomic_write_json(state_path, attempt_state)
            audio = provider.synthesize(
                text=record["text"],
                voice=config.voice,
                language_code=language_code,
                speaking_rate=config.speaking_rate,
                pitch=config.pitch,
            )
            synthesis_calls += 1
            if not isinstance(audio, (bytes, bytearray)) or not audio:
                raise RuntimeError(
                    f"Google returned empty audio for {record['unit_id']}"
                )
            audio_bytes = bytes(audio)
            if not (audio_bytes.startswith(b"ID3") or audio_bytes.startswith(b"\xff")):
                raise RuntimeError(
                    f"Google returned non-MP3 audio for {record['unit_id']}"
                )
            audio_path = Path(record["audio_path"])
            atomic_write_bytes(audio_path, audio_bytes)
            record["audio_sha256"] = sha256_bytes(audio_bytes)
            record["audio_size_bytes"] = len(audio_bytes)
            record.pop("text")
    except Exception as exc:  # noqa: BLE001
        execution_error = exc
    finally:
        try:
            atomic_write_bytes(config.lock_path.expanduser().resolve(), original_lock)
        except Exception as restore_exc:  # noqa: BLE001
            execution_error = PipelineError(
                "PAID_LOCK_RESTORE_FAILED",
                f"Paid lock restoration failed: {restore_exc}",
                exit_code=7,
            )

    lock_after = config.lock_path.expanduser().resolve().read_bytes()
    lock_restored = lock_after == original_lock
    if not lock_restored and not isinstance(execution_error, PipelineError):
        execution_error = PipelineError(
            "PAID_LOCK_RESTORE_FAILED",
            "Paid lock was not restored byte-for-byte",
            exit_code=7,
        )

    result_status = (
        "AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED"
        if config.mode == "audition"
        else "FULL_GENERATION_PRIVATE_QA_PENDING"
    )
    if execution_error is not None:
        result_status = f"{config.mode.upper()}_PROVIDER_FAILED_PRIVATE_ONLY"
    result = {
        **preflight,
        "status": result_status,
        "started_at": started_at,
        "finished_at": iso_now(),
        "provider_calls_ran": provider_calls_ran,
        "synthesis_calls": synthesis_calls,
        "private_run_dir": str(run_dir),
        "result_manifest_path": str(result_manifest_path),
        "sanitized_source_copy": str(run_dir / "sanitized_source.txt"),
        "input_manifest_copy": str(run_dir / "input_manifest.json"),
        "generated_audio": records,
        "actual_provider_billing": "NOT_REPORTED",
        "paid_lock_touched": True,
        "paid_lock_restored_byte_for_byte": lock_restored,
        "paid_lock_sha256_before": lock_sha256_before,
        "paid_lock_sha256_after": sha256_bytes(lock_after),
        "errors": (
            [f"{type(execution_error).__name__}: {execution_error}"]
            if execution_error
            else []
        ),
    }

    evidence_path: Path | None = None
    if execution_error is None and config.mode == "audition":
        evidence_path = run_dir / "audition_listening_evidence.json"
        result["listening_evidence_path"] = str(evidence_path)
        result["next_exact_command"] = next_command(
            config,
            evidence_path,
            title_spend_usd=budget["projected_title_spend_usd"],
            sprint_spend_usd=budget["projected_sprint_spend_usd"],
        )
    elif execution_error is None:
        result["next_exact_command"] = (
            f"{sys.executable} -m json.tool {shlex.quote(str(result_manifest_path))}"
        )
    else:
        result["next_exact_command"] = (
            f"{sys.executable} -m json.tool {shlex.quote(str(state_path))}"
        )

    atomic_write_json(result_manifest_path, result)
    if evidence_path is not None:
        atomic_write_json(
            evidence_path,
            listening_template(
                config=config,
                bundle=bundle,
                language_code=language_code,
                fingerprint=fingerprint,
                records=records,
                audition_manifest_path=result_manifest_path,
                audition_manifest_sha256=sha256_bytes(
                    result_manifest_path.read_bytes()
                ),
            ),
        )
    attempt_state.update(
        {
            "status": result_status,
            "finished_at": result["finished_at"],
            "synthesis_calls": synthesis_calls,
            "result_manifest_path": str(result_manifest_path),
            "paid_lock_restored_byte_for_byte": lock_restored,
            "errors": result["errors"],
        }
    )
    atomic_write_json(state_path, attempt_state)
    if execution_error is not None:
        if isinstance(execution_error, PipelineError):
            raise execution_error
        raise PipelineError(
            "PROVIDER_EXECUTION_FAILED",
            f"Private Google {config.mode} failed: {execution_error}",
            exit_code=6,
            details={
                "result_manifest_path": str(result_manifest_path),
                "paid_lock_restored_byte_for_byte": lock_restored,
                "provider_calls_ran": provider_calls_ran,
            },
        ) from execution_error
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("--sanitized-source", required=True, type=Path)
    parser.add_argument("--input-manifest", required=True, type=Path)
    parser.add_argument("--paid-lock", required=True, type=Path)
    parser.add_argument("--private-output-dir", required=True, type=Path)
    parser.add_argument(
        "--voice",
        required=True,
        help="Google English voice name, for example en-GB-Studio-C",
    )
    parser.add_argument(
        "--language-code", help="Optional locale; must match the voice prefix"
    )
    parser.add_argument("--usd-per-million-chars", required=True, type=float)
    parser.add_argument("--run-budget-usd", required=True, type=float)
    parser.add_argument("--title-budget-usd", required=True, type=float)
    parser.add_argument("--title-spend-usd", type=float, default=0.0)
    parser.add_argument("--sprint-budget-usd", required=True, type=float)
    parser.add_argument("--sprint-spend-usd", type=float, default=0.0)
    parser.add_argument("--audition-evidence", type=Path)
    parser.add_argument("--minimum-listening-score", type=float, default=9.3)
    parser.add_argument("--minimum-listening-confidence", type=float, default=0.90)
    parser.add_argument("--max-passage-chars", type=int, default=1200)
    parser.add_argument("--max-chunk-chars", type=int, default=1600)
    parser.add_argument("--speaking-rate", type=float, default=0.94)
    parser.add_argument("--pitch", type=float, default=0.0)
    parser.add_argument("--project-id")
    parser.add_argument(
        "--execute", action="store_true", help="Acquire the paid lock and call Google"
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> PipelineConfig:
    return PipelineConfig(
        mode=args.mode,
        source_path=args.sanitized_source,
        manifest_path=args.input_manifest,
        lock_path=args.paid_lock,
        private_output_dir=args.private_output_dir,
        voice=args.voice,
        language_code=args.language_code,
        usd_per_million_chars=args.usd_per_million_chars,
        run_budget_usd=args.run_budget_usd,
        title_budget_usd=args.title_budget_usd,
        title_spend_usd=args.title_spend_usd,
        sprint_budget_usd=args.sprint_budget_usd,
        sprint_spend_usd=args.sprint_spend_usd,
        audition_evidence_path=args.audition_evidence,
        minimum_listening_score=args.minimum_listening_score,
        minimum_listening_confidence=args.minimum_listening_confidence,
        max_passage_chars=args.max_passage_chars,
        max_chunk_chars=args.max_chunk_chars,
        speaking_rate=args.speaking_rate,
        pitch=args.pitch,
        project_id=args.project_id,
        execute=args.execute,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        result = run_pipeline(config_from_args(parse_args(argv)))
    except PipelineError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return exc.exit_code
    except (OSError, ValueError) as exc:
        error = PipelineError("BLOCKED_INPUT", str(exc))
        print(json.dumps(error.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return error.exit_code
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
