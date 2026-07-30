#!/usr/bin/env python3
"""Prepare or execute one private, source-bound Jekyll chunk repair.

The workflow is intentionally title- and chunk-specific.  It accepts only the
retained Jekyll Google full manifest and the failed six-sample listening
evidence named in this module.  Preflight is read-only.  ``--execute`` makes
exactly one Google synthesis call, restores ``paid_tts.lock`` byte-for-byte,
and constructs a new private full-candidate directory in which the other 91
MP3 files are byte-identical copies of the retained candidate.

This script never uploads media, mutates controlled publication truth, changes
release gates, or publishes audio.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPT_DIR / "factory_hooks"
sys.path[:0] = [str(SCRIPT_DIR), str(HOOK_DIR)]

import sprint1_google_english_full_candidate_qa as candidate_qa  # noqa: E402
import sprint1_google_english_private_pipeline as google_pipeline  # noqa: E402


SCHEMA = "earnalism.jekyll_google_chunk36_bounded_repair.v1"
REPAIR_BLOCK_SCHEMA = "earnalism.google_english_bounded_chunk_repair.v1"
SLUG = "jekyll-and-hyde"
TITLE = "The Strange Case of Dr. Jekyll and Mr. Hyde"
AUTHOR = "Robert Louis Stevenson"
EXPECTED_SOURCE_SHA256 = (
    "0e8cc7fb6c18abd38def7c85cc2a8f4907bde5f11db48e36ba7fd9afff7fdc8e"
)
EXPECTED_INPUT_MANIFEST_SHA256 = (
    "43177dc6f71521a6558dfcccbd784d46213e9e0f533c4e8ac3133be29725fd22"
)
EXPECTED_FULL_MANIFEST_SHA256 = (
    "5bbbc01f9ab2dcba7194c1a0a28f636863896e68adb2f9a743ee33ddd7395439"
)
EXPECTED_FAILED_LISTENING_SHA256 = (
    "108a8dce73e92955da6d0b81f3fc4d82ec1acf50eff50112781dca91de31140d"
)
EXPECTED_BASE_ATTEMPT_FINGERPRINT = (
    "3f8ecfd4a75738d2f34f9081046d7aeae1b9f21f53f690ed58692e9baf4050a0"
)
EXPECTED_BASE_AUDIO_SEQUENCE_SHA256 = (
    "50eb4f5a6f75231f6f9b65b2426a9f3d8362530d9c333d8deaa7930b8f42fadd"
)
EXPECTED_BASE_CANDIDATE_BINDING_SHA256 = (
    "14239235336a1e562746b8c06987a6fb508c461dc898559f29880855b8d6232d"
)
EXPECTED_UNIT_COUNT = 92
TARGET_INDEX = 36
TARGET_UNIT_ID = "chunk_0036"
TARGET_TEXT_SHA256 = (
    "5060aa4dd568a123face1f08a448187d72f6d90b124e70cfaf75db48a73b9ede"
)
TARGET_PRIOR_AUDIO_SHA256 = (
    "d76d8462ca591054ecc2c45ee320fef140f9378559b0fe5e21754da80a0be731"
)
TARGET_PRIOR_AUDIO_SIZE_BYTES = 365_376
BASE_VOICE = "en-GB-Chirp3-HD-Charon"
BASE_LANGUAGE_CODE = "en-GB"
BASE_SPEAKING_RATE = 0.94
BASE_PITCH = 0.0

# Keep narrator identity stable.  The bounded repair changes pacing enough to
# produce a new provider fingerprint while avoiding a one-chunk voice switch.
RECOMMENDED_VOICE = "en-GB-Chirp3-HD-Charon"
RECOMMENDED_SPEAKING_RATE = 1.0
RECOMMENDED_PITCH = 0.0
SYNTHESIS_INPUT_KIND = "exact_plain_text"
APPROVAL_ENV = "EARNALISM_APPROVE_JEKYLL_CHUNK36_GOOGLE_REPAIR"
STOP_ON_BUDGET_ENV = "EARNALISM_STOP_ON_BUDGET_EXCEEDED"
FATAL_FLAGS = (
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "list_reading_rhythm_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
    "placeholder_audio_detected",
)
NO_REPEAT_REGISTRIES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
)


class BoundedRepairError(RuntimeError):
    """A fail-closed repair decision with a stable status."""

    def __init__(
        self,
        status: str,
        message: str,
        *,
        exit_code: int = 2,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.exit_code = exit_code
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "error": str(self), **self.details}


@dataclass(frozen=True)
class RepairConfig:
    full_manifest: Path
    failed_listening_evidence: Path
    paid_lock: Path
    private_output_dir: Path
    voice: str = RECOMMENDED_VOICE
    language_code: str = BASE_LANGUAGE_CODE
    speaking_rate: float = RECOMMENDED_SPEAKING_RATE
    pitch: float = RECOMMENDED_PITCH
    usd_per_million_chars: float = 30.0
    run_budget_usd: float = 0.10
    title_budget_usd: float = 8.0
    title_spend_usd: float = 3.47931
    sprint_budget_usd: float = 75.0
    sprint_spend_usd: float = 18.6854
    project_id: str | None = None
    execute: bool = False


ProviderFactory = Callable[[RepairConfig], google_pipeline.TTSProvider]


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


def atomic_write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    temporary.write_bytes(value)
    if mode is not None:
        os.chmod(temporary, mode)
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    atomic_write_bytes(
        path,
        (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8"),
    )


def require(condition: bool, status: str, message: str) -> None:
    if not condition:
        raise BoundedRepairError(status, message)


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BoundedRepairError(
            "BLOCKED_INVALID_EVIDENCE",
            f"{label} is not readable UTF-8 JSON: {path}",
        ) from exc
    require(
        isinstance(payload, dict),
        "BLOCKED_INVALID_EVIDENCE",
        f"{label} must contain one JSON object",
    )
    return payload


def _all_fingerprints(value: Any, key: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _all_fingerprints(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from _all_fingerprints(child, key)
    elif isinstance(value, str) and "fingerprint" in key.lower():
        yield value


def unit_attempt_fingerprint(
    *,
    source_sha256: str,
    input_manifest_sha256: str,
    base_full_manifest_sha256: str,
    text_sha256: str,
    prior_audio_sha256: str,
    voice: str,
    language_code: str,
    speaking_rate: float,
    pitch: float,
) -> str:
    return canonical_sha256(
        {
            "schema_version": REPAIR_BLOCK_SCHEMA,
            "provider": "google",
            "mode": "bounded_chunk_repair",
            "slug": SLUG,
            "source_sha256": source_sha256,
            "input_manifest_sha256": input_manifest_sha256,
            "base_full_manifest_sha256": base_full_manifest_sha256,
            "chunk_index": TARGET_INDEX,
            "unit_id": TARGET_UNIT_ID,
            "text_sha256": text_sha256,
            "prior_audio_sha256": prior_audio_sha256,
            "voice": voice,
            "language_code": language_code,
            "speaking_rate": speaking_rate,
            "pitch": pitch,
            "synthesis_input_kind": SYNTHESIS_INPUT_KIND,
        }
    )


def base_unit_fingerprint() -> str:
    return unit_attempt_fingerprint(
        source_sha256=EXPECTED_SOURCE_SHA256,
        input_manifest_sha256=EXPECTED_INPUT_MANIFEST_SHA256,
        base_full_manifest_sha256=EXPECTED_FULL_MANIFEST_SHA256,
        text_sha256=TARGET_TEXT_SHA256,
        prior_audio_sha256=TARGET_PRIOR_AUDIO_SHA256,
        voice=BASE_VOICE,
        language_code=BASE_LANGUAGE_CODE,
        speaking_rate=BASE_SPEAKING_RATE,
        pitch=BASE_PITCH,
    )


def validate_config(config: RepairConfig) -> Path:
    try:
        output_dir = google_pipeline.validate_private_output_dir(
            config.private_output_dir
        )
    except google_pipeline.PipelineError as exc:
        raise BoundedRepairError(exc.status, str(exc)) from exc
    require(
        config.voice.startswith(f"{config.language_code}-"),
        "BLOCKED_GOOGLE_VOICE",
        "replacement voice locale must match --language-code",
    )
    require(
        config.language_code == BASE_LANGUAGE_CODE,
        "BLOCKED_LANGUAGE_CHANGE",
        "bounded Jekyll repair must remain en-GB",
    )
    require(
        math.isfinite(config.speaking_rate)
        and 0.25 <= config.speaking_rate <= 4.0,
        "BLOCKED_CONFIG",
        "speaking rate must be finite and within the Google contract",
    )
    require(
        math.isfinite(config.pitch) and -20.0 <= config.pitch <= 20.0,
        "BLOCKED_CONFIG",
        "pitch must be finite and within the Google contract",
    )
    require(
        (config.voice, config.speaking_rate, config.pitch)
        != (BASE_VOICE, BASE_SPEAKING_RATE, BASE_PITCH),
        "BLOCKED_DUPLICATE_SETTINGS",
        "repair must not repeat the same voice, rate, pitch, and text",
    )
    return output_dir


def validate_failed_listening(
    path: Path,
    evidence: candidate_qa.CandidateEvidence,
) -> dict[str, Any]:
    require(
        sha256_file(path) == EXPECTED_FAILED_LISTENING_SHA256,
        "BLOCKED_LISTENING_EVIDENCE_HASH",
        "failed listening evidence does not match the retained Jekyll review",
    )
    payload = read_json(path, "failed listening evidence")
    require(
        payload.get("status") == "BLOCKED_LISTENING_QA",
        "BLOCKED_LISTENING_EVIDENCE_STATE",
        "input listening evidence must be the blocked full-candidate result",
    )
    for field, expected in {
        "slug": SLUG,
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "input_manifest_sha256": EXPECTED_INPUT_MANIFEST_SHA256,
        "full_manifest_sha256": EXPECTED_FULL_MANIFEST_SHA256,
        "candidate_audio_sequence_sha256": EXPECTED_BASE_AUDIO_SEQUENCE_SHA256,
        "candidate_binding_sha256": EXPECTED_BASE_CANDIDATE_BINDING_SHA256,
    }.items():
        require(
            payload.get(field) == expected,
            "BLOCKED_LISTENING_EVIDENCE_BINDING",
            f"failed listening evidence changed at {field}",
        )
    require(
        payload.get("candidate_binding_sha256")
        == evidence.candidate_binding_sha256,
        "BLOCKED_LISTENING_EVIDENCE_BINDING",
        "failed listening evidence is not bound to the validated base candidate",
    )
    listening = (
        (payload.get("listening_quality_report") or {}).get("listening_quality")
        or {}
    )
    samples = listening.get("samples")
    require(
        isinstance(samples, list) and len(samples) == 6,
        "BLOCKED_LISTENING_EVIDENCE_STATE",
        "exactly six listening samples are required",
    )
    sample_by_unit = {
        str(sample.get("unit_id") or ""): sample
        for sample in samples
        if isinstance(sample, dict)
    }
    require(
        set(sample_by_unit)
        == {
            "chunk_0000",
            "chunk_0018",
            TARGET_UNIT_ID,
            "chunk_0041",
            "chunk_0045",
            "chunk_0091",
        },
        "BLOCKED_LISTENING_EVIDENCE_STATE",
        "deterministic six-sample selection changed",
    )
    for unit_id, sample in sample_by_unit.items():
        flags = sample.get("judge_flags") or {}
        require(
            all(flags.get(flag) is False for flag in FATAL_FLAGS),
            "BLOCKED_FATAL_LISTENING_FLAG",
            f"{unit_id} contains a fatal listening flag",
        )
        scores = sample.get("scores") or {}
        if unit_id == TARGET_UNIT_ID:
            require(
                sample.get("section_index") == TARGET_INDEX
                and sample.get("source_text_sha256") == TARGET_TEXT_SHA256
                and sample.get("sample_audio_hash") == TARGET_PRIOR_AUDIO_SHA256
                and float(scores.get("overall_listening_score") or 0.0) == 8.4
                and float(scores.get("confidence_score") or 0.0) == 0.90,
                "BLOCKED_TARGET_EVIDENCE_MISMATCH",
                "chunk_0036 is not the exact retained low-scoring sample",
            )
        else:
            require(
                float(scores.get("overall_listening_score") or 0.0) >= 9.4
                and float(scores.get("confidence_score") or 0.0) >= 0.95,
                "BLOCKED_MULTI_CHUNK_REPAIR",
                f"{unit_id} does not support a one-chunk-only repair",
            )
    return payload


def validate_bound_inputs(
    config: RepairConfig,
    *,
    duration_probe: Callable[[Path], float] = candidate_qa.ffprobe_duration,
) -> tuple[candidate_qa.CandidateEvidence, dict[str, Any], dict[str, Any]]:
    full_manifest = config.full_manifest.expanduser().resolve()
    listening_path = config.failed_listening_evidence.expanduser().resolve()
    require(
        sha256_file(full_manifest) == EXPECTED_FULL_MANIFEST_SHA256,
        "BLOCKED_FULL_MANIFEST_HASH",
        "full manifest is not the exact retained Jekyll candidate",
    )
    try:
        evidence = candidate_qa.validate_full_candidate(
            full_manifest,
            duration_probe=duration_probe,
        )
    except candidate_qa.CandidateQAError as exc:
        raise BoundedRepairError(exc.code, str(exc)) from exc
    manifest = evidence.manifest
    for observed, expected, label in (
        (manifest.get("slug"), SLUG, "slug"),
        (manifest.get("title"), TITLE, "title"),
        (manifest.get("author"), AUTHOR, "author"),
        (evidence.source_sha256, EXPECTED_SOURCE_SHA256, "source SHA-256"),
        (
            evidence.input_manifest_sha256,
            EXPECTED_INPUT_MANIFEST_SHA256,
            "input manifest SHA-256",
        ),
        (
            manifest.get("attempt_fingerprint"),
            EXPECTED_BASE_ATTEMPT_FINGERPRINT,
            "base attempt fingerprint",
        ),
        (manifest.get("voice"), BASE_VOICE, "base voice"),
        (manifest.get("language_code"), BASE_LANGUAGE_CODE, "base language"),
        (float(manifest.get("speaking_rate")), BASE_SPEAKING_RATE, "base rate"),
        (float(manifest.get("pitch")), BASE_PITCH, "base pitch"),
        (len(evidence.records), EXPECTED_UNIT_COUNT, "unit count"),
        (
            evidence.candidate_audio_sequence_sha256,
            EXPECTED_BASE_AUDIO_SEQUENCE_SHA256,
            "base audio sequence",
        ),
        (
            evidence.candidate_binding_sha256,
            EXPECTED_BASE_CANDIDATE_BINDING_SHA256,
            "base candidate binding",
        ),
    ):
        require(
            observed == expected,
            "BLOCKED_BASE_CANDIDATE_BINDING",
            f"retained candidate changed at {label}",
        )
    target = evidence.records[TARGET_INDEX]
    for observed, expected, label in (
        (target.get("unit_id"), TARGET_UNIT_ID, "target unit ID"),
        (target.get("text_sha256"), TARGET_TEXT_SHA256, "target text SHA-256"),
        (
            target.get("audio_sha256"),
            TARGET_PRIOR_AUDIO_SHA256,
            "target prior audio SHA-256",
        ),
        (
            target.get("audio_size_bytes"),
            TARGET_PRIOR_AUDIO_SIZE_BYTES,
            "target prior audio size",
        ),
    ):
        require(
            observed == expected,
            "BLOCKED_TARGET_BINDING",
            f"retained target changed at {label}",
        )
    listening = validate_failed_listening(listening_path, evidence)
    return evidence, listening, target


def budget_guard(config: RepairConfig, character_count: int) -> dict[str, Any]:
    values = {
        "usd_per_million_chars": config.usd_per_million_chars,
        "run_budget_usd": config.run_budget_usd,
        "title_budget_usd": config.title_budget_usd,
        "title_spend_usd": config.title_spend_usd,
        "sprint_budget_usd": config.sprint_budget_usd,
        "sprint_spend_usd": config.sprint_spend_usd,
    }
    for name, value in values.items():
        require(
            math.isfinite(value) and value >= 0,
            "BLOCKED_BUDGET",
            f"{name} must be finite and nonnegative",
        )
    require(
        config.usd_per_million_chars > 0
        and config.run_budget_usd > 0
        and config.title_budget_usd > 0
        and config.sprint_budget_usd > 0,
        "BLOCKED_BUDGET",
        "price and budget caps must be positive",
    )
    estimate = round(
        character_count / 1_000_000 * config.usd_per_million_chars, 6
    )
    projected_title = round(config.title_spend_usd + estimate, 6)
    projected_sprint = round(config.sprint_spend_usd + estimate, 6)
    blockers: list[str] = []
    if estimate > config.run_budget_usd:
        blockers.append("estimated repair exceeds run cap")
    if projected_title > config.title_budget_usd:
        blockers.append("projected title spend exceeds title cap")
    if projected_sprint > config.sprint_budget_usd:
        blockers.append("projected sprint spend exceeds sprint cap")
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


def reject_repeated_fingerprint(
    output_dir: Path,
    fingerprint: str,
) -> Path:
    require(
        fingerprint != base_unit_fingerprint(),
        "BLOCKED_DUPLICATE_FINGERPRINT",
        "repair fingerprint repeats the failed base unit settings",
    )
    state_path = output_dir / SLUG / "repair_attempts" / f"{fingerprint}.json"
    if state_path.is_file():
        prior = read_json(state_path, "prior repair state")
        require(
            not (
                prior.get("attempt_fingerprint") == fingerprint
                and prior.get("provider_calls_ran") is True
            ),
            "BLOCKED_DUPLICATE_FINGERPRINT",
            "this exact repair fingerprint already reached Google",
        )
    for registry in NO_REPEAT_REGISTRIES:
        if registry.is_file():
            known = set(_all_fingerprints(read_json(registry, "fingerprint registry")))
            require(
                fingerprint not in known,
                "BLOCKED_DUPLICATE_FINGERPRINT",
                f"repair fingerprint is already closed in {registry}",
            )
    return state_path


def next_exact_command(config: RepairConfig, *, execute: bool) -> str:
    parts = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--full-manifest",
        str(config.full_manifest),
        "--failed-listening-evidence",
        str(config.failed_listening_evidence),
        "--paid-lock",
        str(config.paid_lock),
        "--private-output-dir",
        str(config.private_output_dir),
        "--voice",
        config.voice,
        "--language-code",
        config.language_code,
        "--speaking-rate",
        str(config.speaking_rate),
        "--pitch",
        str(config.pitch),
        "--usd-per-million-chars",
        str(config.usd_per_million_chars),
        "--run-budget-usd",
        str(config.run_budget_usd),
        "--title-budget-usd",
        str(config.title_budget_usd),
        "--title-spend-usd",
        str(config.title_spend_usd),
        "--sprint-budget-usd",
        str(config.sprint_budget_usd),
        "--sprint-spend-usd",
        str(config.sprint_spend_usd),
    ]
    if config.project_id:
        parts.extend(["--project-id", config.project_id])
    if execute:
        parts.append("--execute")
    return " ".join(shlex.quote(part) for part in parts)


def _validate_runtime(config: RepairConfig) -> None:
    errors: list[str] = []
    if os.environ.get(APPROVAL_ENV, "").strip().lower() != "true":
        errors.append(f"{APPROVAL_ENV}=true is required")
    if os.environ.get(STOP_ON_BUDGET_ENV, "").strip().lower() != "true":
        errors.append(f"{STOP_ON_BUDGET_ENV}=true is required")
    if not (config.project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")):
        errors.append("GOOGLE_CLOUD_PROJECT or --project-id is required")
    if errors:
        raise BoundedRepairError(
            "BLOCKED_RUNTIME_GATES",
            "explicit one-chunk paid runtime approval is incomplete",
            details={"errors": errors, "provider_calls_ran": False},
        )


def _default_provider_factory(
    config: RepairConfig,
) -> google_pipeline.TTSProvider:
    return google_pipeline.GoogleCloudTTSProvider(
        config.project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
    )


def _acquired_lock(
    original: Mapping[str, Any],
    *,
    config: RepairConfig,
    fingerprint: str,
    budget: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(original)
    payload.update(
        {
            "current_holder": (
                "sprint1_jekyll_google_chunk36_bounded_repair:"
                f"{SLUG}:{TARGET_UNIT_ID}"
            ),
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "allowed_slugs": [SLUG],
            "budget_cap_usd": config.run_budget_usd,
            "estimated_cost_usd": budget["estimated_run_usd"],
            "approved_scope": (
                "One private Google synthesis call for jekyll-and-hyde "
                "chunk_0036 only; exact source and prior audio binding; "
                f"fingerprint {fingerprint}; no upload, publication, or gate mutation."
            ),
            "stop_conditions": [
                "Any exact source, manifest, listening, audio, lock, or budget binding fails",
                "The exact repair fingerprint already reached Google",
                "Google returns empty or non-MP3 audio",
                "Any output path is public or release-facing",
                "Any upload, publication, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def _copy_verified(source: Path, target: Path, expected_sha256: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    require(
        sha256_file(target) == expected_sha256,
        "BLOCKED_COPY_HASH_MISMATCH",
        f"private candidate copy changed bytes: {target.name}",
    )


def _build_replacement_manifest(
    *,
    config: RepairConfig,
    evidence: candidate_qa.CandidateEvidence,
    fingerprint: str,
    replacement_audio_path: Path,
    replacement_audio_sha256: str,
    replacement_audio_size_bytes: int,
    budget: Mapping[str, Any],
    output_dir: Path,
    duration_probe: Callable[[Path], float],
) -> tuple[Path, candidate_qa.CandidateEvidence]:
    base_hashes = [str(record["audio_sha256"]) for record in evidence.records]
    new_hashes = list(base_hashes)
    new_hashes[TARGET_INDEX] = replacement_audio_sha256
    sequence_sha256 = candidate_qa.sha256_json(new_hashes)
    candidate_id = canonical_sha256(
        {
            "repair_attempt_fingerprint": fingerprint,
            "ordered_audio_hashes": new_hashes,
        }
    )
    run_dir = output_dir / SLUG / "repaired_full" / candidate_id[:16]
    require(
        not run_dir.exists(),
        "BLOCKED_IMMUTABLE_OUTPUT_EXISTS",
        "replacement candidate directory already exists",
    )
    source_copy = run_dir / "sanitized_source.txt"
    input_copy = run_dir / "input_manifest.json"
    _copy_verified(evidence.source_path, source_copy, evidence.source_sha256)
    _copy_verified(
        evidence.input_manifest_path,
        input_copy,
        evidence.input_manifest_sha256,
    )

    generated_audio: list[dict[str, Any]] = []
    preserved = 0
    for index, record in enumerate(evidence.records):
        destination = run_dir / "audio" / f"chunk_{index:04d}.mp3"
        if index == TARGET_INDEX:
            _copy_verified(
                replacement_audio_path,
                destination,
                replacement_audio_sha256,
            )
            updated = {
                key: value
                for key, value in record.items()
                if key not in {"source_text", "measured_duration_seconds"}
            }
            updated.update(
                {
                    "audio_path": str(destination),
                    "audio_sha256": replacement_audio_sha256,
                    "audio_size_bytes": replacement_audio_size_bytes,
                }
            )
        else:
            _copy_verified(
                Path(str(record["audio_path"])),
                destination,
                str(record["audio_sha256"]),
            )
            preserved += 1
            updated = {
                key: value
                for key, value in record.items()
                if key not in {"source_text", "measured_duration_seconds"}
            }
            updated["audio_path"] = str(destination)
        generated_audio.append(updated)

    require(
        preserved == EXPECTED_UNIT_COUNT - 1,
        "BLOCKED_PRESERVATION_COUNT",
        "replacement candidate did not preserve exactly 91 chunks",
    )
    differences = [
        index
        for index, (before, after) in enumerate(zip(base_hashes, new_hashes))
        if before != after
    ]
    require(
        differences == [TARGET_INDEX],
        "BLOCKED_MULTI_CHUNK_REPAIR",
        "replacement candidate changed more than chunk_0036",
    )

    manifest_path = run_dir / "full_generation_manifest.json"
    repair_block = {
        "schema_version": REPAIR_BLOCK_SCHEMA,
        "status": "PRIVATE_REPLACEMENT_CANDIDATE_QA_PENDING",
        "slug": SLUG,
        "source_sha256": evidence.source_sha256,
        "input_manifest_sha256": evidence.input_manifest_sha256,
        "base_full_manifest_path": str(evidence.manifest_path),
        "base_full_manifest_sha256": evidence.manifest_sha256,
        "base_attempt_fingerprint": EXPECTED_BASE_ATTEMPT_FINGERPRINT,
        "failed_listening_evidence_path": str(
            config.failed_listening_evidence.expanduser().resolve()
        ),
        "failed_listening_evidence_sha256": EXPECTED_FAILED_LISTENING_SHA256,
        "base_candidate_audio_sequence_sha256": (
            evidence.candidate_audio_sequence_sha256
        ),
        "base_candidate_binding_sha256": evidence.candidate_binding_sha256,
        "repair_attempt_fingerprint": fingerprint,
        "chunk_index": TARGET_INDEX,
        "unit_id": TARGET_UNIT_ID,
        "text_sha256": TARGET_TEXT_SHA256,
        "prior_audio_sha256": TARGET_PRIOR_AUDIO_SHA256,
        "replacement_audio_sha256": replacement_audio_sha256,
        "replacement_voice": config.voice,
        "replacement_language_code": config.language_code,
        "replacement_speaking_rate": config.speaking_rate,
        "replacement_pitch": config.pitch,
        "synthesis_input_kind": SYNTHESIS_INPUT_KIND,
        "base_ordered_audio_hashes": base_hashes,
        "candidate_audio_sequence_sha256": sequence_sha256,
        "preserved_audio_file_count": preserved,
        "replacement_audio_file_count": 1,
        "changed_chunk_indexes": differences,
        "full_source_text_changed": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
    }
    manifest = {
        **evidence.manifest,
        "status": "FULL_GENERATION_PRIVATE_QA_PENDING",
        "started_at": iso_now(),
        "finished_at": iso_now(),
        "result_manifest_path": str(manifest_path),
        "private_run_dir": str(run_dir),
        "sanitized_source_copy": str(source_copy),
        "input_manifest_copy": str(input_copy),
        "generated_audio": generated_audio,
        "candidate_audio_sequence_sha256": sequence_sha256,
        "bounded_chunk_repair": repair_block,
        "repair_budget": dict(budget),
        "provider_calls_ran": True,
        "synthesis_calls": EXPECTED_UNIT_COUNT,
        "repair_synthesis_calls": 1,
        "total_provider_calls_across_lineage": EXPECTED_UNIT_COUNT + 1,
        "actual_provider_billing": "NOT_REPORTED",
        "public_release_approved": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "errors": [],
    }
    atomic_write_json(manifest_path, manifest)
    try:
        repaired = candidate_qa.validate_full_candidate(
            manifest_path,
            duration_probe=duration_probe,
        )
    except candidate_qa.CandidateQAError as exc:
        raise BoundedRepairError(exc.code, str(exc)) from exc
    require(
        repaired.candidate_audio_sequence_sha256 == sequence_sha256,
        "BLOCKED_REPLACEMENT_SEQUENCE_BINDING",
        "recalculated replacement audio sequence does not match the manifest",
    )
    return manifest_path, repaired


def run(
    config: RepairConfig,
    *,
    provider_factory: ProviderFactory | None = None,
    duration_probe: Callable[[Path], float] = candidate_qa.ffprobe_duration,
) -> dict[str, Any]:
    output_dir = validate_config(config)
    evidence, _listening, target = validate_bound_inputs(
        config,
        duration_probe=duration_probe,
    )
    budget = budget_guard(config, int(target["characters"]))
    require(
        budget["status"] == "PASS",
        "BLOCKED_BUDGET",
        "; ".join(budget["blockers"]),
    )
    fingerprint = unit_attempt_fingerprint(
        source_sha256=evidence.source_sha256,
        input_manifest_sha256=evidence.input_manifest_sha256,
        base_full_manifest_sha256=evidence.manifest_sha256,
        text_sha256=str(target["text_sha256"]),
        prior_audio_sha256=str(target["audio_sha256"]),
        voice=config.voice,
        language_code=config.language_code,
        speaking_rate=config.speaking_rate,
        pitch=config.pitch,
    )
    state_path = reject_repeated_fingerprint(output_dir, fingerprint)
    preflight = {
        "schema_version": SCHEMA,
        "status": "PREFLIGHT_PASS_PRIVATE_ONE_CHUNK_ONLY",
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "source_sha256": evidence.source_sha256,
        "input_manifest_sha256": evidence.input_manifest_sha256,
        "base_full_manifest_sha256": evidence.manifest_sha256,
        "base_attempt_fingerprint": EXPECTED_BASE_ATTEMPT_FINGERPRINT,
        "base_candidate_audio_sequence_sha256": (
            evidence.candidate_audio_sequence_sha256
        ),
        "base_candidate_binding_sha256": evidence.candidate_binding_sha256,
        "failed_listening_evidence_sha256": EXPECTED_FAILED_LISTENING_SHA256,
        "repair_attempt_fingerprint": fingerprint,
        "base_unit_fingerprint": base_unit_fingerprint(),
        "target": {
            "chunk_index": TARGET_INDEX,
            "unit_id": TARGET_UNIT_ID,
            "text_sha256": TARGET_TEXT_SHA256,
            "prior_audio_sha256": TARGET_PRIOR_AUDIO_SHA256,
            "characters": target["characters"],
            "retained_listening_score": 8.4,
            "retained_listening_confidence": 0.90,
            "retained_fatal_flags": [],
        },
        "replacement": {
            "provider": "google",
            "voice": config.voice,
            "language_code": config.language_code,
            "speaking_rate": config.speaking_rate,
            "pitch": config.pitch,
            "synthesis_input_kind": SYNTHESIS_INPUT_KIND,
            "exact_source_text": True,
            "rationale": (
                "Preserve the Charon narrator identity while increasing rate "
                "from 0.94 to 1.00 for more engaged emotionally intense dialogue; "
                "do not introduce a one-chunk voice discontinuity or SSML text drift."
            ),
        },
        "budget": budget,
        "preserved_audio_file_count": EXPECTED_UNIT_COUNT - 1,
        "replacement_audio_file_count": 1,
        "private_output_only": True,
        "provider_calls_ran": False,
        "synthesis_calls": 0,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "public_release_approved": False,
        "paid_lock_touched": False,
        "next_exact_command": next_exact_command(config, execute=True),
    }
    if not config.execute:
        return preflight

    _validate_runtime(config)
    lock_path = config.paid_lock.expanduser().resolve()
    original_lock = lock_path.read_bytes()
    try:
        parsed_lock = google_pipeline.validate_paid_lock(original_lock)
    except google_pipeline.PipelineError as exc:
        raise BoundedRepairError(exc.status, str(exc)) from exc

    repair_dir = output_dir / SLUG / "chunk_repairs" / fingerprint[:16]
    require(
        not repair_dir.exists(),
        "BLOCKED_IMMUTABLE_OUTPUT_EXISTS",
        "repair output directory already exists",
    )
    replacement_audio = repair_dir / "source_audio" / f"{TARGET_UNIT_ID}.mp3"
    state = {
        **preflight,
        "status": "PROVIDER_READY_PENDING_ONE_SYNTHESIS",
        "provider_calls_ran": False,
        "started_at": iso_now(),
    }
    atomic_write_json(state_path, state)
    acquired = _acquired_lock(
        parsed_lock,
        config=config,
        fingerprint=fingerprint,
        budget=budget,
    )
    lock_sha256_before = sha256_bytes(original_lock)
    provider_calls = 0
    execution_error: Exception | None = None
    replacement_bytes = b""
    try:
        atomic_write_json(lock_path, acquired)
        provider = (provider_factory or _default_provider_factory)(config)
        ensure_voice = getattr(provider, "ensure_voice", None)
        if callable(ensure_voice):
            ensure_voice(voice=config.voice, language_code=config.language_code)
        state.update(
            {"status": "PROVIDER_CALL_STARTED", "provider_calls_ran": True}
        )
        atomic_write_json(state_path, state)
        replacement_bytes = bytes(
            provider.synthesize(
                text=str(target["source_text"]),
                voice=config.voice,
                language_code=config.language_code,
                speaking_rate=config.speaking_rate,
                pitch=config.pitch,
            )
        )
        provider_calls = 1
        require(
            bool(replacement_bytes)
            and (
                replacement_bytes.startswith(b"ID3")
                or replacement_bytes.startswith(b"\xff")
            ),
            "PROVIDER_EXECUTION_FAILED",
            "Google returned empty or non-MP3 replacement audio",
        )
        atomic_write_bytes(replacement_audio, replacement_bytes)
    except Exception as exc:  # noqa: BLE001
        execution_error = exc
    finally:
        try:
            atomic_write_bytes(lock_path, original_lock)
        except Exception as restore_exc:  # noqa: BLE001
            execution_error = BoundedRepairError(
                "PAID_LOCK_RESTORE_FAILED",
                f"paid lock restoration failed: {restore_exc}",
                exit_code=7,
            )

    lock_after = lock_path.read_bytes()
    lock_restored = lock_after == original_lock
    if not lock_restored:
        execution_error = BoundedRepairError(
            "PAID_LOCK_RESTORE_FAILED",
            "paid lock was not restored byte-for-byte",
            exit_code=7,
        )
    if execution_error is not None:
        state.update(
            {
                "status": "PROVIDER_FAILED_PRIVATE_ONLY",
                "finished_at": iso_now(),
                "provider_calls_ran": provider_calls > 0,
                "synthesis_calls": provider_calls,
                "paid_lock_touched": True,
                "paid_lock_restored_byte_for_byte": lock_restored,
                "paid_lock_sha256_before": lock_sha256_before,
                "paid_lock_sha256_after": sha256_bytes(lock_after),
                "errors": [
                    f"{type(execution_error).__name__}: {execution_error}"
                ],
            }
        )
        atomic_write_json(state_path, state)
        if isinstance(execution_error, BoundedRepairError):
            raise execution_error
        raise BoundedRepairError(
            "PROVIDER_EXECUTION_FAILED",
            f"private one-chunk Google repair failed: {execution_error}",
            exit_code=6,
            details={"provider_calls_ran": provider_calls > 0},
        ) from execution_error

    replacement_sha256 = sha256_bytes(replacement_bytes)
    require(
        replacement_sha256 != TARGET_PRIOR_AUDIO_SHA256,
        "BLOCKED_IDENTICAL_REPLACEMENT_AUDIO",
        "Google replacement bytes are identical to the rejected chunk",
    )
    manifest_path, repaired = _build_replacement_manifest(
        config=config,
        evidence=evidence,
        fingerprint=fingerprint,
        replacement_audio_path=replacement_audio,
        replacement_audio_sha256=replacement_sha256,
        replacement_audio_size_bytes=len(replacement_bytes),
        budget=budget,
        output_dir=output_dir,
        duration_probe=duration_probe,
    )
    result = {
        **preflight,
        "status": "REPLACEMENT_FULL_CANDIDATE_PRIVATE_QA_PENDING",
        "finished_at": iso_now(),
        "provider_calls_ran": True,
        "synthesis_calls": 1,
        "replacement_audio_path": str(replacement_audio),
        "replacement_audio_sha256": replacement_sha256,
        "replacement_audio_size_bytes": len(replacement_bytes),
        "replacement_full_manifest_path": str(manifest_path),
        "replacement_full_manifest_sha256": sha256_file(manifest_path),
        "candidate_audio_sequence_sha256": (
            repaired.candidate_audio_sequence_sha256
        ),
        "candidate_binding_sha256": repaired.candidate_binding_sha256,
        "preserved_audio_hashes_verified": True,
        "changed_chunk_indexes": [TARGET_INDEX],
        "paid_lock_touched": True,
        "paid_lock_restored_byte_for_byte": True,
        "paid_lock_sha256_before": lock_sha256_before,
        "paid_lock_sha256_after": sha256_bytes(lock_after),
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "public_release_approved": False,
        "next_exact_command": (
            f"{shlex.quote(sys.executable)} "
            f"{shlex.quote(str(SCRIPT_DIR / 'sprint1_google_english_full_audio_derived_qa.py'))} "
            f"--full-manifest {shlex.quote(str(manifest_path))} "
            f"--output {shlex.quote(str(manifest_path.with_name('full_audio_derived_asr_sync_qa.json')))}"
        ),
        "incremental_listening_command_after_objective_pass": (
            f"{shlex.quote(sys.executable)} "
            f"{shlex.quote(str(SCRIPT_DIR / 'sprint1_jekyll_google_chunk36_incremental_listening_qa.py'))} "
            f"--replacement-full-manifest {shlex.quote(str(manifest_path))} "
            f"--audio-derived-qa {shlex.quote(str(manifest_path.with_name('full_audio_derived_asr_sync_qa.json')))} "
            f"--prior-listening-evidence "
            f"{shlex.quote(str(config.failed_listening_evidence.expanduser().resolve()))} "
            f"--paid-lock {shlex.quote(str(config.paid_lock.expanduser().resolve()))} "
            f"--output {shlex.quote(str(manifest_path.with_name('incremental_six_sample_listening_qa.json')))}"
        ),
    }
    evidence_path = manifest_path.with_name("bounded_chunk_repair_evidence.json")
    result["repair_evidence_path"] = str(evidence_path)
    atomic_write_json(evidence_path, result)
    state.update(
        {
            "status": result["status"],
            "finished_at": result["finished_at"],
            "provider_calls_ran": True,
            "synthesis_calls": 1,
            "replacement_audio_sha256": replacement_sha256,
            "replacement_full_manifest_sha256": result[
                "replacement_full_manifest_sha256"
            ],
            "candidate_binding_sha256": result["candidate_binding_sha256"],
            "paid_lock_restored_byte_for_byte": True,
        }
    )
    atomic_write_json(state_path, state)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-manifest", required=True, type=Path)
    parser.add_argument("--failed-listening-evidence", required=True, type=Path)
    parser.add_argument("--paid-lock", required=True, type=Path)
    parser.add_argument("--private-output-dir", required=True, type=Path)
    parser.add_argument("--voice", default=RECOMMENDED_VOICE)
    parser.add_argument("--language-code", default=BASE_LANGUAGE_CODE)
    parser.add_argument("--speaking-rate", type=float, default=RECOMMENDED_SPEAKING_RATE)
    parser.add_argument("--pitch", type=float, default=RECOMMENDED_PITCH)
    parser.add_argument("--usd-per-million-chars", type=float, default=30.0)
    parser.add_argument("--run-budget-usd", type=float, default=0.10)
    parser.add_argument("--title-budget-usd", type=float, default=8.0)
    parser.add_argument("--title-spend-usd", type=float, default=3.47931)
    parser.add_argument("--sprint-budget-usd", type=float, default=75.0)
    parser.add_argument("--sprint-spend-usd", type=float, default=18.6854)
    parser.add_argument("--project-id")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Acquire paid_tts.lock and make exactly one private Google call",
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> RepairConfig:
    return RepairConfig(
        full_manifest=args.full_manifest,
        failed_listening_evidence=args.failed_listening_evidence,
        paid_lock=args.paid_lock,
        private_output_dir=args.private_output_dir,
        voice=args.voice,
        language_code=args.language_code,
        speaking_rate=args.speaking_rate,
        pitch=args.pitch,
        usd_per_million_chars=args.usd_per_million_chars,
        run_budget_usd=args.run_budget_usd,
        title_budget_usd=args.title_budget_usd,
        title_spend_usd=args.title_spend_usd,
        sprint_budget_usd=args.sprint_budget_usd,
        sprint_spend_usd=args.sprint_spend_usd,
        project_id=args.project_id,
        execute=args.execute,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        result = run(config_from_args(parse_args(argv)))
    except BoundedRepairError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return exc.exit_code
    except (OSError, ValueError) as exc:
        error = BoundedRepairError("BLOCKED_INPUT", str(exc))
        print(json.dumps(error.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return error.exit_code
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
