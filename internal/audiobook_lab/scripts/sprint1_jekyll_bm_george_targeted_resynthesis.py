#!/usr/bin/env python3
"""Resynthesize only Jekyll's failed bm_george opening passage.

The retained transcript projection proved that three passages are exact and
that ``opening_character`` alone retains the substantive
``wondering``/``wandering`` mismatch.  This private, zero-provider-cost repair
changes punctuation and pronunciation binding only, preserves every canonical
lexical token, and requires one of three local Whisper arms to prove exact
ordered content for the replacement WAV.

It cannot generate the full title, run listening QA, upload, publish, enable
audio, or mutate ``paid_tts.lock`` or controlled release truth.
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
    "jekyll_bm_george_target_profile",
    SCRIPT_DIR / "sprint1_jekyll_kokoro_private_bakeoff.py",
)
PROFILE_MODULE.configure_base("bm_george")
PROJECTION = _load(
    "jekyll_bm_george_prior_projection",
    SCRIPT_DIR / "sprint1_jekyll_bm_george_asr_projection.py",
)
REPAIR = _load(
    "jekyll_bm_george_decoder_core",
    SCRIPT_DIR / "sprint1_jekyll_kokoro_asr_repair.py",
)
REPAIR.configure("bm_george")
BASE = PROFILE_MODULE.BASE
CORE = REPAIR.CORE
ROOT = BASE.ROOT

SCHEMA = "earnalism.kokoro.jekyll_bm_george_targeted_resynthesis.v1"
TARGET_PASSAGE_IDS = ("opening_character",)
REUSED_PASSAGE_IDS = (
    "carew_murder",
    "lanyon_transformation",
    "final_confession",
)
PRIOR_PROJECTION_SHA256 = (
    "bbd402797591bbdd66d086faaab7132cb46ca9f1c9336148b8edb84d998d1e65"
)
PRIOR_PROJECTION_FINGERPRINT = PROJECTION.EXPECTED_PROJECTION_FINGERPRINT
EXPECTED_PAID_LOCK_SHA256 = PROJECTION.EXPECTED_PAID_LOCK_SHA256
PREPARED_TEXT_BINDING = {
    "characters": 988,
    "sha256": "854a327350457e198f4ba94858306755ec3b1b2d4a51f508c0e0db0e819e597b",
    "phoneme_sha256": "3054f6c39a4b6fdb7aa36c15a281ada7bcace35e9f3fb3f392537bd3ff00c6ab",
}
SPEED = 0.93
RANDOM_SEED = 2026072108
PRONUNCIATION_OVERRIDES = {
    **PROFILE_MODULE.VOICE_PROFILES["bm_george"]["pronunciation_overrides"],
    "wondering": "wˈʌndəɹɪŋ",
    "beaconed": "bˈiːkənd",
}
EXPECTED_ATTEMPT_FINGERPRINT = (
    "f2b2345ecef735b5ff79e8beeeb61cdbc567392669281606b0b9c5505570599b"
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
EQUIVALENCE_POLICY = (
    {
        "pattern": r"\bbeakened\b",
        "replacement": "beaconed",
        "expected_count_when_observed": 1,
        "reason": "non-word ASR spelling for source-generated beaconed phonemes",
    },
    {
        "pattern": r"\btheater\b",
        "replacement": "theatre",
        "expected_count_when_observed": 1,
        "reason": "American ASR spelling for source British spelling theatre",
    },
)
FORBIDDEN_NORMALIZATIONS = (
    "wondering/wandering",
    "unexpected speech deletion",
    "missing content insertion",
    "substantive word substitution",
)

DEFAULT_ARTIFACT_DIR = PROFILE_MODULE.DEFAULT_ARTIFACT_DIR
DEFAULT_WHISPER_CACHE = PROFILE_MODULE.DEFAULT_WHISPER_CACHE
DEFAULT_PRIVATE_OUTPUT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/jekyll-and-hyde/"
    "f3ff3571-bm-george-opening-targeted-v2"
)
DEFAULT_INPUT = PROJECTION.DEFAULT_OUTPUT
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "jekyll-and-hyde_kokoro_bm_george_targeted_resynthesis_v2.json"
)
DEFAULT_PAID_LOCK = PROFILE_MODULE.DEFAULT_PAID_LOCK
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/"
    "sprint1_provider_failure_registry.json",
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "jekyll-and-hyde_release_gate_evidence.json",
    DEFAULT_INPUT,
)


class JekyllTargetedResynthesisError(RuntimeError):
    """Raised when the bounded opening repair cannot preserve its contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return BASE.read_json(path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def canonical_passages() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    _chapters, passages = PROFILE_MODULE.controlled_source(ROOT, PROFILE_MODULE.SLUG)
    indexed = {str(item["passage_id"]): item for item in passages}
    if set(indexed) != set((*TARGET_PASSAGE_IDS, *REUSED_PASSAGE_IDS)):
        raise JekyllTargetedResynthesisError("representative passage set changed")
    return passages, indexed


def prepare_text(source: str) -> tuple[str, list[dict[str, str]]]:
    first = "something eminently human beaconed from his eye; something indeed"
    second = "for others; sometimes wondering, almost with envy, at the high pressure"
    if source.count(first) != 1 or source.count(second) != 1:
        raise JekyllTargetedResynthesisError("opening punctuation markers changed")
    prepared = source.replace(
        first,
        "something eminently human beaconed from his eye. Something indeed",
        1,
    ).replace(
        second,
        "for others. Sometimes—wondering, almost with envy—at the high pressure",
        1,
    )
    transformations = [
        {
            "source": first,
            "prepared": "something eminently human beaconed from his eye. Something indeed",
            "reason": "separate the beaconed clause while preserving every lexical token",
        },
        {
            "source": second,
            "prepared": "for others. Sometimes—wondering, almost with envy—at the high pressure",
            "reason": "isolate wondering for audible stress without changing lexical content",
        },
    ]
    if len(prepared) != PREPARED_TEXT_BINDING["characters"]:
        raise JekyllTargetedResynthesisError("prepared character count changed")
    if sha256_text(prepared) != PREPARED_TEXT_BINDING["sha256"]:
        raise JekyllTargetedResynthesisError("prepared text hash changed")
    if BASE.lexical_tokens(source) != BASE.lexical_tokens(prepared):
        raise JekyllTargetedResynthesisError(
            "punctuation preparation changed canonical lexical content"
        )
    return prepared, transformations


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
        raise JekyllTargetedResynthesisError(
            "fallback-free G2P unresolved tokens: " + ", ".join(unresolved)
        )
    phoneme_sha = sha256_text(str(phonemes or ""))
    if phoneme_sha != PREPARED_TEXT_BINDING["phoneme_sha256"]:
        raise JekyllTargetedResynthesisError("prepared phoneme hash changed")
    return {
        "passage_id": TARGET_PASSAGE_IDS[0],
        "status": "PASS",
        "kokoro_lang_code": "b",
        "british": True,
        "fallback": None,
        "all_source_tokens_resolved": True,
        "phoneme_sha256": phoneme_sha,
        "unresolved_tokens": [],
    }


def validate_prior(
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    if BASE.sha256_file(path) != PRIOR_PROJECTION_SHA256:
        raise JekyllTargetedResynthesisError("prior projection evidence hash changed")
    evidence = read_json(path)
    if evidence.get("status") != "PRIVATE_REPRESENTATIVE_OBJECTIVE_PARTIAL_3_OF_4":
        raise JekyllTargetedResynthesisError("prior projection status changed")
    if evidence.get("projection_fingerprint") != PRIOR_PROJECTION_FINGERPRINT:
        raise JekyllTargetedResynthesisError("prior projection fingerprint changed")
    reports = (evidence.get("asr") or {}).get("reports")
    if not isinstance(reports, list) or len(reports) != 4:
        raise JekyllTargetedResynthesisError("prior report count changed")
    passed_ids = {
        str(item.get("passage_id")) for item in reports if item.get("pass") is True
    }
    failed_ids = {
        str(item.get("passage_id")) for item in reports if item.get("pass") is not True
    }
    if passed_ids != set(REUSED_PASSAGE_IDS) or failed_ids != set(TARGET_PASSAGE_IDS):
        raise JekyllTargetedResynthesisError("prior pass/fail passage sets changed")
    samples = evidence.get("samples")
    if not isinstance(samples, list) or len(samples) != 4:
        raise JekyllTargetedResynthesisError("prior private sample count changed")
    for sample in samples:
        audio = BASE.assert_private_audio_path(Path(str(sample.get("audio_path") or "")))
        if not audio.is_file():
            raise JekyllTargetedResynthesisError(f"prior private WAV missing: {audio}")
        if BASE.sha256_file(audio) != sample.get("audio_sha256"):
            raise JekyllTargetedResynthesisError(f"prior private WAV hash changed: {audio}")
    return evidence, reports, samples


def attempt_fingerprint() -> str:
    contract = {
        "contract": SCHEMA,
        "slug": PROFILE_MODULE.SLUG,
        "target_passage_ids": list(TARGET_PASSAGE_IDS),
        "source_text_sha256": PROFILE_MODULE.PASSAGE_SPECS[0]["sha256"],
        "prepared_text_binding": PREPARED_TEXT_BINDING,
        "prior_attempt_fingerprint": PROFILE_MODULE.VOICE_PROFILES["bm_george"][
            "expected_attempt_fingerprint"
        ],
        "prior_projection_fingerprint": PRIOR_PROJECTION_FINGERPRINT,
        "prior_projection_evidence_sha256": PRIOR_PROJECTION_SHA256,
        "model_revision": BASE.MODEL_REVISION,
        "model_sha256": BASE.MODEL_SHA256,
        "config_sha256": BASE.CONFIG_SHA256,
        "voice": "bm_george",
        "voice_sha256": PROFILE_MODULE.VOICE_PROFILES["bm_george"]["voice_sha256"],
        "kokoro_lang_code": "b",
        "g2p_british": True,
        "speed": SPEED,
        "random_seed": RANDOM_SEED,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "decoder_arms": DECODING_ARMS,
        "equivalence_policy": EQUIVALENCE_POLICY,
        "forbidden_normalizations": FORBIDDEN_NORMALIZATIONS,
        "scope": "one_failed_passage_targeted_private_resynthesis",
    }
    return sha256_text(json.dumps(contract, sort_keys=True, separators=(",", ":")))


def ensure_not_repeated(output: Path, fingerprint: str) -> None:
    for path in NO_REPEAT_FILES:
        if path.is_file() and fingerprint in path.read_text(
            encoding="utf-8", errors="strict"
        ):
            raise JekyllTargetedResynthesisError(
                f"attempt fingerprint already exists: {path}"
            )
    if output.is_file():
        prior = read_json(output)
        if prior.get("attempt_fingerprint") == fingerprint and prior.get(
            "safety", {}
        ).get("audio_generated") is True:
            raise JekyllTargetedResynthesisError(
                "this targeted fingerprint already generated audio"
            )


def apply_equivalences(transcript: str) -> tuple[str, list[dict[str, Any]]]:
    evaluated = transcript
    applications: list[dict[str, Any]] = []
    for rule in EQUIVALENCE_POLICY:
        count = len(re.findall(str(rule["pattern"]), evaluated, flags=re.IGNORECASE))
        if count == 0:
            continue
        expected = int(rule["expected_count_when_observed"])
        if count != expected:
            raise JekyllTargetedResynthesisError("equivalence count mismatch")
        evaluated, replaced = re.subn(
            str(rule["pattern"]),
            str(rule["replacement"]),
            evaluated,
            flags=re.IGNORECASE,
        )
        if replaced != expected:
            raise JekyllTargetedResynthesisError("equivalence replacement changed")
        applications.append({**rule, "observed_count": count})
    return evaluated, applications


def evaluate(
    canonical: Mapping[str, Any],
    sample: Mapping[str, Any],
    transcript: str,
    arm: str,
) -> dict[str, Any]:
    evaluated, applications = apply_equivalences(transcript)
    metrics = BASE.ordered_token_integrity(str(canonical["text"]), evaluated)
    passed = bool(
        float(metrics["score"]) == 10.0
        and float(metrics["coverage"]) == 1.0
        and float(metrics["precision"]) == 1.0
        and metrics["first_words_match"] is True
        and metrics["last_words_match"] is True
        and metrics["ordered_content_integrity_pass"] is True
        and metrics["no_missing_content"] is True
        and metrics["no_duplicate_content"] is True
        and metrics["no_reordered_content"] is True
        and metrics["no_unexpected_content"] is True
    )
    return {
        "passage_id": canonical["passage_id"],
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
    BASE.KOKORO_LANG_CODE = "b"
    BASE.G2P_BRITISH = True


def preflight(
    *,
    input_path: Path,
    output: Path,
    artifact_dir: Path,
    whisper_cache: Path,
    private_dir: Path,
    paid_lock: Path,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Path],
    list[dict[str, Any]],
]:
    BASE.assert_private_audio_path(private_dir)
    all_passages, indexed = canonical_passages()
    canonical = indexed[TARGET_PASSAGE_IDS[0]]
    prepared, transformations = prepare_text(str(canonical["text"]))
    g2p_evidence = validate_prepared_g2p(prepared)
    prepared_passages = [
        {
            **canonical,
            "canonical_text_sha256": canonical["text_sha256"],
            "text": prepared,
            "text_sha256": PREPARED_TEXT_BINDING["sha256"],
            "characters": len(prepared),
        }
    ]
    _prior, prior_reports, _prior_samples = validate_prior(input_path)
    artifacts, artifact_evidence = BASE.validate_artifacts(artifact_dir, whisper_cache)
    runtime = BASE.runtime_evidence()
    lock = BASE.lock_snapshot(paid_lock)
    if lock["sha256"] != EXPECTED_PAID_LOCK_SHA256:
        raise JekyllTargetedResynthesisError("paid_tts.lock hash changed")
    fingerprint = attempt_fingerprint()
    if fingerprint != EXPECTED_ATTEMPT_FINGERPRINT:
        raise JekyllTargetedResynthesisError(
            "targeted attempt fingerprint changed: "
            f"expected {EXPECTED_ATTEMPT_FINGERPRINT}, observed {fingerprint}"
        )
    ensure_not_repeated(output, fingerprint)
    payload = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": "READY_FOR_OPENING_TARGETED_PRIVATE_RESYNTHESIS",
        "go_no_go": "GO_OPENING_TARGETED_PRIVATE_RESYNTHESIS_ONLY",
        "attempt_fingerprint": fingerprint,
        "scope": {
            "slug": PROFILE_MODULE.SLUG,
            "title": PROFILE_MODULE.TITLE,
            "author": PROFILE_MODULE.AUTHOR,
            "voice": "bm_george",
            "target_passage_ids": list(TARGET_PASSAGE_IDS),
            "reused_passage_ids": list(REUSED_PASSAGE_IDS),
            "representative_only": True,
            "full_title_generated": False,
        },
        "prior_projection": {
            "path": str(input_path),
            "sha256": PRIOR_PROJECTION_SHA256,
            "projection_fingerprint": PRIOR_PROJECTION_FINGERPRINT,
            "exact_pass_count": 3,
        },
        "text_preparation": {
            "canonical_text_sha256": canonical["text_sha256"],
            "prepared_text_sha256": PREPARED_TEXT_BINDING["sha256"],
            "canonical_lexical_tokens_unchanged": True,
            "transformations": transformations,
        },
        "g2p_preflight_evidence": g2p_evidence,
        "engine": {
            "family": "open_weight_local_tts",
            "package": "kokoro",
            "model_revision": BASE.MODEL_REVISION,
            "voice": "bm_george",
            "voice_sha256": PROFILE_MODULE.VOICE_PROFILES["bm_george"]["voice_sha256"],
            "speed": SPEED,
            "random_seed": RANDOM_SEED,
            "g2p_british": True,
            "g2p_fallback_enabled": False,
        },
        "decoder_arms": DECODING_ARMS,
        "artifact_evidence": artifact_evidence,
        "runtime_evidence": runtime,
        "next_stage_contract": {
            "listening_qa_allowed": False,
            "full_title_generation_allowed": False,
            "upload_allowed": False,
            "publication_allowed": False,
            "release_gate_mutation_allowed": False,
        },
        "safety": {
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "paid_tts_lock": lock,
            "paid_tts_lock_touched": False,
            "private_output_dir": str(private_dir),
            "audio_generated": False,
            "resynthesized_passage_count": 0,
            "reused_passage_count": 3,
            "listening_qa_run": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
        },
        "blockers_to_release": [
            "OPENING_TARGETED_RESYNTHESIS_NOT_RUN",
            "INDEPENDENT_LISTENING_QA_NOT_RUN",
            "FULL_TITLE_NOT_GENERATED",
            "FULL_TITLE_ASR_BOUNDARY_CONTENT_NOT_RUN",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "FRONT_COVER_LINKAGE_REQUIRED_BEFORE_PUBLICATION",
            "PRIVATE_MEDIA_DELIVERY_MANIFEST_NOT_BUILT",
            "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
            "PUBLIC_RELEASE_NOT_APPROVED",
            "OWNER_10_TARGET_NOT_VERIFIED",
        ],
    }
    return payload, all_passages, prepared_passages, artifacts, prior_reports


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
    model_loader: Callable[[Path], Any] = CORE.load_whisper_model,
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], str] = CORE.run_decoding_arm,
) -> tuple[int, dict[str, Any]]:
    lock_before = BASE.lock_snapshot(paid_lock)
    artifact_hashes_before = {
        name: BASE.sha256_file(path) for name, path in artifacts.items()
    }
    configure_synthesis()
    samples = BASE.synthesize(
        prepared_passages,
        artifacts,
        BASE.assert_private_audio_path(private_dir),
    )
    if len(samples) != 1 or samples[0].get("objective_format_pass") is not True:
        raise JekyllTargetedResynthesisError("targeted WAV failed objective format")
    canonical_by_id = {str(item["passage_id"]): item for item in all_passages}
    sample = samples[0]
    passage_id = str(sample["passage_id"])
    canonical = canonical_by_id[passage_id]
    sample["canonical_source_text_sha256"] = canonical["text_sha256"]
    sample["prepared_text_sha256"] = PREPARED_TEXT_BINDING["sha256"]
    model = model_loader(whisper_cache)
    candidates = [
        evaluate(
            canonical,
            sample,
            decoder(model, arm, sample),
            str(arm["id"]),
        )
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
    reused = [
        dict(item)
        for item in prior_reports
        if str(item.get("passage_id")) in REUSED_PASSAGE_IDS
    ]
    combined = [selected, *reused]
    expected_order = [str(item["passage_id"]) for item in all_passages]
    combined.sort(key=lambda item: expected_order.index(str(item["passage_id"])))
    passed = bool(
        len(combined) == 4
        and [str(item["passage_id"]) for item in combined] == expected_order
        and all(item.get("pass") is True for item in combined)
    )
    artifact_hashes_after = {
        name: BASE.sha256_file(path) for name, path in artifacts.items()
    }
    if artifact_hashes_before != artifact_hashes_after:
        raise JekyllTargetedResynthesisError("model, voice, or ASR artifacts changed")
    lock_after = BASE.lock_snapshot(paid_lock)
    if lock_before != lock_after:
        raise JekyllTargetedResynthesisError("paid_tts.lock changed during execution")
    blockers = [
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "FULL_TITLE_ASR_BOUNDARY_CONTENT_NOT_RUN",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "FRONT_COVER_LINKAGE_REQUIRED_BEFORE_PUBLICATION",
        "PRIVATE_MEDIA_DELIVERY_MANIFEST_NOT_BUILT",
        "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
        "PUBLIC_RELEASE_NOT_APPROVED",
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
        "targeted_samples": samples,
        "targeted_asr": {
            "status": "PASS" if selected["pass"] else "FAIL",
            "all_candidates": {passage_id: candidates},
            "selected": [selected],
        },
        "combined_representative_reports": combined,
        "next_stage_contract": {
            **payload["next_stage_contract"],
            "listening_qa_allowed": passed,
            "full_title_generation_allowed": False,
            "do_not_repeat_completed_fingerprint": True,
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
            "resynthesized_passage_count": 1,
            "reused_passage_count": 3,
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
                    "paid_tts_lock_touched": False,
                    "upload_performed": False,
                    "publication_performed": False,
                    "release_gate_mutated": False,
                },
                indent=2,
            )
        )
        return int(code)
    except (
        JekyllTargetedResynthesisError,
        BASE.KokoroTitlePilotError,
        PROJECTION.JekyllProjectionError,
        REPAIR.JekyllASRRepairError,
    ) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
