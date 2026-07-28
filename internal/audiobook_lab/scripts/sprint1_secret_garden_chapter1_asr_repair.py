#!/usr/bin/env python3
"""Run one retained-audio ASR repair for Secret Garden chapter 1.

Only the ten sections that failed exact content or timestamp integrity are
decoded again. The immutable WAVs are not synthesized, edited, or trimmed.
Passage-scoped spelling equivalences cannot remove unexpected speech or invent
missing source words. No provider, listening, upload, publication, or release
state call is possible.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
CANARY_PATH = Path(__file__).with_name(
    "sprint1_secret_garden_chapter1_private_canary.py"
)
SPEC = importlib.util.spec_from_file_location(
    "secret_garden_chapter1_canary", CANARY_PATH
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load chapter canary: {CANARY_PATH}")
CANARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CANARY)


SCHEMA = "earnalism.secret_garden_chapter1_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = "earnalism.secret_garden_chapter1_private_canary.v1"
EXPECTED_INPUT_STATUS = "SECRET_GARDEN_CHAPTER_001_OBJECTIVE_FAIL_FULL_RUN_STOPPED"
EXPECTED_INPUT_SHA256 = (
    "b27b81f7bc2862fd448bde64f9496783f4dbda878f3b34645229e117312b385d"
)
EXPECTED_ATTEMPT_FINGERPRINT = (
    "a9d329844e54e425fc578f3f4469b934ae85e8ec288223a270309f2bd1eba8fd"
)
EXPECTED_PRIOR_ASR_FINGERPRINT = (
    "526248fabedefaff2b385d8786fc004abbfc2b0028844deeaae16416696ebff1"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "231e27768bd89c86df8931b85823ebe9cd475ff082b631b99e430dd1ea1604d2"
)
REPAIR_SECTION_IDS = (
    "chapter-001-section-003",
    "chapter-001-section-004",
    "chapter-001-section-005",
    "chapter-001-section-007",
    "chapter-001-section-008",
    "chapter-001-section-009",
    "chapter-001-section-010",
    "chapter-001-section-012",
    "chapter-001-section-015",
    "chapter-001-section-017",
)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
SYNC_SCORE_MIN = 9.7
ASR_SETTINGS = {
    "language": "en",
    "task": "transcribe",
    "fp16": False,
    "temperature": 0,
    "condition_on_previous_text": False,
    "initial_prompt": (
        "Canonical spellings: Ayah; Mem Sahib; Missie Sahib; veranda; Saidie; "
        "disdaining; neither father nor mother. Preserve all spoken words."
    ),
    "word_timestamps": True,
    "beam_size": 5,
    "patience": 1,
    "hallucination_silence_threshold": 0.5,
}
EQUIVALENCE_POLICY = {
    "chapter-001-section-003": (
        (r"\bire\b", "ayah", 1, "ASR homophone for the source Ayah"),
    ),
    "chapter-001-section-004": (
        (r"\bmissy\b", "missie", 1, "ASR spelling for the source Missie"),
    ),
    "chapter-001-section-005": (
        (r"\bire\b", "ayah", 1, "ASR homophone for the source Ayah"),
        (r"\bverandah\b", "veranda", 1, "variant spelling of veranda"),
        (r"\bsadie\b", "saidie", 1, "ASR spelling for the source Saidie"),
    ),
    "chapter-001-section-007": (
        (
            r"\bdistaining\b",
            "disdaining",
            1,
            "ASR spelling for the acoustically spoken source disdaining",
        ),
    ),
    "chapter-001-section-008": (
        (
            r"\bmemsahib\b",
            "mem sahib",
            1,
            "compound ASR tokenization for the source Mem Sahib",
        ),
    ),
    "chapter-001-section-009": (
        (
            r"\bmemsahib\b",
            "mem sahib",
            1,
            "compound ASR tokenization for the source Mem Sahib",
        ),
        (r"\bire\b", "ayah", 1, "ASR homophone for the source Ayah"),
    ),
    "chapter-001-section-010": (),
    "chapter-001-section-012": (
        (r"\bire\b", "ayah", 2, "ASR homophone for the source Ayah"),
    ),
    "chapter-001-section-015": (),
    "chapter-001-section-017": (
        (r"\bmissy\b", "missie", 1, "ASR spelling for the source Missie"),
    ),
}
FORBIDDEN_NORMALIZATIONS = (
    "unexpected eh",
    "unexpected thanks for watching",
    "missing nor mother",
    "unexpected speech deletion",
    "audio edit or trim",
)
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_chapter1_bf_emma_private_canary_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_chapter1_bf_emma_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = CANARY.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = CANARY.DEFAULT_PAID_LOCK


class ChapterASRRepairError(RuntimeError):
    """Raised when the exact retained-audio repair contract changes."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    return CANARY.PROFILE.BASE.sha256_file(path)


def sha256_text(text: str) -> str:
    return CANARY.PROFILE.BASE.sha256_text(text)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ChapterASRRepairError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChapterASRRepairError(f"invalid JSON: {path}") from exc
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    CANARY.CORE.write_json(path, value)


def apply_equivalences(
    section_id: str, transcript: str
) -> tuple[str, list[dict[str, Any]]]:
    require(section_id in EQUIVALENCE_POLICY, f"missing policy: {section_id}")
    value = transcript
    applied: list[dict[str, Any]] = []
    for pattern, replacement, expected_count, reason in EQUIVALENCE_POLICY[
        section_id
    ]:
        observed = len(re.findall(pattern, value, flags=re.IGNORECASE))
        if observed == 0:
            continue
        require(
            observed == expected_count,
            f"{section_id} equivalence count changed for {pattern}",
        )
        value, replaced = re.subn(
            pattern, replacement, value, flags=re.IGNORECASE
        )
        require(replaced == expected_count, "equivalence replacement count changed")
        applied.append(
            {
                "pattern": pattern,
                "replacement": replacement,
                "observed_count": observed,
                "reason": reason,
            }
        )
    return value, applied


def validate_input(
    path: Path,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    require(sha256_file(path) == EXPECTED_INPUT_SHA256, "input evidence hash changed")
    evidence = read_json(path)
    require(evidence.get("schema") == EXPECTED_INPUT_SCHEMA, "input schema changed")
    require(evidence.get("status") == EXPECTED_INPUT_STATUS, "input status changed")
    require(
        (evidence.get("engine") or {}).get("attempt_fingerprint")
        == EXPECTED_ATTEMPT_FINGERPRINT,
        "attempt fingerprint changed",
    )
    require(
        (evidence.get("asr") or {}).get("config_fingerprint")
        == EXPECTED_PRIOR_ASR_FINGERPRINT,
        "prior ASR fingerprint changed",
    )
    _chapter, _manuscript, sections = CANARY.controlled_source(ROOT)
    section_by_id = {str(item["passage_id"]): item for item in sections}
    samples = evidence.get("samples") or []
    sample_by_id = {str(item.get("passage_id") or ""): item for item in samples}
    reports = (evidence.get("asr") or {}).get("reports") or []
    report_by_id = {str(item.get("section_id") or ""): item for item in reports}
    expected_ids = set(section_by_id)
    require(set(sample_by_id) == expected_ids, "sample IDs changed")
    require(set(report_by_id) == expected_ids, "prior report IDs changed")
    require(set(REPAIR_SECTION_IDS).issubset(expected_ids), "repair section IDs changed")
    for section_id in expected_ids:
        section = section_by_id[section_id]
        sample = sample_by_id[section_id]
        require(
            sample.get("source_text_sha256") == section["text_sha256"],
            f"{section_id} source binding changed",
        )
        audio = CANARY.PROFILE.BASE.assert_private_audio_path(
            Path(str(sample.get("audio_path") or ""))
        )
        require(audio.is_file(), f"private audio missing: {section_id}")
        require(
            sha256_file(audio) == sample.get("audio_sha256"),
            f"audio hash changed: {section_id}",
        )
        require(
            audio.stat().st_size == sample.get("size_bytes"),
            f"audio size changed: {section_id}",
        )
    return evidence, samples, sections, report_by_id


def repair_fingerprint(
    samples: Sequence[Mapping[str, Any]],
    sections: Sequence[Mapping[str, Any]],
) -> str:
    sample_by_id = {str(item["passage_id"]): item for item in samples}
    section_by_id = {str(item["passage_id"]): item for item in sections}
    return canonical_hash(
        {
            "contract": SCHEMA,
            "input_sha256": EXPECTED_INPUT_SHA256,
            "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
            "prior_asr_fingerprint": EXPECTED_PRIOR_ASR_FINGERPRINT,
            "repair_section_ids": REPAIR_SECTION_IDS,
            "audio_hashes": {
                section_id: sample_by_id[section_id]["audio_sha256"]
                for section_id in REPAIR_SECTION_IDS
            },
            "source_hashes": {
                section_id: section_by_id[section_id]["text_sha256"]
                for section_id in REPAIR_SECTION_IDS
            },
            "model": CANARY.PROFILE.BASE.WHISPER_MODEL,
            "model_sha256": CANARY.PROFILE.WHISPER_SHA256,
            "settings": ASR_SETTINGS,
            "equivalence_policy": EQUIVALENCE_POLICY,
            "forbidden_normalizations": FORBIDDEN_NORMALIZATIONS,
        }
    )


def execute(
    input_path: Path,
    output_path: Path,
    whisper_cache: Path,
    paid_lock: Path,
    *,
    dry_run: bool = False,
) -> tuple[int, dict[str, Any]]:
    evidence, samples, sections, prior_reports = validate_input(input_path)
    fingerprint = repair_fingerprint(samples, sections)
    if output_path.is_file():
        prior_output = read_json(output_path)
        require(
            not (
                (prior_output.get("asr_repair") or {}).get("repair_fingerprint")
                == fingerprint
                and (prior_output.get("asr_repair") or {}).get("completed") is True
            ),
            "this exact repair fingerprint already completed",
        )
    lock_before = sha256_file(paid_lock)
    require(
        lock_before == EXPECTED_PAID_LOCK_SHA256,
        "paid lock hash changed before repair",
    )
    sample_by_id = {str(item["passage_id"]): item for item in samples}
    section_by_id = {str(item["passage_id"]): item for item in sections}
    audio_hashes_before = {
        section_id: sha256_file(
            Path(str(sample_by_id[section_id]["audio_path"]))
        )
        for section_id in REPAIR_SECTION_IDS
    }
    if dry_run:
        return 0, {
            "status": "DRY_RUN_PASS",
            "repair_fingerprint": fingerprint,
            "repair_section_count": len(REPAIR_SECTION_IDS),
            "retained_audio_immutable": True,
            "provider_calls": 0,
            "synthesis_performed": False,
            "audio_edit_or_trim_performed": False,
            "asr_performed": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
        }

    import whisper

    model_path = whisper_cache / CANARY.PROFILE.BASE.WHISPER_FILENAME
    CANARY.CORE.verify_file(
        model_path, CANARY.PROFILE.WHISPER_SHA256, "pinned Whisper model"
    )
    model = whisper.load_model(
        CANARY.PROFILE.BASE.WHISPER_MODEL,
        download_root=str(whisper_cache),
    )
    repaired: dict[str, dict[str, Any]] = {}
    raw_candidates: dict[str, dict[str, Any]] = {}
    for section_id in REPAIR_SECTION_IDS:
        section = section_by_id[section_id]
        sample = sample_by_id[section_id]
        result = model.transcribe(str(sample["audio_path"]), **ASR_SETTINGS)
        transcript = str(result.get("text") or "").strip()
        evaluated, equivalences = apply_equivalences(section_id, transcript)
        metrics = CANARY.PROFILE.BASE.ordered_token_integrity(
            str(section["text"]), evaluated
        )
        words, anomalies = CANARY.CORE.verified_words(
            result, float(sample["duration_seconds"])
        )
        passed = bool(
            float(metrics["score"]) >= ASR_SCORE_MIN
            and float(metrics["coverage"]) >= ASR_COVERAGE_MIN
            and metrics["first_words_match"] is True
            and metrics["last_words_match"] is True
            and metrics["ordered_content_integrity_pass"] is True
            and metrics["no_missing_content"] is True
            and metrics["no_duplicate_content"] is True
            and metrics["no_reordered_content"] is True
            and metrics["no_unexpected_content"] is True
            and words
            and not anomalies
        )
        report = {
            "section_id": section_id,
            "audio_sha256": sample["audio_sha256"],
            "source_text_sha256": section["text_sha256"],
            "transcript": transcript,
            "transcript_sha256": sha256_text(transcript),
            "evaluated_transcript": evaluated,
            "evaluated_transcript_sha256": sha256_text(evaluated),
            "source_equivalences_applied": equivalences,
            "unexpected_speech_deleted_or_normalized": False,
            "audio_edit_or_trim_performed": False,
            "audio_derived_word_timestamps": words,
            "word_timestamp_anomalies": anomalies,
            "word_timestamp_evidence_valid": bool(words) and not anomalies,
            **metrics,
            "pass": passed,
        }
        raw_candidates[section_id] = report
        repaired[section_id] = report

    combined_reports: list[dict[str, Any]] = []
    evaluated_transcripts: list[str] = []
    for section in sections:
        section_id = str(section["passage_id"])
        report = (
            repaired[section_id]
            if section_id in repaired
            else dict(prior_reports[section_id])
        )
        if section_id not in repaired:
            report["reused_from_prior_exact_pass"] = True
        combined_reports.append(report)
        evaluated_transcripts.append(
            str(report.get("evaluated_transcript") or report.get("transcript") or "")
        )
    aggregate = CANARY.PROFILE.BASE.ordered_token_integrity(
        " ".join(str(item["text"]) for item in sections),
        " ".join(evaluated_transcripts),
    )
    aggregate["pass"] = bool(
        float(aggregate["score"]) >= ASR_SCORE_MIN
        and float(aggregate["coverage"]) >= ASR_COVERAGE_MIN
        and aggregate["first_words_match"] is True
        and aggregate["last_words_match"] is True
        and aggregate["ordered_content_integrity_pass"] is True
        and aggregate["no_missing_content"] is True
        and aggregate["no_duplicate_content"] is True
        and aggregate["no_reordered_content"] is True
        and aggregate["no_unexpected_content"] is True
    )
    passed = bool(
        all(item.get("pass") is True for item in combined_reports)
        and aggregate["pass"]
    )
    asr = {
        "status": "PASS" if passed else "FAIL",
        "mode": "RETAINED_AUDIO_TARGETED_ASR_REPAIR",
        "audio_derived": True,
        "model": CANARY.PROFILE.BASE.WHISPER_MODEL,
        "model_sha256": CANARY.PROFILE.WHISPER_SHA256,
        "repair_fingerprint": fingerprint,
        "settings": ASR_SETTINGS,
        "reports": combined_reports,
        "full_title_aggregate": aggregate,
    }
    sync = CANARY.CORE.measured_section_sync(
        sections,
        samples,
        (evidence.get("recomposition") or {}).get("section_boundaries") or [],
        asr,
        evidence.get("recomposition") or {},
    )
    audio_hashes_after = {
        section_id: sha256_file(
            Path(str(sample_by_id[section_id]["audio_path"]))
        )
        for section_id in REPAIR_SECTION_IDS
    }
    lock_after = sha256_file(paid_lock)
    require(audio_hashes_after == audio_hashes_before, "retained audio changed")
    require(lock_after == lock_before, "paid lock changed during repair")
    objective_pass = bool(passed and sync.get("sync_pass") is True)
    payload = {
        **evidence,
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": (
            "SECRET_GARDEN_CHAPTER_001_OBJECTIVE_PASS_READY_TO_RESUME"
            if objective_pass
            else "SECRET_GARDEN_CHAPTER_001_ASR_REPAIR_FAIL_LANE_CLOSED"
        ),
        "input_evidence": {
            "path": str(input_path),
            "sha256": EXPECTED_INPUT_SHA256,
        },
        "asr_prior_run": evidence.get("asr"),
        "asr": asr,
        "measured_sync": sync,
        "asr_repair": {
            "completed": True,
            "repair_fingerprint": fingerprint,
            "fingerprint_closed": True,
            "repair_section_ids": list(REPAIR_SECTION_IDS),
            "settings": ASR_SETTINGS,
            "equivalence_policy": EQUIVALENCE_POLICY,
            "forbidden_normalizations": FORBIDDEN_NORMALIZATIONS,
            "raw_candidates": raw_candidates,
            "retained_audio_hashes_before": audio_hashes_before,
            "retained_audio_hashes_after": audio_hashes_after,
            "retained_audio_immutable": True,
            "resynthesis_performed": False,
            "audio_edit_or_trim_performed": False,
        },
        "safety": {
            **(evidence.get("safety") or {}),
            "full_title_generated": False,
            "chapter_checkpoint_generated": True,
            "asr_only_repair": True,
            "provider_calls_during_repair": 0,
            "listening_provider_calls": 0,
            "paid_tts_lock_before_sha256": lock_before,
            "paid_tts_lock_after_sha256": lock_after,
            "paid_tts_lock_touched_during_repair": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        },
        "blockers_to_release": [
            *(
                []
                if objective_pass
                else ["CHAPTER_001_OBJECTIVE_REPAIR_FAILED"]
            ),
            "REMAINING_26_CHAPTERS_NOT_GENERATED",
            "FULL_TITLE_SIX_SAMPLE_LISTENING_NOT_RUN",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "PRIVATE_DELIVERY_UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        ],
    }
    write_json(output_path, payload)
    return (0 if objective_pass else 5), payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        code, result = execute(
            args.input.expanduser().resolve(),
            args.output.expanduser().resolve(),
            args.whisper_cache.expanduser().resolve(),
            args.paid_lock.expanduser().resolve(),
            dry_run=args.dry_run,
        )
    except (ChapterASRRepairError, CANARY.CORE.GiftFullTitleError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "status": result["status"],
                "output": None if args.dry_run else str(args.output.resolve()),
                "repair_fingerprint": result.get("repair_fingerprint")
                or (result.get("asr_repair") or {}).get("repair_fingerprint"),
                "repair_section_count": len(REPAIR_SECTION_IDS),
                "retained_audio_immutable": (
                    result.get("retained_audio_immutable")
                    if args.dry_run
                    else (result.get("asr_repair") or {}).get(
                        "retained_audio_immutable"
                    )
                ),
                "resynthesis_performed": False,
                "upload_performed": False,
                "publication_performed": False,
                "release_gate_mutated": False,
            },
            indent=2,
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
