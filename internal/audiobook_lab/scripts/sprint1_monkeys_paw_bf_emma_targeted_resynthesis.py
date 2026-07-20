#!/usr/bin/env python3
"""Target only the failed Monkey's Paw ``bf_emma`` passage.

The first British profile produced three exact representative passages.  This
bounded private repair resynthesizes only ``factory_news_and_grief`` with two
punctuation-only source-preserving preparations: the opening em dash becomes
an audible hesitation, and ``slower-witted`` loses only its hyphen.  The
lexical manuscript is unchanged.  Three deterministic ASR decoders must prove
the repaired WAV before listening can be considered.
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
import sys
from typing import Any, Callable, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROFILE_MODULE = _load(
    "monkeys_paw_bf_target_profile",
    SCRIPT_DIR / "sprint1_monkeys_paw_bf_emma_private_audition.py",
)
REPAIR_MODULE = _load(
    "monkeys_paw_bf_prior_repair",
    SCRIPT_DIR / "sprint1_monkeys_paw_bf_emma_asr_repair.py",
)
PROFILE = PROFILE_MODULE.PROFILE_BASE
CORE = REPAIR_MODULE.REPAIR.CORE
ROOT = PROFILE.ROOT

TARGET_PASSAGE_ID = "factory_news_and_grief"
SCHEMA = "earnalism.kokoro.monkeys_paw_bf_emma_targeted_resynthesis.v1"
PRIOR_REPAIR_SHA256 = (
    "8dd1a4c381522e34daee914d1b2971e94b173311f2b1089dc251dc8cf66efcba"
)
PRIOR_REPAIR_FINGERPRINT = (
    "12a5b40c13022312a66b96adbc6e7fb6743da1efad9c20b6c5bed2f03935986e"
)
PREPARED_TEXT_SHA256 = (
    "c3d23dbe8c1d5786345aa5a576ff9ada61b12208f6d60c140aaedd1529396a60"
)
PREPARED_TEXT_CHARACTERS = 992
PREPARED_PHONEME_SHA256 = (
    "3b7f7df19c13b572d7fd64478e402e5cd07a8048648c8f6f12557378aaed9e45"
)
SPEED = 0.94
RANDOM_SEED = 2026072004
PRONUNCIATION_OVERRIDES = {
    **PROFILE_MODULE.PRONUNCIATION_OVERRIDES,
    "witted": "wˈɪtɪd",
}
EXPECTED_ATTEMPT_FINGERPRINT = (
    "29da95f0687756670f1a3c21bee7e17e2fe4fdf2cbfeed8d06a32ce558306b81"
)
VOCABULARY_PROMPT = (
    "Canonical spellings: I was asked to call; Maw and Meggins; Herbert; "
    "slower-witted; Oh, thank God. Preserve every spoken word."
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
EQUIVALENCE_POLICY = (
    {
        "pattern": r"\b(?:moor|moore|more)\b",
        "replacement": "maw",
        "expected_count_when_observed": 1,
        "reason": "non-rhotic British homophone for source Maw",
    },
)

DEFAULT_ARTIFACT_DIR = PROFILE_MODULE.PROFILE_BASE.DEFAULT_ARTIFACT_DIR
DEFAULT_WHISPER_CACHE = PROFILE_MODULE.PROFILE_BASE.DEFAULT_WHISPER_CACHE
DEFAULT_PRIVATE_OUTPUT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-monkeys-paw/"
    "f3ff3571-bf-emma-factory-targeted-v2"
)
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_bf_emma_asr_repair_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_bf_emma_targeted_resynthesis_v2.json"
)
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    DEFAULT_INPUT,
)


class TargetedResynthesisError(RuntimeError):
    """Raised when the one-passage repair cannot preserve its contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return PROFILE.sha256_file(path)


def read_json(path: Path) -> dict[str, Any]:
    return PROFILE.read_json(path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def canonical_passages() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _chapters, passages = PROFILE.controlled_source(ROOT, PROFILE.SLUG)
    target = next(
        (item for item in passages if item["passage_id"] == TARGET_PASSAGE_ID), None
    )
    if target is None:
        raise TargetedResynthesisError("target passage is absent from controlled source")
    return passages, target


def prepare_text(source: str) -> tuple[str, list[dict[str, str]]]:
    if source.count("I—was") != 1 or source.count("slower-witted") != 1:
        raise TargetedResynthesisError("target punctuation markers changed")
    prepared = source.replace("I—was", "I ... was", 1).replace(
        "slower-witted", "slower witted", 1
    )
    if len(prepared) != PREPARED_TEXT_CHARACTERS:
        raise TargetedResynthesisError("prepared character count changed")
    if sha256_text(prepared) != PREPARED_TEXT_SHA256:
        raise TargetedResynthesisError("prepared text hash changed")
    if PROFILE.BASE.lexical_tokens(source) != PROFILE.BASE.lexical_tokens(prepared):
        raise TargetedResynthesisError("punctuation preparation changed lexical content")
    return prepared, [
        {
            "source": "I—was",
            "prepared": "I ... was",
            "reason": "preserve the interrupted opening while making initial I audible",
        },
        {
            "source": "slower-witted",
            "prepared": "slower witted",
            "reason": "preserve both source words while removing G2P hyphen ambiguity",
        },
    ]


def validate_prepared_g2p(prepared: str) -> dict[str, Any]:
    from misaki import en as misaki_en  # noqa: PLC0415

    g2p = misaki_en.G2P(trf=False, british=True, fallback=None, unk="")
    g2p.lexicon.golds.update(PRONUNCIATION_OVERRIDES)
    g2p.lexicon.golds.update(
        {key.lower(): value for key, value in PRONUNCIATION_OVERRIDES.items()}
    )
    phonemes, tokens = g2p(prepared)
    unresolved = sorted(
        {
            str(token.text)
            for token in tokens
            if re.search(r"[A-Za-z0-9]", str(token.text or ""))
            and not str(token.phonemes or "").strip()
        }
    )
    if unresolved:
        raise TargetedResynthesisError(
            f"fallback-free G2P unresolved tokens: {', '.join(unresolved)}"
        )
    phoneme_sha = sha256_text(str(phonemes or ""))
    if phoneme_sha != PREPARED_PHONEME_SHA256:
        raise TargetedResynthesisError("prepared phoneme hash changed")
    return {
        "status": "PASS",
        "kokoro_lang_code": "b",
        "british": True,
        "fallback": None,
        "all_source_tokens_resolved": True,
        "phoneme_sha256": phoneme_sha,
        "unresolved_tokens": [],
    }


def validate_prior(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(path) != PRIOR_REPAIR_SHA256:
        raise TargetedResynthesisError("prior repair evidence hash changed")
    evidence = read_json(path)
    repair = evidence.get("asr_repair") or {}
    if evidence.get("status") != "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED":
        raise TargetedResynthesisError("prior repair status changed")
    if repair.get("repair_fingerprint") != PRIOR_REPAIR_FINGERPRINT:
        raise TargetedResynthesisError("prior repair fingerprint changed")
    reports = evidence.get("asr", {}).get("reports", [])
    if not isinstance(reports, list) or len(reports) != 4:
        raise TargetedResynthesisError("prior selected ASR report count changed")
    passed_ids = {
        str(item.get("passage_id")) for item in reports if item.get("pass") is True
    }
    expected = {
        "opening_domestic_tension",
        "paw_warning_and_fate",
        "final_knocking_and_third_wish",
    }
    if passed_ids != expected:
        raise TargetedResynthesisError("prior three-passage pass set changed")
    failed = [item for item in reports if item.get("pass") is not True]
    if len(failed) != 1 or failed[0].get("passage_id") != TARGET_PASSAGE_ID:
        raise TargetedResynthesisError("prior failed target changed")
    return evidence, reports


def attempt_fingerprint() -> str:
    contract = {
        "contract": SCHEMA,
        "slug": PROFILE.SLUG,
        "target_passage_id": TARGET_PASSAGE_ID,
        "source_text_sha256": PROFILE_MODULE.PROFILE_BASE.PASSAGE_SPECS[2]["sha256"],
        "prepared_text_sha256": PREPARED_TEXT_SHA256,
        "prior_attempt_fingerprint": PROFILE_MODULE.EXPECTED_ATTEMPT_FINGERPRINT,
        "prior_repair_fingerprint": PRIOR_REPAIR_FINGERPRINT,
        "prior_repair_evidence_sha256": PRIOR_REPAIR_SHA256,
        "model_revision": PROFILE.MODEL_REVISION,
        "model_sha256": PROFILE.MODEL_SHA256,
        "config_sha256": PROFILE.CONFIG_SHA256,
        "voice": PROFILE_MODULE.VOICE,
        "voice_sha256": PROFILE_MODULE.VOICE_SHA256,
        "kokoro_lang_code": "b",
        "g2p_british": True,
        "speed": SPEED,
        "random_seed": RANDOM_SEED,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "decoder_arms": [item["id"] for item in DECODING_ARMS],
        "scope": "one_failed_passage_targeted_private_resynthesis",
    }
    return sha256_text(json.dumps(contract, sort_keys=True, separators=(",", ":")))


def ensure_not_repeated(output: Path, fingerprint: str) -> None:
    for path in NO_REPEAT_FILES:
        if path.is_file() and fingerprint in set(PROFILE._fingerprints(read_json(path))):
            raise TargetedResynthesisError(f"attempt fingerprint already exists: {path}")
    if output.is_file():
        prior = read_json(output)
        if prior.get("attempt_fingerprint") == fingerprint and prior.get("safety", {}).get(
            "audio_generated"
        ) is True:
            raise TargetedResynthesisError("this targeted fingerprint already generated audio")


def apply_equivalences(transcript: str) -> tuple[str, list[dict[str, Any]]]:
    evaluated = transcript
    applications: list[dict[str, Any]] = []
    for rule in EQUIVALENCE_POLICY:
        count = len(re.findall(rule["pattern"], evaluated, flags=re.IGNORECASE))
        if count == 0:
            continue
        expected = int(rule["expected_count_when_observed"])
        if count != expected:
            raise TargetedResynthesisError("target equivalence count mismatch")
        evaluated, replaced = re.subn(
            rule["pattern"], rule["replacement"], evaluated, flags=re.IGNORECASE
        )
        if replaced != expected:
            raise TargetedResynthesisError("target equivalence replacement changed")
        applications.append({**rule, "observed_count": count})
    return evaluated, applications


def evaluate(
    canonical: Mapping[str, Any], sample: Mapping[str, Any], transcript: str, arm: str
) -> dict[str, Any]:
    evaluated, applications = apply_equivalences(transcript)
    metrics = PROFILE.BASE.ordered_token_integrity(str(canonical["text"]), evaluated)
    passed = bool(
        float(metrics["score"]) >= 9.7
        and float(metrics["coverage"]) >= 0.98
        and metrics["first_words_match"] is True
        and metrics["last_words_match"] is True
        and metrics["ordered_content_integrity_pass"] is True
        and metrics["no_missing_content"] is True
        and metrics["no_duplicate_content"] is True
        and metrics["no_reordered_content"] is True
        and metrics["no_unexpected_content"] is True
    )
    return {
        "passage_id": TARGET_PASSAGE_ID,
        "decoder_arm": arm,
        "audio_sha256": sample["audio_sha256"],
        "canonical_source_text_sha256": canonical["text_sha256"],
        "prepared_text_sha256": PREPARED_TEXT_SHA256,
        "raw_transcript": transcript,
        "raw_transcript_sha256": sha256_text(transcript),
        "evaluated_transcript": evaluated,
        "source_equivalences_applied": applications,
        "substantive_normalization_performed": False,
        "unexpected_speech_deleted_or_normalized": False,
        **metrics,
        "pass": passed,
    }


def configure_synthesis() -> None:
    PROFILE.BASE.SPEED = SPEED
    PROFILE.BASE.RANDOM_SEED = RANDOM_SEED
    PROFILE.BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    PROFILE.BASE.KOKORO_LANG_CODE = "b"
    PROFILE.BASE.G2P_BRITISH = True


def exact_execute_command() -> str:
    return (
        "PYTHONDONTWRITEBYTECODE=1 "
        "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
        ".venv-audio/bin/python internal/audiobook_lab/scripts/"
        "sprint1_monkeys_paw_bf_emma_targeted_resynthesis.py --execute"
    )


def preflight(
    *, input_path: Path, output: Path, artifact_dir: Path, whisper_cache: Path, private_dir: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path], list[dict[str, Any]]]:
    PROFILE.assert_private_path(private_dir)
    all_passages, target = canonical_passages()
    prepared, transformations = prepare_text(str(target["text"]))
    g2p = validate_prepared_g2p(prepared)
    prior, prior_reports = validate_prior(input_path)
    artifacts, artifact_evidence = PROFILE.validate_artifacts(artifact_dir, whisper_cache)
    runtime = PROFILE.runtime_evidence()
    fingerprint = attempt_fingerprint()
    if fingerprint != EXPECTED_ATTEMPT_FINGERPRINT:
        raise TargetedResynthesisError("targeted attempt fingerprint changed")
    ensure_not_repeated(output, fingerprint)
    payload = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": "READY_FOR_ONE_TARGETED_PRIVATE_RESYNTHESIS",
        "go_no_go": "GO_ONE_TARGETED_PRIVATE_RESYNTHESIS_ONLY",
        "attempt_fingerprint": fingerprint,
        "scope": {
            "slug": PROFILE.SLUG,
            "title": PROFILE.TITLE,
            "author": PROFILE.AUTHOR,
            "target_passage_id": TARGET_PASSAGE_ID,
            "resynthesized_passage_count": 1,
            "reused_exact_passage_count": 3,
            "full_title_generated": False,
        },
        "source": {
            "canonical_source_text_sha256": target["text_sha256"],
            "prepared_text_sha256": PREPARED_TEXT_SHA256,
            "canonical_lexical_tokens_unchanged": True,
            "transformations": transformations,
        },
        "prior_evidence": {
            "path": str(input_path),
            "sha256": PRIOR_REPAIR_SHA256,
            "attempt_fingerprint": PROFILE_MODULE.EXPECTED_ATTEMPT_FINGERPRINT,
            "repair_fingerprint": PRIOR_REPAIR_FINGERPRINT,
            "three_exact_passages_reused": True,
        },
        "engine": {
            "provider": "local_kokoro",
            "model_revision": PROFILE.MODEL_REVISION,
            "model_sha256": PROFILE.MODEL_SHA256,
            "config_sha256": PROFILE.CONFIG_SHA256,
            "voice": PROFILE_MODULE.VOICE,
            "voice_sha256": PROFILE_MODULE.VOICE_SHA256,
            "speed": SPEED,
            "random_seed": RANDOM_SEED,
            "kokoro_lang_code": "b",
            "g2p_british": True,
            "g2p_fallback_enabled": False,
        },
        "g2p_audit": g2p,
        "artifact_evidence": artifact_evidence,
        "runtime_evidence": runtime,
        "decoder_arms": DECODING_ARMS,
        "next_stage_contract": {
            "exact_execute_command": exact_execute_command(),
            "listening_qa_allowed": False,
            "full_title_generation_allowed": False,
            "upload_allowed": False,
            "publication_allowed": False,
            "release_gate_mutation_allowed": False,
        },
        "safety": {
            "private_output_dir": str(private_dir),
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "paid_tts_lock_inspected": False,
            "paid_tts_lock_touched": False,
            "audio_generated": False,
            "asr_run": False,
            "listening_qa_run": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        },
        "blockers_to_release": [
            "TARGETED_PASSAGE_AUDIO_NOT_GENERATED",
            "TARGETED_PASSAGE_ASR_NOT_RUN",
            "INDEPENDENT_LISTENING_QA_NOT_RUN",
            "FULL_TITLE_NOT_GENERATED",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "CANONICAL_FRONT_COVER_MISSING",
            "TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
            "OWNER_10_TARGET_NOT_VERIFIED",
        ],
    }
    prepared_passage = {
        **target,
        "canonical_text_sha256": target["text_sha256"],
        "text": prepared,
        "text_sha256": PREPARED_TEXT_SHA256,
        "characters": len(prepared),
    }
    return payload, prepared_passage, artifacts, prior_reports


def execute(
    *, payload: dict[str, Any], prepared: Mapping[str, Any], artifacts: Mapping[str, Path],
    prior_reports: Sequence[Mapping[str, Any]], private_dir: Path, whisper_cache: Path,
    model_loader: Callable[[Path], Any] = CORE.load_whisper_model,
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], str] = CORE.run_decoding_arm,
) -> tuple[int, dict[str, Any]]:
    if payload["runtime_evidence"]["pinned_execution_runtime_verified"] is not True:
        raise TargetedResynthesisError("execution requires the pinned runtime")
    configure_synthesis()
    before = {name: sha256_file(path) for name, path in artifacts.items()}
    samples = PROFILE.BASE.synthesize([prepared], artifacts, PROFILE.assert_private_path(private_dir))
    if len(samples) != 1 or samples[0].get("objective_format_pass") is not True:
        raise TargetedResynthesisError("targeted WAV failed objective format")
    sample = samples[0]
    sample["canonical_source_text_sha256"] = prepared["canonical_text_sha256"]
    sample["prepared_text_sha256"] = PREPARED_TEXT_SHA256
    model = model_loader(whisper_cache)
    canonical = dict(prepared)
    canonical["text"] = next(
        item["text"] for item in canonical_passages()[0]
        if item["passage_id"] == TARGET_PASSAGE_ID
    )
    canonical["text_sha256"] = prepared["canonical_text_sha256"]
    candidates = [
        evaluate(canonical, sample, decoder(model, arm, sample), str(arm["id"]))
        for arm in DECODING_ARMS
    ]
    selected = max(
        candidates,
        key=lambda item: (
            bool(item["pass"]),
            float(item["score"]),
            float(item["coverage"]),
            float(item["precision"]),
        ),
    )
    reused = [item for item in prior_reports if item.get("passage_id") != TARGET_PASSAGE_ID]
    combined = [*reused, selected]
    expected_order = [item["passage_id"] for item in canonical_passages()[0]]
    combined.sort(key=lambda item: expected_order.index(str(item["passage_id"])))
    passed = bool(
        len(combined) == 4
        and [item["passage_id"] for item in combined] == expected_order
        and all(item.get("pass") is True for item in combined)
    )
    after = {name: sha256_file(path) for name, path in artifacts.items()}
    if before != after:
        raise TargetedResynthesisError("model, voice, or ASR artifacts changed")
    blockers = [
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "CANONICAL_FRONT_COVER_MISSING",
        "TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        "OWNER_10_TARGET_NOT_VERIFIED",
    ]
    if not passed:
        blockers.insert(0, "TARGETED_RESYNTHESIS_OBJECTIVE_GATE_FAILED")
    result = {
        **payload,
        "generated_at": utc_now(),
        "status": (
            "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
            if passed
            else "PRIVATE_TARGETED_RESYNTHESIS_FAILED_FINGERPRINT_CLOSED"
        ),
        "go_no_go": (
            "GO_PRIVATE_LISTENING_QA_ONLY"
            if passed
            else "NO_GO_TARGETED_RESYNTHESIS_OBJECTIVE_FAILED"
        ),
        "targeted_sample": sample,
        "targeted_asr": {
            "status": "PASS" if selected["pass"] else "FAIL",
            "all_candidates": candidates,
            "selected": selected,
        },
        "combined_representative_reports": combined,
        "next_stage_contract": {
            **payload["next_stage_contract"],
            "exact_execute_command": None,
            "do_not_repeat_completed_fingerprint": True,
            "listening_qa_allowed": passed,
            "full_title_generation_allowed": False,
        },
        "safety": {
            **payload["safety"],
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "paid_tts_lock_inspected": False,
            "paid_tts_lock_touched": False,
            "audio_generated": True,
            "resynthesized_passage_count": 1,
            "reused_passage_count": 3,
            "asr_run": True,
            "listening_qa_run": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
            "artifact_hashes_before": before,
            "artifact_hashes_after": after,
            "artifact_hashes_unchanged": True,
        },
        "blockers_to_release": blockers,
    }
    return (0 if passed else 4), result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--private-output-dir", type=Path, default=DEFAULT_PRIVATE_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload, prepared, artifacts, prior_reports = preflight(
            input_path=args.input.resolve(),
            output=args.output.resolve(),
            artifact_dir=args.artifact_dir.resolve(),
            whisper_cache=args.whisper_cache.resolve(),
            private_dir=args.private_output_dir.resolve(),
        )
        code = 0
        if args.execute:
            code, payload = execute(
                payload=payload,
                prepared=prepared,
                artifacts=artifacts,
                prior_reports=prior_reports,
                private_dir=args.private_output_dir.resolve(),
                whisper_cache=args.whisper_cache.resolve(),
            )
        write_json(args.output.resolve(), payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "go_no_go": payload["go_no_go"],
                    "attempt_fingerprint": payload["attempt_fingerprint"],
                    "output": str(args.output.resolve()),
                    "audio_generated": payload["safety"]["audio_generated"],
                    "resynthesized_passage_count": payload["safety"].get(
                        "resynthesized_passage_count", 0
                    ),
                    "provider_calls": 0,
                    "upload_performed": False,
                    "publication_performed": False,
                    "release_gate_mutated": False,
                },
                indent=2,
            )
        )
        return code
    except (TargetedResynthesisError, PROFILE.MonkeysPawPilotError, PROFILE.BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
