#!/usr/bin/env python3
"""Run Alice's single retained-WAV ASR repair without resynthesis.

Two materially different local Whisper decoder arms evaluate every immutable
sample. Only the exact ``armchair``/``arm-chair`` tokenization equivalence is
allowed. The missing repeated ``I`` and unexpected ``The end`` may not be
normalized, deleted, or invented.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
REPAIR_PATH = SCRIPT_DIR / "sprint1_secret_garden_kokoro_asr_repair.py"
REPAIR_SPEC = importlib.util.spec_from_file_location(
    "alice_retained_wav_repair_base", REPAIR_PATH
)
if REPAIR_SPEC is None or REPAIR_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load retained-WAV repair: {REPAIR_PATH}")
REPAIR = importlib.util.module_from_spec(REPAIR_SPEC)
REPAIR_SPEC.loader.exec_module(REPAIR)

PROFILE_PATH = SCRIPT_DIR / "sprint1_alice_kokoro_private_audition.py"
PROFILE_SPEC = importlib.util.spec_from_file_location(
    "alice_kokoro_profile", PROFILE_PATH
)
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load Alice profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILE)


ROOT = PROFILE.BASE.ROOT
SCHEMA = "earnalism.kokoro.alice_bf_emma_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.alice_private_representative.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = (
    "64260c0e243523956a1e45b4b44d79595930429e5bd6f24ed89d0228e2a29da2"
)
EXPECTED_ATTEMPT_FINGERPRINT = (
    "c1e8a0ae6617093d8f13b0b07ca3a72115dd56d9336a04716f44d116f7aad458"
)
EXPECTED_PRIOR_ASR_FINGERPRINT = (
    "a25889cf25534e85c8b53180afa765086cfd574496d9178f67b945d8e7a58f5b"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "9f54fb0bf4f77946280028a1c7a562ac425fb11750bf9f613eb22a836a36efd9"
)
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_rabbit_hook": (
        "a376f0e0dfa1da63be793324167fe87277e3b81a66ec9756d136b342ac3f1262"
    ),
    "caterpillar_identity_dialogue": (
        "b8ebaa3fcd7ff35f012154d14c0306fa657aabc7cbcacbf3f29ece9a644772d4"
    ),
    "mad_tea_party_exchange": (
        "4235c216e317158e080b704a68944050e955546fde33738c4e6983f36307f9b9"
    ),
    "wonderland_reflective_finale": (
        "dbaff6498caafb0ce71cc37a1b97461595e162a4576836961726e3e7e641decc"
    ),
}
EXPECTED_SAMPLE_BINDINGS = {
    "opening_rabbit_hook": {
        "source_text_sha256": (
            "9fa63f79b504b41a39bb743cca05f022ff6466fee7a379f95518efe33b95838c"
        ),
        "audio_sha256": (
            "cb4ad0682efc82453cfd0c5030260e2dd10e76d04f6a090775e402e6527f9fcf"
        ),
        "size_bytes": 1_580_444,
        "duration_seconds": 32.925,
    },
    "caterpillar_identity_dialogue": {
        "source_text_sha256": (
            "c4756e5876057019307352225d5fce7548bb7a9a44efea5b3b9a7cc7cf6b4273"
        ),
        "audio_sha256": (
            "dd020a54d6876f3d8d8229c7127088099a9c55d2b255cbaccdce31c01edbf4ec"
        ),
        "size_bytes": 1_165_244,
        "duration_seconds": 24.275,
    },
    "mad_tea_party_exchange": {
        "source_text_sha256": (
            "cf7055d45141e8acc3f1c34b906174efba37a6b6c90fba1fec59cbef51c02877"
        ),
        "audio_sha256": (
            "06e09899d635d3bbe9bf1b55f5b2e18bcb668ef754f29d225c080338d039d4f9"
        ),
        "size_bytes": 1_610_444,
        "duration_seconds": 33.55,
    },
    "wonderland_reflective_finale": {
        "source_text_sha256": (
            "5a5706f3b83a57db584682ba373e0de231f5c327de20a65374058d14264212f6"
        ),
        "audio_sha256": (
            "1019cfc62849222c9dca2f8d85665c56f06bfe0d5035c6fd7d336933ec42b3d2"
        ),
        "size_bytes": 1_454_444,
        "duration_seconds": 30.3,
    },
}

DECODING_ARMS = (
    {
        "id": "canonical_prompt_beam_5",
        "initial_prompt": (
            "Canonical spellings: Alice; White Rabbit; Caterpillar; March "
            "Hare; Hatter; Dormouse; Wonderland. Preserve repeated source "
            "words and never add an ending announcement."
        ),
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": 5,
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
    "opening_rabbit_hook": (),
    "caterpillar_identity_dialogue": (),
    "mad_tea_party_exchange": (
        {
            "pattern": r"\barmchair\b",
            "replacement": "arm chair",
            "expected_count_when_observed": 1,
            "reason": (
                "ASR compound tokenization for the acoustically spoken source "
                "hyphenated arm-chair"
            ),
        },
    ),
    "wonderland_reflective_finale": (),
}
FORBIDDEN_NORMALIZATIONS = (
    "missing repeated I",
    "unexpected trailing The end",
    "unexpected speech deletion",
    "missing source word invention",
    "audio edit or trim",
)
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "alices-adventures-in-wonderland_kokoro_bf_emma_representative_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "alices-adventures-in-wonderland_kokoro_bf_emma_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
)
AliceASRRepairError = REPAIR.CORE.GiftEmmaASRRepairError


def configure() -> None:
    values = {
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
        "SecretGardenASRRepairError": AliceASRRepairError,
    }
    for name, value in values.items():
        setattr(REPAIR, name, value)
    REPAIR._configure_core()


def validate_input(path: Path = DEFAULT_INPUT):
    configure()
    return REPAIR.validate_input(path)


def repair_fingerprint() -> str:
    configure()
    return REPAIR.repair_fingerprint()


def apply_equivalences(passage_id: str, transcript: str):
    configure()
    return REPAIR.apply_equivalences(passage_id, transcript)


def execute(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    whisper_cache: Path = DEFAULT_WHISPER_CACHE,
    paid_lock: Path = DEFAULT_PAID_LOCK,
    *,
    dry_run: bool = False,
    model_loader: Callable[[Path], Any] = REPAIR.CORE.load_whisper_model,
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], str] = (
        REPAIR.CORE.run_decoding_arm
    ),
):
    configure()
    return REPAIR.execute(
        input_path,
        output_path,
        whisper_cache,
        paid_lock,
        dry_run=dry_run,
        model_loader=model_loader,
        decoder=decoder,
    )


def main(argv: Sequence[str] | None = None) -> int:
    configure()
    return int(REPAIR.main(argv))


configure()


if __name__ == "__main__":
    raise SystemExit(main())
