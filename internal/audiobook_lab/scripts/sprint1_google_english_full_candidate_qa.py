#!/usr/bin/env python3
"""Fail-closed QA for one private Google English full-candidate manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

import sprint1_google_english_private_pipeline as pipeline  # noqa: E402
from asr_sync_hook import (  # noqa: E402
    BINARY_LISTENING_FLAGS,
    LISTENING_QA_HOOK_VERSION,
    LISTENING_QA_RUBRIC_VERSION,
    LISTENING_QA_SCHEMA_VERSION,
    LISTENING_THRESHOLDS,
    evaluate_listening_evidence,
    judge_audio_sample_with_openai,
    openai_listening_qa_budget_guard,
    validate_listening_quality_report,
)


QA_SCHEMA_VERSION = 1
LISTENING_SAMPLE_COUNT = 6
ALLOWED_ENGLISH_POLICIES = {
    "schema3_universal_9_7",
    "tiered_audiobook_acceptance_v1",
}
CAP_ENV_NAMES = (
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD",
    "MAX_TTS_BUDGET_USD",
    "EARNALISM_PRIOR_ESTIMATED_SPEND_USD",
)


class CandidateQAError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

    @property
    def blocker(self) -> str:
        return f"{self.code}: {self}"


@dataclass(frozen=True)
class CandidateEvidence:
    manifest: dict[str, Any]
    manifest_path: Path
    manifest_sha256: str
    source_path: Path
    source_sha256: str
    input_manifest_path: Path
    input_manifest_sha256: str
    records: list[dict[str, Any]]
    measured_sync: dict[str, Any]
    construction: dict[str, Any]
    candidate_audio_sequence_sha256: str
    candidate_binding_sha256: str


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateQAError(
            "INVALID_JSON_EVIDENCE", f"{label} is not readable UTF-8 JSON: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise CandidateQAError(
            "INVALID_JSON_EVIDENCE", f"{label} must contain one JSON object"
        )
    return payload


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise CandidateQAError(code, message)


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_run_artifact(value: Any, run_dir: Path, label: str) -> Path:
    require(bool(str(value or "").strip()), "MISSING_ARTIFACT", f"{label} path is missing")
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        run_relative = (run_dir / path).resolve()
        root_relative = (ROOT / path).resolve()
        path = run_relative if run_relative.exists() else root_relative
    else:
        path = path.resolve()
    require(
        is_within(path, run_dir),
        "NON_PRIVATE_ARTIFACT",
        f"{label} must remain inside the private full-candidate run directory",
    )
    require(path.is_file(), "MISSING_ARTIFACT", f"{label} does not exist: {path}")
    return path


def ffprobe_duration(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        raise CandidateQAError(
            "MEASURED_SYNC_UNAVAILABLE",
            f"ffprobe could not measure {path.name}: {completed.stderr.strip()}",
        )
    try:
        duration = float(completed.stdout.strip())
    except ValueError as exc:
        raise CandidateQAError(
            "MEASURED_SYNC_UNAVAILABLE",
            f"ffprobe returned an invalid duration for {path.name}",
        ) from exc
    return duration


def flattened_source(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def boundary_words(text: str, *, start: bool, count: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    return words[:count] if start else words[-count:]


def validate_manifest_state(manifest: dict[str, Any]) -> None:
    require(
        manifest.get("status") == "FULL_GENERATION_PRIVATE_QA_PENDING",
        "FULL_MANIFEST_NOT_READY",
        "full manifest status must be FULL_GENERATION_PRIVATE_QA_PENDING",
    )
    require(manifest.get("mode") == "full", "FULL_MANIFEST_NOT_READY", "manifest mode must be full")
    require(manifest.get("provider") == "google", "PROVIDER_MISMATCH", "provider must be google")
    require(
        str(manifest.get("language_code") or "").startswith("en-"),
        "LANGUAGE_MISMATCH",
        "full candidate must use an English language code",
    )
    require(manifest.get("private_output_only") is True, "PUBLIC_OUTPUT_BLOCKED", "private_output_only must be true")
    require(manifest.get("public_release_approved") is False, "PUBLIC_OUTPUT_BLOCKED", "public release must remain unapproved")
    for field in ("upload_performed", "publication_performed", "release_mutation_performed"):
        require(manifest.get(field) is False, "PUBLIC_OUTPUT_BLOCKED", f"{field} must be false")
    require(
        manifest.get("paid_lock_restored_byte_for_byte") is True,
        "PAID_LOCK_EVIDENCE_FAILED",
        "paid lock restoration evidence must pass before QA",
    )
    require(manifest.get("provider_calls_ran") is True, "FULL_MANIFEST_NOT_READY", "full TTS provider evidence is missing")
    require(not manifest.get("errors"), "FULL_MANIFEST_NOT_READY", "full TTS manifest contains provider errors")


def reconstruct_segments(source: str, generated: list[dict[str, Any]]) -> list[str]:
    normalized = flattened_source(source)
    require(bool(normalized), "EMPTY_SOURCE", "sanitized source is empty")
    segments: list[str] = []
    cursor = 0
    for index, record in enumerate(generated):
        characters = record.get("characters")
        require(
            isinstance(characters, int) and not isinstance(characters, bool) and characters > 0,
            "CONSTRUCTION_COVERAGE_FAILED",
            f"chunk_{index:04d} has an invalid character count",
        )
        end = cursor + characters
        require(
            end <= len(normalized),
            "CONSTRUCTION_COVERAGE_FAILED",
            f"chunk_{index:04d} extends beyond the sanitized source",
        )
        segment = normalized[cursor:end]
        require(
            pipeline.sha256_text(segment) == record.get("text_sha256"),
            "CONSTRUCTION_ORDER_FAILED",
            f"chunk_{index:04d} text hash does not match the next source segment",
        )
        segments.append(segment)
        cursor = end
        if index < len(generated) - 1:
            require(
                normalized[cursor : cursor + 1] == " ",
                "CONSTRUCTION_COVERAGE_FAILED",
                f"chunk_{index:04d} boundary does not align with normalized source whitespace",
            )
            cursor += 1
    require(
        cursor == len(normalized),
        "CONSTRUCTION_COVERAGE_FAILED",
        "ordered TTS chunks do not cover the complete sanitized source",
    )
    return segments


def validate_full_candidate(
    manifest_path: Path,
    *,
    duration_probe: Callable[[Path], float] = ffprobe_duration,
) -> CandidateEvidence:
    manifest_path = manifest_path.expanduser().resolve()
    require(manifest_path.is_file(), "MISSING_FULL_MANIFEST", f"full manifest does not exist: {manifest_path}")
    manifest = read_json_object(manifest_path, "full candidate manifest")
    validate_manifest_state(manifest)
    run_dir = manifest_path.parent

    declared_result = resolve_run_artifact(
        manifest.get("result_manifest_path"), run_dir, "result_manifest_path"
    )
    require(
        declared_result == manifest_path,
        "FULL_MANIFEST_BINDING_FAILED",
        "result_manifest_path does not identify the consumed manifest",
    )
    source_path = resolve_run_artifact(
        manifest.get("sanitized_source_copy"), run_dir, "sanitized_source_copy"
    )
    input_manifest_path = resolve_run_artifact(
        manifest.get("input_manifest_copy"), run_dir, "input_manifest_copy"
    )

    source_sha256 = sha256_file(source_path)
    input_manifest_sha256 = sha256_file(input_manifest_path)
    require(
        source_sha256 == manifest.get("source_sha256"),
        "SOURCE_HASH_MISMATCH",
        "sanitized source bytes do not match the full manifest",
    )
    require(
        input_manifest_sha256 == manifest.get("input_manifest_sha256"),
        "INPUT_MANIFEST_HASH_MISMATCH",
        "input manifest bytes do not match the full manifest",
    )
    try:
        source_bundle = pipeline.load_source_bundle(source_path, input_manifest_path)
    except pipeline.PipelineError as exc:
        raise CandidateQAError(exc.status, str(exc)) from exc
    require(
        source_bundle.slug == manifest.get("slug"),
        "FULL_MANIFEST_BINDING_FAILED",
        "slug differs between full and input manifests",
    )
    require(
        source_bundle.title == manifest.get("title"),
        "FULL_MANIFEST_BINDING_FAILED",
        "title differs between full and input manifests",
    )

    generated = manifest.get("generated_audio")
    require(isinstance(generated, list) and generated, "MISSING_AUDIO", "generated_audio must be a non-empty list")
    unit_count = manifest.get("unit_count")
    require(
        isinstance(unit_count, int) and not isinstance(unit_count, bool) and unit_count == len(generated),
        "CONSTRUCTION_COVERAGE_FAILED",
        "unit_count does not match generated_audio",
    )
    require(
        manifest.get("synthesis_calls") == unit_count,
        "CONSTRUCTION_COVERAGE_FAILED",
        "synthesis_calls does not match the full chunk count",
    )
    for index, record in enumerate(generated):
        require(isinstance(record, dict), "INVALID_AUDIO_EVIDENCE", f"generated_audio[{index}] must be an object")
    expected_unit_hashes = [record.get("text_sha256") for record in generated]
    require(
        manifest.get("unit_hashes") == expected_unit_hashes,
        "CONSTRUCTION_ORDER_FAILED",
        "unit_hashes do not match generated_audio order",
    )
    for index, record in enumerate(generated):
        require(
            record.get("unit_id") == f"chunk_{index:04d}",
            "CONSTRUCTION_ORDER_FAILED",
            f"generated_audio[{index}] has a non-contiguous unit_id",
        )

    source_text = source_path.read_text(encoding="utf-8")
    segments = reconstruct_segments(source_text, generated)
    reconstructed = " ".join(segments)
    first_source = boundary_words(source_text, start=True)
    last_source = boundary_words(source_text, start=False)
    first_reconstructed = boundary_words(reconstructed, start=True)
    last_reconstructed = boundary_words(reconstructed, start=False)
    require(
        first_source and first_source == first_reconstructed,
        "FIRST_SPAN_MISMATCH",
        "constructed TTS sequence does not match the source opening",
    )
    require(
        last_source and last_source == last_reconstructed,
        "LAST_SPAN_MISMATCH",
        "constructed TTS sequence does not match the source ending",
    )

    checked_records: list[dict[str, Any]] = []
    seen_audio_paths: set[Path] = set()
    seen_audio_hashes: set[str] = set()
    cue_start = 0.0
    cues: list[dict[str, Any]] = []
    for index, (record, segment) in enumerate(zip(generated, segments)):
        audio_path = resolve_run_artifact(record.get("audio_path"), run_dir, record["unit_id"])
        require(audio_path.suffix.lower() == ".mp3", "INVALID_AUDIO_EVIDENCE", f"{record['unit_id']} is not MP3")
        require(audio_path not in seen_audio_paths, "DUPLICATE_AUDIO", f"{record['unit_id']} reuses an audio path")
        size = audio_path.stat().st_size
        require(size > 3, "INVALID_AUDIO_EVIDENCE", f"{record['unit_id']} audio is empty")
        require(size == record.get("audio_size_bytes"), "AUDIO_SIZE_MISMATCH", f"{record['unit_id']} size changed")
        audio_sha256 = sha256_file(audio_path)
        require(audio_sha256 == record.get("audio_sha256"), "AUDIO_HASH_MISMATCH", f"{record['unit_id']} hash changed")
        require(audio_sha256 not in seen_audio_hashes, "DUPLICATE_AUDIO", f"{record['unit_id']} duplicates another audio hash")
        header = audio_path.read_bytes()[:3]
        require(header == b"ID3" or header[:1] == b"\xff", "INVALID_AUDIO_EVIDENCE", f"{record['unit_id']} lacks an MP3 header")
        try:
            duration = float(duration_probe(audio_path))
        except CandidateQAError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise CandidateQAError(
                "MEASURED_SYNC_UNAVAILABLE",
                f"could not measure {record['unit_id']} duration: {exc}",
            ) from exc
        require(
            math.isfinite(duration) and duration > 0,
            "MEASURED_SYNC_UNAVAILABLE",
            f"{record['unit_id']} has no positive measured duration",
        )
        cue_end = cue_start + duration
        checked_records.append(
            {
                **record,
                "audio_path": str(audio_path),
                "source_text": segment,
                "measured_duration_seconds": round(duration, 6),
            }
        )
        cues.append(
            {
                "index": index,
                "unit_id": record["unit_id"],
                "source_text_sha256": record["text_sha256"],
                "audio_sha256": audio_sha256,
                "start_seconds": round(cue_start, 6),
                "end_seconds": round(cue_end, 6),
                "duration_seconds": round(duration, 6),
            }
        )
        cue_start = cue_end
        seen_audio_paths.add(audio_path)
        seen_audio_hashes.add(audio_sha256)

    audio_sequence_sha256 = sha256_json(
        [record["audio_sha256"] for record in checked_records]
    )
    manifest_sha256 = sha256_file(manifest_path)
    candidate_binding_sha256 = sha256_json(
        {
            "manifest_sha256": manifest_sha256,
            "source_sha256": source_sha256,
            "input_manifest_sha256": input_manifest_sha256,
            "ordered_text_hashes": expected_unit_hashes,
            "ordered_audio_hashes": [record["audio_sha256"] for record in checked_records],
        }
    )
    measured_sync = {
        "status": "PASS",
        "sync_tier": "MEASURED_SECTION_SYNC_PRIVATE_CANDIDATE",
        "sync_granularity": "section",
        "sync_method": "measured_source_bound_chunk_audio_duration",
        "alignment_method": "measured_source_bound_chunk_audio_duration",
        "auto_estimated_sync": False,
        "coverage_percent": 100.0,
        "cue_count": len(cues),
        "total_measured_duration_seconds": round(cue_start, 6),
        "cues": cues,
    }
    construction = {
        "status": "PASS",
        "source_verification_method": "hash_bound_tts_by_construction",
        "source_match_score": 10.0,
        "coverage_percent": 100.0,
        "ordered_chunk_count": len(checked_records),
        "first_words_match": True,
        "last_words_match": True,
        "first_words": first_source,
        "last_words": last_source,
        "no_missing_content": True,
        "no_duplicate_content": True,
        "no_reordered_content": True,
        "asr_provider_calls_ran": False,
    }
    return CandidateEvidence(
        manifest=manifest,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        source_path=source_path,
        source_sha256=source_sha256,
        input_manifest_path=input_manifest_path,
        input_manifest_sha256=input_manifest_sha256,
        records=checked_records,
        measured_sync=measured_sync,
        construction=construction,
        candidate_audio_sequence_sha256=audio_sequence_sha256,
        candidate_binding_sha256=candidate_binding_sha256,
    )


def risk_score(text: str) -> tuple[int, int]:
    dialogue = sum(text.count(mark) for mark in ('"', "\u201c", "\u201d", "\u2018", "\u2019"))
    punctuation = sum(text.count(mark) for mark in ("?", "!", ";", ":", "\u2014", ","))
    return dialogue * 20 + punctuation * 3, len(text)


def select_listening_samples(evidence: CandidateEvidence) -> list[dict[str, Any]]:
    records = evidence.records
    require(
        len(records) >= LISTENING_SAMPLE_COUNT,
        "UNREPRESENTATIVE_FULL_CANDIDATE",
        "schema-3 full-candidate listening QA requires at least six distinct source-bound audio sections",
    )
    last = len(records) - 1
    middle = last // 2
    risk = max(range(1, last), key=lambda index: risk_score(records[index]["source_text"]))
    selected: list[int] = []
    for index in (0, middle, risk, last):
        if index not in selected:
            selected.append(index)
    for factor in (0.2, 0.4, 0.6, 0.8):
        index = round(last * factor)
        if index not in selected:
            selected.append(index)
        if len(selected) == LISTENING_SAMPLE_COUNT:
            break
    for index in range(len(records)):
        if len(selected) == LISTENING_SAMPLE_COUNT:
            break
        if index not in selected:
            selected.append(index)
    require(
        len(selected) == LISTENING_SAMPLE_COUNT
        and len(set(selected)) == LISTENING_SAMPLE_COUNT,
        "UNREPRESENTATIVE_FULL_CANDIDATE",
        "could not select six distinct full-candidate sections",
    )
    selected = sorted(selected)

    def label_for(index: int) -> str:
        if index == 0:
            return "first_section"
        if index == last:
            return "final_section"
        if index == middle and index == risk:
            return "middle_dialogue_or_risk_section"
        if index == middle:
            return "middle_section"
        if index == risk:
            return "dialogue_or_risk_section"
        return f"coverage_section_{index + 1:02d}"

    return [
        {
            "sample_label": label_for(index),
            "section_index": index,
            "unit_id": records[index]["unit_id"],
            "start_time": evidence.measured_sync["cues"][index]["start_seconds"],
            "duration": records[index]["measured_duration_seconds"],
            "sample_audio_path": records[index]["audio_path"],
            "sample_audio_hash": records[index]["audio_sha256"],
            "source_text_sha256": records[index]["text_sha256"],
            "selection_method": "deterministic_source_bound_full_candidate_section",
        }
        for index in selected
    ]


def finite_nonnegative_env(env: dict[str, str], name: str, *, positive: bool) -> str | None:
    raw = str(env.get(name) or "").strip()
    if not raw:
        return f"{name} is required"
    try:
        value = float(raw)
    except ValueError:
        return f"{name} must be numeric"
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        qualifier = "positive" if positive else "nonnegative"
        return f"{name} must be finite and {qualifier}"
    return None


def listening_runtime_errors(env: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if str(env.get("EARNALISM_ENABLE_OPENAI_LISTENING_QA") or "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        errors.append("EARNALISM_ENABLE_OPENAI_LISTENING_QA=true is required")
    if str(env.get("EARNALISM_STOP_ON_BUDGET_EXCEEDED") or "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        errors.append("EARNALISM_STOP_ON_BUDGET_EXCEEDED=true is required")
    if not env.get("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is required")
    if not env.get("EARNALISM_OPENAI_LISTENING_QA_MODEL"):
        errors.append("EARNALISM_OPENAI_LISTENING_QA_MODEL is required")
    policy_name = str(env.get("EARNALISM_LISTENING_POLICY_VERSION") or "").strip()
    if policy_name not in ALLOWED_ENGLISH_POLICIES:
        errors.append(
            "EARNALISM_LISTENING_POLICY_VERSION must name an approved English schema-3 policy"
        )
    for name in CAP_ENV_NAMES[:3]:
        error = finite_nonnegative_env(env, name, positive=True)
        if error:
            errors.append(error)
    if env.get("EARNALISM_PRIOR_ESTIMATED_SPEND_USD"):
        error = finite_nonnegative_env(
            env, "EARNALISM_PRIOR_ESTIMATED_SPEND_USD", positive=False
        )
        if error:
            errors.append(error)
    return errors


def listening_budget_guard(env: dict[str, str], sample_count: int) -> dict[str, Any]:
    previous = {name: os.environ.get(name) for name in CAP_ENV_NAMES}
    try:
        for name in CAP_ENV_NAMES:
            if name in env:
                os.environ[name] = str(env[name])
            else:
                os.environ.pop(name, None)
        return openai_listening_qa_budget_guard(
            sample_count=sample_count,
            prior_estimated_usd=float(
                env.get("EARNALISM_PRIOR_ESTIMATED_SPEND_USD") or 0.0
            ),
        )
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def base_result(evidence: CandidateEvidence) -> dict[str, Any]:
    manifest = evidence.manifest
    return {
        "qa_schema_version": QA_SCHEMA_VERSION,
        "status": "OBJECTIVE_QA_PASS_LISTENING_PENDING",
        "slug": manifest.get("slug"),
        "title": manifest.get("title"),
        "author": manifest.get("author"),
        "provider": manifest.get("provider"),
        "voice": manifest.get("voice"),
        "language": "English",
        "full_manifest_path": str(evidence.manifest_path),
        "full_manifest_sha256": evidence.manifest_sha256,
        "source_path": str(evidence.source_path),
        "source_sha256": evidence.source_sha256,
        "input_manifest_path": str(evidence.input_manifest_path),
        "input_manifest_sha256": evidence.input_manifest_sha256,
        "candidate_audio_sequence_sha256": evidence.candidate_audio_sequence_sha256,
        "candidate_binding_sha256": evidence.candidate_binding_sha256,
        "audio_file_count": len(evidence.records),
        "objective_qa": {
            "status": "PASS",
            "source_hash_status": "PASS",
            "audio_hash_status": "PASS",
            "construction": evidence.construction,
            "measured_sync": evidence.measured_sync,
        },
        "private_output_only": True,
        "public_release_approved": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "provider_calls_ran": False,
        "provider_call_count": 0,
        "actual_provider_billing": "NOT_REPORTED",
        "blockers": [],
    }


def blocked_without_evidence(
    manifest_path: Path, status: str, blocker: str
) -> dict[str, Any]:
    return {
        "qa_schema_version": QA_SCHEMA_VERSION,
        "status": status,
        "full_manifest_path": str(manifest_path.expanduser().resolve()),
        "objective_qa": {"status": "BLOCKED"},
        "private_output_only": True,
        "public_release_approved": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "provider_calls_ran": False,
        "provider_call_count": 0,
        "actual_provider_billing": "NOT_REPORTED",
        "blockers": [blocker],
    }


def normalize_judgment(
    sample: dict[str, Any], judged: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    raw_scores = judged.get("scores") if isinstance(judged.get("scores"), dict) else {}
    scores: dict[str, float] = {}
    for field in LISTENING_THRESHOLDS:
        if field not in raw_scores:
            blockers.append(f"{sample['sample_label']}: missing schema-3 score {field}")
            continue
        try:
            value = float(raw_scores[field])
        except (TypeError, ValueError):
            blockers.append(f"{sample['sample_label']}: invalid schema-3 score {field}")
            continue
        maximum = 1.0 if field == "confidence_score" else 10.0
        if not math.isfinite(value) or not 0.0 <= value <= maximum:
            blockers.append(f"{sample['sample_label']}: out-of-range schema-3 score {field}")
            continue
        scores[field] = value

    raw_flags = (
        judged.get("judge_flags") if isinstance(judged.get("judge_flags"), dict) else {}
    )
    flags: dict[str, bool] = {}
    for field in BINARY_LISTENING_FLAGS:
        if field not in raw_flags or not isinstance(raw_flags[field], bool):
            blockers.append(f"{sample['sample_label']}: missing boolean schema-3 flag {field}")
            continue
        flags[field] = raw_flags[field]
    frontmatter = judged.get("frontmatter_present")
    if not isinstance(frontmatter, bool):
        blockers.append(f"{sample['sample_label']}: frontmatter_present must be boolean")
        frontmatter = True
    reason = str(judged.get("blocker_reason") or "").strip()
    if reason:
        blockers.append(f"{sample['sample_label']}: {reason}")
    return (
        {
            **sample,
            "scores": scores,
            "confidence": scores.get("confidence_score", 0.0),
            "judge_flags": flags,
            "frontmatter_present": frontmatter,
            "notes": str(judged.get("notes") or ""),
            "blocker_reason": reason,
        },
        blockers,
    )


def build_listening_report(
    evidence: CandidateEvidence,
    samples: list[dict[str, Any]],
    *,
    policy_name: str,
    model: str,
    blockers: list[str],
) -> tuple[dict[str, Any], list[str]]:
    aggregate: dict[str, float] = {}
    for field in LISTENING_THRESHOLDS:
        values = [
            float((sample.get("scores") or {}).get(field))
            for sample in samples
            if field in (sample.get("scores") or {})
        ]
        if len(values) == len(samples) and values:
            aggregate[field] = round(min(values), 4)
    flags = {
        field: any(bool((sample.get("judge_flags") or {}).get(field)) for sample in samples)
        for field in BINARY_LISTENING_FLAGS
    }
    frontmatter = any(sample.get("frontmatter_present") is not False for sample in samples)
    _, policy_blockers, policy = evaluate_listening_evidence(
        aggregate,
        flags,
        language="English",
        release_policy=policy_name,
        frontmatter_present=frontmatter,
    )
    all_blockers = list(dict.fromkeys([*blockers, *policy_blockers]))
    listening = {
        "status": "PASS" if not all_blockers else "BLOCKED",
        "model_or_judge": f"openai:{model}",
        "audio_hash": evidence.candidate_audio_sequence_sha256,
        "release_policy": policy["name"],
        "samples": samples,
        "aggregate": aggregate,
        **flags,
        "dialogue_emotional_sections_judged": len(samples) == LISTENING_SAMPLE_COUNT,
        "blockers": all_blockers,
    }
    report = {
        "qa_schema_version": LISTENING_QA_SCHEMA_VERSION,
        "rubric_version": LISTENING_QA_RUBRIC_VERSION,
        "audio_judge_hook_version": LISTENING_QA_HOOK_VERSION,
        "slug": evidence.manifest.get("slug"),
        "title": evidence.manifest.get("title"),
        "author": evidence.manifest.get("author"),
        "language": "English",
        "audio_path": "MULTI_FILE_PRIVATE_FULL_CANDIDATE",
        "audio_hash": evidence.candidate_audio_sequence_sha256,
        "candidate_binding_sha256": evidence.candidate_binding_sha256,
        "listening_quality": listening,
        "release_policy": policy["name"],
    }
    valid, schema_blockers = validate_listening_quality_report(
        report,
        expected_audio_hash=evidence.candidate_audio_sequence_sha256,
        language="English",
        release_policy=policy_name,
    )
    if not valid:
        all_blockers = list(dict.fromkeys([*all_blockers, *schema_blockers]))
        report["listening_quality"]["status"] = "BLOCKED"
        report["listening_quality"]["blockers"] = all_blockers
    return report, all_blockers


def reusable_prior_result(
    output_path: Path, evidence: CandidateEvidence
) -> tuple[int, dict[str, Any]] | None:
    if not output_path.is_file():
        return None
    try:
        prior = read_json_object(output_path, "prior full-candidate QA result")
    except CandidateQAError:
        return None
    if (
        prior.get("candidate_binding_sha256") != evidence.candidate_binding_sha256
        or prior.get("provider_calls_ran") is not True
    ):
        return None
    listening_report = prior.get("listening_quality_report")
    policy_name = str((listening_report or {}).get("release_policy") or "")
    listening_valid = False
    if isinstance(listening_report, dict) and policy_name in ALLOWED_ENGLISH_POLICIES:
        listening_valid, _ = validate_listening_quality_report(
            listening_report,
            expected_audio_hash=evidence.candidate_audio_sequence_sha256,
            language="English",
            release_policy=policy_name,
        )
    if (
        prior.get("status") == "FULL_CANDIDATE_QA_PASS_PRIVATE_ONLY"
        and listening_valid
    ):
        return 0, {**prior, "cached_result_reused": True}
    return 4, {
        **prior,
        "status": "BLOCKED_REPEAT_LISTENING_QA",
        "cached_result_reused": True,
        "blockers": list(
            dict.fromkeys(
                [
                    *(prior.get("blockers") or []),
                    "REPEAT_LISTENING_QA_BLOCKED: this candidate binding already reached the listening provider",
                ]
            )
        ),
    }


def evaluate(
    manifest_path: Path,
    output_path: Path,
    *,
    env: dict[str, str] | None = None,
    judge: Callable[[Any, Any, dict[str, Any]], dict[str, Any]] = judge_audio_sample_with_openai,
    client: Any | None = None,
    duration_probe: Callable[[Path], float] = ffprobe_duration,
) -> tuple[int, dict[str, Any]]:
    manifest_path = manifest_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if output_path == manifest_path:
        return 2, blocked_without_evidence(
            manifest_path,
            "BLOCKED_OUTPUT_PATH",
            "INVALID_OUTPUT_PATH: QA output must not overwrite the full manifest",
        )
    try:
        pipeline.validate_private_output_dir(output_path.parent)
    except pipeline.PipelineError as exc:
        return 2, blocked_without_evidence(
            manifest_path,
            "BLOCKED_OUTPUT_PATH",
            f"{exc.status}: {exc}",
        )
    try:
        evidence = validate_full_candidate(manifest_path, duration_probe=duration_probe)
        samples = select_listening_samples(evidence)
    except CandidateQAError as exc:
        result = blocked_without_evidence(
            manifest_path, "BLOCKED_OBJECTIVE_QA", exc.blocker
        )
        atomic_write_json(output_path, result)
        return 2, result

    result = base_result(evidence)
    prior = reusable_prior_result(output_path, evidence)
    if prior is not None:
        return prior

    process_env = dict(os.environ if env is None else env)
    runtime_errors = listening_runtime_errors(process_env)
    if runtime_errors:
        result.update(
            {
                "status": "BLOCKED_BEFORE_LISTENING_QA",
                "blockers": runtime_errors,
                "listening_samples": samples,
            }
        )
        atomic_write_json(output_path, result)
        return 2, result

    budget = listening_budget_guard(process_env, len(samples))
    result["listening_qa_budget_guard"] = budget
    if not budget.get("ok"):
        result.update(
            {
                "status": "BLOCKED_BEFORE_LISTENING_QA",
                "blockers": [
                    str(budget.get("blocker") or "LISTENING_QA_BUDGET_BLOCKED")
                ],
                "listening_samples": samples,
            }
        )
        atomic_write_json(output_path, result)
        return 2, result

    if client is None:
        try:
            from openai import OpenAI

            client = OpenAI()
        except Exception as exc:  # noqa: BLE001
            result.update(
                {
                    "status": "BLOCKED_BEFORE_LISTENING_QA",
                    "blockers": [f"LISTENING_QA_NOT_RUN: OpenAI client unavailable: {exc}"],
                    "listening_samples": samples,
                }
            )
            atomic_write_json(output_path, result)
            return 2, result

    args = SimpleNamespace(
        slug=evidence.manifest.get("slug"),
        title=evidence.manifest.get("title"),
        author=evidence.manifest.get("author") or "",
        language="English",
    )
    judged_samples: list[dict[str, Any]] = []
    judgment_blockers: list[str] = []
    provider_call_count = 0
    for sample in samples:
        try:
            judged = judge(client, args, dict(sample))
            provider_call_count += 1
            if not isinstance(judged, dict):
                raise TypeError("judge returned a non-object result")
            normalized, blockers = normalize_judgment(sample, judged)
        except Exception as exc:  # noqa: BLE001
            provider_call_count += 1
            normalized = {
                **sample,
                "scores": {},
                "judge_flags": {},
                "frontmatter_present": True,
                "notes": f"listening judge failed: {exc}",
                "blocker_reason": "LISTENING_QA_NOT_RUN",
            }
            blockers = [f"{sample['sample_label']}: LISTENING_QA_NOT_RUN: {exc}"]
        judged_samples.append(normalized)
        judgment_blockers.extend(blockers)

    policy_name = process_env["EARNALISM_LISTENING_POLICY_VERSION"]
    listening_report, listening_blockers = build_listening_report(
        evidence,
        judged_samples,
        policy_name=policy_name,
        model=process_env["EARNALISM_OPENAI_LISTENING_QA_MODEL"],
        blockers=judgment_blockers,
    )
    passed = not listening_blockers
    result.update(
        {
            "status": (
                "FULL_CANDIDATE_QA_PASS_PRIVATE_ONLY"
                if passed
                else "BLOCKED_LISTENING_QA"
            ),
            "listening_quality_report": listening_report,
            "provider_calls_ran": provider_call_count > 0,
            "provider_call_count": provider_call_count,
            "blockers": listening_blockers,
        }
    )
    atomic_write_json(output_path, result)
    return (0 if passed else 3), result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    returncode, result = evaluate(args.full_manifest, args.output)
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": str(args.output.expanduser().resolve()),
                "provider_calls_ran": result.get("provider_calls_ran", False),
                "blockers": result.get("blockers", []),
            },
            ensure_ascii=False,
        )
    )
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
