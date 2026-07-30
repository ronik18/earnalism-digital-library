#!/usr/bin/env python3
"""Run fail-closed audio-derived QA for a private Google English full title.

This adapter consumes only the ``full_generation_manifest.json`` written by
``sprint1_google_english_private_pipeline.py``.  It revalidates the complete
private manifest/source/audio binding, runs pinned local Whisper source-blind
on every ordered Google chunk, and requires:

* ASR/source score >= 9.7 and coverage >= 0.98;
* exact first and last spans;
* no missing, duplicated, reordered, or unexpected content;
* audio-derived, monotonic word timestamps for every chunk; and
* measured source-bound section sync with no estimated timestamps.

The adapter performs no synthesis, upload, publication, release mutation,
network/provider call, or paid-lock access.  Construction evidence is retained
as provenance only and never substitutes for audio-derived ASR.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPT_DIR / "factory_hooks"
sys.path[:0] = [str(SCRIPT_DIR), str(HOOK_DIR)]

import sprint1_gift_kokoro_full_title_private_qa as asr_common  # noqa: E402
import sprint1_google_english_full_candidate_qa as candidate_qa  # noqa: E402
import sprint1_google_english_private_pipeline as google_pipeline  # noqa: E402
import sprint1_google_english_representative_objective_qa as representative_qa  # noqa: E402
import sprint1_kokoro_title_private_audition as whisper_common  # noqa: E402
from asr_sync_hook import audio_derived_asr_gate, frontmatter_absent  # noqa: E402


SCHEMA = "earnalism.google_english_full_audio_derived_qa.v1"
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
SYNC_SCORE_MIN = 9.7
WHISPER_MODEL = representative_qa.WHISPER_MODEL
WHISPER_FILENAME = representative_qa.WHISPER_FILENAME
WHISPER_SHA256 = representative_qa.WHISPER_SHA256
ASR_SETTINGS = dict(representative_qa.ASR_SETTINGS)
DEFAULT_WHISPER_CACHE = representative_qa.DEFAULT_WHISPER_CACHE
BOUNDED_CHUNK_REPAIR_SCHEMA = (
    "earnalism.google_english_bounded_chunk_repair.v1"
)


class FullAudioDerivedQAError(RuntimeError):
    """Raised when the private contract cannot be safely consumed."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

    @property
    def blocker(self) -> str:
        return f"{self.code}: {self}"


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise FullAudioDerivedQAError(code, message)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return candidate_qa.sha256_file(path)


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def validate_output_path(output_path: Path, run_dir: Path) -> Path:
    output = output_path.expanduser().resolve()
    require(
        candidate_qa.is_within(output, run_dir),
        "NON_PRIVATE_OUTPUT",
        "QA output must remain inside the private Google full-run directory",
    )
    require(
        output != run_dir / "full_generation_manifest.json",
        "INVALID_OUTPUT_PATH",
        "QA output must not overwrite the full generation manifest",
    )
    require(
        not output.exists(),
        "OUTPUT_ALREADY_EXISTS",
        "QA output already exists; preserve immutable evidence and choose a new path",
    )
    try:
        google_pipeline.validate_private_output_dir(output.parent)
    except google_pipeline.PipelineError as exc:
        raise FullAudioDerivedQAError(exc.status, str(exc)) from exc
    return output


def validate_attempt_binding(
    evidence: candidate_qa.CandidateEvidence,
) -> str:
    manifest = evidence.manifest
    require(
        manifest.get("schema_version") == google_pipeline.PIPELINE_SCHEMA,
        "FULL_MANIFEST_SCHEMA_MISMATCH",
        "full generation manifest schema is not supported",
    )
    input_manifest = candidate_qa.read_json_object(
        evidence.input_manifest_path,
        "input manifest",
    )
    require(
        manifest.get("input_schema") == input_manifest.get("schema_version"),
        "INPUT_MANIFEST_SCHEMA_MISMATCH",
        "full manifest input_schema does not match the bound input manifest",
    )
    voice = str(manifest.get("voice") or "")
    language_code = str(manifest.get("language_code") or "")
    require(
        voice.startswith(f"{language_code}-"),
        "VOICE_BINDING_INVALID",
        "Google English voice must be bound to the declared English language code",
    )
    try:
        speaking_rate = float(manifest.get("speaking_rate"))
        pitch = float(manifest.get("pitch"))
    except (TypeError, ValueError) as exc:
        raise FullAudioDerivedQAError(
            "VOICE_SETTINGS_INVALID",
            "speaking_rate and pitch must be numeric",
        ) from exc
    require(
        math.isfinite(speaking_rate)
        and 0.25 <= speaking_rate <= 4.0
        and math.isfinite(pitch)
        and -20.0 <= pitch <= 20.0,
        "VOICE_SETTINGS_INVALID",
        "speaking_rate or pitch is outside the Google pipeline contract",
    )
    units = [
        {
            "chunk_id": record["unit_id"],
            "text_sha256": record["text_sha256"],
            "characters": record["characters"],
        }
        for record in evidence.records
    ]
    expected = google_pipeline.attempt_fingerprint(
        mode="full",
        source_sha256=evidence.source_sha256,
        manifest_sha256=evidence.input_manifest_sha256,
        voice=voice,
        language_code=language_code,
        speaking_rate=speaking_rate,
        pitch=pitch,
        units=units,
    )
    require(
        manifest.get("attempt_fingerprint") == expected,
        "ATTEMPT_FINGERPRINT_MISMATCH",
        (
            "full manifest fingerprint does not match the exact source, voice, "
            "settings, and ordered chunks"
        ),
    )
    repair = manifest.get("bounded_chunk_repair")
    if repair is not None:
        require(
            isinstance(repair, dict),
            "BOUNDED_REPAIR_BINDING_INVALID",
            "bounded_chunk_repair must be an object",
        )
        expected = validate_bounded_chunk_repair_binding(
            evidence,
            base_attempt_fingerprint=expected,
            repair=repair,
        )
    audition_hash = str(manifest.get("audition_evidence_sha256") or "")
    require(
        len(audition_hash) == 64
        and all(character in "0123456789abcdef" for character in audition_hash),
        "AUDITION_BINDING_MISSING",
        "full manifest lacks a valid hash binding to passing representative evidence",
    )
    return expected


def _valid_sha256(value: Any) -> bool:
    rendered = str(value or "")
    return len(rendered) == 64 and all(
        character in "0123456789abcdef" for character in rendered
    )


def validate_bounded_chunk_repair_binding(
    evidence: candidate_qa.CandidateEvidence,
    *,
    base_attempt_fingerprint: str,
    repair: Mapping[str, Any],
) -> str:
    """Validate one hash-bound audio substitution in a Google full candidate."""

    manifest = evidence.manifest
    require(
        repair.get("schema_version") == BOUNDED_CHUNK_REPAIR_SCHEMA,
        "BOUNDED_REPAIR_SCHEMA_MISMATCH",
        "bounded repair schema is not supported",
    )
    require(
        repair.get("status") == "PRIVATE_REPLACEMENT_CANDIDATE_QA_PENDING",
        "BOUNDED_REPAIR_STATE_INVALID",
        "bounded repair must remain private and QA-pending",
    )
    for field in (
        "base_full_manifest_sha256",
        "base_candidate_audio_sequence_sha256",
        "base_candidate_binding_sha256",
        "failed_listening_evidence_sha256",
        "repair_attempt_fingerprint",
        "text_sha256",
        "prior_audio_sha256",
        "replacement_audio_sha256",
        "candidate_audio_sequence_sha256",
    ):
        require(
            _valid_sha256(repair.get(field)),
            "BOUNDED_REPAIR_BINDING_INVALID",
            f"bounded repair has an invalid {field}",
        )
    require(
        repair.get("slug") == manifest.get("slug")
        and repair.get("source_sha256") == evidence.source_sha256
        and repair.get("input_manifest_sha256")
        == evidence.input_manifest_sha256,
        "BOUNDED_REPAIR_BINDING_INVALID",
        "bounded repair source or title binding changed",
    )
    require(
        repair.get("base_attempt_fingerprint")
        == base_attempt_fingerprint,
        "BOUNDED_REPAIR_BINDING_INVALID",
        "bounded repair does not bind the validated base attempt",
    )
    try:
        target_index = int(repair.get("chunk_index"))
    except (TypeError, ValueError) as exc:
        raise FullAudioDerivedQAError(
            "BOUNDED_REPAIR_BINDING_INVALID",
            "bounded repair chunk_index must be an integer",
        ) from exc
    require(
        0 <= target_index < len(evidence.records),
        "BOUNDED_REPAIR_BINDING_INVALID",
        "bounded repair chunk_index is outside the full candidate",
    )
    target = evidence.records[target_index]
    require(
        repair.get("unit_id") == target.get("unit_id")
        and repair.get("text_sha256") == target.get("text_sha256")
        and repair.get("replacement_audio_sha256")
        == target.get("audio_sha256"),
        "BOUNDED_REPAIR_BINDING_INVALID",
        "bounded repair target does not match the replacement record",
    )
    require(
        repair.get("prior_audio_sha256")
        != repair.get("replacement_audio_sha256"),
        "BOUNDED_REPAIR_BINDING_INVALID",
        "bounded repair did not change the rejected audio bytes",
    )

    base_hashes = repair.get("base_ordered_audio_hashes")
    require(
        isinstance(base_hashes, list)
        and len(base_hashes) == len(evidence.records)
        and all(_valid_sha256(item) for item in base_hashes),
        "BOUNDED_REPAIR_BINDING_INVALID",
        "bounded repair lacks the complete base audio sequence",
    )
    candidate_hashes = [record["audio_sha256"] for record in evidence.records]
    changed_indexes = [
        index
        for index, (before, after) in enumerate(
            zip(base_hashes, candidate_hashes)
        )
        if before != after
    ]
    require(
        changed_indexes == [target_index]
        and repair.get("changed_chunk_indexes") == [target_index],
        "BOUNDED_REPAIR_CHANGED_MULTIPLE_CHUNKS",
        "bounded repair must change exactly one declared chunk",
    )
    require(
        base_hashes[target_index] == repair.get("prior_audio_sha256")
        and repair.get("preserved_audio_file_count")
        == len(evidence.records) - 1
        and repair.get("replacement_audio_file_count") == 1,
        "BOUNDED_REPAIR_BINDING_INVALID",
        "bounded repair preservation counts or prior hash changed",
    )
    base_sequence_sha256 = candidate_qa.sha256_json(base_hashes)
    require(
        repair.get("base_candidate_audio_sequence_sha256")
        == base_sequence_sha256,
        "BOUNDED_REPAIR_BINDING_INVALID",
        "bounded repair base audio sequence hash changed",
    )
    base_binding_sha256 = candidate_qa.sha256_json(
        {
            "manifest_sha256": repair.get("base_full_manifest_sha256"),
            "source_sha256": evidence.source_sha256,
            "input_manifest_sha256": evidence.input_manifest_sha256,
            "ordered_text_hashes": [
                record["text_sha256"] for record in evidence.records
            ],
            "ordered_audio_hashes": base_hashes,
        }
    )
    require(
        repair.get("base_candidate_binding_sha256")
        == base_binding_sha256,
        "BOUNDED_REPAIR_BINDING_INVALID",
        "bounded repair base candidate binding changed",
    )
    require(
        repair.get("candidate_audio_sequence_sha256")
        == evidence.candidate_audio_sequence_sha256
        == manifest.get("candidate_audio_sequence_sha256"),
        "BOUNDED_REPAIR_BINDING_INVALID",
        "bounded repair replacement audio sequence hash changed",
    )
    require(
        repair.get("full_source_text_changed") is False
        and repair.get("synthesis_input_kind") == "exact_plain_text",
        "BOUNDED_REPAIR_SOURCE_MUTATION_BLOCKED",
        "bounded repair must synthesize the exact source text without SSML drift",
    )
    for field in (
        "upload_performed",
        "publication_performed",
        "release_mutation_performed",
    ):
        require(
            repair.get(field) is False,
            "BOUNDED_REPAIR_PUBLIC_MUTATION_BLOCKED",
            f"bounded repair {field} must remain false",
        )
    require(
        manifest.get("repair_synthesis_calls") == 1
        and manifest.get("total_provider_calls_across_lineage")
        == len(evidence.records) + 1,
        "BOUNDED_REPAIR_CALL_COUNT_INVALID",
        "bounded repair must record exactly one replacement provider call",
    )

    replacement_voice = str(repair.get("replacement_voice") or "")
    replacement_language = str(
        repair.get("replacement_language_code") or ""
    )
    require(
        replacement_voice.startswith(f"{replacement_language}-")
        and replacement_language == manifest.get("language_code"),
        "BOUNDED_REPAIR_VOICE_INVALID",
        "bounded repair replacement voice locale changed",
    )
    try:
        replacement_rate = float(repair.get("replacement_speaking_rate"))
        replacement_pitch = float(repair.get("replacement_pitch"))
    except (TypeError, ValueError) as exc:
        raise FullAudioDerivedQAError(
            "BOUNDED_REPAIR_VOICE_INVALID",
            "bounded repair replacement rate and pitch must be numeric",
        ) from exc
    require(
        math.isfinite(replacement_rate)
        and 0.25 <= replacement_rate <= 4.0
        and math.isfinite(replacement_pitch)
        and -20.0 <= replacement_pitch <= 20.0,
        "BOUNDED_REPAIR_VOICE_INVALID",
        "bounded repair replacement settings are outside the Google contract",
    )
    require(
        (
            replacement_voice,
            replacement_rate,
            replacement_pitch,
        )
        != (
            manifest.get("voice"),
            float(manifest.get("speaking_rate")),
            float(manifest.get("pitch")),
        ),
        "BOUNDED_REPAIR_DUPLICATE_SETTINGS",
        "bounded repair repeats the rejected voice, rate, pitch, and text",
    )
    expected_repair_fingerprint = canonical_sha256(
        {
            "schema_version": BOUNDED_CHUNK_REPAIR_SCHEMA,
            "provider": "google",
            "mode": "bounded_chunk_repair",
            "slug": manifest.get("slug"),
            "source_sha256": evidence.source_sha256,
            "input_manifest_sha256": evidence.input_manifest_sha256,
            "base_full_manifest_sha256": repair.get(
                "base_full_manifest_sha256"
            ),
            "chunk_index": target_index,
            "unit_id": target.get("unit_id"),
            "text_sha256": target.get("text_sha256"),
            "prior_audio_sha256": repair.get("prior_audio_sha256"),
            "voice": replacement_voice,
            "language_code": replacement_language,
            "speaking_rate": replacement_rate,
            "pitch": replacement_pitch,
            "synthesis_input_kind": "exact_plain_text",
        }
    )
    require(
        repair.get("repair_attempt_fingerprint")
        == expected_repair_fingerprint,
        "BOUNDED_REPAIR_FINGERPRINT_MISMATCH",
        "bounded repair fingerprint does not match exact source and settings",
    )
    return expected_repair_fingerprint


def validate_contract(
    manifest_path: Path,
    *,
    duration_getter: Callable[[Path], float] = candidate_qa.ffprobe_duration,
) -> candidate_qa.CandidateEvidence:
    manifest = manifest_path.expanduser().resolve()
    require(
        manifest.name == "full_generation_manifest.json",
        "INVALID_FULL_MANIFEST",
        "adapter accepts only a Google full_generation_manifest.json",
    )
    try:
        google_pipeline.validate_private_output_dir(manifest.parent)
    except google_pipeline.PipelineError as exc:
        raise FullAudioDerivedQAError(exc.status, str(exc)) from exc
    try:
        evidence = candidate_qa.validate_full_candidate(
            manifest,
            duration_probe=duration_getter,
        )
    except candidate_qa.CandidateQAError as exc:
        raise FullAudioDerivedQAError(exc.code, str(exc)) from exc
    validate_attempt_binding(evidence)
    return evidence


def _strict_metrics_pass(metrics: Mapping[str, Any]) -> bool:
    return bool(
        float(metrics.get("score") or 0.0) >= ASR_SCORE_MIN
        and float(metrics.get("coverage") or 0.0) >= ASR_COVERAGE_MIN
        and metrics.get("first_words_match") is True
        and metrics.get("last_words_match") is True
        and metrics.get("ordered_content_integrity_pass") is True
        and metrics.get("no_missing_content") is True
        and metrics.get("no_duplicate_content") is True
        and metrics.get("no_reordered_content") is True
        and metrics.get("no_unexpected_content") is True
    )


def _evaluated_metrics(
    source: str,
    transcript: str,
    *,
    slug: str,
) -> dict[str, Any]:
    normalized_source, normalized_transcript, equivalences = (
        representative_qa.apply_spoken_number_equivalences(
            source,
            transcript,
            slug=slug,
        )
    )
    metrics = whisper_common.ordered_token_integrity(
        normalized_source,
        normalized_transcript,
    )
    return {
        **metrics,
        "explicit_equivalences_applied": equivalences,
        "normalized_source_sha256": google_pipeline.sha256_text(normalized_source),
        "normalized_transcript_sha256": google_pipeline.sha256_text(
            normalized_transcript
        ),
        "pass": _strict_metrics_pass(metrics),
    }


def _absolute_words(
    words: Sequence[Mapping[str, Any]],
    *,
    offset_seconds: float,
) -> list[dict[str, Any]]:
    return [
        {
            **dict(word),
            "start_seconds": round(
                float(word["start_seconds"]) + offset_seconds,
                6,
            ),
            "end_seconds": round(
                float(word["end_seconds"]) + offset_seconds,
                6,
            ),
        }
        for word in words
    ]


def load_reusable_asr_reports(
    report_path: Path | None,
    expected_report_sha256: str | None,
    evidence: candidate_qa.CandidateEvidence,
    attempt_fingerprint: str,
) -> dict[str, dict[str, Any]]:
    """Load immutable per-chunk ASR evidence from an earlier private full run.

    A replacement candidate commonly changes only one audio chunk. Reusing
    source-blind Whisper evidence for byte-identical chunks avoids hours of
    duplicate local inference while preserving the same objective gate. The
    prior report is never accepted wholesale: each unit is re-bound below to
    its exact source hash, audio hash, duration, model hash, and ASR settings.
    """

    require(
        (report_path is None) == (expected_report_sha256 is None),
        "REUSABLE_ASR_REPORT_BINDING_REQUIRED",
        (
            "--reuse-report and --reuse-report-sha256 must be supplied "
            "together"
        ),
    )
    if report_path is None:
        return {}
    resolved = report_path.expanduser().resolve()
    expected_sha256 = str(expected_report_sha256 or "")
    require(
        len(expected_sha256) == 64
        and all(character in "0123456789abcdef" for character in expected_sha256),
        "REUSABLE_ASR_REPORT_HASH_INVALID",
        "reusable report SHA-256 must be 64 lowercase hexadecimal characters",
    )
    try:
        google_pipeline.validate_private_output_dir(resolved.parent)
        require(
            resolved.is_file(),
            "REUSABLE_ASR_REPORT_INVALID",
            f"reusable report does not exist: {resolved}",
        )
        report_bytes = resolved.read_bytes()
        require(
            hashlib.sha256(report_bytes).hexdigest() == expected_sha256,
            "REUSABLE_ASR_REPORT_HASH_MISMATCH",
            "reusable report bytes do not match the independently supplied SHA-256",
        )
        payload = json.loads(report_bytes.decode("utf-8"))
        require(
            isinstance(payload, dict),
            "REUSABLE_ASR_REPORT_INVALID",
            "reusable full audio-derived ASR report must be a JSON object",
        )
    except FullAudioDerivedQAError:
        raise
    except google_pipeline.PipelineError as exc:
        code = getattr(exc, "status", None) or getattr(exc, "code", None)
        raise FullAudioDerivedQAError(
            str(code or "REUSABLE_ASR_REPORT_INVALID"),
            str(exc),
        ) from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FullAudioDerivedQAError(
            "REUSABLE_ASR_REPORT_INVALID",
            f"reusable report is not readable UTF-8 JSON: {resolved}",
        ) from exc
    require(
        payload.get("schema_version") == SCHEMA
        and payload.get("private_output_only") is True
        and payload.get("provider_calls_made_by_adapter") is False
        and payload.get("network_calls_made_by_adapter") is False,
        "REUSABLE_ASR_REPORT_INVALID",
        "reusable report must be private, provider-free evidence from this adapter",
    )
    bounded_repair = evidence.manifest.get("bounded_chunk_repair")
    prior_attempt_fingerprint = attempt_fingerprint
    if isinstance(bounded_repair, Mapping):
        prior_attempt_fingerprint = str(
            bounded_repair.get("base_attempt_fingerprint") or ""
        )
        require(
            payload.get("full_manifest_sha256")
            == bounded_repair.get("base_full_manifest_sha256")
            and payload.get("candidate_audio_sequence_sha256")
            == bounded_repair.get("base_candidate_audio_sequence_sha256")
            and payload.get("candidate_binding_sha256")
            == bounded_repair.get("base_candidate_binding_sha256"),
            "REUSABLE_ASR_REPORT_CANDIDATE_MISMATCH",
            (
                "bounded repair may reuse evidence only from its exact "
                "hash-bound base candidate"
            ),
        )
    require(
        payload.get("slug") == evidence.manifest.get("slug")
        and payload.get("title") == evidence.manifest.get("title")
        and payload.get("author") == evidence.manifest.get("author")
        and payload.get("source_sha256") == evidence.source_sha256
        and payload.get("input_manifest_sha256")
        == evidence.input_manifest_sha256
        and payload.get("attempt_fingerprint") == prior_attempt_fingerprint
        and payload.get("voice") == evidence.manifest.get("voice")
        and payload.get("language_code") == evidence.manifest.get("language_code"),
        "REUSABLE_ASR_REPORT_CANDIDATE_MISMATCH",
        (
            "reusable report must match the current title, manuscript, input "
            "manifest, attempt, voice, and language"
        ),
    )
    asr = payload.get("audio_derived_asr")
    require(
        isinstance(asr, Mapping)
        and asr.get("model") == WHISPER_MODEL
        and asr.get("model_sha256") == WHISPER_SHA256
        and asr.get("settings") == ASR_SETTINGS
        and asr.get("source_blind") is True
        and asr.get("audio_derived") is True
        and asr.get("provider") == "local_openai_whisper",
        "REUSABLE_ASR_REPORT_INVALID",
        "reusable report model, settings, or source-blind contract changed",
    )
    reports = asr.get("reports")
    require(
        isinstance(reports, list),
        "REUSABLE_ASR_REPORT_INVALID",
        "reusable report has no ordered per-chunk ASR reports",
    )
    require(
        asr.get("chunk_count") == len(reports),
        "REUSABLE_ASR_REPORT_INVALID",
        "reusable report chunk count does not match its ordered reports",
    )
    report_objects: list[dict[str, Any]] = []
    seen_unit_ids: set[str] = set()
    for index, item in enumerate(reports):
        require(
            isinstance(item, dict)
            and item.get("index") == index
            and isinstance(item.get("unit_id"), str)
            and bool(item["unit_id"]),
            "REUSABLE_ASR_REPORT_INVALID",
            "reusable report units must be objects in exact indexed order",
        )
        require(
            item["unit_id"] not in seen_unit_ids,
            "REUSABLE_ASR_REPORT_DUPLICATE_UNIT",
            f"reusable report repeats unit_id {item['unit_id']}",
        )
        seen_unit_ids.add(item["unit_id"])
        report_objects.append(item)
    ordered_audio_hashes = [item.get("audio_sha256") for item in report_objects]
    ordered_transcript_hashes = [
        item.get("transcript_sha256") for item in report_objects
    ]
    prior_binding = {
        "schema_version": SCHEMA,
        "full_manifest_sha256": payload.get("full_manifest_sha256"),
        "source_sha256": payload.get("source_sha256"),
        "input_manifest_sha256": payload.get("input_manifest_sha256"),
        "attempt_fingerprint": payload.get("attempt_fingerprint"),
        "candidate_audio_sequence_sha256": payload.get(
            "candidate_audio_sequence_sha256"
        ),
        "candidate_binding_sha256": payload.get("candidate_binding_sha256"),
        "asr_model_sha256": asr.get("model_sha256"),
        "asr_settings": asr.get("settings"),
        "ordered_audio_hashes": ordered_audio_hashes,
        "ordered_transcript_hashes": ordered_transcript_hashes,
    }
    origin_fields_present = [
        "asr_evidence_origin" in item for item in report_objects
    ]
    require(
        not any(origin_fields_present) or all(origin_fields_present),
        "REUSABLE_ASR_REPORT_INVALID",
        "reusable report has a partial ASR evidence-origin binding",
    )
    prior_has_origin_binding = all(origin_fields_present)
    if prior_has_origin_binding:
        allowed_origins = {
            "local_source_blind_whisper",
            "exact_prior_private_report",
        }
        require(
            all(
                item.get("asr_evidence_origin") in allowed_origins
                and (
                    (
                        item["asr_evidence_origin"]
                        == "exact_prior_private_report"
                        and isinstance(item.get("reused_from_report_sha256"), str)
                        and len(item["reused_from_report_sha256"]) == 64
                        and all(
                            character in "0123456789abcdef"
                            for character in item["reused_from_report_sha256"]
                        )
                    )
                    or (
                        item["asr_evidence_origin"]
                        == "local_source_blind_whisper"
                        and item.get("reused_from_report_sha256") is None
                    )
                )
                for item in report_objects
            ),
            "REUSABLE_ASR_REPORT_INVALID",
            "reusable report has invalid per-unit ASR evidence provenance",
        )
        prior_reused_count = sum(
            item["asr_evidence_origin"] == "exact_prior_private_report"
            for item in report_objects
        )
        prior_reused_unit_ids = [
            item["unit_id"]
            for item in report_objects
            if item["asr_evidence_origin"] == "exact_prior_private_report"
        ]
        prior_reused_report_sha256s = sorted(
            {
                item["reused_from_report_sha256"]
                for item in report_objects
                if item["asr_evidence_origin"]
                == "exact_prior_private_report"
            }
        )
        require(
            asr.get("reused_local_asr_report_count") == prior_reused_count
            and asr.get("local_asr_run_count")
            == len(report_objects) - prior_reused_count,
            "REUSABLE_ASR_REPORT_INVALID",
            "reusable report ASR execution counts contradict unit provenance",
        )
        require(
            asr.get("reused_unit_ids") == prior_reused_unit_ids
            and asr.get("reused_report_sha256s")
            == prior_reused_report_sha256s,
            "REUSABLE_ASR_REPORT_INVALID",
            "reusable report aggregate provenance contradicts its units",
        )
        prior_binding["ordered_asr_evidence_origins"] = [
            item["asr_evidence_origin"] for item in report_objects
        ]
        prior_binding["ordered_reuse_report_sha256s"] = [
            item.get("reused_from_report_sha256") for item in report_objects
        ]
        prior_binding["ordered_unit_evidence"] = [
            {
                "index": item.get("index"),
                "unit_id": item.get("unit_id"),
                "source_text_sha256": item.get("source_text_sha256"),
                "audio_sha256": item.get("audio_sha256"),
                "duration_seconds": item.get("duration_seconds"),
                "transcript_sha256": item.get("transcript_sha256"),
                "word_timestamp_sha256": item.get("word_timestamp_sha256"),
            }
            for item in report_objects
        ]
    require(
        payload.get("qa_binding_sha256") == canonical_sha256(prior_binding)
        and payload.get("candidate_audio_sequence_sha256")
        == canonical_sha256(ordered_audio_hashes),
        "REUSABLE_ASR_REPORT_BINDING_MISMATCH",
        "reusable report's internal QA or ordered-audio binding is inconsistent",
    )
    by_id: dict[str, dict[str, Any]] = {}
    for item in report_objects:
        unit_id = item["unit_id"]
        by_id[unit_id] = {
            **item,
            "reused_from_report_sha256": expected_sha256,
        }
    return by_id


def reusable_unit_result(
    prior: Mapping[str, Any] | None,
    record: Mapping[str, Any],
    *,
    expected_index: int,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]] | None:
    """Return revalidated transcript/timestamps for one exact bound unit."""

    if not isinstance(prior, Mapping):
        return None
    duration = float(record["measured_duration_seconds"])
    if not (
        prior.get("index") == expected_index
        and prior.get("unit_id") == record["unit_id"]
        and prior.get("source_text_sha256") == record["text_sha256"]
        and prior.get("audio_sha256") == record["audio_sha256"]
    ):
        return None
    try:
        prior_duration = float(prior.get("duration_seconds"))
    except (TypeError, ValueError):
        return None
    if (
        not math.isfinite(duration)
        or not math.isfinite(prior_duration)
        or abs(prior_duration - duration) > 0.000001
    ):
        return None
    transcript = str(prior.get("transcript") or "").strip()
    if (
        not transcript
        or google_pipeline.sha256_text(transcript)
        != prior.get("transcript_sha256")
    ):
        return None
    stored_words = prior.get("audio_derived_word_timestamps")
    if not isinstance(stored_words, list) or not stored_words:
        return None
    raw_words: list[dict[str, Any]] = []
    try:
        for word in stored_words:
            start = float(word["start_seconds"])
            end = float(word["end_seconds"])
            probability = float(word.get("probability") or 0.0)
            if not all(math.isfinite(value) for value in (start, end, probability)):
                return None
            raw_words.append(
                {
                    "word": str(word["word"]),
                    "start": start,
                    "end": end,
                    "probability": probability,
                }
            )
    except (KeyError, TypeError, ValueError):
        return None
    words, anomalies = asr_common.verified_words(
        {
            "text": transcript,
            "segments": [{"start": 0.0, "end": duration, "words": raw_words}],
        },
        duration,
    )
    if (
        anomalies
        or canonical_sha256(words) != prior.get("word_timestamp_sha256")
        or prior.get("word_timestamp_evidence_valid") is not True
    ):
        return None
    return transcript, words, anomalies


def run_source_blind_asr(
    evidence: candidate_qa.CandidateEvidence,
    *,
    whisper_cache: Path,
    model_loader: Callable[..., Any] | None = None,
    reusable_reports: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    require(
        ASR_SETTINGS.get("initial_prompt") is None,
        "ASR_SOURCE_LEAK",
        "source text or vocabulary prompts are forbidden in full-title ASR",
    )
    require(
        ASR_SETTINGS.get("word_timestamps") is True,
        "ASR_TIMESTAMP_CONFIG_INVALID",
        "audio-derived word timestamps are mandatory",
    )
    model_path = whisper_cache.expanduser().resolve() / WHISPER_FILENAME
    require(
        model_path.is_file(),
        "ASR_MODEL_MISSING",
        f"pinned Whisper model is missing: {model_path}",
    )
    require(
        sha256_file(model_path) == WHISPER_SHA256,
        "ASR_MODEL_HASH_MISMATCH",
        "pinned Whisper model hash changed",
    )
    slug = str(evidence.manifest.get("slug") or "")
    reusable = reusable_reports or {}
    model: Any | None = None

    def get_model() -> Any:
        nonlocal model, model_loader
        if model is not None:
            return model
        if model_loader is None:
            try:
                import whisper  # noqa: PLC0415
            except ImportError as exc:
                raise FullAudioDerivedQAError(
                    "ASR_RUNTIME_MISSING",
                    "openai-whisper is required for local source-blind ASR",
                ) from exc
            model_loader = whisper.load_model
        model = model_loader(WHISPER_MODEL, download_root=str(whisper_cache))
        return model

    reports: list[dict[str, Any]] = []
    aggregate_transcripts: list[str] = []
    absolute_word_timestamps: list[dict[str, Any]] = []
    total_local_asr_runs = 0
    reused_local_asr_reports = 0
    for index, record in enumerate(evidence.records):
        audio_path = Path(str(record["audio_path"]))
        duration = float(record["measured_duration_seconds"])
        reusable_item = reusable.get(record["unit_id"])
        reused = reusable_unit_result(
            reusable_item,
            record,
            expected_index=index,
        )
        if reused is None:
            # Deliberately audio-only: source text is never supplied to Whisper.
            result = get_model().transcribe(str(audio_path), **ASR_SETTINGS)
            total_local_asr_runs += 1
            require(
                isinstance(result, Mapping),
                "ASR_RESULT_INVALID",
                f"{record['unit_id']}: local Whisper returned a non-object result",
            )
            transcript = str(result.get("text") or "").strip()
            words, anomalies = asr_common.verified_words(result, duration)
        else:
            transcript, words, anomalies = reused
            reused_local_asr_reports += 1
        evidence_origin = (
            "exact_prior_private_report"
            if reused is not None
            else "local_source_blind_whisper"
        )
        metrics = _evaluated_metrics(
            record["source_text"],
            transcript,
            slug=slug,
        )
        cue = evidence.measured_sync["cues"][index]
        absolute_words = _absolute_words(
            words,
            offset_seconds=float(cue["start_seconds"]),
        )
        audio_gate_metrics = {
            "score": metrics["score"],
            "coverage": metrics["coverage"],
            "token_order_similarity": (
                1.0 if metrics["ordered_content_integrity_pass"] is True else 0.0
            ),
            "first_words_match": metrics["first_words_match"],
            "last_words_match": metrics["last_words_match"],
            "frontmatter_absent": frontmatter_absent(transcript),
        }
        audio_gate_pass, audio_gate_blockers = audio_derived_asr_gate(
            audio_gate_metrics,
            word_timestamp_count=len(words),
        )
        passed = bool(
            metrics["pass"]
            and audio_gate_pass
            and words
            and not anomalies
            and frontmatter_absent(transcript)
        )
        reports.append(
            {
                "index": index,
                "unit_id": record["unit_id"],
                "source_text_sha256": record["text_sha256"],
                "audio_sha256": record["audio_sha256"],
                "duration_seconds": duration,
                "transcript": transcript,
                "transcript_sha256": google_pipeline.sha256_text(transcript),
                "audio_derived_word_timestamps": words,
                "absolute_audio_derived_word_timestamps": absolute_words,
                "word_timestamp_sha256": canonical_sha256(words),
                "word_timestamp_anomalies": anomalies,
                "word_timestamp_evidence_valid": bool(words) and not anomalies,
                "asr_evidence_origin": evidence_origin,
                "reused_from_report_sha256": (
                    reusable_item.get("reused_from_report_sha256")
                    if reused is not None and isinstance(reusable_item, Mapping)
                    else None
                ),
                "frontmatter_absent": frontmatter_absent(transcript),
                "audio_derived_asr_gate_pass": audio_gate_pass,
                "audio_derived_asr_gate_blockers": audio_gate_blockers,
                **metrics,
                "pass": passed,
            }
        )
        aggregate_transcripts.append(transcript)
        absolute_word_timestamps.extend(absolute_words)

    full_source = " ".join(record["source_text"] for record in evidence.records)
    full_transcript = " ".join(aggregate_transcripts)
    aggregate = _evaluated_metrics(
        full_source,
        full_transcript,
        slug=slug,
    )
    aggregate_audio_gate_metrics = {
        "score": aggregate["score"],
        "coverage": aggregate["coverage"],
        "token_order_similarity": (
            1.0 if aggregate["ordered_content_integrity_pass"] is True else 0.0
        ),
        "first_words_match": aggregate["first_words_match"],
        "last_words_match": aggregate["last_words_match"],
        "frontmatter_absent": frontmatter_absent(full_transcript),
    }
    aggregate_gate_pass, aggregate_gate_blockers = audio_derived_asr_gate(
        aggregate_audio_gate_metrics,
        word_timestamp_count=len(absolute_word_timestamps),
    )
    aggregate.update(
        {
            "transcript_sha256": google_pipeline.sha256_text(full_transcript),
            "frontmatter_absent": frontmatter_absent(full_transcript),
            "audio_derived_word_timestamp_count": len(absolute_word_timestamps),
            "audio_derived_word_timestamps_sha256": canonical_sha256(
                absolute_word_timestamps
            ),
            "audio_derived_asr_gate_pass": aggregate_gate_pass,
            "audio_derived_asr_gate_blockers": aggregate_gate_blockers,
            "pass": bool(
                aggregate["pass"]
                and aggregate_gate_pass
                and reports
                and all(report["pass"] for report in reports)
            ),
        }
    )
    reused_unit_ids = [
        report["unit_id"]
        for report in reports
        if report["asr_evidence_origin"] == "exact_prior_private_report"
    ]
    reused_report_sha256s = sorted(
        {
            str(report["reused_from_report_sha256"])
            for report in reports
            if report.get("reused_from_report_sha256")
        }
    )
    return {
        "status": "PASS" if aggregate["pass"] else "FAIL",
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "settings": ASR_SETTINGS,
        "source_blind": True,
        "audio_derived": True,
        "provider": "local_openai_whisper",
        "provider_calls_made": False,
        "local_asr_run_count": total_local_asr_runs,
        "reused_local_asr_report_count": reused_local_asr_reports,
        "reused_unit_ids": reused_unit_ids,
        "reused_report_sha256s": reused_report_sha256s,
        "chunk_count": len(reports),
        "required_score": ASR_SCORE_MIN,
        "required_coverage": ASR_COVERAGE_MIN,
        "reports": reports,
        "full_title_aggregate": aggregate,
    }


def measured_section_sync(
    evidence: candidate_qa.CandidateEvidence,
    asr: Mapping[str, Any],
) -> dict[str, Any]:
    reports = asr.get("reports") if isinstance(asr.get("reports"), list) else []
    report_by_id = {
        str(report.get("unit_id")): report
        for report in reports
        if isinstance(report, Mapping)
    }
    sections: list[dict[str, Any]] = []
    prior_end = 0.0
    for record, cue in zip(evidence.records, evidence.measured_sync["cues"]):
        report = report_by_id.get(record["unit_id"]) or {}
        start = float(cue["start_seconds"])
        end = float(cue["end_seconds"])
        duration = float(record["measured_duration_seconds"])
        contiguous = abs(start - prior_end) <= 0.000001
        duration_bound = abs((end - start) - duration) <= 0.000002
        binding_pass = bool(
            report.get("source_text_sha256") == record["text_sha256"]
            and report.get("audio_sha256") == record["audio_sha256"]
            and report.get("word_timestamp_evidence_valid") is True
            and report.get("pass") is True
            and contiguous
            and duration_bound
            and end > start
        )
        sections.append(
            {
                "unit_id": record["unit_id"],
                "source_text_sha256": record["text_sha256"],
                "audio_sha256": record["audio_sha256"],
                "start_seconds": round(start, 6),
                "end_seconds": round(end, 6),
                "duration_seconds": round(duration, 6),
                "source_score": report.get("score"),
                "source_coverage": report.get("coverage"),
                "audio_derived_word_timestamp_sha256": report.get(
                    "word_timestamp_sha256"
                ),
                "contiguous_measured_interval": contiguous,
                "duration_binding_pass": duration_bound,
                "binding_pass": binding_pass,
            }
        )
        prior_end = end

    aggregate = asr.get("full_title_aggregate")
    aggregate = aggregate if isinstance(aggregate, Mapping) else {}
    scores = [float(section.get("source_score") or 0.0) for section in sections]
    coverages = [
        float(section.get("source_coverage") or 0.0) for section in sections
    ]
    score = min(scores + [float(aggregate.get("score") or 0.0)]) if scores else 0.0
    coverage = (
        min(coverages + [float(aggregate.get("coverage") or 0.0)])
        if coverages
        else 0.0
    )
    expected_total = float(
        evidence.measured_sync["total_measured_duration_seconds"]
    )
    passed = bool(
        sections
        and len(sections) == len(evidence.records)
        and len(reports) == len(evidence.records)
        and all(section["binding_pass"] for section in sections)
        and abs(prior_end - expected_total) <= 0.000002
        and score >= SYNC_SCORE_MIN
        and coverage >= ASR_COVERAGE_MIN
        and aggregate.get("pass") is True
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "sync_tier": "PARAGRAPH_OR_SECTION_SYNC_PREMIUM",
        "granularity": "measured_source_bound_section",
        "sync_method": (
            "audio_derived_word_timestamps_with_measured_google_chunk_duration"
        ),
        "alignment_method": (
            "audio_derived_word_timestamps_with_measured_google_chunk_duration"
        ),
        "audio_derived_or_measured": True,
        "auto_estimated_sync": False,
        "public_word_level_sync_claim_allowed": False,
        "required_score": SYNC_SCORE_MIN,
        "required_coverage": ASR_COVERAGE_MIN,
        "sync_score": round(score, 4),
        "coverage": round(coverage, 4),
        "section_count": len(sections),
        "total_measured_duration_seconds": round(prior_end, 6),
        "sections": sections,
        "sync_pass": passed,
    }


def _blockers(
    asr: Mapping[str, Any],
    sync: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    reports = asr.get("reports") if isinstance(asr.get("reports"), list) else []
    for report in reports:
        if not isinstance(report, Mapping) or report.get("pass") is True:
            continue
        unit_id = str(report.get("unit_id") or "unknown")
        if float(report.get("score") or 0.0) < ASR_SCORE_MIN:
            blockers.append(
                f"{unit_id}: ASR_SOURCE_SCORE_BELOW_9_7 ({report.get('score')})"
            )
        if float(report.get("coverage") or 0.0) < ASR_COVERAGE_MIN:
            blockers.append(
                f"{unit_id}: ASR_SOURCE_COVERAGE_BELOW_0_98 ({report.get('coverage')})"
            )
        for field, code in (
            ("first_words_match", "FIRST_SPAN_MISMATCH"),
            ("last_words_match", "LAST_SPAN_MISMATCH"),
            ("no_missing_content", "MISSING_CONTENT"),
            ("no_duplicate_content", "DUPLICATED_CONTENT"),
            ("no_reordered_content", "REORDERED_CONTENT"),
            ("no_unexpected_content", "UNEXPECTED_CONTENT"),
        ):
            if report.get(field) is not True:
                blockers.append(f"{unit_id}: {code}")
        if report.get("word_timestamp_evidence_valid") is not True:
            blockers.append(f"{unit_id}: AUDIO_DERIVED_TIMESTAMPS_INVALID")
        if report.get("frontmatter_absent") is not True:
            blockers.append(f"{unit_id}: FRONTMATTER_IN_ASR_TRANSCRIPT")
    aggregate = asr.get("full_title_aggregate")
    aggregate = aggregate if isinstance(aggregate, Mapping) else {}
    if aggregate.get("pass") is not True:
        blockers.append("FULL_TITLE_ASR_SOURCE_ORDER_OR_BOUNDARY_GATE_FAILED")
        blockers.extend(
            str(item)
            for item in aggregate.get("audio_derived_asr_gate_blockers") or []
        )
    if sync.get("sync_pass") is not True:
        blockers.append("MEASURED_PARAGRAPH_OR_SECTION_SYNC_FAILED")
    return list(dict.fromkeys(blockers))


def build_report(
    evidence: candidate_qa.CandidateEvidence,
    *,
    attempt_fingerprint: str,
    asr: Mapping[str, Any],
    sync: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = _blockers(asr, sync)
    objective_pass = bool(
        asr.get("status") == "PASS"
        and sync.get("sync_pass") is True
        and not blockers
    )
    binding = {
        "schema_version": SCHEMA,
        "full_manifest_sha256": evidence.manifest_sha256,
        "source_sha256": evidence.source_sha256,
        "input_manifest_sha256": evidence.input_manifest_sha256,
        "attempt_fingerprint": attempt_fingerprint,
        "candidate_audio_sequence_sha256": evidence.candidate_audio_sequence_sha256,
        "candidate_binding_sha256": evidence.candidate_binding_sha256,
        "asr_model_sha256": WHISPER_SHA256,
        "asr_settings": ASR_SETTINGS,
        "ordered_audio_hashes": [
            record["audio_sha256"] for record in evidence.records
        ],
        "ordered_transcript_hashes": [
            report["transcript_sha256"] for report in asr["reports"]
        ],
        "ordered_asr_evidence_origins": [
            report["asr_evidence_origin"] for report in asr["reports"]
        ],
        "ordered_reuse_report_sha256s": [
            report["reused_from_report_sha256"] for report in asr["reports"]
        ],
        "ordered_unit_evidence": [
            {
                "index": report["index"],
                "unit_id": report["unit_id"],
                "source_text_sha256": report["source_text_sha256"],
                "audio_sha256": report["audio_sha256"],
                "duration_seconds": report["duration_seconds"],
                "transcript_sha256": report["transcript_sha256"],
                "word_timestamp_sha256": report["word_timestamp_sha256"],
            }
            for report in asr["reports"]
        ],
    }
    return {
        "schema_version": SCHEMA,
        "status": (
            "FULL_AUDIO_DERIVED_ASR_SYNC_PASS_PRIVATE_ONLY"
            if objective_pass
            else "FULL_AUDIO_DERIVED_ASR_SYNC_BLOCKED"
        ),
        "slug": evidence.manifest.get("slug"),
        "title": evidence.manifest.get("title"),
        "author": evidence.manifest.get("author"),
        "provider": "google",
        "voice": evidence.manifest.get("voice"),
        "language_code": evidence.manifest.get("language_code"),
        "full_manifest_path": str(evidence.manifest_path),
        "full_manifest_sha256": evidence.manifest_sha256,
        "source_path": str(evidence.source_path),
        "source_sha256": evidence.source_sha256,
        "input_manifest_path": str(evidence.input_manifest_path),
        "input_manifest_sha256": evidence.input_manifest_sha256,
        "attempt_fingerprint": attempt_fingerprint,
        "candidate_audio_sequence_sha256": evidence.candidate_audio_sequence_sha256,
        "candidate_binding_sha256": evidence.candidate_binding_sha256,
        "qa_binding_sha256": canonical_sha256(binding),
        "construction_provenance": {
            **evidence.construction,
            "satisfies_audio_derived_asr_gate": False,
        },
        "audio_derived_asr": asr,
        "measured_sync": sync,
        "objective_pass": objective_pass,
        "blockers": blockers,
        "next_stage": (
            "FULL_TITLE_LISTENING_QA_PRIVATE_ONLY"
            if objective_pass
            else "STOP_NO_LISTENING_UPLOAD_OR_RELEASE"
        ),
        "private_output_only": True,
        "public_release_approved": False,
        "provider_calls_made_by_adapter": False,
        "network_calls_made_by_adapter": False,
        "listening_qa_called": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "paid_lock_read_or_written": False,
    }


def blocked_report(manifest_path: Path, blocker: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "status": "FULL_AUDIO_DERIVED_ASR_SYNC_BLOCKED",
        "full_manifest_path": str(manifest_path.expanduser().resolve()),
        "objective_pass": False,
        "blockers": [blocker],
        "next_stage": "STOP_NO_LISTENING_UPLOAD_OR_RELEASE",
        "private_output_only": True,
        "public_release_approved": False,
        "provider_calls_made_by_adapter": False,
        "network_calls_made_by_adapter": False,
        "listening_qa_called": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "paid_lock_read_or_written": False,
    }


def evaluate(
    manifest_path: Path,
    output_path: Path,
    *,
    whisper_cache: Path = DEFAULT_WHISPER_CACHE,
    model_loader: Callable[..., Any] | None = None,
    duration_getter: Callable[[Path], float] = candidate_qa.ffprobe_duration,
    reuse_report_path: Path | None = None,
    reuse_report_sha256: str | None = None,
) -> tuple[int, dict[str, Any]]:
    manifest = manifest_path.expanduser().resolve()
    output = output_path.expanduser().resolve()
    try:
        output = validate_output_path(output, manifest.parent)
    except FullAudioDerivedQAError as exc:
        return 2, blocked_report(manifest, exc.blocker)
    try:
        evidence = validate_contract(
            manifest,
            duration_getter=duration_getter,
        )
        fingerprint = validate_attempt_binding(evidence)
        reusable_reports = load_reusable_asr_reports(
            reuse_report_path,
            reuse_report_sha256,
            evidence,
            fingerprint,
        )
        asr = run_source_blind_asr(
            evidence,
            whisper_cache=whisper_cache,
            model_loader=model_loader,
            reusable_reports=reusable_reports,
        )
        sync = measured_section_sync(evidence, asr)
        report = build_report(
            evidence,
            attempt_fingerprint=fingerprint,
            asr=asr,
            sync=sync,
        )
    except FullAudioDerivedQAError as exc:
        report = blocked_report(manifest, exc.blocker)
        atomic_write_json(output, report)
        return 2, report
    except Exception as exc:  # noqa: BLE001
        report = blocked_report(
            manifest,
            f"ASR_RUNTIME_FAILED: {type(exc).__name__}: {exc}",
        )
        atomic_write_json(output, report)
        return 2, report
    atomic_write_json(output, report)
    return (0 if report["objective_pass"] else 3), report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-manifest", required=True, type=Path)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--reuse-report",
        type=Path,
        help=(
            "Prior private report from this adapter. Exact byte-identical units "
            "are revalidated and reused; changed units are transcribed locally."
        ),
    )
    parser.add_argument(
        "--reuse-report-sha256",
        help=(
            "Independently recorded exact SHA-256 of --reuse-report. Required "
            "with --reuse-report so mutable paths cannot become trust anchors."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    returncode, report = evaluate(
        args.full_manifest,
        args.output,
        whisper_cache=args.whisper_cache,
        reuse_report_path=args.reuse_report,
        reuse_report_sha256=args.reuse_report_sha256,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "objective_pass": report["objective_pass"],
                "output": str(args.output.expanduser().resolve()),
                "blockers": report["blockers"],
                "provider_calls_made_by_adapter": False,
                "upload_performed": False,
                "publication_performed": False,
                "release_mutation_performed": False,
                "paid_lock_read_or_written": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
