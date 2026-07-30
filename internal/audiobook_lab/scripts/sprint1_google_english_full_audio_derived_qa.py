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
    audition_hash = str(manifest.get("audition_evidence_sha256") or "")
    require(
        len(audition_hash) == 64
        and all(character in "0123456789abcdef" for character in audition_hash),
        "AUDITION_BINDING_MISSING",
        "full manifest lacks a valid hash binding to passing representative evidence",
    )
    return expected


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


def run_source_blind_asr(
    evidence: candidate_qa.CandidateEvidence,
    *,
    whisper_cache: Path,
    model_loader: Callable[..., Any] | None = None,
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
    slug = str(evidence.manifest.get("slug") or "")

    reports: list[dict[str, Any]] = []
    aggregate_transcripts: list[str] = []
    absolute_word_timestamps: list[dict[str, Any]] = []
    total_local_asr_runs = 0
    for index, record in enumerate(evidence.records):
        audio_path = Path(str(record["audio_path"]))
        duration = float(record["measured_duration_seconds"])
        # Deliberately audio-only: the source text is never supplied to Whisper.
        result = model.transcribe(str(audio_path), **ASR_SETTINGS)
        total_local_asr_runs += 1
        require(
            isinstance(result, Mapping),
            "ASR_RESULT_INVALID",
            f"{record['unit_id']}: local Whisper returned a non-object result",
        )
        transcript = str(result.get("text") or "").strip()
        metrics = _evaluated_metrics(
            record["source_text"],
            transcript,
            slug=slug,
        )
        words, anomalies = asr_common.verified_words(result, duration)
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
        asr = run_source_blind_asr(
            evidence,
            whisper_cache=whisper_cache,
            model_loader=model_loader,
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    returncode, report = evaluate(
        args.full_manifest,
        args.output,
        whisper_cache=args.whisper_cache,
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
