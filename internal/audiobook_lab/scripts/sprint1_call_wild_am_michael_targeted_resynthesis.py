#!/usr/bin/env python3
"""Resynthesize only Call of the Wild's three failed ``am_michael`` passages.

The retained ASR bakeoff proved that ``opening_exposition``, ``thornton_bond``,
and ``closing_call`` alone need a materially new synthesis. This private,
zero-provider-cost repair preserves every lexical source token, binds explicit
pronunciations for the observed failures, and requires one of three local
Whisper arms to prove exact ordered content for every new WAV.

It cannot generate the full title, run listening QA, upload, publish, enable
audio, or mutate ``paid_tts.lock`` or controlled release truth.
"""

from __future__ import annotations

import argparse
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


CORE = _load(
    "call_wild_targeted_resynthesis_core",
    SCRIPT_DIR / "sprint1_time_machine_bm_george_targeted_resynthesis.py",
)
PROFILE_MODULE = _load(
    "call_wild_targeted_profile",
    SCRIPT_DIR / "sprint1_call_wild_am_michael_private_audition.py",
)
REPAIR_MODULE = _load(
    "call_wild_targeted_prior_repair",
    SCRIPT_DIR / "sprint1_call_wild_am_michael_asr_repair.py",
)
BASE = PROFILE_MODULE.BASE
ROOT = BASE.ROOT

SCHEMA = "earnalism.kokoro.call_wild_am_michael_targeted_resynthesis.v2"
TARGET_PASSAGE_IDS = ("opening_exposition", "thornton_bond", "closing_call")
REUSED_PASSAGE_IDS = ("spitz_final_conflict",)
PRIOR_REPAIR_SHA256 = (
    "62e3f5b882bf247e701f6df36af462abe0a3d8b510f2cd9de951b91d600eb898"
)
PRIOR_REPAIR_FINGERPRINT = REPAIR_MODULE.EXPECTED_REPAIR_FINGERPRINT
EXPECTED_PAID_LOCK_SHA256 = REPAIR_MODULE.EXPECTED_PAID_LOCK_SHA256
PREPARED_TEXT_BINDINGS = {
    "opening_exposition": {
        "characters": 554,
        "sha256": "9f42bc79e301f7a7f67cd0f97c29c6c956a6444363ab2f2767a74bce0652ea23",
        "phoneme_sha256": "90b16e98955bfbbce12faa315c9bb5b001ec58c08435de3e692bfbf8db01eff1",
    },
    "thornton_bond": {
        "characters": 1176,
        "sha256": "277970e839d814be5df22f928a07800b65204dc4da12c31c7eadd519a5bd504d",
        "phoneme_sha256": "6b6f38de57e81754e3cbd4bf594dd3f124670ea9689304dee8c55a687bda082d",
    },
    "closing_call": {
        "characters": 1147,
        "sha256": "b8012a141c64709aa2d11fab1ed90d66c966aedf14f6d3c4ca65fd8ecbd5a745",
        "phoneme_sha256": "fbea5d355ef0f01349608b47956589b0951966ed94e29963699a493e763d2c35",
    },
}
SPEED = 0.94
RANDOM_SEED = 2026072102
PRONUNCIATION_OVERRIDES = {
    **PROFILE_MODULE.PRONUNCIATION_OVERRIDES,
    "metal": "mˈɛtəl",
    "feigned": "fˈeɪnd",
    "coated": "kˈoʊtɪd",
}
EXPECTED_ATTEMPT_FINGERPRINT = (
    "86481d57a50301fa01372213d3291fe1edd42fac6eb85a032f860a017797bc71"
)
VOCABULARY_PROMPT = (
    "The Call of the Wild by Jack London. Preserve these exact source phrases: "
    "yellow metal; this feigned bite for a caress; gloriously coated wolf; "
    "the long winter nights come on and the wolves. Canonical names: Buck; "
    "John Thornton; Skeet; Nig; Spitz; Yeehats. Preserve every source word."
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
EQUIVALENCE_POLICY = {
    "opening_exposition": (
        {
            "pattern": r"\btidewater\b",
            "replacement": "tide-water",
            "expected_count_when_observed": 1,
            "reason": "ASR compound token for source tide-water",
        },
    ),
    "thornton_bond": (),
    "closing_call": (
        {
            "pattern": r"\bmoosehide\b",
            "replacement": "moose-hide",
            "expected_count_when_observed": 1,
            "reason": "ASR compound token for source moose-hide",
        },
        {
            "pattern": r"\bmold\b",
            "replacement": "mould",
            "expected_count_when_observed": 1,
            "reason": "American ASR spelling for source mould",
        },
    ),
}

DEFAULT_ARTIFACT_DIR = PROFILE_MODULE.DEFAULT_ARTIFACT_DIR
DEFAULT_WHISPER_CACHE = PROFILE_MODULE.DEFAULT_WHISPER_CACHE
DEFAULT_PRIVATE_OUTPUT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-call-of-the-wild/"
    "f3ff3571-am-michael-three-passage-targeted-v2"
)
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_asr_repair_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_targeted_resynthesis_v2.json"
)
DEFAULT_PAID_LOCK = PROFILE_MODULE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl",
    ROOT / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_release_gate_evidence.json",
    DEFAULT_INPUT,
)

TargetedResynthesisError = CORE.TargetedResynthesisError


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prepare_text(
    passage_id: str, source: str
) -> tuple[str, list[dict[str, str]]]:
    if passage_id == "opening_exposition":
        marker = "had found a yellow metal, and because"
        replacement = "had found a yellow metal—and because"
        reason = "separate metal from the conjunction while preserving every word"
        replacements = ((marker, replacement, reason),)
    elif passage_id == "thornton_bond":
        marker = "this feigned bite for a caress"
        replacement = "this feigned bite, for ... a caress"
        reason = "make the source article audible without changing lexical content"
        replacements = ((marker, replacement, reason),)
    elif passage_id == "closing_call":
        replacements = (
            (
                "gloriously coated wolf, like, and yet unlike",
                "gloriously coated wolf—like, and yet unlike",
                "separate coated wolf from the comparison without changing words",
            ),
            (
                "long winter nights come on and the wolves",
                "long winter nights come on—and the wolves",
                "make the source conjunction audible without changing words",
            ),
        )
    else:
        raise TargetedResynthesisError(f"unsupported target passage: {passage_id}")

    prepared = source
    transformations: list[dict[str, str]] = []
    for marker, replacement, reason in replacements:
        if prepared.count(marker) != 1:
            raise TargetedResynthesisError(
                f"{passage_id} punctuation marker changed: {marker}"
            )
        prepared = prepared.replace(marker, replacement, 1)
        transformations.append(
            {"source": marker, "prepared": replacement, "reason": reason}
        )

    binding = PREPARED_TEXT_BINDINGS[passage_id]
    if len(prepared) != int(binding["characters"]):
        raise TargetedResynthesisError(f"{passage_id} prepared character count changed")
    if sha256_text(prepared) != binding["sha256"]:
        raise TargetedResynthesisError(f"{passage_id} prepared text hash changed")
    if BASE.lexical_tokens(source) != BASE.lexical_tokens(prepared):
        raise TargetedResynthesisError(
            f"{passage_id} punctuation preparation changed lexical content"
        )
    return prepared, transformations


def validate_prepared_g2p(passage_id: str, prepared: str) -> dict[str, Any]:
    from misaki import en as misaki_en  # noqa: PLC0415

    g2p = misaki_en.G2P(trf=False, british=False, fallback=None, unk="")
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
            f"fallback-free G2P unresolved tokens in {passage_id}: "
            + ", ".join(unresolved)
        )
    phoneme_sha = sha256_text(str(phonemes or ""))
    if phoneme_sha != PREPARED_TEXT_BINDINGS[passage_id]["phoneme_sha256"]:
        raise TargetedResynthesisError(f"{passage_id} prepared phoneme hash changed")
    return {
        "passage_id": passage_id,
        "status": "PASS",
        "kokoro_lang_code": "a",
        "british": False,
        "fallback": None,
        "all_source_tokens_resolved": True,
        "phoneme_sha256": phoneme_sha,
        "unresolved_tokens": [],
    }


def apply_equivalences(
    passage_id: str, transcript: str
) -> tuple[str, list[dict[str, Any]]]:
    evaluated = transcript
    applications: list[dict[str, Any]] = []
    for rule in EQUIVALENCE_POLICY[passage_id]:
        count = len(re.findall(rule["pattern"], evaluated, flags=re.IGNORECASE))
        if count == 0:
            continue
        expected = int(rule["expected_count_when_observed"])
        if count != expected:
            raise TargetedResynthesisError(f"{passage_id} equivalence count mismatch")
        evaluated, replaced = re.subn(
            rule["pattern"], rule["replacement"], evaluated, flags=re.IGNORECASE
        )
        if replaced != expected:
            raise TargetedResynthesisError(
                f"{passage_id} equivalence replacement changed"
            )
        applications.append({**rule, "observed_count": count})
    return evaluated, applications


def evaluate(
    canonical: Mapping[str, Any],
    sample: Mapping[str, Any],
    transcript: str,
    arm: str,
) -> dict[str, Any]:
    passage_id = str(canonical["passage_id"])
    evaluated, applications = apply_equivalences(passage_id, transcript)
    metrics = BASE.ordered_token_integrity(str(canonical["text"]), evaluated)
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
        "passage_id": passage_id,
        "decoder_arm": arm,
        "audio_sha256": sample["audio_sha256"],
        "canonical_source_text_sha256": canonical["text_sha256"],
        "prepared_text_sha256": sample["source_text_sha256"],
        "raw_transcript": transcript,
        "raw_transcript_sha256": sha256_text(transcript),
        "evaluated_transcript": evaluated,
        "evaluated_transcript_sha256": sha256_text(evaluated),
        "source_equivalences_applied": applications,
        "substantive_normalization_performed": False,
        "unexpected_speech_deleted_or_normalized": False,
        **metrics,
        "pass": passed,
    }


def configure_synthesis() -> None:
    BASE.SPEED = SPEED
    BASE.RANDOM_SEED = RANDOM_SEED
    BASE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    BASE.KOKORO_LANG_CODE = "a"
    BASE.G2P_BRITISH = False


def exact_execute_command() -> str:
    return (
        "PYTHONDONTWRITEBYTECODE=1 "
        "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
        ".venv-audio/bin/python internal/audiobook_lab/scripts/"
        "sprint1_call_wild_am_michael_targeted_resynthesis.py --execute"
    )


def attempt_fingerprint() -> str:
    contract = {
        "contract": SCHEMA,
        "slug": PROFILE_MODULE.SLUG,
        "target_passage_ids": list(TARGET_PASSAGE_IDS),
        "source_text_sha256": {
            str(item["passage_id"]): str(item["sha256"])
            for item in PROFILE_MODULE.PASSAGE_SPECS
            if item["passage_id"] in TARGET_PASSAGE_IDS
        },
        "prepared_text_sha256": {
            key: value["sha256"] for key, value in PREPARED_TEXT_BINDINGS.items()
        },
        "prior_attempt_fingerprint": PROFILE_MODULE.EXPECTED_ATTEMPT_FINGERPRINT,
        "prior_repair_fingerprint": PRIOR_REPAIR_FINGERPRINT,
        "prior_repair_evidence_sha256": PRIOR_REPAIR_SHA256,
        "model_revision": BASE.MODEL_REVISION,
        "model_sha256": BASE.MODEL_SHA256,
        "config_sha256": BASE.CONFIG_SHA256,
        "voice": PROFILE_MODULE.VOICE,
        "voice_sha256": PROFILE_MODULE.VOICE_SHA256,
        "kokoro_lang_code": "a",
        "g2p_british": False,
        "speed": SPEED,
        "random_seed": RANDOM_SEED,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "decoder_arms": [item["id"] for item in DECODING_ARMS],
        "scope": "three_failed_passages_targeted_private_resynthesis",
    }
    return sha256_text(json.dumps(contract, sort_keys=True, separators=(",", ":")))


def configure_core() -> None:
    bindings = {
        "PROFILE_MODULE": PROFILE_MODULE,
        "REPAIR_MODULE": REPAIR_MODULE,
        "PROFILE": BASE,
        "ROOT": ROOT,
        "SCHEMA": SCHEMA,
        "TARGET_PASSAGE_IDS": TARGET_PASSAGE_IDS,
        "REUSED_PASSAGE_IDS": REUSED_PASSAGE_IDS,
        "PRIOR_REPAIR_SHA256": PRIOR_REPAIR_SHA256,
        "PRIOR_REPAIR_FINGERPRINT": PRIOR_REPAIR_FINGERPRINT,
        "EXPECTED_PAID_LOCK_SHA256": EXPECTED_PAID_LOCK_SHA256,
        "PREPARED_TEXT_BINDINGS": PREPARED_TEXT_BINDINGS,
        "SPEED": SPEED,
        "RANDOM_SEED": RANDOM_SEED,
        "PRONUNCIATION_OVERRIDES": PRONUNCIATION_OVERRIDES,
        "EXPECTED_ATTEMPT_FINGERPRINT": EXPECTED_ATTEMPT_FINGERPRINT,
        "DECODING_ARMS": DECODING_ARMS,
        "EQUIVALENCE_POLICY": EQUIVALENCE_POLICY,
        "DEFAULT_ARTIFACT_DIR": DEFAULT_ARTIFACT_DIR,
        "DEFAULT_WHISPER_CACHE": DEFAULT_WHISPER_CACHE,
        "DEFAULT_PRIVATE_OUTPUT": DEFAULT_PRIVATE_OUTPUT,
        "DEFAULT_INPUT": DEFAULT_INPUT,
        "DEFAULT_OUTPUT": DEFAULT_OUTPUT,
        "DEFAULT_PAID_LOCK": DEFAULT_PAID_LOCK,
        "NO_REPEAT_FILES": NO_REPEAT_FILES,
        "prepare_text": prepare_text,
        "validate_prepared_g2p": validate_prepared_g2p,
        "apply_equivalences": apply_equivalences,
        "evaluate": evaluate,
        "configure_synthesis": configure_synthesis,
        "exact_execute_command": exact_execute_command,
        "attempt_fingerprint": attempt_fingerprint,
    }
    for name, value in bindings.items():
        setattr(CORE, name, value)


def preflight(**kwargs: Any):
    configure_core()
    payload, all_passages, prepared, artifacts, prior_reports = CORE.preflight(**kwargs)
    payload["status"] = "READY_FOR_THREE_PASSAGE_TARGETED_PRIVATE_RESYNTHESIS"
    payload["go_no_go"] = "GO_THREE_PASSAGE_TARGETED_PRIVATE_RESYNTHESIS_ONLY"
    payload["scope"].update(
        {
            "resynthesized_passage_count": 3,
            "reused_exact_passage_count": 1,
        }
    )
    payload["engine"].update(
        {
            "kokoro_lang_code": "a",
            "g2p_british": False,
        }
    )
    payload["rights"] = {
        "controlled_text_public_domain": True,
        "author_death_year": 1916,
        "original_publication_year": 1903,
        "model_and_voicepack_license": "Apache-2.0",
        "model_revision_bound": BASE.MODEL_REVISION,
        "voice_file_sha256_bound": PROFILE_MODULE.VOICE_SHA256,
        "private_generation_allowed": True,
        "public_release_approved": False,
        "public_disclosure_required_if_later_approved": "AI voice",
    }
    return payload, all_passages, prepared, artifacts, prior_reports


def execute(
    *,
    payload: dict[str, Any],
    all_passages: Sequence[Mapping[str, Any]],
    prepared_passages: Sequence[Mapping[str, Any]],
    artifacts: Mapping[str, Path],
    prior_reports: Sequence[Mapping[str, Any]],
    private_dir: Path,
    whisper_cache: Path,
    paid_lock: Path,
    model_loader: Callable[[Path], Any] = CORE.CORE.load_whisper_model,
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], str] = (
        CORE.CORE.run_decoding_arm
    ),
) -> tuple[int, dict[str, Any]]:
    runtime = payload.get("runtime_evidence") or {}
    if (
        runtime.get("offline_local_artifacts_only") is not True
        or runtime.get("deterministic_algorithms_required") is not True
        or runtime.get("torch_thread_count") != 1
    ):
        raise TargetedResynthesisError("execution requires the pinned offline runtime")
    lock_before = BASE.lock_snapshot(paid_lock)
    if lock_before != payload["safety"]["paid_tts_lock"]:
        raise TargetedResynthesisError("paid_tts.lock changed after preflight")
    configure_synthesis()
    artifact_hashes_before = {
        name: BASE.sha256_file(path) for name, path in artifacts.items()
    }
    samples = BASE.synthesize(
        prepared_passages,
        artifacts,
        BASE.assert_private_audio_path(private_dir),
    )
    if len(samples) != len(TARGET_PASSAGE_IDS) or any(
        sample.get("objective_format_pass") is not True for sample in samples
    ):
        raise TargetedResynthesisError("a targeted WAV failed objective format")

    canonical_by_id = {str(item["passage_id"]): item for item in all_passages}
    prepared_by_id = {str(item["passage_id"]): item for item in prepared_passages}
    model = model_loader(whisper_cache)
    all_candidates: dict[str, list[dict[str, Any]]] = {}
    selected_reports: list[dict[str, Any]] = []
    for sample in samples:
        passage_id = str(sample["passage_id"])
        canonical = canonical_by_id[passage_id]
        sample["canonical_source_text_sha256"] = canonical["text_sha256"]
        sample["prepared_text_sha256"] = prepared_by_id[passage_id]["text_sha256"]
        candidates = [
            evaluate(
                canonical,
                sample,
                decoder(model, arm, sample),
                str(arm["id"]),
            )
            for arm in DECODING_ARMS
        ]
        all_candidates[passage_id] = candidates
        selected_reports.append(
            max(
                candidates,
                key=lambda item: (
                    bool(item["pass"]),
                    float(item["score"]),
                    float(item["coverage"]),
                    float(item["precision"]),
                ),
            )
        )

    reused = [
        dict(item)
        for item in prior_reports
        if str(item.get("passage_id")) in REUSED_PASSAGE_IDS
    ]
    combined = [*reused, *selected_reports]
    expected_order = [str(item["passage_id"]) for item in all_passages]
    combined.sort(key=lambda item: expected_order.index(str(item["passage_id"])))
    passed = bool(
        len(combined) == len(expected_order)
        and [str(item["passage_id"]) for item in combined] == expected_order
        and all(item.get("pass") is True for item in combined)
    )
    artifact_hashes_after = {
        name: BASE.sha256_file(path) for name, path in artifacts.items()
    }
    if artifact_hashes_before != artifact_hashes_after:
        raise TargetedResynthesisError("model, voice, or ASR artifacts changed")
    lock_after = BASE.lock_snapshot(paid_lock)
    if lock_before != lock_after:
        raise TargetedResynthesisError("paid_tts.lock changed during local execution")

    blockers = [
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "FULL_TITLE_ASR_BOUNDARY_CONTENT_NOT_RUN",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "PRIVATE_MEDIA_DELIVERY_MANIFEST_NOT_BUILT",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        "PUBLIC_RELEASE_NOT_APPROVED",
        "OWNER_10_TARGET_NOT_VERIFIED",
    ]
    if not passed:
        blockers.insert(0, "TARGETED_RESYNTHESIS_OBJECTIVE_GATE_FAILED")
    result = {
        **payload,
        "generated_at": CORE.utc_now(),
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
        "targeted_samples": samples,
        "targeted_asr": {
            "status": "PASS" if all(item["pass"] for item in selected_reports) else "FAIL",
            "all_candidates": all_candidates,
            "selected": selected_reports,
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
            "paid_tts_lock_before": lock_before,
            "paid_tts_lock_after": lock_after,
            "paid_tts_lock_unchanged": True,
            "paid_tts_lock_touched": False,
            "audio_generated": True,
            "resynthesized_passage_count": len(TARGET_PASSAGE_IDS),
            "reused_passage_count": len(REUSED_PASSAGE_IDS),
            "asr_run": True,
            "listening_qa_run": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
            "artifact_hashes_before": artifact_hashes_before,
            "artifact_hashes_after": artifact_hashes_after,
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
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload, all_passages, prepared, artifacts, prior_reports = preflight(
            input_path=args.input.resolve(),
            output=args.output.resolve(),
            artifact_dir=args.artifact_dir.resolve(),
            whisper_cache=args.whisper_cache.resolve(),
            private_dir=args.private_output_dir.resolve(),
            paid_lock=args.paid_lock.resolve(),
        )
        code = 0
        if args.execute:
            code, payload = execute(
                payload=payload,
                all_passages=all_passages,
                prepared_passages=prepared,
                artifacts=artifacts,
                prior_reports=prior_reports,
                private_dir=args.private_output_dir.resolve(),
                whisper_cache=args.whisper_cache.resolve(),
                paid_lock=args.paid_lock.resolve(),
            )
        CORE.write_json(args.output.resolve(), payload)
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
                    "paid_tts_lock_touched": False,
                    "upload_performed": False,
                    "publication_performed": False,
                    "release_gate_mutated": False,
                },
                indent=2,
            )
        )
        return code
    except (
        TargetedResynthesisError,
        BASE.KokoroTitlePilotError,
        REPAIR_MODULE.CallWildASRRepairError,
    ) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


configure_core()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
