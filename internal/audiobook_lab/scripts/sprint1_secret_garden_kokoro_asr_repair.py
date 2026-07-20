#!/usr/bin/env python3
"""Run one bounded decoder bakeoff over retained Secret Garden WAVs.

Three deterministic local Whisper arms inspect every immutable private WAV.
Every raw transcript is retained and no transcript normalization is allowed in
this first repair pass.  The module cannot synthesize, edit audio, listen,
upload, publish, or mutate controlled release truth.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
CORE_PATH = Path(__file__).with_name("sprint1_gift_bf_emma_asr_repair.py")
CORE_SPEC = importlib.util.spec_from_file_location(
    "secret_garden_retained_wav_asr_core", CORE_PATH
)
if CORE_SPEC is None or CORE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load retained-WAV ASR repair core: {CORE_PATH}")
CORE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE)

PROFILE_PATH = Path(__file__).with_name(
    "sprint1_secret_garden_af_bella_private_audition.py"
)
PROFILE_SPEC = importlib.util.spec_from_file_location(
    "secret_garden_kokoro_profile", PROFILE_PATH
)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Secret Garden profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILE)


SCHEMA = "earnalism.kokoro.secret_garden_af_bella_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.secret_garden_representative.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = (
    "6bb01cc0fb29ebe49fa4b4f5e5000d010b1768cfd374559b712f1bd86f8d5ed4"
)
EXPECTED_ATTEMPT_FINGERPRINT = PROFILE.EXPECTED_ATTEMPT_FINGERPRINT
EXPECTED_PRIOR_ASR_FINGERPRINT = (
    "38c9f10438fcfc4811c91545be6327fd47ed7966a1c39424303792e113c569e8"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "f586acc793022f28adb3e5fe08969075c2a16f09ef6814ebb31f6e6c90163df3"
)
EXPECTED_REPAIR_FINGERPRINT = (
    "54c3054797c0c1ef9f193a63c2ec538759c3a23ced1f7b41610e10dc7da38692"
)
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_india": "b2fe3a449fc2a6630f95da3af3e8fe7c0662340e3848fa436300e13c1fd37ebe",
    "yorkshire_dialogue": "767fdbda81e6a631369f1b94744846092fe8e3c671ca71862fcb43538d299d92",
    "mary_colin_emotion": "337c78914bdb27b9f1eec2247ca014810723eda963d656506aaca78fb799531a",
    "ending_return": "ed377c4b84d74c5a5917f24b4f936aa0a2a52f67309b4e076d16d1db08f172df",
}
EXPECTED_SAMPLE_BINDINGS = {
    "opening_india": {
        "source_text_sha256": "9921329ed99b36731d1ca45e6f209dd44e3fc22376009f75d3e4246d94daf341",
        "audio_sha256": "82471a359c466ecd2d5f42a2320df0eec0634c10c1532302f3acdce7ce173730",
        "size_bytes": 2_306_444,
        "duration_seconds": 48.05,
    },
    "yorkshire_dialogue": {
        "source_text_sha256": "be1275f2818dab21ed28678a84a6a4029a41166bc74fe7b2caedbc58290285ad",
        "audio_sha256": "cf2f59435cd7a591c23f9bdab0403b23e389115542b87e26d298e4eccfd82c4b",
        "size_bytes": 2_278_844,
        "duration_seconds": 47.475,
    },
    "mary_colin_emotion": {
        "source_text_sha256": "ff3b5af98b532ad81f19df606c456aea0580519c9683d5a81b48de755a4023dd",
        "audio_sha256": "38bb4bf3613794a7d3486b28ede1f791dfde7e8252fd7c6edc235aca3beb1f6b",
        "size_bytes": 2_473_244,
        "duration_seconds": 51.525,
    },
    "ending_return": {
        "source_text_sha256": "bdd08b81e13c0ec9c4e74854e1c8eb939963ba13c76187c258b39488193cb6cc",
        "audio_sha256": "e3096aee4f44ec6c5e59c7c5c385b401f82259919a8857e8377c3897c9929dd4",
        "size_bytes": 1_291_244,
        "duration_seconds": 26.9,
    },
}

VOCABULARY_PROMPT = (
    "Canonical spellings: Mary Lennox; Misselthwaite; Martha; Mrs. Medlock; "
    "Ayah; Mem Sahib; Colin; Yorkshire; Canna; tha; thysen; Eh; sayin; bein. "
    "Preserve every spoken word and the Yorkshire dialect."
)
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
    {
        "id": "canonical_vocabulary_beam_2",
        "initial_prompt": VOCABULARY_PROMPT,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": 2,
        "patience": 1,
        "hallucination_silence_threshold": 0.5,
    },
)

# Raw decoder evidence must stand on its own in this first retained-WAV pass.
# Any later acoustic/orthographic projection must be separately reviewed,
# fingerprinted, and operate only on these retained raw candidates.
EQUIVALENCE_POLICY = {
    "opening_india": (),
    "yorkshire_dialogue": (
        {
            "pattern": r"\bcan a\b",
            "replacement": "canna",
            "expected_count_when_observed": 1,
            "reason": "ASR token split for the acoustically identical dialect source canna",
        },
        {
            "pattern": r"\bdress thy sen\b",
            "replacement": "dress thysen",
            "expected_count_when_observed": 1,
            "reason": "context-bound ASR token split for source dress thysen",
        },
        {
            "pattern": r"\bwait on thy sen\b",
            "replacement": "wait on thysen",
            "expected_count_when_observed": 1,
            "reason": "context-bound ASR token split for source wait on thysen",
        },
    ),
    "mary_colin_emotion": (),
    "ending_return": (),
}
FORBIDDEN_NORMALIZATIONS = (
    "missing Who is",
    "tha / they",
    "thysen / thy son",
    "Eh / ay",
    "thee / the",
    "sayin / saying",
    "bein / being",
    "an / and",
    "trailing unexpected speech",
    "unexpected speech deletion",
)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_af_bella_representative_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_af_bella_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_release_gate_evidence.json",
)

SecretGardenASRRepairError = CORE.GiftEmmaASRRepairError


def _configure_core() -> None:
    bindings = {
        "ROOT": ROOT,
        "PROFILE": PROFILE,
        "SCHEMA": SCHEMA,
        "EXPECTED_INPUT_SCHEMA": EXPECTED_INPUT_SCHEMA,
        "EXPECTED_INPUT_STATUS": EXPECTED_INPUT_STATUS,
        "EXPECTED_INPUT_SHA256": EXPECTED_INPUT_SHA256,
        "EXPECTED_ATTEMPT_FINGERPRINT": EXPECTED_ATTEMPT_FINGERPRINT,
        "EXPECTED_PRIOR_ASR_FINGERPRINT": EXPECTED_PRIOR_ASR_FINGERPRINT,
        "EXPECTED_PAID_LOCK_SHA256": EXPECTED_PAID_LOCK_SHA256,
        "EXPECTED_PRIOR_TRANSCRIPT_HASHES": EXPECTED_PRIOR_TRANSCRIPT_HASHES,
        "EXPECTED_SAMPLE_BINDINGS": EXPECTED_SAMPLE_BINDINGS,
        "DECODING_ARMS": DECODING_ARMS,
        "EQUIVALENCE_POLICY": EQUIVALENCE_POLICY,
        "FORBIDDEN_NORMALIZATIONS": FORBIDDEN_NORMALIZATIONS,
        "ASR_SCORE_MIN": ASR_SCORE_MIN,
        "ASR_COVERAGE_MIN": ASR_COVERAGE_MIN,
        "DEFAULT_INPUT": DEFAULT_INPUT,
        "DEFAULT_OUTPUT": DEFAULT_OUTPUT,
        "DEFAULT_WHISPER_CACHE": DEFAULT_WHISPER_CACHE,
        "DEFAULT_PAID_LOCK": DEFAULT_PAID_LOCK,
        "NO_REPEAT_FILES": NO_REPEAT_FILES,
    }
    for name, value in bindings.items():
        setattr(CORE, name, value)
    CORE.evaluate_transcript = evaluate_transcript


def evaluate_transcript(
    passage: Mapping[str, Any],
    sample: Mapping[str, Any],
    transcript: str,
    arm_id: str,
) -> dict[str, Any]:
    evaluated, applications = CORE.apply_equivalences(
        str(passage["passage_id"]), transcript
    )
    metrics = PROFILE.BASE.ordered_token_integrity(str(passage["text"]), evaluated)
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
    return {
        "passage_id": passage["passage_id"],
        "decoder_arm": arm_id,
        "audio_sha256": sample["audio_sha256"],
        "source_text_sha256": passage["text_sha256"],
        "raw_transcript": transcript,
        "raw_transcript_sha256": PROFILE.BASE.sha256_text(transcript),
        "evaluated_transcript": evaluated,
        "evaluated_transcript_sha256": PROFILE.BASE.sha256_text(evaluated),
        "source_equivalences_applied": applications,
        "substantive_normalization_performed": False,
        "unexpected_speech_deleted_or_normalized": False,
        **metrics,
        "pass": passed,
    }


def validate_input(path: Path):
    _configure_core()
    return CORE.validate_input(path)


def repair_fingerprint() -> str:
    _configure_core()
    observed = CORE.repair_fingerprint()
    if observed != EXPECTED_REPAIR_FINGERPRINT:
        raise SecretGardenASRRepairError(
            "Secret Garden ASR repair contract changed without fingerprint rebind"
        )
    return observed


def execute(
    input_path: Path,
    output_path: Path,
    whisper_cache: Path,
    paid_lock: Path,
    *,
    dry_run: bool = False,
    model_loader: Callable[[Path], Any] = CORE.load_whisper_model,
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], str] = CORE.run_decoding_arm,
) -> tuple[int, dict[str, Any]]:
    _configure_core()
    repair_fingerprint()
    code, result = CORE.execute(
        input_path,
        output_path,
        whisper_cache,
        paid_lock,
        dry_run=dry_run,
        model_loader=model_loader,
        decoder=decoder,
    )
    if dry_run:
        return code, result
    repair = result["asr_repair"]
    repair.pop("substantive_were_are_normalized", None)
    repair["substantive_normalization_performed"] = False
    passed = result["status"] == (
        "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
    )
    result["go_no_go"] = (
        "GO_PRIVATE_LISTENING_QA_ONLY"
        if passed
        else "NO_GO_REPRESENTATIVE_ASR_REPAIR_FAILED"
    )
    result["blockers_to_release"] = [
        (
            "SECRET_GARDEN_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
            if blocker == "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
            else blocker
        )
        for blocker in result["blockers_to_release"]
    ]
    CORE.write_json(output_path, result)
    return code, result


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
            args.input.resolve(),
            args.output.resolve(),
            args.whisper_cache.resolve(),
            args.paid_lock.resolve(),
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
                    "decoder_arms": len(DECODING_ARMS),
                    "resynthesis_performed": False,
                    "audio_edit_or_trim_performed": False,
                    "listening_provider_calls": 0,
                    "upload_performed": False,
                    "publication_performed": False,
                    "release_gate_mutated": False,
                },
                indent=2,
            )
        )
        return code
    except (SecretGardenASRRepairError, PROFILE.BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


_configure_core()


if __name__ == "__main__":
    raise SystemExit(main())
