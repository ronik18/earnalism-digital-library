#!/usr/bin/env python3
"""Run fail-closed objective QA for four private Google English samples.

The adapter consumes the private audition manifest and the pending-listening
artifact created by ``sprint1_google_english_private_pipeline.py``. It performs
no synthesis and makes no provider or listening call. It verifies the copied
source, input manifest, audition manifest, evidence, passage selection, audio
paths and hashes before running pinned local Whisper medium.en source-blind.

An objective report is always written. A separate listening-input artifact is
written only when all four samples pass every objective gate.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPT_DIR / "factory_hooks"
sys.path[:0] = [str(SCRIPT_DIR), str(HOOK_DIR)]

import sprint1_gift_kokoro_full_title_private_qa as asr_common  # noqa: E402
import sprint1_google_english_private_pipeline as google_pipeline  # noqa: E402
import sprint1_kokoro_title_private_audition as whisper_common  # noqa: E402
from common import ffprobe_duration  # noqa: E402


SCHEMA = "earnalism.google_english_representative_objective_qa.v1"
LISTENING_INPUT_SCHEMA = google_pipeline.LISTENING_SCHEMA
PASSAGE_IDS = tuple(google_pipeline.PASSAGE_IDS)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
WHISPER_MODEL = whisper_common.WHISPER_MODEL
WHISPER_FILENAME = whisper_common.WHISPER_FILENAME
WHISPER_SHA256 = whisper_common.WHISPER_SHA256
ASR_SETTINGS = dict(asr_common.ASR_SETTINGS)
DEFAULT_WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/whisper-cache"
)
FORBIDDEN_COMPONENTS = frozenset(
    {"build", "dist", "frontend", "public", "release", "releases", "static", "uploads"}
)
NUMBER_WORDS = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety",
}
WORDS_TO_NUMBER = {
    tuple(
        (
            NUMBER_WORDS[number // 10 * 10],
            NUMBER_WORDS[number % 10],
        )
        if number > 20 and number % 10
        else (NUMBER_WORDS[number],)
    ): number
    for number in range(100)
    if number in NUMBER_WORDS
    or (
        number > 20
        and number // 10 * 10 in NUMBER_WORDS
        and number % 10 in NUMBER_WORDS
    )
}


class GoogleObjectiveQAError(RuntimeError):
    """Raised when any private input or objective gate contract is invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GoogleObjectiveQAError(message)


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    require(path.is_file(), f"{label} is missing: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GoogleObjectiveQAError(f"{label} is invalid JSON: {path}") from exc
    require(isinstance(payload, dict), f"{label} must be one JSON object")
    return payload, raw


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_private_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    forbidden = {part.casefold() for part in resolved.parts} & FORBIDDEN_COMPONENTS
    require(not forbidden, f"private root contains forbidden components: {sorted(forbidden)}")
    require(
        not is_within(resolved, ROOT.resolve()),
        "private root must not be inside the repository",
    )
    return resolved


def validate_private_path(
    path: Path,
    *,
    private_root: Path,
    label: str,
    must_exist: bool = True,
) -> Path:
    resolved = path.expanduser().resolve()
    require(is_within(resolved, private_root), f"{label} is outside the private root")
    forbidden = {part.casefold() for part in resolved.parts} & FORBIDDEN_COMPONENTS
    require(not forbidden, f"{label} contains forbidden path components")
    if must_exist:
        require(resolved.is_file(), f"{label} is missing: {resolved}")
    return resolved


def exact_records(
    values: Sequence[Mapping[str, Any]],
    id_key: str,
    label: str,
) -> dict[str, Mapping[str, Any]]:
    require(len(values) == len(PASSAGE_IDS), f"{label} must contain exactly four samples")
    result: dict[str, Mapping[str, Any]] = {}
    for value in values:
        require(isinstance(value, Mapping), f"{label} contains a non-object")
        passage_id = str(value.get(id_key) or "")
        require(passage_id in PASSAGE_IDS, f"{label} has invalid passage id: {passage_id}")
        require(passage_id not in result, f"{label} duplicates passage id: {passage_id}")
        result[passage_id] = value
    require(tuple(result) == PASSAGE_IDS, f"{label} order must be {PASSAGE_IDS}")
    return result


def parse_number_tokens(tokens: Sequence[str]) -> tuple[int, str] | None:
    if len(tokens) == 1 and tokens[0].isdigit():
        value = int(tokens[0])
        if 0 <= value <= 99:
            return value, "digits"
    value = WORDS_TO_NUMBER.get(tuple(tokens))
    return (value, "words") if value is not None else None


def apply_spoken_number_equivalences(
    source: str,
    transcript: str,
) -> tuple[str, str, list[dict[str, Any]]]:
    """Normalize only aligned standalone 0-99 digit/word substitutions."""
    source_tokens = whisper_common.lexical_tokens(source)
    transcript_tokens = whisper_common.lexical_tokens(transcript)
    source_case_value = (
        source.replace("’", "'").replace("‘", "'").replace("—", " ").replace("–", " ")
    )
    transcript_case_value = (
        transcript.replace("’", "'")
        .replace("‘", "'")
        .replace("—", " ")
        .replace("–", " ")
    )
    source_case_tokens = re.findall(
        r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", source_case_value
    )
    transcript_case_tokens = re.findall(
        r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", transcript_case_value
    )
    require(
        len(source_case_tokens) == len(source_tokens)
        and len(transcript_case_tokens) == len(transcript_tokens),
        "case-preserving tokenization diverged",
    )
    matcher = SequenceMatcher(None, source_tokens, transcript_tokens, autojunk=False)
    evaluated_source: list[str] = []
    evaluated_transcript: list[str] = []
    applications: list[dict[str, Any]] = []
    for tag, source_start, source_end, transcript_start, transcript_end in matcher.get_opcodes():
        source_slice = source_tokens[source_start:source_end]
        transcript_slice = transcript_tokens[transcript_start:transcript_end]
        source_number = parse_number_tokens(source_slice) if tag == "replace" else None
        transcript_number = (
            parse_number_tokens(transcript_slice) if tag == "replace" else None
        )
        if (
            source_number
            and transcript_number
            and source_number[0] == transcript_number[0]
            and {source_number[1], transcript_number[1]} == {"digits", "words"}
        ):
            canonical = f"num{source_number[0]}"
            evaluated_source.append(canonical)
            evaluated_transcript.append(canonical)
            applications.append(
                {
                    "source_range": [source_start, source_end],
                    "transcript_range": [transcript_start, transcript_end],
                    "source_tokens": source_slice,
                    "transcript_tokens": transcript_slice,
                    "canonical_token": canonical,
                    "reason": "STANDALONE_0_99_DIGIT_WORD_EQUIVALENCE",
                }
            )
        elif (
            len(source_slice) == 1
            and len(transcript_slice) == 1
            and {source_slice[0], transcript_slice[0]}
            == {"neighbouring", "neighboring"}
            and source_case_tokens[source_start:source_end] == source_slice
            and transcript_case_tokens[transcript_start:transcript_end]
            == transcript_slice
        ):
            canonical = "orth_neighbouring"
            evaluated_source.append(canonical)
            evaluated_transcript.append(canonical)
            applications.append(
                {
                    "source_range": [source_start, source_end],
                    "transcript_range": [transcript_start, transcript_end],
                    "source_tokens": source_slice,
                    "transcript_tokens": transcript_slice,
                    "canonical_token": canonical,
                    "reason": (
                        "EXPLICIT_STANDALONE_BRITISH_AMERICAN_ORTHOGRAPHY_"
                        "NEIGHBOURING_NEIGHBORING"
                    ),
                }
            )
        else:
            evaluated_source.extend(source_slice)
            evaluated_transcript.extend(transcript_slice)
    return " ".join(evaluated_source), " ".join(evaluated_transcript), applications


def validate_input_contract(
    *,
    audition_manifest_path: Path,
    audition_evidence_path: Path,
    private_root: Path,
) -> dict[str, Any]:
    root = validate_private_root(private_root)
    manifest_path = validate_private_path(
        audition_manifest_path,
        private_root=root,
        label="audition manifest",
    )
    evidence_path = validate_private_path(
        audition_evidence_path,
        private_root=root,
        label="audition evidence",
    )
    manifest, manifest_bytes = load_json(manifest_path, "audition manifest")
    evidence, evidence_bytes = load_json(evidence_path, "audition evidence")

    require(
        manifest.get("schema_version") == google_pipeline.PIPELINE_SCHEMA,
        "audition manifest schema changed",
    )
    require(manifest.get("mode") == "audition", "manifest is not an audition")
    require(
        manifest.get("status") == "AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED",
        "audition manifest status is not audio-ready",
    )
    require(manifest.get("provider") == "google", "manifest provider is not Google")
    require(manifest.get("provider_calls_ran") is True, "manifest lacks provider-call evidence")
    require(manifest.get("synthesis_calls") == 4, "manifest must prove exactly four synthesis calls")
    require(manifest.get("private_output_only") is True, "manifest is not private-only")
    require(
        manifest.get("paid_lock_restored_byte_for_byte") is True,
        "audition paid lock was not restored",
    )
    for field in ("upload_performed", "publication_performed", "release_mutation_performed"):
        require(manifest.get(field) is False, f"manifest {field} must be false")

    require(
        evidence.get("schema_version") == google_pipeline.LISTENING_SCHEMA,
        "audition evidence schema changed",
    )
    require(
        evidence.get("status") == "PENDING_LISTENING_REVIEW",
        "audition evidence status is invalid",
    )
    require(evidence.get("provider") == "google", "evidence provider is not Google")
    require(evidence.get("private_output_only") is True, "evidence is not private-only")
    for field in ("upload_performed", "publication_performed", "release_mutation_performed"):
        require(evidence.get(field) is False, f"evidence {field} must be false")

    declared_manifest_path = Path(str(evidence.get("audition_manifest_path") or ""))
    require(
        declared_manifest_path.expanduser().resolve() == manifest_path,
        "evidence audition_manifest_path does not bind the supplied manifest",
    )
    manifest_sha256 = sha256_bytes(manifest_bytes)
    require(
        evidence.get("audition_manifest_sha256") == manifest_sha256,
        "evidence audition manifest hash is stale",
    )

    source_copy = validate_private_path(
        Path(str(manifest.get("sanitized_source_copy") or "")),
        private_root=root,
        label="sanitized source copy",
    )
    input_manifest_copy = validate_private_path(
        Path(str(manifest.get("input_manifest_copy") or "")),
        private_root=root,
        label="input manifest copy",
    )
    try:
        bundle = google_pipeline.load_source_bundle(source_copy, input_manifest_copy)
    except (OSError, google_pipeline.PipelineError) as exc:
        raise GoogleObjectiveQAError(f"source bundle validation failed: {exc}") from exc

    fingerprint = str(manifest.get("attempt_fingerprint") or "")
    require(len(fingerprint) == 64, "audition fingerprint is invalid")
    for payload, label in ((manifest, "manifest"), (evidence, "evidence")):
        require(payload.get("slug") == bundle.slug, f"{label} slug mismatch")
        require(payload.get("source_sha256") == bundle.source_sha256, f"{label} source hash mismatch")
        require(
            payload.get("input_manifest_sha256") == bundle.manifest_sha256,
            f"{label} input manifest hash mismatch",
        )
        fingerprint_key = (
            "attempt_fingerprint" if label == "manifest" else "audition_fingerprint"
        )
        require(payload.get(fingerprint_key) == fingerprint, f"{label} fingerprint mismatch")

    passages = google_pipeline.select_representative_passages(bundle.source_text)
    passage_by_id = exact_records(passages, "passage_id", "recomputed passages")
    manifest_passages = exact_records(
        manifest.get("representative_passages") or [],
        "passage_id",
        "manifest representative passages",
    )
    generated = exact_records(
        manifest.get("generated_audio") or [],
        "unit_id",
        "manifest generated audio",
    )
    evidence_samples = exact_records(
        evidence.get("samples") or [],
        "passage_id",
        "evidence samples",
    )
    require(
        tuple(evidence.get("required_passages") or ()) == PASSAGE_IDS,
        "evidence required passage order changed",
    )
    require(
        list(manifest.get("unit_hashes") or [])
        == [passage_by_id[item]["text_sha256"] for item in PASSAGE_IDS],
        "manifest unit hashes do not match recomputed passages",
    )

    records: list[dict[str, Any]] = []
    for passage_id in PASSAGE_IDS:
        passage = passage_by_id[passage_id]
        manifest_passage = manifest_passages[passage_id]
        generated_record = generated[passage_id]
        evidence_record = evidence_samples[passage_id]
        source_hash = passage["text_sha256"]
        require(
            manifest_passage.get("text_sha256") == source_hash,
            f"{passage_id}: manifest passage hash is stale",
        )
        require(
            generated_record.get("text_sha256") == source_hash,
            f"{passage_id}: generated source hash is stale",
        )
        require(
            evidence_record.get("source_text_sha256") == source_hash,
            f"{passage_id}: evidence source hash is stale",
        )
        audio_path = validate_private_path(
            Path(str(generated_record.get("audio_path") or "")),
            private_root=root,
            label=f"{passage_id} audio",
        )
        require(
            Path(str(evidence_record.get("audio_path") or "")).expanduser().resolve()
            == audio_path,
            f"{passage_id}: evidence audio path mismatch",
        )
        observed_audio_sha = sha256_file(audio_path)
        for record, label in (
            (generated_record, "manifest"),
            (evidence_record, "evidence"),
        ):
            require(
                record.get("audio_sha256") == observed_audio_sha,
                f"{passage_id}: {label} audio hash is stale",
            )
        require(
            int(generated_record.get("audio_size_bytes") or 0) == audio_path.stat().st_size,
            f"{passage_id}: audio size mismatch",
        )
        header = audio_path.read_bytes()[:3]
        require(
            header.startswith(b"ID3") or header[:1] == b"\xff",
            f"{passage_id}: audio is not an MP3",
        )
        records.append(
            {
                "passage_id": passage_id,
                "source_text": passage["text"],
                "source_text_sha256": source_hash,
                "audio_path": str(audio_path),
                "audio_sha256": observed_audio_sha,
                "audio_size_bytes": audio_path.stat().st_size,
            }
        )

    return {
        "private_root": root,
        "bundle": bundle,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_sha256": manifest_sha256,
        "evidence": evidence,
        "evidence_path": evidence_path,
        "evidence_sha256": sha256_bytes(evidence_bytes),
        "attempt_fingerprint": fingerprint,
        "records": records,
    }


def evaluate_transcription(
    *,
    source_text: str,
    source_text_sha256: str,
    audio_sha256: str,
    result: Mapping[str, Any],
    duration_seconds: float,
) -> dict[str, Any]:
    transcript = str(result.get("text") or "").strip()
    raw_metrics = whisper_common.ordered_token_integrity(source_text, transcript)
    normalized_source, normalized_transcript, equivalences = (
        apply_spoken_number_equivalences(source_text, transcript)
    )
    normalized_metrics = whisper_common.ordered_token_integrity(
        normalized_source, normalized_transcript
    )
    words, anomalies = asr_common.verified_words(result, duration_seconds)
    passed = bool(
        float(normalized_metrics["score"]) >= ASR_SCORE_MIN
        and float(normalized_metrics["coverage"]) >= ASR_COVERAGE_MIN
        and normalized_metrics["first_words_match"] is True
        and normalized_metrics["last_words_match"] is True
        and normalized_metrics["ordered_content_integrity_pass"] is True
        and normalized_metrics["no_missing_content"] is True
        and normalized_metrics["no_duplicate_content"] is True
        and normalized_metrics["no_reordered_content"] is True
        and normalized_metrics["no_unexpected_content"] is True
        and words
        and not anomalies
    )
    return {
        "source_text_sha256": source_text_sha256,
        "audio_sha256": audio_sha256,
        "transcript": transcript,
        "transcript_sha256": google_pipeline.sha256_text(transcript),
        "raw_source_sha256": google_pipeline.sha256_text(source_text),
        "raw_metrics": raw_metrics,
        "explicit_equivalences_applied": equivalences,
        "spoken_number_equivalences_applied": [
            item
            for item in equivalences
            if item["reason"] == "STANDALONE_0_99_DIGIT_WORD_EQUIVALENCE"
        ],
        "orthography_equivalences_applied": [
            item
            for item in equivalences
            if item["reason"].startswith(
                "EXPLICIT_STANDALONE_BRITISH_AMERICAN_ORTHOGRAPHY_"
            )
        ],
        "normalized_source_sha256": google_pipeline.sha256_text(normalized_source),
        "normalized_transcript_sha256": google_pipeline.sha256_text(
            normalized_transcript
        ),
        "normalized_metrics": normalized_metrics,
        "audio_derived_word_timestamps": words,
        "word_timestamp_anomalies": anomalies,
        "word_timestamp_evidence_valid": bool(words) and not anomalies,
        **normalized_metrics,
        "pass": passed,
    }


def run_source_blind_asr(
    records: Sequence[Mapping[str, Any]],
    *,
    whisper_cache: Path,
    model_loader: Callable[..., Any] | None = None,
    duration_getter: Callable[[Path], float | None] = ffprobe_duration,
) -> dict[str, Any]:
    require(len(records) == 4, "ASR requires exactly four records")
    require(ASR_SETTINGS.get("initial_prompt") is None, "ASR prompt injection is forbidden")
    require(ASR_SETTINGS.get("word_timestamps") is True, "word timestamps are required")
    model_path = whisper_cache.expanduser().resolve() / WHISPER_FILENAME
    require(model_path.is_file(), f"pinned Whisper model is missing: {model_path}")
    require(sha256_file(model_path) == WHISPER_SHA256, "pinned Whisper hash mismatch")
    if model_loader is None:
        try:
            import whisper  # noqa: PLC0415
        except ImportError as exc:
            raise GoogleObjectiveQAError("openai-whisper is required") from exc
        model_loader = whisper.load_model
    model = model_loader(WHISPER_MODEL, download_root=str(whisper_cache))

    reports: list[dict[str, Any]] = []
    for record in records:
        audio_path = Path(str(record["audio_path"]))
        duration = float(duration_getter(audio_path) or 0.0)
        require(duration > 0, f"{record['passage_id']}: measured audio duration missing")
        # Deliberately audio-only: no source text or initial prompt reaches Whisper.
        result = model.transcribe(str(audio_path), **ASR_SETTINGS)
        report = evaluate_transcription(
            source_text=str(record["source_text"]),
            source_text_sha256=str(record["source_text_sha256"]),
            audio_sha256=str(record["audio_sha256"]),
            result=result,
            duration_seconds=duration,
        )
        reports.append(
            {
                "passage_id": record["passage_id"],
                "duration_seconds": round(duration, 6),
                **report,
            }
        )
    passed = bool(len(reports) == 4 and all(report["pass"] for report in reports))
    return {
        "status": "PASS" if passed else "FAIL",
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "settings": ASR_SETTINGS,
        "source_blind": True,
        "sample_count": 4,
        "required_score": ASR_SCORE_MIN,
        "required_coverage": ASR_COVERAGE_MIN,
        "reports": reports,
    }


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def build_objective_report(contract: Mapping[str, Any], asr: Mapping[str, Any]) -> dict[str, Any]:
    bundle = contract["bundle"]
    passed = asr["status"] == "PASS"
    return {
        "schema_version": SCHEMA,
        "status": (
            "REPRESENTATIVE_OBJECTIVE_PASS_LISTENING_INPUT_READY"
            if passed
            else "REPRESENTATIVE_OBJECTIVE_FAIL_LISTENING_BLOCKED"
        ),
        "generated_at": utc_now(),
        "slug": bundle.slug,
        "title": bundle.title,
        "author": bundle.author,
        "provider": "google",
        "voice": contract["manifest"].get("voice"),
        "source_sha256": bundle.source_sha256,
        "input_manifest_sha256": bundle.manifest_sha256,
        "audition_fingerprint": contract["attempt_fingerprint"],
        "audition_manifest_sha256": contract["manifest_sha256"],
        "audition_evidence_sha256": contract["evidence_sha256"],
        "objective_asr": asr,
        "objective_pass": passed,
        "listening_qa_called": False,
        "provider_calls_made": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "paid_lock_read_or_written": False,
        "public_release_approved": False,
    }


def build_listening_input(
    *,
    contract: Mapping[str, Any],
    objective_report_path: Path,
    objective_report_sha256: str,
) -> dict[str, Any]:
    bundle = contract["bundle"]
    return {
        "schema_version": LISTENING_INPUT_SCHEMA,
        "status": "PENDING_LISTENING_REVIEW",
        "generated_at": utc_now(),
        "slug": bundle.slug,
        "title": bundle.title,
        "author": bundle.author,
        "provider": "google",
        "voice": contract["manifest"].get("voice"),
        "source_sha256": bundle.source_sha256,
        "input_manifest_sha256": bundle.manifest_sha256,
        "audition_fingerprint": contract["attempt_fingerprint"],
        "audition_manifest_path": str(contract["manifest_path"]),
        "audition_manifest_sha256": contract["manifest_sha256"],
        "audition_evidence_sha256": contract["evidence_sha256"],
        "objective_report_path": str(objective_report_path),
        "objective_report_sha256": objective_report_sha256,
        "objective_gate_status": "PASS",
        "minimum_listening_score": contract["evidence"].get(
            "minimum_listening_score"
        ),
        "minimum_listening_confidence": contract["evidence"].get(
            "minimum_listening_confidence"
        ),
        "per_dimension_score_min": contract["evidence"].get(
            "per_dimension_score_min"
        ),
        "anti_robotic_texture_score_min": contract["evidence"].get(
            "anti_robotic_texture_score_min"
        ),
        "anti_choppy_join_score_min": contract["evidence"].get(
            "anti_choppy_join_score_min"
        ),
        "required_passages": list(PASSAGE_IDS),
        "fatal_flags_required_false": list(google_pipeline.FATAL_LISTENING_FLAGS),
        "samples": [
            {
                "passage_id": record["passage_id"],
                "source_text_sha256": record["source_text_sha256"],
                "audio_path": record["audio_path"],
                "audio_sha256": record["audio_sha256"],
                "overall_listening_score": None,
                "confidence_score": None,
                "scores": {},
                "fatal_flags": [],
                "judge_flags": {
                    flag: False for flag in google_pipeline.FATAL_LISTENING_FLAGS
                },
                "review_notes": "",
            }
            for record in contract["records"]
        ],
        "private_output_only": True,
        "listening_qa_called": False,
        "provider_calls_ran": True,
        "provider_calls_made_by_adapter": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "paid_lock_read_or_written": False,
    }


def run_adapter(
    *,
    audition_manifest_path: Path,
    audition_evidence_path: Path,
    private_root: Path,
    whisper_cache: Path,
    objective_report_path: Path,
    listening_input_path: Path,
    model_loader: Callable[..., Any] | None = None,
    duration_getter: Callable[[Path], float | None] = ffprobe_duration,
) -> dict[str, Any]:
    root = validate_private_root(private_root)
    objective_path = validate_private_path(
        objective_report_path,
        private_root=root,
        label="objective report output",
        must_exist=False,
    )
    listening_path = validate_private_path(
        listening_input_path,
        private_root=root,
        label="listening input output",
        must_exist=False,
    )
    require(not objective_path.exists(), "objective report output already exists")
    require(not listening_path.exists(), "listening input output already exists")
    contract = validate_input_contract(
        audition_manifest_path=audition_manifest_path,
        audition_evidence_path=audition_evidence_path,
        private_root=root,
    )
    asr = run_source_blind_asr(
        contract["records"],
        whisper_cache=whisper_cache,
        model_loader=model_loader,
        duration_getter=duration_getter,
    )
    report = build_objective_report(contract, asr)
    atomic_write_json(objective_path, report)
    if report["objective_pass"]:
        report_sha256 = sha256_file(objective_path)
        listening = build_listening_input(
            contract=contract,
            objective_report_path=objective_path,
            objective_report_sha256=report_sha256,
        )
        atomic_write_json(listening_path, listening)
        report["listening_input_path"] = str(listening_path)
        report["listening_input_sha256"] = sha256_file(listening_path)
    else:
        report["listening_input_created"] = False
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audition-manifest", required=True, type=Path)
    parser.add_argument("--audition-evidence", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--objective-report", required=True, type=Path)
    parser.add_argument("--listening-input", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run_adapter(
            audition_manifest_path=args.audition_manifest,
            audition_evidence_path=args.audition_evidence,
            private_root=args.private_root,
            whisper_cache=args.whisper_cache,
            objective_report_path=args.objective_report,
            listening_input_path=args.listening_input,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["objective_pass"] else 3
    except GoogleObjectiveQAError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
