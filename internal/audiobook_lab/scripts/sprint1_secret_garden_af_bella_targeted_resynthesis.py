#!/usr/bin/env python3
"""Repair only The Secret Garden's failed ``af_bella`` Yorkshire passage.

The original private pilot produced exact opening and emotional passages.  Its
ending differs only by Whisper's spelling of the source-bound proper name
``Misselthwaite``.  This adapter preserves those three WAVs, validates the
proper-name projection explicitly, and resynthesizes only the Yorkshire
dialogue with lexical-source-preserving punctuation preparation.  It cannot
listen, upload, publish, expose audio, or mutate release truth.
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


PROFILE = _load(
    "secret_garden_af_target_profile",
    SCRIPT_DIR / "sprint1_secret_garden_af_bella_private_audition.py",
)
REPAIR = _load(
    "secret_garden_af_prior_repair",
    SCRIPT_DIR / "sprint1_secret_garden_kokoro_asr_repair.py",
)
BASE = PROFILE.BASE
CORE = REPAIR.CORE
ROOT = BASE.ROOT

SCHEMA = "earnalism.kokoro.secret_garden_af_bella_targeted_resynthesis.v1"
TARGET_PASSAGE_ID = "yorkshire_dialogue"
PRIOR_REPAIR_SHA256 = (
    "c097a977827c51cf0e6e57b1757ebde9e01659920a6a3d55c25c43f715a2d9c8"
)
PRIOR_REPAIR_FINGERPRINT = (
    "54c3054797c0c1ef9f193a63c2ec538759c3a23ced1f7b41610e10dc7da38692"
)
PRIOR_ATTEMPT_FINGERPRINT = (
    "85ea18462a896ab42f61cca055a8d6a24190077884c24fef9a80701e955d3a67"
)
PREPARED_TEXT_SHA256 = (
    "2aeae45c39f433ce2264b7e702e6985c06e5f28c469b2c44d9e793b63e939b46"
)
PREPARED_TEXT_CHARACTERS = 854
PREPARED_PHONEME_SHA256 = (
    "a103dcc490303b2a0cc1e05e13e9af9a15cfb88704fb52464d81a0de72595045"
)
SPEED = 0.96
RANDOM_SEED = 2026072005
PRONUNCIATION_OVERRIDES = dict(PROFILE.PRONUNCIATION_OVERRIDES)
EXPECTED_ATTEMPT_FINGERPRINT = (
    "3b59c99aabc0a7e68c1509452dd7996108658e6078fbff5ee163bd79fe857949"
)
EXPECTED_PAID_LOCK_SHA256 = (
    "f586acc793022f28adb3e5fe08969075c2a16f09ef6814ebb31f6e6c90163df3"
)
VOCABULARY_PROMPT = (
    "Canonical source spellings: Who is going to dress me; Canna; tha; "
    "thysen; sayin; Ayah dressed me; nurses an bein washed an dressed an "
    "took. Preserve every complete word and the Yorkshire dialect."
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
        "id": "canonical_yorkshire_beam_5",
        "initial_prompt": VOCABULARY_PROMPT,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": 5,
        "patience": 1,
        "hallucination_silence_threshold": 0.5,
    },
)
YORKSHIRE_EQUIVALENCES = (
    {
        "pattern": r"\bcan a\b",
        "replacement": "canna",
        "expected_count_when_observed": 1,
        "reason": "ASR token split for the source-bound dialect word canna",
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
)
ENDING_EQUIVALENCES = (
    {
        "pattern": r"\bMizzlethwaite\b",
        "replacement": "Misselthwaite",
        "expected_count_when_observed": 1,
        "reason": (
            "one-occurrence ASR orthographic projection for the canonical "
            "proper name bound to the retained WAV and pinned G2P phoneme hash"
        ),
    },
)
EXPECTED_SAMPLE_BINDINGS = {
    "opening_india": {
        "audio_sha256": "82471a359c466ecd2d5f42a2320df0eec0634c10c1532302f3acdce7ce173730",
        "size_bytes": 2_306_444,
        "duration_seconds": 48.05,
        "raw_transcript_sha256": "140c2dc08a927a239a859ad3543cd5c9ab436ee5e8249b1850b9acd5c39f4a63",
    },
    "yorkshire_dialogue": {
        "audio_sha256": "cf2f59435cd7a591c23f9bdab0403b23e389115542b87e26d298e4eccfd82c4b",
        "size_bytes": 2_278_844,
        "duration_seconds": 47.475,
        "raw_transcript_sha256": "6bb78b98a63a544cdb7ca070ca807fef497c441d2b766104af09bb638c9dc0b8",
    },
    "mary_colin_emotion": {
        "audio_sha256": "38bb4bf3613794a7d3486b28ede1f791dfde7e8252fd7c6edc235aca3beb1f6b",
        "size_bytes": 2_473_244,
        "duration_seconds": 51.525,
        "raw_transcript_sha256": "7f42385ba6f479ceba4a0232530e112762218f635ae49725beefbc26d44d6c1b",
    },
    "ending_return": {
        "audio_sha256": "e3096aee4f44ec6c5e59c7c5c385b401f82259919a8857e8377c3897c9929dd4",
        "size_bytes": 1_291_244,
        "duration_seconds": 26.9,
        "raw_transcript_sha256": "5a699dc5aaa863916bb7ef380987fd2212d2a65ba7685ff7272d83f705a9afdc",
    },
}

DEFAULT_ARTIFACT_DIR = PROFILE.DEFAULT_ARTIFACT_DIR
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
DEFAULT_PAID_LOCK = PROFILE.DEFAULT_PAID_LOCK
DEFAULT_PRIVATE_OUTPUT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-secret-garden/"
    "f3ff3571-af-bella-yorkshire-targeted-v2"
)
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_af_bella_asr_repair_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-secret-garden_kokoro_af_bella_targeted_resynthesis_v2.json"
)
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl",
    ROOT / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
    ROOT / (
        "internal/audiobook_lab/sprint1_publication/title_runs/"
        "the-secret-garden_release_gate_evidence.json"
    ),
    DEFAULT_INPUT,
)


class TargetedResynthesisError(RuntimeError):
    """Raised when the bounded repair cannot preserve its evidence contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return BASE.sha256_file(path)


def read_json(path: Path) -> dict[str, Any]:
    return BASE.read_json(path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def canonical_passages() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _source, passages = PROFILE.controlled_source(ROOT, PROFILE.SLUG)
    target = next(
        (item for item in passages if item["passage_id"] == TARGET_PASSAGE_ID), None
    )
    if target is None:
        raise TargetedResynthesisError("target passage is absent from controlled source")
    return passages, target


def prepare_text(source: str) -> tuple[str, list[dict[str, str]]]:
    transformations = (
        ("“Who is going to dress me?”", "“... Who is going to dress me?”", "make the complete opening question independently audible"),
        ("“Canna’ tha’ dress thysen!”", "“Canna tha dress thysen!”", "remove only terminal dialect apostrophes"),
        ("sayin’", "sayin", "remove only the terminal dialect apostrophe"),
        ("“it’s time tha’ should learn. Tha’ cannot begin younger.", "“it’s time tha should learn. Tha cannot begin younger.", "remove only two terminal dialect apostrophes"),
        ("wait on thysen a bit.", "wait on thysen, a bit.", "separate thysen from the following article"),
        ("nurses an’ bein’ washed an’ dressed an’ took", "nurses, an bein washed, an dressed, an took", "make each dialect conjunction and verb boundary audible"),
    )
    prepared = source
    evidence: list[dict[str, str]] = []
    for old, new, reason in transformations:
        if prepared.count(old) != 1:
            raise TargetedResynthesisError(f"punctuation marker count changed: {old}")
        prepared = prepared.replace(old, new, 1)
        evidence.append({"source": old, "prepared": new, "reason": reason})
    if len(prepared) != PREPARED_TEXT_CHARACTERS:
        raise TargetedResynthesisError("prepared character count changed")
    if sha256_text(prepared) != PREPARED_TEXT_SHA256:
        raise TargetedResynthesisError("prepared text hash changed")
    if BASE.lexical_tokens(source) != BASE.lexical_tokens(prepared):
        raise TargetedResynthesisError("punctuation preparation changed lexical content")
    return prepared, evidence


def validate_prepared_g2p(prepared: str) -> dict[str, Any]:
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
            f"fallback-free G2P unresolved tokens: {', '.join(unresolved)}"
        )
    phoneme_sha = sha256_text(str(phonemes or ""))
    if phoneme_sha != PREPARED_PHONEME_SHA256:
        raise TargetedResynthesisError("prepared phoneme hash changed")
    return {
        "status": "PASS",
        "kokoro_lang_code": "a",
        "british": False,
        "fallback": None,
        "all_source_tokens_resolved": True,
        "phoneme_sha256": phoneme_sha,
        "unresolved_tokens": [],
    }


def _apply_rules(
    transcript: str, rules: Sequence[Mapping[str, Any]]
) -> tuple[str, list[dict[str, Any]]]:
    evaluated = transcript
    applications: list[dict[str, Any]] = []
    for rule in rules:
        count = len(re.findall(str(rule["pattern"]), evaluated, flags=re.IGNORECASE))
        if count == 0:
            continue
        expected = int(rule["expected_count_when_observed"])
        if count != expected:
            raise TargetedResynthesisError("source equivalence count mismatch")
        evaluated, replaced = re.subn(
            str(rule["pattern"]),
            str(rule["replacement"]),
            evaluated,
            flags=re.IGNORECASE,
        )
        if replaced != expected:
            raise TargetedResynthesisError("source equivalence replacement changed")
        applications.append({**rule, "observed_count": count})
    return evaluated, applications


def apply_equivalences(
    passage_id: str, transcript: str
) -> tuple[str, list[dict[str, Any]]]:
    if passage_id == TARGET_PASSAGE_ID:
        return _apply_rules(transcript, YORKSHIRE_EQUIVALENCES)
    if passage_id == "ending_return":
        return _apply_rules(transcript, ENDING_EQUIVALENCES)
    return transcript, []


def evaluate(
    canonical: Mapping[str, Any], sample: Mapping[str, Any], transcript: str, arm: str
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


def validate_prior(
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    if sha256_file(path) != PRIOR_REPAIR_SHA256:
        raise TargetedResynthesisError("prior repair evidence hash changed")
    evidence = read_json(path)
    if evidence.get("schema") != "earnalism.kokoro.secret_garden_af_bella_asr_repair.v1":
        raise TargetedResynthesisError("prior repair schema changed")
    if evidence.get("status") != "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED":
        raise TargetedResynthesisError("prior repair status changed")
    repair = evidence.get("asr_repair") or {}
    if repair.get("repair_fingerprint") != PRIOR_REPAIR_FINGERPRINT:
        raise TargetedResynthesisError("prior repair fingerprint changed")
    if (evidence.get("engine") or {}).get("attempt_fingerprint") != PRIOR_ATTEMPT_FINGERPRINT:
        raise TargetedResynthesisError("prior synthesis fingerprint changed")

    passages, _target = canonical_passages()
    canonical = {str(item["passage_id"]): item for item in passages}
    samples = evidence.get("samples") or []
    reports = (evidence.get("asr") or {}).get("reports") or []
    if not isinstance(samples, list) or not isinstance(reports, list):
        raise TargetedResynthesisError("prior samples or reports are malformed")
    expected_order = [str(item["passage_id"]) for item in passages]
    if [item.get("passage_id") for item in samples] != expected_order:
        raise TargetedResynthesisError("prior sample order changed")
    if [item.get("passage_id") for item in reports] != expected_order:
        raise TargetedResynthesisError("prior selected report order changed")

    for sample, report in zip(samples, reports):
        passage_id = str(sample["passage_id"])
        binding = EXPECTED_SAMPLE_BINDINGS[passage_id]
        for key in ("audio_sha256", "size_bytes", "duration_seconds"):
            if sample.get(key) != binding[key]:
                raise TargetedResynthesisError(f"prior {passage_id} {key} changed")
        if sample.get("objective_format_pass") is not True:
            raise TargetedResynthesisError(f"prior {passage_id} format no longer passes")
        audio_path = BASE.assert_private_audio_path(Path(str(sample["audio_path"])))
        if not audio_path.is_file():
            raise TargetedResynthesisError(f"retained private WAV is missing: {audio_path}")
        if audio_path.stat().st_size != binding["size_bytes"]:
            raise TargetedResynthesisError(f"retained {passage_id} byte size changed")
        if sha256_file(audio_path) != binding["audio_sha256"]:
            raise TargetedResynthesisError(f"retained {passage_id} WAV hash changed")
        if report.get("audio_sha256") != binding["audio_sha256"]:
            raise TargetedResynthesisError(f"selected {passage_id} audio binding changed")
        if sha256_text(str(report.get("raw_transcript") or "")) != binding["raw_transcript_sha256"]:
            raise TargetedResynthesisError(f"selected {passage_id} transcript changed")

    passed_ids = {str(item["passage_id"]) for item in reports if item.get("pass") is True}
    if passed_ids != {"opening_india", "mary_colin_emotion"}:
        raise TargetedResynthesisError("prior exact-passage pass set changed")
    failed_ids = {str(item["passage_id"]) for item in reports if item.get("pass") is not True}
    if failed_ids != {TARGET_PASSAGE_ID, "ending_return"}:
        raise TargetedResynthesisError("prior failed-passage set changed")

    ending_report = next(item for item in reports if item["passage_id"] == "ending_return")
    ending_sample = next(item for item in samples if item["passage_id"] == "ending_return")
    ending_projection = evaluate(
        canonical["ending_return"],
        ending_sample,
        str(ending_report["raw_transcript"]),
        f"{ending_report['decoder_arm']}+source_bound_proper_name_projection",
    )
    if ending_projection["pass"] is not True:
        raise TargetedResynthesisError("retained ending proper-name projection failed")
    applications = ending_projection["source_equivalences_applied"]
    if len(applications) != 1 or applications[0]["replacement"] != "Misselthwaite":
        raise TargetedResynthesisError("retained ending projection contract changed")

    reusable = [
        next(item for item in reports if item["passage_id"] == "opening_india"),
        next(item for item in reports if item["passage_id"] == "mary_colin_emotion"),
        ending_projection,
    ]
    return evidence, samples, reusable


def attempt_fingerprint() -> str:
    contract = {
        "contract": SCHEMA,
        "slug": PROFILE.SLUG,
        "target_passage_id": TARGET_PASSAGE_ID,
        "source_text_sha256": PROFILE.PASSAGE_SPECS[1]["sha256"],
        "prepared_text_sha256": PREPARED_TEXT_SHA256,
        "prepared_phoneme_sha256": PREPARED_PHONEME_SHA256,
        "prior_attempt_fingerprint": PRIOR_ATTEMPT_FINGERPRINT,
        "prior_repair_fingerprint": PRIOR_REPAIR_FINGERPRINT,
        "prior_repair_evidence_sha256": PRIOR_REPAIR_SHA256,
        "retained_audio_hashes": {
            key: value["audio_sha256"] for key, value in EXPECTED_SAMPLE_BINDINGS.items()
        },
        "model_revision": BASE.MODEL_REVISION,
        "model_sha256": BASE.MODEL_SHA256,
        "config_sha256": BASE.CONFIG_SHA256,
        "voice": PROFILE.VOICE,
        "voice_sha256": PROFILE.VOICE_SHA256,
        "whisper_sha256": PROFILE.WHISPER_SHA256,
        "kokoro_lang_code": "a",
        "g2p_british": False,
        "speed": SPEED,
        "random_seed": RANDOM_SEED,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "decoder_arms": DECODING_ARMS,
        "yorkshire_equivalences": YORKSHIRE_EQUIVALENCES,
        "ending_equivalences": ENDING_EQUIVALENCES,
        "scope": "one_failed_passage_targeted_private_resynthesis",
    }
    return sha256_text(json.dumps(contract, sort_keys=True, separators=(",", ":")))


def ensure_not_repeated(output: Path, fingerprint: str) -> None:
    resolved_output = output.expanduser().resolve()
    paths = list(NO_REPEAT_FILES)
    paths.extend(
        sorted(
            (ROOT / "internal/audiobook_lab/sprint1_publication/title_runs").glob("*.json")
        )
    )
    for path in paths:
        if not path.is_file() or path.resolve() == resolved_output:
            continue
        if fingerprint in path.read_text(encoding="utf-8", errors="strict"):
            raise TargetedResynthesisError(
                f"attempt fingerprint already exists in durable evidence: {path}"
            )
    if resolved_output.is_file():
        prior = read_json(resolved_output)
        if prior.get("attempt_fingerprint") == fingerprint and (
            prior.get("safety") or {}
        ).get("audio_generated") is True:
            raise TargetedResynthesisError("this targeted fingerprint already generated audio")


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
        "sprint1_secret_garden_af_bella_targeted_resynthesis.py --execute"
    )


def preflight(
    *,
    input_path: Path,
    output: Path,
    artifact_dir: Path,
    whisper_cache: Path,
    private_dir: Path,
    paid_lock: Path,
) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Path], list[dict[str, Any]]
]:
    resolved_private = BASE.assert_private_audio_path(private_dir)
    if (resolved_private / f"{TARGET_PASSAGE_ID}.wav").exists():
        raise TargetedResynthesisError("target private WAV already exists without bound output")
    _all_passages, target = canonical_passages()
    prepared, transformations = prepare_text(str(target["text"]))
    fingerprint = attempt_fingerprint()
    if fingerprint != EXPECTED_ATTEMPT_FINGERPRINT:
        raise TargetedResynthesisError("targeted attempt fingerprint changed")
    ensure_not_repeated(output, fingerprint)
    g2p = validate_prepared_g2p(prepared)
    prior, _samples, reusable_reports = validate_prior(input_path)
    artifacts, artifact_evidence = BASE.validate_artifacts(artifact_dir, whisper_cache)
    runtime = BASE.runtime_evidence()
    lock = BASE.lock_snapshot(paid_lock)
    if lock["sha256"] != EXPECTED_PAID_LOCK_SHA256:
        raise TargetedResynthesisError("paid_tts.lock hash changed")
    payload = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": "PRIVATE_TARGETED_RESYNTHESIS_PREFLIGHT_PASS",
        "go_no_go": "GO_ONE_TARGETED_PRIVATE_RESYNTHESIS_ONLY",
        "attempt_fingerprint": fingerprint,
        "scope": {
            "slug": PROFILE.SLUG,
            "title": PROFILE.TITLE,
            "author": PROFILE.AUTHOR,
            "target_passage_id": TARGET_PASSAGE_ID,
            "resynthesized_passage_count": 1,
            "reused_exact_passage_count": 2,
            "reused_source_bound_projection_count": 1,
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
            "attempt_fingerprint": PRIOR_ATTEMPT_FINGERPRINT,
            "repair_fingerprint": PRIOR_REPAIR_FINGERPRINT,
            "prior_status": prior["status"],
            "two_exact_passages_reused": True,
            "ending_source_bound_proper_name_projection_validated": True,
        },
        "engine": {
            "provider": "local_kokoro",
            "model_revision": BASE.MODEL_REVISION,
            "model_sha256": BASE.MODEL_SHA256,
            "config_sha256": BASE.CONFIG_SHA256,
            "voice": PROFILE.VOICE,
            "voice_sha256": PROFILE.VOICE_SHA256,
            "speed": SPEED,
            "random_seed": RANDOM_SEED,
            "kokoro_lang_code": "a",
            "g2p_british": False,
            "g2p_fallback_enabled": False,
        },
        "g2p_audit": g2p,
        "artifact_evidence": artifact_evidence,
        "runtime_evidence": runtime,
        "decoder_arms": DECODING_ARMS,
        "equivalence_policy": {
            TARGET_PASSAGE_ID: YORKSHIRE_EQUIVALENCES,
            "ending_return": ENDING_EQUIVALENCES,
        },
        "next_stage_contract": {
            "exact_execute_command": exact_execute_command(),
            "listening_qa_allowed": False,
            "full_title_generation_allowed": False,
            "upload_allowed": False,
            "publication_allowed": False,
            "release_gate_mutation_allowed": False,
        },
        "safety": {
            "private_output_dir": str(resolved_private),
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "paid_tts_lock": lock,
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
            "SECRET_GARDEN_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "PRIVATE_DELIVERY_MANIFEST_NOT_COMPLETE",
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
    return payload, prepared_passage, artifacts, reusable_reports


def execute(
    *,
    payload: dict[str, Any],
    prepared: Mapping[str, Any],
    artifacts: Mapping[str, Path],
    reusable_reports: Sequence[Mapping[str, Any]],
    private_dir: Path,
    whisper_cache: Path,
    paid_lock: Path,
    model_loader: Callable[[Path], Any] = CORE.load_whisper_model,
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], str] = CORE.run_decoding_arm,
) -> tuple[int, dict[str, Any]]:
    if payload["runtime_evidence"].get("offline_local_artifacts_only") is not True:
        raise TargetedResynthesisError("execution requires the pinned offline runtime")
    configure_synthesis()
    artifact_before = {name: sha256_file(path) for name, path in artifacts.items()}
    lock_before = BASE.lock_snapshot(paid_lock)
    samples = BASE.synthesize(
        [prepared], artifacts, BASE.assert_private_audio_path(private_dir)
    )
    if len(samples) != 1 or samples[0].get("objective_format_pass") is not True:
        raise TargetedResynthesisError("targeted WAV failed objective format")
    sample = samples[0]
    sample["canonical_source_text_sha256"] = prepared["canonical_text_sha256"]
    sample["prepared_text_sha256"] = PREPARED_TEXT_SHA256
    model = model_loader(whisper_cache)
    canonical = dict(prepared)
    canonical["text"] = next(
        item["text"]
        for item in canonical_passages()[0]
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
    combined = [*reusable_reports, selected]
    expected_order = [item["passage_id"] for item in canonical_passages()[0]]
    combined.sort(key=lambda item: expected_order.index(str(item["passage_id"])))
    passed = bool(
        len(combined) == 4
        and [item["passage_id"] for item in combined] == expected_order
        and all(item.get("pass") is True for item in combined)
    )
    artifact_after = {name: sha256_file(path) for name, path in artifacts.items()}
    lock_after = BASE.lock_snapshot(paid_lock)
    if artifact_before != artifact_after:
        raise TargetedResynthesisError("model, voice, or ASR artifacts changed")
    if lock_before != lock_after or lock_after["sha256"] != EXPECTED_PAID_LOCK_SHA256:
        raise TargetedResynthesisError("paid_tts.lock changed during local repair")
    blockers = [
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "SECRET_GARDEN_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
        "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
        "PRIVATE_DELIVERY_MANIFEST_NOT_COMPLETE",
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
            "paid_tts_lock_before": lock_before,
            "paid_tts_lock_after": lock_after,
            "paid_tts_lock_unchanged": True,
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "paid_tts_lock_touched": False,
            "audio_generated": True,
            "resynthesized_passage_count": 1,
            "reused_exact_passage_count": 2,
            "reused_source_bound_projection_count": 1,
            "asr_run": True,
            "listening_qa_run": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
            "artifact_hashes_before": artifact_before,
            "artifact_hashes_after": artifact_after,
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
        payload, prepared, artifacts, reusable = preflight(
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
                prepared=prepared,
                artifacts=artifacts,
                reusable_reports=reusable,
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
                    "provider_calls": 0,
                    "upload_performed": False,
                    "publication_performed": False,
                    "release_gate_mutated": False,
                },
                indent=2,
            )
        )
        return code
    except (TargetedResynthesisError, BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
