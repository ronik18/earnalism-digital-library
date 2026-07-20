#!/usr/bin/env python3
"""Run one bounded ASR-only repair over retained Tell-Tale Heart WAVs.

The two local, unprompted Whisper decoder arms run over every immutable
``bf_emma`` representative WAV and every raw candidate is retained.  The
source-equivalence policy is deliberately empty: trailing ``you`` or ``thanks
for watching`` can pass only when an alternate decoder does not hallucinate
them.  This module cannot synthesize or edit audio, call a provider, inspect a
paid coordination lock, listen, upload, publish, or mutate release truth.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
EXECUTOR_PATH = Path(__file__).with_name(
    "sprint1_tell_tale_kokoro_private_executor.py"
)
EXECUTOR_SPEC = importlib.util.spec_from_file_location(
    "tell_tale_kokoro_executor_for_asr_repair", EXECUTOR_PATH
)
if EXECUTOR_SPEC is None or EXECUTOR_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Tell-Tale executor: {EXECUTOR_PATH}")
EXECUTOR = importlib.util.module_from_spec(EXECUTOR_SPEC)
EXECUTOR_SPEC.loader.exec_module(EXECUTOR)


SCHEMA = "earnalism.kokoro.tell_tale_bf_emma_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.tell_tale_private_executor.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = (
    "97ffb3204af82f42c6f306dd9a2640d6736d058c7f055e432b09e8c75c712408"
)
EXPECTED_ATTEMPT_FINGERPRINT = (
    "5ab7a8abdc62cd901d16d7cb9fb6fe10094bb829d279574a6ccd6da88e1562f9"
)
EXPECTED_PRIOR_ASR_FINGERPRINT = (
    "9aec87e0efcb5ff795ca4488dbc2143cac34d386862445bda90c3f947772c288"
)
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_unreliable_sanity": (
        "c0c6b13c36a180c1d20209c481cec826402fe531e61d8698f3bc5341f5c5a094"
    ),
    "bedroom_suspense_dialogue": (
        "f328665fff147def049da745c75dcee14bbaf2707d6ae02393257a8359a9a01b"
    ),
    "heartbeat_crescendo": (
        "6ed223a1d6905c6dbd4bda18109c7d286d32379e1ddc7a06f00d19b09f5bb6e4"
    ),
    "final_confession": (
        "62adee7f9fe8f26367085e1c10e96c4bd7257ef2eaf092c51b32b4976f722cf6"
    ),
}
EXPECTED_SAMPLE_BINDINGS = {
    "opening_unreliable_sanity": {
        "source_text_sha256": (
            "1bd845cd383b10550ac7fe03ccfafc01d3059c7ae9f473a4a371c20782f6a524"
        ),
        "audio_sha256": (
            "e8d932b1a11e59c286d540e6f62117ecb4a2d36413e7245246dc439248a8422b"
        ),
        "size_bytes": 1_032_044,
        "duration_seconds": 21.5,
    },
    "bedroom_suspense_dialogue": {
        "source_text_sha256": (
            "7b2efa882aed81bb447c8d00fee89dfc011d48ffb2c2ba0f1d2b202918125029"
        ),
        "audio_sha256": (
            "bd737502e4e606cada8f6e35938f9061b11ae8f223932fb5831fa73f866a890f"
        ),
        "size_bytes": 1_412_444,
        "duration_seconds": 29.425,
    },
    "heartbeat_crescendo": {
        "source_text_sha256": (
            "90686993699298d204d639da36bf779b3ae52397e99e2d6e1b5fdb5a316ab639"
        ),
        "audio_sha256": (
            "baf322c5af34276e234ab7bf9a19e3087302fe8fb1a3f3e411df5d61bd3c31a7"
        ),
        "size_bytes": 1_617_644,
        "duration_seconds": 33.7,
    },
    "final_confession": {
        "source_text_sha256": (
            "3e0f8c27ceca25a940b8d411c6bf015a46ba188a513273748c9666f7a7695745"
        ),
        "audio_sha256": (
            "c85148a6389d543ca1e4ed443e97f970c5063b902958a102cf94cac176883c86"
        ),
        "size_bytes": 1_454_444,
        "duration_seconds": 30.3,
    },
}

DECODING_ARMS = (
    {
        "id": "unprompted_beam_2",
        "initial_prompt": None,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": 2,
        "patience": 1,
        "hallucination_silence_threshold": 0.5,
    },
    {
        "id": "unprompted_greedy",
        "initial_prompt": None,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": None,
        "patience": None,
        "hallucination_silence_threshold": 0.5,
    },
)

# There are no source-equivalence rules for this repair.  Unexpected trailing
# speech remains unexpected speech, even when it resembles a common decoder
# hallucination.
SOURCE_EQUIVALENCE_POLICY = {
    passage_id: () for passage_id in EXPECTED_SAMPLE_BINDINGS
}
FORBIDDEN_NORMALIZATIONS = (
    "trailing you deletion",
    "trailing thanks for watching deletion",
    "unexpected speech deletion",
    "source-prompt injection",
)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-tell-tale-heart_kokoro_bf_emma_representative_execution_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-tell-tale-heart_kokoro_bf_emma_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = EXECUTOR.PREFLIGHT.DEFAULT_WHISPER_CACHE
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
)


class TellTaleASRRepairError(RuntimeError):
    """Raised when retained-audio repair truth is not exact or safe."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TellTaleASRRepairError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TellTaleASRRepairError(f"expected JSON object: {path}")
    return value


def _require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise TellTaleASRRepairError(
            f"{label} changed: expected {expected!r}, observed {observed!r}"
        )


def assert_nonpublic(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    rendered = f"/{resolved.as_posix().lower().strip('/')}/"
    if any(
        marker in rendered
        for marker in (
            "/frontend/public/",
            "/frontend/build/",
            "/public/audio/",
            "/static/audio/",
        )
    ):
        raise TellTaleASRRepairError(f"public output path is forbidden: {resolved}")
    return resolved


def assert_private_audio(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    rendered = f"/{resolved.as_posix().lower().strip('/')}/"
    if "/internal/audiobook_lab/private_runs/" not in rendered:
        raise TellTaleASRRepairError(f"audio is outside private_runs: {resolved}")
    assert_nonpublic(resolved)
    return resolved


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    assert_nonpublic(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def validate_input(
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    measured_input_hash = EXECUTOR.PREFLIGHT.sha256_file(path)
    _require(measured_input_hash, EXPECTED_INPUT_SHA256, "input evidence SHA-256")
    evidence = read_json(path)
    _require(evidence.get("schema"), EXPECTED_INPUT_SCHEMA, "input schema")
    _require(evidence.get("status"), EXPECTED_INPUT_STATUS, "input status")

    scope = evidence.get("scope") if isinstance(evidence.get("scope"), dict) else {}
    for key, expected in {
        "slug": EXECUTOR.SLUG,
        "title": EXECUTOR.TITLE,
        "author": EXECUTOR.AUTHOR,
        "passage_count": 4,
        "representative_only": True,
        "full_title_generated": False,
    }.items():
        _require(scope.get(key), expected, f"scope.{key}")
    engine = evidence.get("engine") if isinstance(evidence.get("engine"), dict) else {}
    _require(
        engine.get("attempt_fingerprint"),
        EXPECTED_ATTEMPT_FINGERPRINT,
        "attempt fingerprint",
    )
    _require(engine.get("voice"), EXECUTOR.VOICE, "voice")
    _require(engine.get("voice_sha256"), EXECUTOR.VOICE_SHA256, "voice SHA-256")
    _require(engine.get("g2p_fallback_enabled"), False, "G2P fallback flag")

    _chapter, passages = EXECUTOR.PREFLIGHT.controlled_source(ROOT, EXECUTOR.SLUG)
    passage_by_id = {str(item["passage_id"]): item for item in passages}
    samples = evidence.get("samples") if isinstance(evidence.get("samples"), list) else []
    _require(len(samples), 4, "sample count")
    sample_by_id = {str(item.get("passage_id") or ""): item for item in samples}
    _require(set(sample_by_id), set(EXPECTED_SAMPLE_BINDINGS), "sample IDs")
    verified_samples: list[dict[str, Any]] = []
    for passage_id, expected in EXPECTED_SAMPLE_BINDINGS.items():
        sample = sample_by_id[passage_id]
        for key, value in expected.items():
            _require(sample.get(key), value, f"{passage_id} sample {key}")
        _require(
            sample.get("source_text_sha256"),
            passage_by_id[passage_id]["text_sha256"],
            f"{passage_id} source binding",
        )
        _require(sample.get("objective_format_pass"), True, f"{passage_id} format gate")
        audio = assert_private_audio(Path(str(sample.get("audio_path") or "")))
        if not audio.is_file():
            raise TellTaleASRRepairError(f"private audio is missing: {passage_id}")
        _require(
            EXECUTOR.PREFLIGHT.sha256_file(audio),
            expected["audio_sha256"],
            f"{passage_id} audio SHA-256",
        )
        _require(audio.stat().st_size, expected["size_bytes"], f"{passage_id} audio size")
        verified_samples.append(dict(sample))

    prior = evidence.get("asr") if isinstance(evidence.get("asr"), dict) else {}
    _require(prior.get("status"), "FAIL", "prior ASR status")
    _require(
        prior.get("config_fingerprint"),
        EXPECTED_PRIOR_ASR_FINGERPRINT,
        "prior ASR fingerprint",
    )
    _require(
        prior.get("source_equivalence_policy"),
        {key: [] for key in SOURCE_EQUIVALENCE_POLICY},
        "prior source equivalence policy",
    )
    reports = prior.get("reports") if isinstance(prior.get("reports"), list) else []
    _require(len(reports), 4, "prior ASR report count")
    report_by_id = {str(item.get("passage_id") or ""): item for item in reports}
    _require(set(report_by_id), set(EXPECTED_PRIOR_TRANSCRIPT_HASHES), "prior ASR passage IDs")
    for passage_id, expected_hash in EXPECTED_PRIOR_TRANSCRIPT_HASHES.items():
        report = report_by_id[passage_id]
        _require(
            report.get("transcript_sha256"),
            expected_hash,
            f"{passage_id} prior transcript hash",
        )
        _require(
            EXECUTOR.PREFLIGHT.sha256_text(str(report.get("transcript") or "")),
            expected_hash,
            f"{passage_id} measured prior transcript hash",
        )
    return evidence, verified_samples, passages


def repair_fingerprint() -> str:
    return canonical_hash(
        {
            "contract": SCHEMA,
            "slug": EXECUTOR.SLUG,
            "input_evidence_sha256": EXPECTED_INPUT_SHA256,
            "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
            "prior_asr_fingerprint": EXPECTED_PRIOR_ASR_FINGERPRINT,
            "audio_hashes": {
                key: value["audio_sha256"]
                for key, value in EXPECTED_SAMPLE_BINDINGS.items()
            },
            "source_hashes": {
                key: value["source_text_sha256"]
                for key, value in EXPECTED_SAMPLE_BINDINGS.items()
            },
            "whisper_model": EXECUTOR.BASE.WHISPER_MODEL,
            "whisper_sha256": EXECUTOR.PREFLIGHT.WHISPER_SHA256,
            "decoding_arms": DECODING_ARMS,
            "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
            "forbidden_normalizations": FORBIDDEN_NORMALIZATIONS,
            "score_min": ASR_SCORE_MIN,
            "coverage_min": ASR_COVERAGE_MIN,
            "both_arms_run_for_every_passage": True,
            "unexpected_speech_may_be_deleted": False,
            "paid_coordination_lock_accessed": False,
        }
    )


def _find_fingerprints(value: Any, key: str = ""):
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _find_fingerprints(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from _find_fingerprints(child, key)
    elif isinstance(value, str) and "fingerprint" in key.lower():
        yield value


def ensure_not_repeated(output: Path, fingerprint: str) -> None:
    if output.is_file():
        prior = read_json(output)
        repair = prior.get("asr_repair") if isinstance(prior.get("asr_repair"), dict) else {}
        if repair.get("repair_fingerprint") == fingerprint and repair.get("completed") is True:
            raise TellTaleASRRepairError("this exact ASR-only repair already completed")
    for path in NO_REPEAT_FILES:
        if path.is_file() and fingerprint in set(_find_fingerprints(read_json(path))):
            raise TellTaleASRRepairError(
                f"repair fingerprint already exists in {path}"
            )


def evaluate_transcript(
    passage: Mapping[str, Any],
    sample: Mapping[str, Any],
    transcript: str,
    arm_id: str,
) -> dict[str, Any]:
    passage_id = str(passage["passage_id"])
    if SOURCE_EQUIVALENCE_POLICY.get(passage_id) != ():
        raise TellTaleASRRepairError(
            f"source equivalence policy is not empty: {passage_id}"
        )
    metrics = EXECUTOR.BASE.ordered_token_integrity(str(passage["text"]), transcript)
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
    )
    transcript_hash = EXECUTOR.PREFLIGHT.sha256_text(transcript)
    return {
        "passage_id": passage_id,
        "decoder_arm": arm_id,
        "audio_sha256": sample["audio_sha256"],
        "source_text_sha256": passage["text_sha256"],
        "raw_transcript": transcript,
        "raw_transcript_sha256": transcript_hash,
        "evaluated_transcript": transcript,
        "evaluated_transcript_sha256": transcript_hash,
        "source_equivalences_applied": [],
        "trailing_you_deleted_or_normalized": False,
        "trailing_thanks_for_watching_deleted_or_normalized": False,
        "unexpected_speech_deleted_or_normalized": False,
        **metrics,
        "pass": passed,
    }


def run_decoding_arm(
    model: Any, arm: Mapping[str, Any], sample: Mapping[str, Any]
) -> str:
    options = {
        "language": "en",
        "task": "transcribe",
        "fp16": False,
        "verbose": None,
        "temperature": arm["temperature"],
        "condition_on_previous_text": arm["condition_on_previous_text"],
        "initial_prompt": arm["initial_prompt"],
        "word_timestamps": arm["word_timestamps"],
        "hallucination_silence_threshold": arm["hallucination_silence_threshold"],
    }
    if arm.get("beam_size") is not None:
        options["beam_size"] = arm["beam_size"]
        options["patience"] = arm["patience"]
    result = model.transcribe(str(sample["audio_path"]), **options)
    return str(result.get("text") or "").strip()


def load_whisper_model(cache: Path):
    import whisper  # noqa: PLC0415

    model_path = cache.expanduser().resolve() / EXECUTOR.BASE.WHISPER_FILENAME
    observed = EXECUTOR.PREFLIGHT.sha256_file(model_path)
    _require(observed, EXECUTOR.PREFLIGHT.WHISPER_SHA256, "Whisper model SHA-256")
    return whisper.load_model(
        EXECUTOR.BASE.WHISPER_MODEL, download_root=str(cache.expanduser().resolve())
    )


def _audio_hashes(samples: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {
        str(sample["passage_id"]): EXECUTOR.PREFLIGHT.sha256_file(
            assert_private_audio(Path(str(sample["audio_path"])))
        )
        for sample in samples
    }


def execute(
    input_path: Path,
    output_path: Path,
    whisper_cache: Path,
    *,
    dry_run: bool = False,
    model_loader: Callable[[Path], Any] = load_whisper_model,
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], str] = run_decoding_arm,
) -> tuple[int, dict[str, Any]]:
    assert_nonpublic(output_path)
    evidence, samples, passages = validate_input(input_path)
    fingerprint = repair_fingerprint()
    ensure_not_repeated(output_path, fingerprint)
    before_hashes = _audio_hashes(samples)
    if dry_run:
        return 0, {
            "status": "DRY_RUN_PASS",
            "repair_fingerprint": fingerprint,
            "audio_hashes_verified": before_hashes,
            "retained_audio_immutable": True,
            "decoder_arms": DECODING_ARMS,
            "both_arms_will_run_for_every_passage": True,
            "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
            "provider_calls": 0,
            "synthesis_performed": False,
            "audio_edit_or_trim_performed": False,
            "asr_performed": False,
            "listening_qa_performed": False,
            "paid_coordination_lock_inspected": False,
            "paid_coordination_lock_touched": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
        }

    sample_by_id = {str(item["passage_id"]): item for item in samples}
    passage_by_id = {str(item["passage_id"]): item for item in passages}
    model = model_loader(whisper_cache)
    candidates: dict[str, list[dict[str, Any]]] = {
        passage_id: [] for passage_id in sample_by_id
    }
    for arm in DECODING_ARMS:
        for passage_id in sample_by_id:
            transcript = decoder(model, arm, sample_by_id[passage_id])
            candidates[passage_id].append(
                evaluate_transcript(
                    passage_by_id[passage_id],
                    sample_by_id[passage_id],
                    transcript,
                    str(arm["id"]),
                )
            )

    selected: list[dict[str, Any]] = []
    for passage_id in sample_by_id:
        reports = candidates[passage_id]
        passing = [item for item in reports if item["pass"]]
        selected.append(
            passing[0]
            if passing
            else max(
                reports,
                key=lambda item: (
                    item["score"],
                    item["coverage"],
                    item["precision"],
                ),
            )
        )
    passed = len(selected) == 4 and all(item["pass"] for item in selected)
    after_hashes = _audio_hashes(samples)
    _require(after_hashes, before_hashes, "retained WAV hashes after ASR")
    _require(
        after_hashes,
        {
            key: value["audio_sha256"]
            for key, value in EXPECTED_SAMPLE_BINDINGS.items()
        },
        "retained WAV expected hashes after ASR",
    )

    result = {
        **evidence,
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": (
            "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
            if passed
            else "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED"
        ),
        "input_evidence": {
            "path": str(input_path.resolve()),
            "sha256": EXPECTED_INPUT_SHA256,
            "unchanged": (
                EXECUTOR.PREFLIGHT.sha256_file(input_path) == EXPECTED_INPUT_SHA256
            ),
        },
        "asr_prior_run": copy.deepcopy(evidence["asr"]),
        "asr": {
            "status": "PASS" if passed else "FAIL",
            "mode": "ASR_ONLY_RETAINED_HASH_BOUND_AUDIO",
            "audio_derived": True,
            "model": EXECUTOR.BASE.WHISPER_MODEL,
            "model_sha256": EXECUTOR.PREFLIGHT.WHISPER_SHA256,
            "repair_fingerprint": fingerprint,
            "score_min": ASR_SCORE_MIN,
            "coverage_min": ASR_COVERAGE_MIN,
            "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
            "reports": selected,
        },
        "asr_repair": {
            "completed": True,
            "repair_fingerprint": fingerprint,
            "fingerprint_closed": True,
            "prior_config_fingerprint": EXPECTED_PRIOR_ASR_FINGERPRINT,
            "prior_transcript_hashes": EXPECTED_PRIOR_TRANSCRIPT_HASHES,
            "decoder_arms": DECODING_ARMS,
            "both_arms_run_for_every_passage": True,
            "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
            "forbidden_normalizations": FORBIDDEN_NORMALIZATIONS,
            "all_candidates": candidates,
            "selected_decoder_by_passage": {
                str(item["passage_id"]): str(item["decoder_arm"])
                for item in selected
            },
            "retained_audio_hashes_before": before_hashes,
            "retained_audio_hashes_after": after_hashes,
            "retained_audio_immutable": before_hashes == after_hashes,
            "resynthesis_performed": False,
            "audio_edit_or_trim_performed": False,
            "trailing_you_deleted_or_normalized": False,
            "trailing_thanks_for_watching_deleted_or_normalized": False,
            "unexpected_speech_deleted_or_normalized": False,
        },
        "safety": {
            **evidence["safety"],
            "asr_run": True,
            "audio_generated_during_repair": False,
            "resynthesis_performed": False,
            "audio_edit_or_trim_performed": False,
            "asr_only_repair": True,
            "provider_calls_during_repair": 0,
            "listening_provider_calls": 0,
            "paid_coordination_lock_inspected": False,
            "paid_coordination_lock_touched": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        },
        "next_stage_contract": {
            "status": (
                "READY_FOR_INDEPENDENT_LISTENING_QA"
                if passed
                else "ASR_REPAIR_FINGERPRINT_CLOSED_OBJECTIVE_FAIL"
            ),
            "repair_fingerprint": fingerprint,
            "exact_execute_command": None,
            "do_not_repeat_completed_fingerprint": True,
            "listening_qa_allowed": passed,
            "full_title_generation_allowed": False,
            "upload_allowed": False,
            "publication_allowed": False,
            "release_gate_mutation_allowed": False,
            "next_action": (
                "Run independent listening QA over the same hash-bound private WAVs."
                if passed
                else "Use a materially different voice/provider or source-bound narration; do not repeat this synthesis or ASR-repair fingerprint."
            ),
        },
        "blockers_to_release": [
            *([] if passed else ["REPRESENTATIVE_ASR_REPAIR_FAILED"]),
            "INDEPENDENT_LISTENING_QA_NOT_RUN",
            "FULL_TITLE_NOT_GENERATED",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "CANONICAL_FRONT_COVER_MISSING",
            "TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "PRIVATE_UPLOAD_CHECKSUM_NOT_RUN",
            "PRODUCTION_ENDPOINT_NOT_RUN",
            "BROWSER_PLAYBACK_GATE_NOT_RUN",
            "OWNER_10_TARGET_NOT_VERIFIED",
        ],
    }
    write_json(output_path, result)
    return (0 if passed else 4), result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        code, result = execute(
            args.input.expanduser().resolve(),
            args.output.expanduser().resolve(),
            args.whisper_cache.expanduser().resolve(),
            dry_run=args.dry_run,
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "repair_fingerprint": result.get("repair_fingerprint")
                    or (result.get("asr_repair") or {}).get("repair_fingerprint"),
                    "output": None if args.dry_run else str(args.output.resolve()),
                    "retained_audio_immutable": (
                        result.get("retained_audio_immutable")
                        if args.dry_run
                        else (result.get("asr_repair") or {}).get(
                            "retained_audio_immutable"
                        )
                    ),
                    "both_arms_run_for_every_passage": (
                        result.get("both_arms_will_run_for_every_passage")
                        if args.dry_run
                        else (result.get("asr_repair") or {}).get(
                            "both_arms_run_for_every_passage"
                        )
                    ),
                    "resynthesis_performed": False,
                    "audio_edit_or_trim_performed": False,
                    "listening_provider_calls": 0,
                    "paid_coordination_lock_inspected": False,
                    "upload_performed": False,
                    "publication_performed": False,
                    "release_gate_mutated": False,
                },
                indent=2,
            )
        )
        return code
    except (
        TellTaleASRRepairError,
        EXECUTOR.TellTaleExecutorError,
        EXECUTOR.PREFLIGHT.TellTalePreflightError,
        EXECUTOR.BASE.KokoroTitlePilotError,
    ) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
