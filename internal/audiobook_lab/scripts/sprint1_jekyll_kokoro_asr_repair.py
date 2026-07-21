#!/usr/bin/env python3
"""Run one bounded ASR-only bakeoff over retained Jekyll WAVs.

Two deterministic, unprompted local Whisper arms inspect every immutable WAV
for either checksum-bound voice.  Every raw transcript is retained.  Only
exact-count acoustic spelling, homophone, and compound-token equivalences are
permitted.  The module cannot synthesize, edit audio, listen, upload, publish,
or mutate controlled release truth.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
CORE_PATH = Path(__file__).with_name("sprint1_gift_bf_emma_asr_repair.py")
CORE_SPEC = importlib.util.spec_from_file_location("jekyll_retained_wav_asr_core", CORE_PATH)
if CORE_SPEC is None or CORE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load retained-WAV ASR repair core: {CORE_PATH}")
CORE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE)

PROFILE_PATH = Path(__file__).with_name("sprint1_jekyll_kokoro_private_bakeoff.py")
PROFILE_SPEC = importlib.util.spec_from_file_location("jekyll_kokoro_profile", PROFILE_PATH)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Jekyll profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILE)


EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.jekyll_representative.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_PAID_LOCK_SHA256 = (
    "f586acc793022f28adb3e5fe08969075c2a16f09ef6814ebb31f6e6c90163df3"
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
)
EQUIVALENCE_POLICY = {
    "opening_character": (
        {
            "pattern": r"\bbeakened\b",
            "replacement": "beaconed",
            "expected_count_when_observed": 1,
            "reason": "non-word ASR spelling for the source-generated beaconed phonemes",
        },
        {
            "pattern": r"\btheater\b",
            "replacement": "theatre",
            "expected_count_when_observed": 1,
            "reason": "American ASR spelling for source British spelling theatre",
        },
    ),
    "carew_murder": (
        {
            "pattern": r"\bunderfoot\b",
            "replacement": "under foot",
            "expected_count_when_observed": 1,
            "reason": "ASR compound for the exact source words under foot",
        },
    ),
    "lanyon_transformation": (
        {
            "pattern": r"\boh\b",
            "replacement": "O",
            "expected_count_when_observed": 2,
            "reason": "ASR interjection spelling for both source O exclamations",
        },
    ),
    "final_confession": (
        {
            "pattern": r"\bre[- ]endue\b",
            "replacement": "reindue",
            "expected_count_when_observed": 1,
            "reason": "ASR tokenization of the source word reindue",
        },
        {
            "pattern": r"\bfear[- ]struck\b",
            "replacement": "fearstruck",
            "expected_count_when_observed": 1,
            "reason": "ASR tokenization of the source compound fearstruck",
        },
        {
            "pattern": r"\bhide\b",
            "replacement": "Hyde",
            "expected_count_when_observed": 1,
            "reason": "ASR homophone spelling for one source occurrence of the name Hyde",
        },
    ),
}
FORBIDDEN_NORMALIZATIONS = (
    "wondering/wandering",
    "beaconed/beacon",
    "features/feature",
    "missing inflection insertion",
    "unexpected speech deletion",
    "missing source content insertion",
    "substantive word substitution",
)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
VOICE_REPAIR_PROFILES: dict[str, dict[str, Any]] = {
    "bm_george": {
        "schema": "earnalism.kokoro.jekyll_bm_george_asr_repair.v1",
        "input_sha256": "568db8d5c220004384bb5ba755628be317cc53513b7c0e485a46aac01c40d90e",
        "attempt_fingerprint": "e10223569eb619615f05c83cc824eca7a247ede7788eba5d78e0fb17fea3ec2f",
        "prior_asr_fingerprint": "35822c09b7b162b790c258557c25abee07363873ab98f0a730edfbc6bb7468d9",
        "prior_transcript_hashes": {
            "opening_character": "a44b2c4c15e3c8bfc9141891dc04cf06f77b046c88c4962f0428912affea5fa4",
            "carew_murder": "681034ce414eeb1bd01fbe6e3abea6f525e6dbc55a4d5278036d20ca786638a0",
            "lanyon_transformation": "eb57286c4d660a926d5409a05e229ad2c9a6d8ece7930b62e8ec3e3ded932c85",
            "final_confession": "ae57240ff9811a31dcb41ccb2e3256308fce88ac87fdb8386b75b3038755e051",
        },
        "sample_bindings": {
            "opening_character": {
                "source_text_sha256": "b491afef3119554f32c9250f5a81446b55bd81a63bf2fecf3b4940da8e4f1994",
                "audio_sha256": "0c39a3fa2fe66131f9c57cfbac3e5b270f5b43d75aa215158d9d298a508381a6",
                "size_bytes": 2_715_644,
                "duration_seconds": 56.575,
            },
            "carew_murder": {
                "source_text_sha256": "b45aebd6abcc2e730d156ad71d2964eeff8a1f472cc7146ade53575ec386bd8f",
                "audio_sha256": "dad290dcd691f60904a855373a1487ab3cd6ce393cb8bbf5776f931938b8145e",
                "size_bytes": 2_510_444,
                "duration_seconds": 52.3,
            },
            "lanyon_transformation": {
                "source_text_sha256": "3bd9b43260be8299d10f73995dd4c5706e39eba3e0844bf88c619bc7373d47ff",
                "audio_sha256": "3fe90dbfdceab82ab91bd28e58406cf145d107c141e2747aee98caa27966f0bb",
                "size_bytes": 1_993_244,
                "duration_seconds": 41.525,
            },
            "final_confession": {
                "source_text_sha256": "fee77d935c85880bed743ddd65949450c5bb5f5528e8a40101d34cf3e2d11e93",
                "audio_sha256": "e4fbad3f91538722187afd82dede7e4e4691977f652e091933fb1a53d11d3112",
                "size_bytes": 4_344_044,
                "duration_seconds": 90.5,
            },
        },
        "expected_repair_fingerprint": "f769f885ffadc9f3553b76d90ecb32550b58a81fb85bab91c3e5da33fda78109",
    },
    "am_michael": {
        "schema": "earnalism.kokoro.jekyll_am_michael_asr_repair.v1",
        "input_sha256": "e5c48e568a0f13ea4942246e66b23a382b758af864475e20d8e8815a31f8c12e",
        "attempt_fingerprint": "d48d3bc8ce9ca01a7ceacea9f9aae806cb9b1cd6f58eb20f15a715230435f881",
        "prior_asr_fingerprint": "9bac2fad37f50627bc49bc26373f2b71dabdc1b42a39ea45899283e049948fb0",
        "prior_transcript_hashes": {
            "opening_character": "9d58aea150181d08ff11c303e8d6817914fc4b7a40831266f35bac8883a8f376",
            "carew_murder": "1fee4c490fda2cf0231580a13c42cc78348de14145dc211211a1e623f062380c",
            "lanyon_transformation": "9b24821daaf14072575b6b7b9f3f2138bc89e11557e72826bc93b3fbaf9da1ff",
            "final_confession": "66822b26275cbe370d9ecd1c9d9d67c3c6aca104d24ba0eb4eef85ad686f6cb1",
        },
        "sample_bindings": {
            "opening_character": {
                "source_text_sha256": "b491afef3119554f32c9250f5a81446b55bd81a63bf2fecf3b4940da8e4f1994",
                "audio_sha256": "6e89fe177ad1f1a17d3d1da2df5ff4d09ff9c7f489652a83d805295059a09a05",
                "size_bytes": 2_996_444,
                "duration_seconds": 62.425,
            },
            "carew_murder": {
                "source_text_sha256": "b45aebd6abcc2e730d156ad71d2964eeff8a1f472cc7146ade53575ec386bd8f",
                "audio_sha256": "7f482ef698f7ed2f990f381404f9b1572d960b086a46ff9f9772226300802cc2",
                "size_bytes": 2_778_044,
                "duration_seconds": 57.875,
            },
            "lanyon_transformation": {
                "source_text_sha256": "3bd9b43260be8299d10f73995dd4c5706e39eba3e0844bf88c619bc7373d47ff",
                "audio_sha256": "7b4aad2cd091ddf3c7fcce42d9ccadf32d235f79ba0fe738ab53ac883b1da205",
                "size_bytes": 2_095_244,
                "duration_seconds": 43.65,
            },
            "final_confession": {
                "source_text_sha256": "fee77d935c85880bed743ddd65949450c5bb5f5528e8a40101d34cf3e2d11e93",
                "audio_sha256": "d342fe81f0a5d6cf03ba9212e7608deba96d9b1cce3b31625659500a7c897ff7",
                "size_bytes": 4_672_844,
                "duration_seconds": 97.35,
            },
        },
        "expected_repair_fingerprint": "e3baf10c2befd2514d5760463934c9a2b23d389542ea69ff0746dacdfd044a4c",
    },
}
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/"
    "sprint1_provider_failure_registry.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "jekyll-and-hyde_release_gate_evidence.json",
)

ACTIVE_VOICE = "bm_george"
ACTIVE = VOICE_REPAIR_PROFILES[ACTIVE_VOICE]
SCHEMA = str(ACTIVE["schema"])
EXPECTED_INPUT_SHA256 = str(ACTIVE["input_sha256"])
EXPECTED_ATTEMPT_FINGERPRINT = str(ACTIVE["attempt_fingerprint"])
EXPECTED_PRIOR_ASR_FINGERPRINT = str(ACTIVE["prior_asr_fingerprint"])
EXPECTED_PRIOR_TRANSCRIPT_HASHES = dict(ACTIVE["prior_transcript_hashes"])
EXPECTED_SAMPLE_BINDINGS = dict(ACTIVE["sample_bindings"])
DEFAULT_INPUT = ROOT / "unused"
DEFAULT_OUTPUT = ROOT / "unused"
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK

JekyllASRRepairError = CORE.GiftEmmaASRRepairError


def default_input(voice: str) -> Path:
    return ROOT / (
        "internal/audiobook_lab/sprint1_publication/title_runs/"
        f"jekyll-and-hyde_kokoro_{voice}_representative_v1.json"
    )


def default_output(voice: str) -> Path:
    return ROOT / (
        "internal/audiobook_lab/sprint1_publication/title_runs/"
        f"jekyll-and-hyde_kokoro_{voice}_asr_repair_v1.json"
    )


def evaluate_transcript(
    passage: Mapping[str, Any],
    sample: Mapping[str, Any],
    transcript: str,
    arm_id: str,
) -> dict[str, Any]:
    try:
        evaluated, applications = CORE.apply_equivalences(
            str(passage["passage_id"]), transcript
        )
        equivalence_error = None
    except JekyllASRRepairError as exc:
        evaluated = transcript
        applications = []
        equivalence_error = str(exc)
    metrics = PROFILE.BASE.ordered_token_integrity(str(passage["text"]), evaluated)
    passed = bool(
        equivalence_error is None
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
        "passage_id": passage["passage_id"],
        "decoder_arm": arm_id,
        "audio_sha256": sample["audio_sha256"],
        "source_text_sha256": passage["text_sha256"],
        "raw_transcript": transcript,
        "raw_transcript_sha256": PROFILE.BASE.sha256_text(transcript),
        "evaluated_transcript": evaluated,
        "evaluated_transcript_sha256": PROFILE.BASE.sha256_text(evaluated),
        "source_equivalences_applied": applications,
        "equivalence_count_error": equivalence_error,
        "substantive_normalization_performed": False,
        "unexpected_speech_deleted_or_normalized": False,
        **metrics,
        "pass": passed,
    }


def configure(voice: str) -> None:
    global ACTIVE, ACTIVE_VOICE, DEFAULT_INPUT, DEFAULT_OUTPUT
    global EXPECTED_ATTEMPT_FINGERPRINT, EXPECTED_INPUT_SHA256
    global EXPECTED_PRIOR_ASR_FINGERPRINT, EXPECTED_PRIOR_TRANSCRIPT_HASHES
    global EXPECTED_SAMPLE_BINDINGS, SCHEMA
    if voice not in VOICE_REPAIR_PROFILES:
        raise JekyllASRRepairError(f"unsupported voice: {voice}")
    ACTIVE_VOICE = voice
    ACTIVE = VOICE_REPAIR_PROFILES[voice]
    PROFILE.configure_base(voice)
    PROFILE.VOICE = voice
    PROFILE.VOICE_SHA256 = str(PROFILE.VOICE_PROFILES[voice]["voice_sha256"])
    PROFILE.WHISPER_SHA256 = PROFILE.BASE.WHISPER_SHA256
    SCHEMA = str(ACTIVE["schema"])
    EXPECTED_INPUT_SHA256 = str(ACTIVE["input_sha256"])
    EXPECTED_ATTEMPT_FINGERPRINT = str(ACTIVE["attempt_fingerprint"])
    EXPECTED_PRIOR_ASR_FINGERPRINT = str(ACTIVE["prior_asr_fingerprint"])
    EXPECTED_PRIOR_TRANSCRIPT_HASHES = dict(ACTIVE["prior_transcript_hashes"])
    EXPECTED_SAMPLE_BINDINGS = dict(ACTIVE["sample_bindings"])
    DEFAULT_INPUT = default_input(voice)
    DEFAULT_OUTPUT = default_output(voice)
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


def repair_fingerprint() -> str:
    observed = CORE.repair_fingerprint()
    expected = str(ACTIVE["expected_repair_fingerprint"])
    if observed != expected:
        raise JekyllASRRepairError(
            f"Jekyll {ACTIVE_VOICE} ASR repair contract changed without fingerprint rebind: "
            f"expected {expected}, observed {observed}"
        )
    return observed


def validate_input(path: Path):
    return CORE.validate_input(path)


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
    blockers = [
        (
            "JEKYLL_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
            if blocker == "GIFT_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND"
            else blocker
        )
        for blocker in result["blockers_to_release"]
    ]
    if "FRONT_COVER_LINKAGE_REQUIRED_BEFORE_PUBLICATION" not in blockers:
        blockers.append("FRONT_COVER_LINKAGE_REQUIRED_BEFORE_PUBLICATION")
    result["blockers_to_release"] = blockers
    CORE.write_json(output_path, result)
    return code, result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--voice", choices=sorted(VOICE_REPAIR_PROFILES), required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        configure(args.voice)
        input_path = (args.input or default_input(args.voice)).resolve()
        output_path = (args.output or default_output(args.voice)).resolve()
        code, result = execute(
            input_path,
            output_path,
            args.whisper_cache.resolve(),
            args.paid_lock.resolve(),
            dry_run=args.dry_run,
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "voice": ACTIVE_VOICE,
                    "repair_fingerprint": result.get("repair_fingerprint")
                    or (result.get("asr_repair") or {}).get("repair_fingerprint"),
                    "output": None if args.dry_run else str(output_path),
                    "retained_audio_immutable": (
                        result.get("retained_audio_immutable")
                        if args.dry_run
                        else (result.get("asr_repair") or {}).get("retained_audio_immutable")
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
        return int(code)
    except (JekyllASRRepairError, PROFILE.BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


configure(ACTIVE_VOICE)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
