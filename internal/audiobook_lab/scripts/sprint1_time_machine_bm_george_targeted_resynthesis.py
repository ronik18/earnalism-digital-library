#!/usr/bin/env python3
"""Resynthesize only The Time Machine's two failed ``bm_george`` passages.

The retained three-arm ASR bakeoff proved that ``eloi_first_contact`` and
``epilogue_tenderness`` alone need a materially new synthesis.  This private,
zero-provider-cost repair changes punctuation only, keeps every lexical source
token, binds the pinned British G2P/model/voice runtime, and requires one of
three local Whisper arms to prove exact ordered content for both new WAVs.

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
    "time_machine_bm_george_target_profile",
    SCRIPT_DIR / "sprint1_time_machine_bm_george_private_audition.py",
)
REPAIR_MODULE = _load(
    "time_machine_bm_george_prior_repair",
    SCRIPT_DIR / "sprint1_time_machine_bm_george_asr_repair.py",
)
PROFILE = PROFILE_MODULE.BASE
CORE = REPAIR_MODULE.CORE
ROOT = PROFILE.ROOT

SCHEMA = "earnalism.kokoro.time_machine_bm_george_targeted_resynthesis.v1"
TARGET_PASSAGE_IDS = ("eloi_first_contact", "epilogue_tenderness")
REUSED_PASSAGE_IDS = ("opening_exposition", "morlock_darkness")
PRIOR_REPAIR_SHA256 = (
    "28f916915bab79d26f91d1069e348967989ba7236f8c67eeed829555ba0e3a15"
)
PRIOR_REPAIR_FINGERPRINT = REPAIR_MODULE.EXPECTED_REPAIR_FINGERPRINT
EXPECTED_PAID_LOCK_SHA256 = REPAIR_MODULE.EXPECTED_PAID_LOCK_SHA256
PREPARED_TEXT_BINDINGS = {
    "eloi_first_contact": {
        "characters": 1475,
        "sha256": "0d5edcf0730963c6cfbccff7851061367c9eaf10de572580da9c992aa7dbe9ce",
        "phoneme_sha256": "679799e8c5bfda6b1e67fcf329b1d8b7dfe8b90b6e16677820930bc537e7a22e",
    },
    "epilogue_tenderness": {
        "characters": 1534,
        "sha256": "4eb253296d579a566e2587ebe611e9be92104d15e52b378a85859567843f01fc",
        "phoneme_sha256": "fc6a09014a2dc34a8c2919459a22c26161855a77c3faec546c247112339652f6",
    },
}
SPEED = 0.94
RANDOM_SEED = 2026072007
PRONUNCIATION_OVERRIDES = {
    **PROFILE_MODULE.PRONUNCIATION_OVERRIDES,
    "plesiosaurus": "plˌiːzɪəsˈɔːrəs",
}
EXPECTED_ATTEMPT_FINGERPRINT = (
    "9c52c3779dbcea0bb395d4de028b52da13a470838b19d61f0113ac339859ab36"
)
VOCABULARY_PROMPT = (
    "Canonical spellings and phrases: I and this fragile thing; ninepins; "
    "Cretaceous; plesiosaurus-haunted Oolitic coral reef; Triassic; "
    "civilisation; shrivelled; brown and flat and brittle. Preserve every "
    "spoken source word and British spelling."
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
    "eloi_first_contact": (
        {
            "pattern": r"\bnine pins\b",
            "replacement": "ninepins",
            "expected_count_when_observed": 1,
            "reason": "ASR token split for the acoustically identical source compound ninepins",
        },
    ),
    "epilogue_tenderness": (
        {
            "pattern": r"\bcivilization\b",
            "replacement": "civilisation",
            "expected_count_when_observed": 1,
            "reason": "American ASR spelling for source British spelling civilisation",
        },
        {
            "pattern": r"\bshriveled\b",
            "replacement": "shrivelled",
            "expected_count_when_observed": 1,
            "reason": "American ASR spelling for source British spelling shrivelled",
        },
    ),
}

DEFAULT_ARTIFACT_DIR = PROFILE_MODULE.DEFAULT_ARTIFACT_DIR
DEFAULT_WHISPER_CACHE = PROFILE_MODULE.DEFAULT_WHISPER_CACHE
DEFAULT_PRIVATE_OUTPUT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-time-machine/"
    "f3ff3571-bm-george-two-passage-targeted-v2"
)
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-time-machine_kokoro_bm_george_asr_repair_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-time-machine_kokoro_bm_george_targeted_resynthesis_v2.json"
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
    "the-time-machine_release_gate_evidence.json",
    DEFAULT_INPUT,
)


class TargetedResynthesisError(RuntimeError):
    """Raised when the bounded two-passage repair cannot preserve its contract."""


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


def canonical_passages() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    _chapters, passages = PROFILE_MODULE.controlled_source(ROOT, PROFILE_MODULE.SLUG)
    indexed = {str(item["passage_id"]): item for item in passages}
    if tuple(item for item in TARGET_PASSAGE_IDS if item not in indexed):
        raise TargetedResynthesisError("a targeted passage is absent from controlled source")
    return passages, indexed


def prepare_text(
    passage_id: str, source: str
) -> tuple[str, list[dict[str, str]]]:
    if passage_id == "eloi_first_contact":
        marker = "face to face, I and this"
        if source.count(marker) != 1:
            raise TargetedResynthesisError("Eloi punctuation marker changed")
        prepared = source.replace(marker, "face to face. I—and this", 1)
        transformations = [
            {
                "source": marker,
                "prepared": "face to face. I—and this",
                "reason": "make both short source words audible without changing lexical content",
            }
        ]
    elif passage_id == "epilogue_tenderness":
        first = "some plesiosaurus-haunted Oolitic"
        second = "brown and flat and brittle"
        if source.count(first) != 1 or source.count(second) != 1:
            raise TargetedResynthesisError("epilogue punctuation markers changed")
        prepared = source.replace(
            first, "some plesiosaurus ... haunted Oolitic", 1
        ).replace(second, "brown, and flat, and brittle", 1)
        transformations = [
            {
                "source": first,
                "prepared": "some plesiosaurus ... haunted Oolitic",
                "reason": "separate the scientific noun from the compound while preserving every word",
            },
            {
                "source": second,
                "prepared": "brown, and flat, and brittle",
                "reason": "make the middle adjective audible without changing lexical content",
            },
        ]
    else:
        raise TargetedResynthesisError(f"unsupported target passage: {passage_id}")

    binding = PREPARED_TEXT_BINDINGS[passage_id]
    if len(prepared) != int(binding["characters"]):
        raise TargetedResynthesisError(f"{passage_id} prepared character count changed")
    if sha256_text(prepared) != binding["sha256"]:
        raise TargetedResynthesisError(f"{passage_id} prepared text hash changed")
    if PROFILE.lexical_tokens(source) != PROFILE.lexical_tokens(prepared):
        raise TargetedResynthesisError(
            f"{passage_id} punctuation preparation changed lexical content"
        )
    return prepared, transformations


def validate_prepared_g2p(passage_id: str, prepared: str) -> dict[str, Any]:
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
            f"fallback-free G2P unresolved tokens in {passage_id}: "
            + ", ".join(unresolved)
        )
    phoneme_sha = sha256_text(str(phonemes or ""))
    if phoneme_sha != PREPARED_TEXT_BINDINGS[passage_id]["phoneme_sha256"]:
        raise TargetedResynthesisError(f"{passage_id} prepared phoneme hash changed")
    return {
        "passage_id": passage_id,
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
    if sha256_file(path) != PRIOR_REPAIR_SHA256:
        raise TargetedResynthesisError("prior repair evidence hash changed")
    evidence = read_json(path)
    repair = evidence.get("asr_repair") or {}
    if evidence.get("status") != (
        "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED"
    ):
        raise TargetedResynthesisError("prior repair status changed")
    if repair.get("repair_fingerprint") != PRIOR_REPAIR_FINGERPRINT:
        raise TargetedResynthesisError("prior repair fingerprint changed")
    reports = evidence.get("asr", {}).get("reports", [])
    if not isinstance(reports, list) or len(reports) != 4:
        raise TargetedResynthesisError("prior selected ASR report count changed")
    passed_ids = {
        str(item.get("passage_id")) for item in reports if item.get("pass") is True
    }
    failed_ids = {
        str(item.get("passage_id")) for item in reports if item.get("pass") is not True
    }
    if passed_ids != set(REUSED_PASSAGE_IDS) or failed_ids != set(TARGET_PASSAGE_IDS):
        raise TargetedResynthesisError("prior pass/fail passage sets changed")

    samples = evidence.get("samples") or []
    if not isinstance(samples, list) or len(samples) != 4:
        raise TargetedResynthesisError("prior private sample count changed")
    for sample in samples:
        path_value = Path(str(sample.get("audio_path") or ""))
        PROFILE.assert_private_audio_path(path_value)
        if not path_value.is_file():
            raise TargetedResynthesisError(f"prior private WAV is missing: {path_value}")
        if sha256_file(path_value) != sample.get("audio_sha256"):
            raise TargetedResynthesisError(f"prior private WAV hash changed: {path_value}")
    return evidence, reports, samples


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
        "scope": "two_failed_passages_targeted_private_resynthesis",
    }
    return sha256_text(json.dumps(contract, sort_keys=True, separators=(",", ":")))


def ensure_not_repeated(output: Path, fingerprint: str) -> None:
    for path in NO_REPEAT_FILES:
        if path.is_file() and fingerprint in path.read_text(
            encoding="utf-8", errors="strict"
        ):
            raise TargetedResynthesisError(f"attempt fingerprint already exists: {path}")
    if output.is_file():
        prior = read_json(output)
        if prior.get("attempt_fingerprint") == fingerprint and prior.get(
            "safety", {}
        ).get("audio_generated") is True:
            raise TargetedResynthesisError(
                "this targeted fingerprint already generated audio"
            )


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
            raise TargetedResynthesisError(
                f"{passage_id} equivalence count mismatch"
            )
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
    metrics = PROFILE.ordered_token_integrity(str(canonical["text"]), evaluated)
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
    PROFILE.SPEED = SPEED
    PROFILE.RANDOM_SEED = RANDOM_SEED
    PROFILE.PRONUNCIATION_OVERRIDES = PRONUNCIATION_OVERRIDES
    PROFILE.KOKORO_LANG_CODE = "b"
    PROFILE.G2P_BRITISH = True


def exact_execute_command() -> str:
    return (
        "PYTHONDONTWRITEBYTECODE=1 "
        "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
        ".venv-audio/bin/python internal/audiobook_lab/scripts/"
        "sprint1_time_machine_bm_george_targeted_resynthesis.py --execute"
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
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Path],
    list[dict[str, Any]],
]:
    PROFILE.assert_private_audio_path(private_dir)
    all_passages, indexed = canonical_passages()
    prepared_passages: list[dict[str, Any]] = []
    preparation_evidence: list[dict[str, Any]] = []
    g2p_evidence: list[dict[str, Any]] = []
    for passage_id in TARGET_PASSAGE_IDS:
        canonical = indexed[passage_id]
        prepared, transformations = prepare_text(passage_id, str(canonical["text"]))
        g2p_evidence.append(validate_prepared_g2p(passage_id, prepared))
        binding = PREPARED_TEXT_BINDINGS[passage_id]
        prepared_passages.append(
            {
                **canonical,
                "canonical_text_sha256": canonical["text_sha256"],
                "text": prepared,
                "text_sha256": binding["sha256"],
                "characters": len(prepared),
            }
        )
        preparation_evidence.append(
            {
                "passage_id": passage_id,
                "canonical_text_sha256": canonical["text_sha256"],
                "prepared_text_sha256": binding["sha256"],
                "canonical_lexical_tokens_unchanged": True,
                "transformations": transformations,
            }
        )

    _prior, prior_reports, _prior_samples = validate_prior(input_path)
    artifacts, artifact_evidence = PROFILE.validate_artifacts(
        artifact_dir, whisper_cache
    )
    runtime = PROFILE.runtime_evidence()
    lock = PROFILE.lock_snapshot(paid_lock)
    if lock["sha256"] != EXPECTED_PAID_LOCK_SHA256:
        raise TargetedResynthesisError("paid_tts.lock hash changed")
    fingerprint = attempt_fingerprint()
    if fingerprint != EXPECTED_ATTEMPT_FINGERPRINT:
        raise TargetedResynthesisError("targeted attempt fingerprint changed")
    ensure_not_repeated(output, fingerprint)
    payload = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": "READY_FOR_TWO_PASSAGE_TARGETED_PRIVATE_RESYNTHESIS",
        "go_no_go": "GO_TWO_PASSAGE_TARGETED_PRIVATE_RESYNTHESIS_ONLY",
        "attempt_fingerprint": fingerprint,
        "scope": {
            "slug": PROFILE_MODULE.SLUG,
            "title": PROFILE_MODULE.TITLE,
            "author": PROFILE_MODULE.AUTHOR,
            "target_passage_ids": list(TARGET_PASSAGE_IDS),
            "resynthesized_passage_count": 2,
            "reused_exact_passage_count": 2,
            "full_title_generated": False,
        },
        "source": {
            "complete_source_sha256": PROFILE_MODULE.EXPECTED_RECONCILIATION_SHA256,
            "preparations": preparation_evidence,
            "all_prepared_lexical_tokens_unchanged": True,
        },
        "prior_evidence": {
            "path": str(input_path),
            "sha256": PRIOR_REPAIR_SHA256,
            "attempt_fingerprint": PROFILE_MODULE.EXPECTED_ATTEMPT_FINGERPRINT,
            "repair_fingerprint": PRIOR_REPAIR_FINGERPRINT,
            "exact_passages_reused": list(REUSED_PASSAGE_IDS),
        },
        "engine": {
            "provider": "local_kokoro",
            "package_version": PROFILE.KOKORO_VERSION,
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
            "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        },
        "rights": {
            "controlled_text_public_domain": True,
            "author_death_year": 1946,
            "original_publication_year": 1895,
            "model_and_voicepack_license": "Apache-2.0",
            "model_revision_bound": PROFILE.MODEL_REVISION,
            "voice_file_sha256_bound": PROFILE_MODULE.VOICE_SHA256,
            "private_generation_allowed": True,
            "public_release_approved": False,
            "public_disclosure_required_if_later_approved": "AI voice",
        },
        "g2p_audit": g2p_evidence,
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
            "FULL_TITLE_ASR_BOUNDARY_CONTENT_NOT_RUN",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
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
    decoder: Callable[[Any, Mapping[str, Any], Mapping[str, Any]], str] = (
        CORE.run_decoding_arm
    ),
) -> tuple[int, dict[str, Any]]:
    runtime = payload.get("runtime_evidence") or {}
    if (
        runtime.get("offline_local_artifacts_only") is not True
        or runtime.get("deterministic_algorithms_required") is not True
        or runtime.get("torch_thread_count") != 1
    ):
        raise TargetedResynthesisError("execution requires the pinned offline runtime")
    lock_before = PROFILE.lock_snapshot(paid_lock)
    if lock_before != payload["safety"]["paid_tts_lock"]:
        raise TargetedResynthesisError("paid_tts.lock changed after preflight")
    configure_synthesis()
    artifact_hashes_before = {name: sha256_file(path) for name, path in artifacts.items()}
    samples = PROFILE.synthesize(
        prepared_passages,
        artifacts,
        PROFILE.assert_private_audio_path(private_dir),
    )
    if len(samples) != 2 or any(
        sample.get("objective_format_pass") is not True for sample in samples
    ):
        raise TargetedResynthesisError("a targeted WAV failed objective format")
    canonical_by_id = {
        str(item["passage_id"]): item for item in all_passages
    }
    prepared_by_id = {
        str(item["passage_id"]): item for item in prepared_passages
    }
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
        len(combined) == 4
        and [str(item["passage_id"]) for item in combined] == expected_order
        and all(item.get("pass") is True for item in combined)
    )
    artifact_hashes_after = {name: sha256_file(path) for name, path in artifacts.items()}
    if artifact_hashes_before != artifact_hashes_after:
        raise TargetedResynthesisError("model, voice, or ASR artifacts changed")
    lock_after = PROFILE.lock_snapshot(paid_lock)
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
            "resynthesized_passage_count": 2,
            "reused_passage_count": 2,
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
        return code
    except (
        TargetedResynthesisError,
        PROFILE.KokoroTitlePilotError,
        REPAIR_MODULE.TimeMachineASRRepairError,
    ) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
