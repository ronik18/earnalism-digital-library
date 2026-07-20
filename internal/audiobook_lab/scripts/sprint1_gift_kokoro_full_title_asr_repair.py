#!/usr/bin/env python3
"""Run one fingerprinted ASR-only repair over the retained Gift full-title WAVs.

This lane never synthesizes, edits, trims, uploads, publishes, or exposes audio.
It preserves the rejected objective-QA report verbatim, verifies every retained
private WAV by SHA-256, and tries two unprompted Whisper decoder strategies.
Only the owner-authorized, exact-count acoustic/orthographic equivalents are
eligible for evaluation; substantive decoder errors remain failures.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
FULL_RUNNER_PATH = Path(__file__).with_name(
    "sprint1_gift_kokoro_full_title_private_qa.py"
)
SPEC = importlib.util.spec_from_file_location("gift_full_title_private_qa", FULL_RUNNER_PATH)
if not SPEC or not SPEC.loader:
    raise RuntimeError(f"cannot load Gift full-title runner: {FULL_RUNNER_PATH}")
FULL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FULL)


SCHEMA = "earnalism.gift_kokoro_full_title_asr_repair.v1"
SLUG = FULL.SLUG
TITLE = FULL.TITLE
AUTHOR = FULL.AUTHOR
EXPECTED_INPUT_SCHEMA = FULL.SCHEMA
EXPECTED_INPUT_STATUS = "PRIVATE_FULL_TITLE_REJECTED_OBJECTIVE_QA"
EXPECTED_INPUT_SHA256 = "0e200bd148717c50c27eb553c863b56d34e4f4b61c410f061ca414cfc9bfc01b"
EXPECTED_GENERATION_FINGERPRINT = (
    "c28f5c70373854feed9009c5cb4dd0789dd7c2d09a5451e71d7fa41723283039"
)
EXPECTED_SECTION_COUNT = 19
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98

DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_kokoro_af_bella_full_title_private_qa_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_kokoro_af_bella_full_title_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/whisper-cache"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)


DECODING_ARMS = (
    {
        "id": "unprompted_beam_10_hallucination_guard",
        "initial_prompt": None,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": 10,
        "patience": 1.0,
        "best_of": None,
        "hallucination_silence_threshold": 0.5,
        "no_speech_threshold": 0.6,
        "logprob_threshold": -1.0,
        "compression_ratio_threshold": 2.4,
    },
    {
        "id": "unprompted_greedy_1_hallucination_guard",
        "initial_prompt": None,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": None,
        "patience": None,
        "best_of": 1,
        "hallucination_silence_threshold": 0.5,
        "no_speech_threshold": 0.6,
        "logprob_threshold": -1.0,
        "compression_ratio_threshold": 2.4,
    },
)

# Every rule is bidirectional and may be applied only if the number of exact
# occurrences in source and transcript is identical.  More specific numeric
# renderings precede simpler numbers so replacements cannot overlap.
EQUIVALENCE_RULES = (
    {
        "id": "numeric_1_87_currency",
        "patterns": (
            r"\$\s*1\.87\b",
            r"\bone dollar and eighty[- ]seven cents\b",
            r"\bone dollar and 87 cents\b",
            r"\ba dollar and eighty[- ]seven cents\b",
            r"\ba dollar and 87 cents\b",
        ),
        "canonical": " number_currency_1_87 ",
    },
    {
        "id": "numeric_8_currency",
        "patterns": (r"\$\s*8\b", r"\beight dollars\b"),
        "canonical": " number_currency_8 ",
    },
    {
        "id": "numeric_20_currency",
        "patterns": (r"\$\s*20\b", r"\btwenty dollars\b"),
        "canonical": " number_currency_20 ",
    },
    {
        "id": "numeric_21_currency",
        "patterns": (r"\$\s*21\b", r"\btwenty[- ]one dollars\b"),
        "canonical": " number_currency_21 ",
    },
    {
        "id": "numeric_30_currency",
        "patterns": (r"\$\s*30\b", r"\bthirty dollars\b"),
        "canonical": " number_currency_30 ",
    },
    {
        "id": "letter_box_letterbox",
        "patterns": (r"\bletter[ -]box\b", r"\bletterbox\b"),
        "canonical": " letterbox ",
    },
    {
        "id": "airshaft_air_shaft",
        "patterns": (r"\bairshaft\b", r"\bair[ -]shaft\b"),
        "canonical": " airshaft ",
    },
    {
        "id": "some_day_someday",
        "patterns": (r"\bsome day\b", r"\bsomeday\b"),
        "canonical": " someday ",
    },
    {
        "id": "sofronie_sifroni",
        "patterns": (r"\bsofronie\b", r"\bsifroni\b"),
        "canonical": " sofronie ",
    },
    {
        "id": "practised_practiced",
        "patterns": (r"\bpractised\b", r"\bpracticed\b"),
        "canonical": " practiced ",
    },
    {
        "id": "chaste_chased",
        "patterns": (r"\bchaste\b", r"\bchased\b"),
        "canonical": " chased ",
    },
    {
        "id": "stair_away_stairway",
        "patterns": (r"\bstair away\b", r"\bstairway\b"),
        "canonical": " stairway ",
    },
    {
        "id": "discreet_discrete",
        "patterns": (r"\bdiscreet\b", r"\bdiscrete\b"),
        "canonical": " discreet ",
    },
    {
        "id": "dell_del",
        "patterns": (r"\bdell\b", r"\bdel\b"),
        "canonical": " dell ",
    },
    {
        "id": "jewelled_jeweled",
        "patterns": (r"\bjewelled\b", r"\bjeweled\b"),
        "canonical": " jeweled ",
    },
    {
        "id": "numeric_100",
        "patterns": (r"\b100\b", r"\bone hundred\b", r"\ba hundred\b"),
        "canonical": " number_100 ",
    },
    {
        "id": "numeric_87",
        "patterns": (r"\b87\b", r"\beighty[- ]seven\b"),
        "canonical": " number_87 ",
    },
    {
        "id": "numeric_40",
        "patterns": (r"\b40\b", r"\bforty\b"),
        "canonical": " number_40 ",
    },
    {
        "id": "numeric_22",
        "patterns": (r"\b22\b", r"\btwenty[- ]two\b"),
        "canonical": " number_22 ",
    },
    {
        "id": "numeric_7",
        "patterns": (r"\b7\b", r"\bseven\b"),
        "canonical": " number_7 ",
    },
)

FORBIDDEN_EQUIVALENCES = (
    {
        "id": "appertaining_appurting",
        "source": r"\bappertaining\b",
        "transcript": r"\bappurting\b",
    },
    {"id": "pier_pure", "source": r"\bpier\b", "transcript": r"\bpure\b"},
    {
        "id": "im_me_i_mean",
        "source": r"\bi[’']?m me\b",
        "transcript": r"\bi mean\b",
    },
    {
        "id": "want_to_wanna",
        "source": r"\bwant to\b",
        "transcript": r"\bwanna\b",
    },
    {
        "id": "em_them",
        "source": r"(?<!\w)[’']?em\b",
        "transcript": r"\bthem\b",
    },
)

NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
)


class GiftASRRepairError(RuntimeError):
    """Raised whenever the immutable-media repair contract is violated."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GiftASRRepairError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GiftASRRepairError(f"expected JSON object: {path}")
    return value


def assert_nonpublic(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    rendered = f"/{resolved.as_posix().lower().strip('/')}/"
    forbidden = ("/frontend/public/", "/frontend/build/", "/public/audio/", "/static/audio/")
    if any(marker in rendered for marker in forbidden):
        raise GiftASRRepairError(f"public output path is forbidden: {resolved}")
    return resolved


def assert_private_audio(path: Path) -> Path:
    resolved = assert_nonpublic(path)
    if "/internal/audiobook_lab/private_runs/" not in f"/{resolved.as_posix().strip('/')}/":
        raise GiftASRRepairError(f"audio is outside private_runs: {resolved}")
    return resolved


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    assert_nonpublic(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise GiftASRRepairError(
            f"{label} changed: expected {expected!r}, observed {observed!r}"
        )


def validate_input(
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    require(sha256_file(path), EXPECTED_INPUT_SHA256, "input evidence SHA-256")
    evidence = read_json(path)
    require(evidence.get("schema"), EXPECTED_INPUT_SCHEMA, "input schema")
    require(evidence.get("status"), EXPECTED_INPUT_STATUS, "input status")
    scope = evidence.get("scope") if isinstance(evidence.get("scope"), dict) else {}
    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "section_count": EXPECTED_SECTION_COUNT,
        "private_only": True,
    }.items():
        require(scope.get(key), expected, f"scope.{key}")
    engine = evidence.get("engine") if isinstance(evidence.get("engine"), dict) else {}
    require(
        engine.get("attempt_fingerprint"),
        EXPECTED_GENERATION_FINGERPRINT,
        "generation fingerprint",
    )

    _chapter, _manuscript, sections = FULL.controlled_source(ROOT)
    section_by_id = {str(item["passage_id"]): item for item in sections}
    samples = evidence.get("samples") if isinstance(evidence.get("samples"), list) else []
    require(len(samples), EXPECTED_SECTION_COUNT, "retained sample count")
    require(
        [item.get("passage_id") for item in samples],
        [item.get("passage_id") for item in sections],
        "retained section order",
    )
    reports = (evidence.get("asr") or {}).get("reports") or []
    require(len(reports), EXPECTED_SECTION_COUNT, "initial ASR report count")
    report_by_id = {str(item.get("section_id") or ""): item for item in reports}
    require(set(report_by_id), set(section_by_id), "initial ASR section IDs")

    for sample in samples:
        section_id = str(sample.get("passage_id") or "")
        section = section_by_id[section_id]
        require(
            sample.get("source_text_sha256"),
            section.get("text_sha256"),
            f"{section_id} source hash",
        )
        require(sample.get("objective_format_pass"), True, f"{section_id} format gate")
        audio = assert_private_audio(Path(str(sample.get("audio_path") or "")))
        if not audio.is_file():
            raise GiftASRRepairError(f"retained private WAV is missing: {section_id}")
        require(sha256_file(audio), sample.get("audio_sha256"), f"{section_id} WAV SHA-256")
        require(audio.stat().st_size, sample.get("size_bytes"), f"{section_id} WAV size")
        report = report_by_id[section_id]
        require(report.get("audio_sha256"), sample.get("audio_sha256"), f"{section_id} report audio")
        require(
            report.get("source_text_sha256"),
            section.get("text_sha256"),
            f"{section_id} report source",
        )
        require(
            sha256_text(str(report.get("transcript") or "")),
            report.get("transcript_sha256"),
            f"{section_id} initial transcript hash",
        )

    recomposition = evidence.get("recomposition") or {}
    full_audio = assert_private_audio(Path(str(recomposition.get("full_audio_path") or "")))
    if not full_audio.is_file():
        raise GiftASRRepairError("retained recomposed full-title WAV is missing")
    require(
        sha256_file(full_audio), recomposition.get("audio_sha256"), "recomposed WAV SHA-256"
    )
    return evidence, [dict(item) for item in samples], sections


def repair_fingerprint(evidence: Mapping[str, Any]) -> str:
    samples = evidence.get("samples") or []
    payload = {
        "contract": SCHEMA,
        "slug": SLUG,
        "input_evidence_sha256": EXPECTED_INPUT_SHA256,
        "initial_asr_snapshot_sha256": canonical_hash(evidence.get("asr") or {}),
        "initial_sync_snapshot_sha256": canonical_hash(evidence.get("measured_sync") or {}),
        "generation_fingerprint": EXPECTED_GENERATION_FINGERPRINT,
        "source_hashes": {
            item["passage_id"]: item["source_text_sha256"] for item in samples
        },
        "audio_hashes": {item["passage_id"]: item["audio_sha256"] for item in samples},
        "whisper_model": FULL.WHISPER_MODEL,
        "whisper_sha256": FULL.WHISPER_SHA256,
        "decoder_arms": DECODING_ARMS,
        "equivalence_rules": EQUIVALENCE_RULES,
        "forbidden_equivalences": FORBIDDEN_EQUIVALENCES,
        "score_min": ASR_SCORE_MIN,
        "coverage_min": ASR_COVERAGE_MIN,
        "manual_transcript_deletion_allowed": False,
        "audio_mutation_allowed": False,
        "implementation_sha256": sha256_text(inspect.getsource(execute)),
    }
    return canonical_hash(payload)


def _fingerprints(value: Any, key: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _fingerprints(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from _fingerprints(child, key)
    elif isinstance(value, str) and "fingerprint" in key.lower():
        yield value


def ensure_not_repeated(output: Path, fingerprint: str) -> None:
    if fingerprint == EXPECTED_GENERATION_FINGERPRINT:
        raise GiftASRRepairError("repair fingerprint collides with generation fingerprint")
    if output.is_file():
        prior = read_json(output)
        repair = prior.get("asr_repair") if isinstance(prior.get("asr_repair"), dict) else {}
        if repair.get("repair_fingerprint") == fingerprint and repair.get("fingerprint_closed") is True:
            raise GiftASRRepairError("this exact ASR repair fingerprint is closed")
    for path in NO_REPEAT_FILES:
        if path.is_file() and fingerprint in set(_fingerprints(read_json(path))):
            raise GiftASRRepairError(f"repair fingerprint already exists in {path}")


def _rule_count(value: str, rule: Mapping[str, Any]) -> int:
    combined = "(?:" + ")|(?:".join(str(item) for item in rule["patterns"]) + ")"
    return len(re.findall(combined, value, flags=re.IGNORECASE))


def _apply_rule(value: str, rule: Mapping[str, Any]) -> tuple[str, int]:
    combined = "(?:" + ")|(?:".join(str(item) for item in rule["patterns"]) + ")"
    return re.subn(combined, str(rule["canonical"]), value, flags=re.IGNORECASE)


def apply_exact_count_equivalences(
    source: str, transcript: str
) -> tuple[str, str, list[dict[str, Any]], list[dict[str, Any]]]:
    evaluated_source = source
    evaluated_transcript = transcript
    applied: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for rule in EQUIVALENCE_RULES:
        source_count = _rule_count(evaluated_source, rule)
        transcript_count = _rule_count(evaluated_transcript, rule)
        if source_count == 0 and transcript_count == 0:
            continue
        if source_count != transcript_count:
            rejected.append(
                {
                    "equivalence": rule["id"],
                    "source_count": source_count,
                    "transcript_count": transcript_count,
                    "reason": "EXACT_COUNT_MISMATCH",
                }
            )
            continue
        evaluated_source, source_replaced = _apply_rule(evaluated_source, rule)
        evaluated_transcript, transcript_replaced = _apply_rule(evaluated_transcript, rule)
        if source_replaced != source_count or transcript_replaced != transcript_count:
            raise GiftASRRepairError(f"replacement count drift: {rule['id']}")
        applied.append(
            {
                "equivalence": rule["id"],
                "source_count": source_count,
                "transcript_count": transcript_count,
                "exact_count_match": True,
            }
        )
    return evaluated_source, evaluated_transcript, applied, rejected


def detect_forbidden_equivalences(source: str, transcript: str) -> list[dict[str, Any]]:
    detected: list[dict[str, Any]] = []
    for rule in FORBIDDEN_EQUIVALENCES:
        source_left_count = len(
            re.findall(str(rule["source"]), source, flags=re.IGNORECASE)
        )
        transcript_left_count = len(
            re.findall(str(rule["source"]), transcript, flags=re.IGNORECASE)
        )
        source_right_count = len(
            re.findall(str(rule["transcript"]), source, flags=re.IGNORECASE)
        )
        transcript_right_count = len(
            re.findall(str(rule["transcript"]), transcript, flags=re.IGNORECASE)
        )
        if (
            source_left_count > transcript_left_count
            and transcript_right_count > source_right_count
        ):
            detected.append(
                {
                    "equivalence": rule["id"],
                    "source_form_count_in_source": source_left_count,
                    "source_form_count_in_transcript": transcript_left_count,
                    "substitute_form_count_in_source": source_right_count,
                    "substitute_form_count_in_transcript": transcript_right_count,
                    "normalized": False,
                    "requires_decoder_or_audio_correctness": True,
                }
            )
    return detected


def alignment_metrics(source: str, transcript: str) -> dict[str, Any]:
    evaluated_source, evaluated_transcript, applied, rejected = (
        apply_exact_count_equivalences(source, transcript)
    )
    forbidden = detect_forbidden_equivalences(source, transcript)
    metrics = FULL.representative.ordered_token_integrity(
        evaluated_source, evaluated_transcript
    )
    exact = bool(
        not rejected
        and not forbidden
        and float(metrics["score"]) >= ASR_SCORE_MIN
        and float(metrics["coverage"]) >= ASR_COVERAGE_MIN
        and metrics["first_words_match"] is True
        and metrics["last_words_match"] is True
        and metrics["ordered_content_integrity_pass"] is True
        and metrics["no_missing_content"] is True
        and metrics["no_duplicate_content"] is True
        and metrics["no_reordered_content"] is True
        and metrics["no_unexpected_content"] is True
    )
    return {
        **metrics,
        "evaluated_source_sha256": sha256_text(evaluated_source),
        "evaluated_transcript_sha256": sha256_text(evaluated_transcript),
        "exact_count_equivalences_applied": applied,
        "equivalence_count_rejections": rejected,
        "forbidden_equivalences_detected": forbidden,
        "forbidden_equivalences_normalized": False,
        "manual_transcript_deletion_performed": False,
        "alignment_pass": exact,
    }


def evaluate_result(
    section: Mapping[str, Any],
    sample: Mapping[str, Any],
    result: Mapping[str, Any],
    arm_id: str,
) -> dict[str, Any]:
    transcript = str(result.get("text") or "").strip()
    metrics = alignment_metrics(str(section["text"]), transcript)
    words, anomalies = FULL.verified_words(result, float(sample["duration_seconds"]))
    timestamp_pass = bool(words) and not anomalies
    trailing_hallucination = bool(
        re.search(r"\bthank you for (?:watching|joining us today)\b", transcript, re.IGNORECASE)
    )
    passed = bool(metrics["alignment_pass"] and timestamp_pass and not trailing_hallucination)
    return {
        "section_id": section["passage_id"],
        "decoder_arm": arm_id,
        "audio_sha256": sample["audio_sha256"],
        "source_text_sha256": section["text_sha256"],
        "transcript": transcript,
        "transcript_sha256": sha256_text(transcript),
        "audio_derived_word_timestamps": words,
        "word_timestamp_anomalies": anomalies,
        "word_timestamp_evidence_valid": timestamp_pass,
        "trailing_hallucination_detected": trailing_hallucination,
        **metrics,
        "pass": passed,
    }


def run_decoding_arm(
    model: Any, arm: Mapping[str, Any], sample: Mapping[str, Any]
) -> Mapping[str, Any]:
    options: dict[str, Any] = {
        "language": "en",
        "task": "transcribe",
        "fp16": False,
        "verbose": None,
        "temperature": arm["temperature"],
        "condition_on_previous_text": arm["condition_on_previous_text"],
        "initial_prompt": arm["initial_prompt"],
        "word_timestamps": arm["word_timestamps"],
        "hallucination_silence_threshold": arm["hallucination_silence_threshold"],
        "no_speech_threshold": arm["no_speech_threshold"],
        "logprob_threshold": arm["logprob_threshold"],
        "compression_ratio_threshold": arm["compression_ratio_threshold"],
    }
    if arm.get("beam_size") is not None:
        options["beam_size"] = arm["beam_size"]
        options["patience"] = arm["patience"]
    elif arm.get("best_of") is not None:
        options["best_of"] = arm["best_of"]
    return model.transcribe(str(sample["audio_path"]), **options)


def load_whisper_model(cache: Path) -> Any:
    try:
        import whisper  # noqa: PLC0415
    except ImportError as exc:
        raise GiftASRRepairError("openai-whisper is required") from exc
    model_path = cache.expanduser().resolve() / FULL.representative.WHISPER_FILENAME
    if not model_path.is_file():
        raise GiftASRRepairError(f"pinned Whisper model is missing: {model_path}")
    require(sha256_file(model_path), FULL.WHISPER_SHA256, "Whisper model SHA-256")
    return whisper.load_model(FULL.WHISPER_MODEL, download_root=str(cache.resolve()))


def _candidate_sort_key(report: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        bool(report.get("pass")),
        bool(report.get("word_timestamp_evidence_valid")),
        bool(report.get("alignment_pass")),
        float(report.get("score") or 0.0),
        float(report.get("coverage") or 0.0),
        float(report.get("precision") or 0.0),
        -next(
            (
                index
                for index, arm in enumerate(DECODING_ARMS)
                if arm["id"] == report.get("decoder_arm")
            ),
            len(DECODING_ARMS),
        ),
    )


def execute(
    input_path: Path,
    output_path: Path,
    whisper_cache: Path,
    paid_lock: Path,
    *,
    dry_run: bool = False,
    model_loader: Callable[[Path], Any] = load_whisper_model,
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]] = run_decoding_arm,
) -> tuple[int, dict[str, Any]]:
    assert_nonpublic(output_path)
    evidence, samples, sections = validate_input(input_path)
    fingerprint = repair_fingerprint(evidence)
    ensure_not_repeated(output_path, fingerprint)
    audio_hashes_before = {
        item["passage_id"]: sha256_file(Path(str(item["audio_path"]))) for item in samples
    }
    if dry_run:
        return 0, {
            "status": "DRY_RUN_PASS",
            "repair_fingerprint": fingerprint,
            "input_evidence_sha256": EXPECTED_INPUT_SHA256,
            "initial_asr_snapshot_sha256": canonical_hash(evidence.get("asr") or {}),
            "retained_audio_hashes_verified": True,
            "decoder_arms": DECODING_ARMS,
            "provider_calls": 0,
            "asr_performed": False,
            "synthesis_performed": False,
            "listening_qa_performed": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
        }

    lock_before = FULL.representative.lock_snapshot(paid_lock)
    sample_by_id = {str(item["passage_id"]): item for item in samples}
    section_by_id = {str(item["passage_id"]): item for item in sections}
    model = model_loader(whisper_cache)
    candidates: dict[str, list[dict[str, Any]]] = {
        section_id: [] for section_id in sample_by_id
    }
    unresolved = set(sample_by_id)
    for arm in DECODING_ARMS:
        targets = list(sample_by_id) if arm is DECODING_ARMS[0] else sorted(unresolved)
        for section_id in targets:
            result = decoder(model, arm, sample_by_id[section_id])
            report = evaluate_result(
                section_by_id[section_id], sample_by_id[section_id], result, str(arm["id"])
            )
            candidates[section_id].append(report)
            if report["pass"]:
                unresolved.discard(section_id)
        if not unresolved:
            break

    selected = [
        max(candidates[str(section["passage_id"])], key=_candidate_sort_key)
        for section in sections
    ]
    aggregate = alignment_metrics(
        " ".join(str(item["text"]) for item in sections),
        " ".join(str(item["transcript"]) for item in selected),
    )
    aggregate["pass"] = aggregate.pop("alignment_pass")
    asr_pass = bool(
        len(selected) == EXPECTED_SECTION_COUNT
        and all(item["pass"] for item in selected)
        and aggregate["pass"]
    )
    asr = {
        "status": "PASS" if asr_pass else "FAIL",
        "mode": "ASR_ONLY_RETAINED_HASH_BOUND_AUDIO",
        "model": FULL.WHISPER_MODEL,
        "model_sha256": FULL.WHISPER_SHA256,
        "audio_derived": True,
        "score_min": ASR_SCORE_MIN,
        "coverage_min": ASR_COVERAGE_MIN,
        "reports": selected,
        "full_title_aggregate": aggregate,
    }
    boundaries = (evidence.get("recomposition") or {}).get("section_boundaries") or []
    sync = FULL.measured_section_sync(
        sections, samples, boundaries, asr, evidence.get("recomposition") or {}
    )
    audio_hashes_after = {
        item["passage_id"]: sha256_file(Path(str(item["audio_path"]))) for item in samples
    }
    require(audio_hashes_after, audio_hashes_before, "retained WAV hashes after ASR repair")
    lock_after = FULL.representative.lock_snapshot(paid_lock)
    require(lock_after, lock_before, "paid_tts.lock snapshot after ASR repair")
    objective_pass = bool(asr_pass and sync.get("sync_pass") is True)

    blockers = [
        "FULL_TITLE_SIX_SAMPLE_LISTENING_NOT_RUN",
        "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "PRIVATE_DELIVERY_UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
    ]
    if not objective_pass:
        blockers.insert(0, "PRIVATE_FULL_TITLE_ASR_REPAIR_FAILED")
    result = {
        **copy.deepcopy(evidence),
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": (
            "PRIVATE_FULL_TITLE_ASR_REPAIR_PASS_LISTENING_PENDING"
            if objective_pass
            else "PRIVATE_FULL_TITLE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED"
        ),
        "scope": {
            **copy.deepcopy(evidence.get("scope") or {}),
            # The predecessor execution produced and hash-bound every section
            # plus the recomposed WAV. Preserve that factual state even though
            # its objective gate rejected the candidate.
            "full_title_generated": True,
        },
        "input_evidence": {
            "path": str(input_path.resolve()),
            "sha256": EXPECTED_INPUT_SHA256,
            "unchanged": sha256_file(input_path) == EXPECTED_INPUT_SHA256,
        },
        "initial_objective_qa": {
            "status": evidence["status"],
            "asr_snapshot_sha256": canonical_hash(evidence.get("asr") or {}),
            "measured_sync_snapshot_sha256": canonical_hash(
                evidence.get("measured_sync") or {}
            ),
            "asr": copy.deepcopy(evidence.get("asr") or {}),
            "measured_sync": copy.deepcopy(evidence.get("measured_sync") or {}),
        },
        "asr": asr,
        "measured_sync": sync,
        "asr_repair": {
            "completed": True,
            "fingerprint_closed": True,
            "repair_fingerprint": fingerprint,
            "generation_fingerprint": EXPECTED_GENERATION_FINGERPRINT,
            "decoder_arms": DECODING_ARMS,
            "equivalence_rules": EQUIVALENCE_RULES,
            "forbidden_equivalences": FORBIDDEN_EQUIVALENCES,
            "all_candidates": candidates,
            "selected_decoder_by_section": {
                item["section_id"]: item["decoder_arm"] for item in selected
            },
            "audio_hashes_before": audio_hashes_before,
            "audio_hashes_after": audio_hashes_after,
            "audio_hashes_unchanged": audio_hashes_before == audio_hashes_after,
            "resynthesis_performed": False,
            "audio_edit_or_trim_performed": False,
            "manual_transcript_deletion_performed": False,
            "global_ledger_mutation_performed": False,
        },
        "safety": {
            **copy.deepcopy(evidence.get("safety") or {}),
            "provider_calls": 0,
            "listening_provider_calls": 0,
            "audio_generated_during_repair": False,
            "resynthesis_performed": False,
            "asr_only_repair": True,
            "paid_tts_lock_before_repair": lock_before,
            "paid_tts_lock_after_repair": lock_after,
            "paid_tts_lock_touched_during_repair": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        },
        "blockers_to_release": blockers,
    }
    write_json(output_path, result)
    return (0 if objective_pass else 4), result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        code, result = execute(
            args.input.expanduser().resolve(),
            args.output.expanduser().resolve(),
            args.whisper_cache.expanduser().resolve(),
            args.paid_lock.expanduser().resolve(),
            dry_run=args.dry_run,
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "repair_fingerprint": result.get("repair_fingerprint")
                    or (result.get("asr_repair") or {}).get("repair_fingerprint"),
                    "output": None if args.dry_run else str(args.output.resolve()),
                    "resynthesis_performed": False,
                    "provider_calls": 0,
                    "listening_provider_calls": 0,
                    "upload_performed": False,
                    "publication_performed": False,
                    "release_gate_mutated": False,
                },
                indent=2,
            )
        )
        return code
    except (GiftASRRepairError, FULL.GiftFullTitleError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
