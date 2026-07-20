#!/usr/bin/env python3
"""Run one bounded ASR-only repair over retained Last Leaf Kokoro WAVs.

The four WAV files are immutable inputs. This audit tries only two unprompted
local Whisper decoding arms (a small beam and greedy decoding), retains every
candidate transcript, and applies only exact-count source/acoustic spelling
equivalences. It never synthesizes or edits audio, deletes unexpected speech,
calls a provider/listener, uploads, publishes, or changes release truth.
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
import re
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
PROFILE_PATH = Path(__file__).with_name("sprint1_last_leaf_kokoro_private_audition.py")
SPEC = importlib.util.spec_from_file_location("last_leaf_kokoro_profile", PROFILE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - installation guard
    raise RuntimeError(f"cannot load Last Leaf profile: {PROFILE_PATH}")
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)


SCHEMA = "earnalism.kokoro.last_leaf_asr_repair.v1"
SLUG = PROFILE.SLUG
TITLE = PROFILE.TITLE
AUTHOR = PROFILE.AUTHOR
EXPECTED_INPUT_SCHEMA = "earnalism.kokoro.last_leaf_private_representative.v1"
EXPECTED_INPUT_STATUS = "PRIVATE_REPRESENTATIVE_PILOT_REJECTED"
EXPECTED_INPUT_SHA256 = "b025ee591e2e470a52ad6f640d5135d2ae0b7ba7256a69634f41f6ba8122d07e"
EXPECTED_ATTEMPT_FINGERPRINT = "f152ffdc135dea3c9ffd463138489739a80a163196059e7cc0130527d83a7ed1"
EXPECTED_PRIOR_ASR_FINGERPRINT = "4313b4d132c6b4886844e2431bd6180c426a7c4882317faa51f29f69290eee47"
EXPECTED_PRIOR_TRANSCRIPT_HASHES = {
    "opening_literary_setting": "8ad16e7b17729d2e348fc34629718e3b9e97fb4ecc9ca52caa43577855cc9330",
    "johnsy_leaf_dialogue": "17459af8ef5f86b3259a0b6570b14217b9f10276e8b33836917f7b4a177dfe6e",
    "behrman_dialect_emotion": "9bf0e80403e26d05784156646409d7c2bab92e9620083aae3962d0ebc0d29bf1",
    "final_masterpiece_reveal": "3e3f68cb9a822a16bc22b01cbfcfdfa42f5feaf05ead6bde4f3db7b01d54376e",
}
EXPECTED_SAMPLE_BINDINGS = {
    "opening_literary_setting": {
        "source_text_sha256": "05c55ee1edd72ef0609c782226e4537ff35051b2ea7ea81e0eedfd2901d02dd5",
        "audio_sha256": "30ff73e6e7050e711662661dd1d029332d596fca091b4bb880db7274b3f64e05",
        "size_bytes": 2_054_444,
        "duration_seconds": 42.8,
    },
    "johnsy_leaf_dialogue": {
        "source_text_sha256": "8ece41198a202de474bef1a33218949f8bd72fd18413f4af140548db7026b775",
        "audio_sha256": "d2eeac9040f29b4c55efbeb75054343dba515b4980609572f0c49b2d5b6a85bc",
        "size_bytes": 1_059_644,
        "duration_seconds": 22.075,
    },
    "behrman_dialect_emotion": {
        "source_text_sha256": "3ee0d5877dcd681e530ea3dc56fe0c7b11614d3bec736c9ca485799c897fafc1",
        "audio_sha256": "87b4b7ace968e8843693b6e73ad638a7058bae699a202b72e0c137b61e59b008",
        "size_bytes": 1_214_444,
        "duration_seconds": 25.3,
    },
    "final_masterpiece_reveal": {
        "source_text_sha256": "9b92d5b089d00a5896d243c6c6ac4c8e5ad645a76f820131df9476f582e1bc00",
        "audio_sha256": "b325b0eb22218168628be0efe9b2624081c637f255794e823132a7af63131406",
        "size_bytes": 2_077_244,
        "duration_seconds": 43.275,
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
        "id": "unprompted_greedy_fallback",
        "initial_prompt": None,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "beam_size": None,
        "patience": None,
        "hallucination_silence_threshold": 0.5,
    },
)

# Transcript-to-source acoustic or orthographic spellings only. Context-bound
# patterns avoid accidentally rewriting genuine source words. There are
# deliberately no rules for do/de, in/and, trailing "Thank you", or duplicated
# "it": an audio-derived decoder must resolve those differences on its own.
EQUIVALENCE_POLICY = {
    "opening_literary_setting": (),
    "johnsy_leaf_dialogue": (),
    "behrman_dialect_emotion": (
        {
            "pattern": r"\bder people\b",
            "replacement": "dere people",
            "expected_count_when_observed": 1,
            "reason": "source dialect dere/der acoustic spelling equivalent",
        },
        {
            "pattern": r"\bleafs de drop\b",
            "replacement": "leafs dey drop",
            "expected_count_when_observed": 1,
            "reason": "source dialect dey/de acoustic spelling equivalent",
        },
        {
            "pattern": r"\bhaff not\b",
            "replacement": "haf not",
            "expected_count_when_observed": 1,
            "reason": "source dialect haf/haff acoustic spelling equivalent",
        },
        {
            "pattern": r"\bsilly pizness\b",
            "replacement": "silly pusiness",
            "expected_count_when_observed": 1,
            "reason": "source dialect pusiness/pizness acoustic spelling equivalent",
        },
        {
            "pattern": r"\bock dot\b",
            "replacement": "ach dot",
            "expected_count_when_observed": 1,
            "reason": "source dialect Ach/Ock acoustic spelling equivalent",
        },
        {
            "pattern": r"\bpoor little\b",
            "replacement": "poor lettle",
            "expected_count_when_observed": 1,
            "reason": "source dialect lettle/little acoustic spelling equivalent",
        },
    ),
    "final_masterpiece_reveal": (
        {
            "pattern": r"\bpneumonia today in\b",
            "replacement": "pneumonia to day in",
            "expected_count_when_observed": 1,
            "reason": "source to-day/today orthographic equivalent",
        },
    ),
}

ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98
DEFAULT_INPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-last-leaf_kokoro_af_sarah_representative_preflight_v1.json"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-last-leaf_kokoro_af_sarah_asr_repair_v1.json"
)
DEFAULT_WHISPER_CACHE = PROFILE.DEFAULT_WHISPER_CACHE
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
)


class LastLeafASRRepairError(RuntimeError):
    """Raised when immutable-audio repair evidence is not exact or safe."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LastLeafASRRepairError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LastLeafASRRepairError(f"expected JSON object: {path}")
    return value


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
        raise LastLeafASRRepairError(f"public output path is forbidden: {resolved}")
    return resolved


def assert_private_audio(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    rendered = f"/{resolved.as_posix().lower().strip('/')}/"
    if "/internal/audiobook_lab/private_runs/" not in rendered:
        raise LastLeafASRRepairError(f"audio is outside private_runs: {resolved}")
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


def _require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise LastLeafASRRepairError(
            f"{label} changed: expected {expected!r}, observed {observed!r}"
        )


def validate_input(
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    _require(PROFILE.BASE.sha256_file(path), EXPECTED_INPUT_SHA256, "input evidence SHA-256")
    evidence = read_json(path)
    _require(evidence.get("schema"), EXPECTED_INPUT_SCHEMA, "input schema")
    _require(evidence.get("status"), EXPECTED_INPUT_STATUS, "input status")
    scope = evidence.get("scope") if isinstance(evidence.get("scope"), dict) else {}
    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "passage_count": 4,
        "representative_only": True,
        "full_title_generated": False,
    }.items():
        _require(scope.get(key), expected, f"scope.{key}")
    engine = evidence.get("engine") if isinstance(evidence.get("engine"), dict) else {}
    _require(engine.get("attempt_fingerprint"), EXPECTED_ATTEMPT_FINGERPRINT, "attempt fingerprint")
    _require(engine.get("voice"), PROFILE.VOICE, "voice")
    _require(engine.get("voice_sha256"), PROFILE.VOICE_SHA256, "voice SHA-256")
    _require(engine.get("g2p_fallback_enabled"), False, "G2P fallback flag")

    _chapter, passages = PROFILE.controlled_source(ROOT, SLUG)
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
            raise LastLeafASRRepairError(f"private audio is missing: {passage_id}")
        _require(PROFILE.BASE.sha256_file(audio), expected["audio_sha256"], f"{passage_id} audio SHA-256")
        _require(audio.stat().st_size, expected["size_bytes"], f"{passage_id} audio size")
        verified_samples.append(dict(sample))

    prior = evidence.get("asr") if isinstance(evidence.get("asr"), dict) else {}
    _require(prior.get("status"), "FAIL", "prior ASR status")
    _require(prior.get("config_fingerprint"), EXPECTED_PRIOR_ASR_FINGERPRINT, "prior ASR fingerprint")
    reports = prior.get("reports") if isinstance(prior.get("reports"), list) else []
    _require(len(reports), 4, "prior ASR report count")
    report_by_id = {str(item.get("passage_id") or ""): item for item in reports}
    _require(set(report_by_id), set(EXPECTED_PRIOR_TRANSCRIPT_HASHES), "prior ASR passage IDs")
    for passage_id, expected_hash in EXPECTED_PRIOR_TRANSCRIPT_HASHES.items():
        report = report_by_id[passage_id]
        _require(report.get("transcript_sha256"), expected_hash, f"{passage_id} prior transcript hash")
        _require(
            PROFILE.BASE.sha256_text(str(report.get("transcript") or "")),
            expected_hash,
            f"{passage_id} measured prior transcript hash",
        )
    return evidence, verified_samples, passages


def repair_fingerprint() -> str:
    return canonical_hash(
        {
            "contract": SCHEMA,
            "slug": SLUG,
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
            "whisper_model": PROFILE.BASE.WHISPER_MODEL,
            "whisper_sha256": PROFILE.WHISPER_SHA256,
            "decoding_arms": DECODING_ARMS,
            "equivalence_policy": EQUIVALENCE_POLICY,
            "score_min": ASR_SCORE_MIN,
            "coverage_min": ASR_COVERAGE_MIN,
            "forbidden_normalizations": [
                "do/de",
                "in/and",
                "trailing Thank you",
                "duplicated it",
            ],
            "unexpected_speech_may_be_deleted": False,
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
            raise LastLeafASRRepairError("this exact ASR-only repair already completed")
    for path in NO_REPEAT_FILES:
        if path.is_file() and fingerprint in set(_find_fingerprints(read_json(path))):
            raise LastLeafASRRepairError(f"repair fingerprint already exists in {path}")


def apply_equivalences(
    passage_id: str, transcript: str
) -> tuple[str, list[dict[str, Any]]]:
    if passage_id not in EQUIVALENCE_POLICY:
        raise LastLeafASRRepairError(f"missing equivalence policy: {passage_id}")
    evaluated = transcript
    applications: list[dict[str, Any]] = []
    for rule in EQUIVALENCE_POLICY[passage_id]:
        observed = len(re.findall(str(rule["pattern"]), evaluated, flags=re.IGNORECASE))
        if observed == 0:
            continue
        expected = int(rule["expected_count_when_observed"])
        if observed != expected:
            raise LastLeafASRRepairError(
                f"{passage_id} equivalence count mismatch for {rule['pattern']}: "
                f"expected {expected}, observed {observed}"
            )
        evaluated, replaced = re.subn(
            str(rule["pattern"]),
            str(rule["replacement"]),
            evaluated,
            flags=re.IGNORECASE,
        )
        if replaced != expected:
            raise LastLeafASRRepairError("equivalence replacement count changed")
        applications.append(
            {
                "pattern": rule["pattern"],
                "replacement": rule["replacement"],
                "observed_count": observed,
                "reason": rule["reason"],
            }
        )
    return evaluated, applications


def evaluate_transcript(
    passage: Mapping[str, Any], sample: Mapping[str, Any], transcript: str, arm_id: str
) -> dict[str, Any]:
    evaluated, applications = apply_equivalences(str(passage["passage_id"]), transcript)
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

    model_path = cache.expanduser().resolve() / PROFILE.BASE.WHISPER_FILENAME
    PROFILE.BASE.verify_hash(model_path, PROFILE.WHISPER_SHA256, "Whisper model")
    return whisper.load_model(PROFILE.BASE.WHISPER_MODEL, download_root=str(cache.resolve()))


def _audio_hashes(samples: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {
        str(sample["passage_id"]): PROFILE.BASE.sha256_file(
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
            "provider_calls": 0,
            "synthesis_performed": False,
            "audio_edit_or_trim_performed": False,
            "asr_performed": False,
            "listening_qa_performed": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
        }

    sample_by_id = {str(item["passage_id"]): item for item in samples}
    passage_by_id = {str(item["passage_id"]): item for item in passages}
    model = model_loader(whisper_cache)
    candidates: dict[str, list[dict[str, Any]]] = {key: [] for key in sample_by_id}
    unresolved = set(sample_by_id)
    for arm in DECODING_ARMS:
        targets = list(sample_by_id) if arm["id"] == DECODING_ARMS[0]["id"] else sorted(unresolved)
        for passage_id in targets:
            transcript = decoder(model, arm, sample_by_id[passage_id])
            report = evaluate_transcript(
                passage_by_id[passage_id], sample_by_id[passage_id], transcript, str(arm["id"])
            )
            candidates[passage_id].append(report)
            if report["pass"]:
                unresolved.discard(passage_id)
        if not unresolved:
            break

    selected: list[dict[str, Any]] = []
    for passage_id in sample_by_id:
        reports = candidates[passage_id]
        passing = [item for item in reports if item["pass"]]
        selected.append(
            passing[0]
            if passing
            else max(reports, key=lambda item: (item["score"], item["coverage"]))
        )
    passed = len(selected) == 4 and all(item["pass"] for item in selected)
    after_hashes = _audio_hashes(samples)
    _require(after_hashes, before_hashes, "retained WAV hashes after ASR")
    _require(
        after_hashes,
        {key: value["audio_sha256"] for key, value in EXPECTED_SAMPLE_BINDINGS.items()},
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
            "unchanged": PROFILE.BASE.sha256_file(input_path) == EXPECTED_INPUT_SHA256,
        },
        "asr_prior_prompted_run": copy.deepcopy(evidence["asr"]),
        "asr": {
            "status": "PASS" if passed else "FAIL",
            "mode": "ASR_ONLY_RETAINED_HASH_BOUND_AUDIO",
            "audio_derived": True,
            "model": PROFILE.BASE.WHISPER_MODEL,
            "model_sha256": PROFILE.WHISPER_SHA256,
            "repair_fingerprint": fingerprint,
            "score_min": ASR_SCORE_MIN,
            "coverage_min": ASR_COVERAGE_MIN,
            "reports": selected,
        },
        "asr_repair": {
            "completed": True,
            "repair_fingerprint": fingerprint,
            "fingerprint_closed": True,
            "prior_config_fingerprint": EXPECTED_PRIOR_ASR_FINGERPRINT,
            "prior_transcript_hashes": EXPECTED_PRIOR_TRANSCRIPT_HASHES,
            "decoder_arms": DECODING_ARMS,
            "equivalence_policy": EQUIVALENCE_POLICY,
            "forbidden_normalizations": [
                "do/de",
                "in/and",
                "trailing Thank you",
                "duplicated it",
            ],
            "all_candidates": candidates,
            "selected_decoder_by_passage": {
                str(item["passage_id"]): str(item["decoder_arm"]) for item in selected
            },
            "retained_audio_hashes_before": before_hashes,
            "retained_audio_hashes_after": after_hashes,
            "retained_audio_immutable": before_hashes == after_hashes,
            "resynthesis_performed": False,
            "audio_edit_or_trim_performed": False,
            "unexpected_speech_deleted_or_normalized": False,
        },
        "safety": {
            **evidence["safety"],
            "audio_generated_during_repair": False,
            "resynthesis_performed": False,
            "audio_edit_or_trim_performed": False,
            "asr_only_repair": True,
            "provider_calls_during_repair": 0,
            "listening_provider_calls": 0,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_approved": False,
            "paid_tts_lock_touched_during_repair": False,
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
                else "Use a materially different voice/provider or validate source-bound narration; do not repeat this synthesis or ASR-repair fingerprint."
            ),
        },
        "blockers_to_release": [
            *([] if passed else ["REPRESENTATIVE_ASR_REPAIR_FAILED"]),
            "INDEPENDENT_LISTENING_QA_NOT_RUN",
            "FULL_TITLE_NOT_GENERATED",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "LAST_LEAF_TITLE_SCOPED_PRODUCTION_RISK_ACCEPTANCE_NOT_BOUND",
            "EDITORIAL_PRONUNCIATION_REVIEW_NOT_RUN",
            "PRIVATE_DELIVERY_MANIFEST_NOT_COMPLETE",
            "UPLOAD_ENDPOINT_BROWSER_GATES_NOT_RUN",
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
            args.input.resolve(),
            args.output.resolve(),
            args.whisper_cache.resolve(),
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
                        else (result.get("asr_repair") or {}).get("retained_audio_immutable")
                    ),
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
    except (LastLeafASRRepairError, PROFILE.BASE.KokoroTitlePilotError) as exc:
        print(json.dumps({"status": "BLOCKED_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
