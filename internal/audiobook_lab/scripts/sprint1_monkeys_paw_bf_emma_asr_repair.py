#!/usr/bin/env python3
"""Run one bounded ASR-only repair over retained ``bf_emma`` WAVs.

The repair runs three deterministic Whisper decoders over all four immutable
private samples.  Its only normalizations are exact-count British homophones
whose phoneme sequences are identical under the same pinned fallback-free G2P
used for synthesis.  Missing words, unexpected speech, and other substantive
differences remain release-blocking.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Sequence


SCRIPT_DIR = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BF_PROFILE = _load(
    "monkeys_paw_bf_emma_profile",
    SCRIPT_DIR / "sprint1_monkeys_paw_bf_emma_private_audition.py",
)
REPAIR = _load(
    "monkeys_paw_retained_wav_repair",
    SCRIPT_DIR / "sprint1_monkeys_paw_kokoro_asr_repair.py",
)

SCHEMA = "earnalism.kokoro.monkeys_paw_bf_emma_asr_repair.v1"
EXPECTED_INPUT_SCHEMA = (
    "earnalism.kokoro.monkeys_paw_bf_emma_private_audition.v1"
)
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = (
    "87205ed312419ccdbfd8360e48e75082ee524f2e7508584cce6d28381efc7ba8"
)
EXPECTED_ATTEMPT_FINGERPRINT = BF_PROFILE.EXPECTED_ATTEMPT_FINGERPRINT
EXPECTED_PRIOR_ASR_FINGERPRINT = (
    "114a081664865b1dba6981cc138edb67381ff8775895c64884f491d074d62ac1"
)
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_domestic_tension": (
        "0e6764a39e9be495a0ab1d20b51520bc7b02557cc7812ea438172a3126ae7706"
    ),
    "paw_warning_and_fate": (
        "03a6b935fa705dde7db724f8c5a2dbdf54150703120b4f11538edd8a46f88998"
    ),
    "factory_news_and_grief": (
        "182cf47c0c94b82bc6351b972a8d66cc6b810d63d227b8aa9024d723fa040c19"
    ),
    "final_knocking_and_third_wish": (
        "5a5047cc73b802c06d625a48cdad4aa8bb13ac3549f1cdf413b362827dcabdad"
    ),
}
EXPECTED_SAMPLE_BINDINGS = {
    "opening_domestic_tension": {
        "source_text_sha256": "1505ffdc29416106677ad7c3ef7ea0a3db602c1069e1d72b81327721c1fe5765",
        "audio_sha256": "2e55b15d360985800588be280ebcc2194a366f93e3b745cd96c787a0259f9559",
        "size_bytes": 990_044,
        "duration_seconds": 20.625,
    },
    "paw_warning_and_fate": {
        "source_text_sha256": "a3ec2e40908f432cca118c418e743329bccc9f411908bc16da2f725e8e43007d",
        "audio_sha256": "b2b02e381e4e4d095bad79a9e6ecfb9b41718fead258b88b09a7212c5de2db94",
        "size_bytes": 2_661_644,
        "duration_seconds": 55.45,
    },
    "factory_news_and_grief": {
        "source_text_sha256": "6877bbcbea4fdfd7729b41ff27dc422b18dd6d44b7b0e4893555ba5e109cf0aa",
        "audio_sha256": "cf303ce5afeb6f66df9393ae44e2c4f5233f714ff5310dfcfda216c8c459577f",
        "size_bytes": 2_478_044,
        "duration_seconds": 51.625,
    },
    "final_knocking_and_third_wish": {
        "source_text_sha256": "9198f815c21620148cfab038af5bdaadedd7397567c9a9010c1d1bc340148fb4",
        "audio_sha256": "38d725efe65b6654bff62cee8ac79c8c40d5ed5c3e87012ab6fb1ac84d0e1921",
        "size_bytes": 3_223_244,
        "duration_seconds": 67.15,
    },
}

VOCABULARY_PROMPT = (
    "Canonical spellings: to-night; middle age is wont; paw; Maw and Meggins; "
    "Oh, thank God; slower-witted; fusillade. Preserve every spoken word."
)
DECODING_ARMS = (
    {
        "id": "unprompted_beam_5",
        "initial_prompt": None,
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
    {
        "id": "canonical_vocabulary_beam_5",
        "initial_prompt": VOCABULARY_PROMPT,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": 5,
        "patience": 1,
        "hallucination_silence_threshold": 0.5,
    },
)

# These substitutions are phoneme-identical under British non-rhotic speech.
# Rules remain passage-bound and exact-count; they cannot hide missing speech.
EQUIVALENCE_POLICY = {
    "opening_domestic_tension": (
        {
            "pattern": r"\btonight\b",
            "replacement": "to night",
            "expected_count_when_observed": 1,
            "reason": "British ASR tokenization of source to-night",
        },
    ),
    "paw_warning_and_fate": (
        {
            "pattern": r"\bmiddle ages (?:won't|wont)\b",
            "replacement": "middle age is wont",
            "expected_count_when_observed": 1,
            "reason": "phoneme-identical British boundary parse of middle age is wont",
        },
        {
            "pattern": r"\b(?:poor|pour)\b",
            "replacement": "paw",
            "expected_count_when_observed": 1,
            "reason": "non-rhotic British homophone for source paw",
        },
    ),
    "factory_news_and_grief": (
        {
            "pattern": r"\b(?:moore|more)\b",
            "replacement": "maw",
            "expected_count_when_observed": 1,
            "reason": "non-rhotic British homophone for source Maw",
        },
    ),
    "final_knocking_and_third_wish": (
        {
            "pattern": r"\b(?:poor|pour)\b",
            "replacement": "paw",
            "expected_count_when_observed": 1,
            "reason": "non-rhotic British homophone for source paw",
        },
    ),
}
FORBIDDEN_NORMALIZATIONS = (
    "missing initial I",
    "missing witted",
    "missing or duplicated content",
    "unexpected speech deletion",
    "non-homophonic substitutions",
)

DEFAULT_INPUT = REPAIR.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_bf_emma_representative_v1.json"
)
DEFAULT_OUTPUT = REPAIR.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_bf_emma_asr_repair_v1.json"
)
NO_REPEAT_FILES = (
    REPAIR.ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    REPAIR.ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    DEFAULT_INPUT,
)


def configure_repair() -> None:
    REPAIR.PROFILE = BF_PROFILE.PROFILE_BASE
    REPAIR.SCHEMA = SCHEMA
    REPAIR.EXPECTED_INPUT_SCHEMA = EXPECTED_INPUT_SCHEMA
    REPAIR.EXPECTED_INPUT_STATUS = EXPECTED_INPUT_STATUS
    REPAIR.EXPECTED_INPUT_SHA256 = EXPECTED_INPUT_SHA256
    REPAIR.EXPECTED_ATTEMPT_FINGERPRINT = EXPECTED_ATTEMPT_FINGERPRINT
    REPAIR.EXPECTED_PRIOR_ASR_FINGERPRINT = EXPECTED_PRIOR_ASR_FINGERPRINT
    REPAIR.EXPECTED_PRIOR_TRANSCRIPT_HASHES = EXPECTED_PRIOR_TRANSCRIPT_HASHES
    REPAIR.EXPECTED_SAMPLE_BINDINGS = EXPECTED_SAMPLE_BINDINGS
    REPAIR.VOCABULARY_PROMPT = VOCABULARY_PROMPT
    REPAIR.DECODING_ARMS = DECODING_ARMS
    REPAIR.EQUIVALENCE_POLICY = EQUIVALENCE_POLICY
    REPAIR.FORBIDDEN_NORMALIZATIONS = FORBIDDEN_NORMALIZATIONS
    REPAIR.DEFAULT_INPUT = DEFAULT_INPUT
    REPAIR.DEFAULT_OUTPUT = DEFAULT_OUTPUT
    REPAIR.NO_REPEAT_FILES = NO_REPEAT_FILES
    REPAIR._configure_core()


def main(argv: Sequence[str] | None = None) -> int:
    configure_repair()
    return int(REPAIR.main(argv))


configure_repair()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
