#!/usr/bin/env python3
"""Run a bounded VoxCPM2 v3.90 representative sample for Gift.

This runner exists to re-evaluate a materially distinct passage after the
owner-approved Sprint 1 v3.90 policy change.  It is deliberately private and
fail closed:

* the controlled manuscript, model weights, reference audio, policy and
  Whisper model are hash-bound;
* the default execution is one adversarial middle passage (section 13);
* no instruction or prompt-continuation controls are passed to VoxCPM2;
* audio-derived ASR and word timestamps are required immediately;
* no listening provider, upload, publication or release-gate mutation is
  possible.

A passing result only permits bounded listening QA and the remaining
representative passages.  It never authorizes a full-title generation or
public release by itself.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import sprint1_gift_kokoro_full_title_private_qa as gift  # noqa: E402


SCHEMA = "earnalism.gift_voxcpm2_v390_representative.v1"
SLUG = "the-gift-of-the-magi"
TITLE = "The Gift of the Magi"
AUTHOR = "O. Henry"
MODEL_ID = "aufklarer/VoxCPM2-MLX-int8"
MODEL_REVISION = "471a37b830ccf5e23fdb4c822649ec7c3b7320b4"
MODEL_SHA256 = "0b3d82c78fda5874333f3a6ae8c9b1dc9802d44932d2f822dd8accd490e33ed3"
REFERENCE_SHA256 = "188da386380ac30e4aad451522869a8bc616d2d8c03ff4b08451484088bc8461"
POLICY_NAME = "sprint1_audiobook_acceptance_v3_90"
POLICY_DECISION_SHA256 = "262095f60b80931b8946460c93defcc74e374b6151d53ca80dac8e93016a3ac3"
SPEECH_VERSION = "0.0.23"
SAMPLE_RATE = 48_000
REPRESENTATIVE_SECTION_INDICES = (1, 7, 13, 17, 18, 19)
DEFAULT_SECTION_INDICES = (13,)
RECOVERABLE_EXISTING_AUDIO_HASHES = {
    # The first accelerator-enabled run completed synthesis, then the generic
    # Kokoro validator rejected the valid 48 kHz WAV before evidence writing.
    # Reuse this immutable output rather than repeat the exact TTS fingerprint.
    "section-013": "785145a429cefb07ecef3239a9b602d4508dc27528dd28f4619a10900a1adb90",
}
SETTINGS = {
    "conditioning": "reference_audio_only",
    "variant": "int8",
    "cfg_value": 2.0,
    "timesteps": 10,
    "max_tokens": 2000,
    "min_tokens": 2,
    "instruction": None,
    "prompt_text": None,
    "prompt_audio": None,
}

DEFAULT_REFERENCE_AUDIO = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/kokoro/the-gift-of-the-magi/"
    "f3ff3571-af-bella-representative-v1/hair_sale_dialogue.wav"
)
DEFAULT_MODEL_CACHE = Path(
    "/Users/ronikbasak/Library/Caches/qwen3-speech/models/"
    "aufklarer/VoxCPM2-MLX-int8/model.safetensors"
)
DEFAULT_WHISPER_CACHE = Path("/Users/ronikbasak/.cache/whisper")
DEFAULT_PRIVATE_DIR = Path(tempfile.gettempdir()) / (
    "earnalism-voxcpm2-private/gift-v390-representative"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_voxcpm2_int8_v390_section13_20260727.json"
)
DEFAULT_POLICY_DECISION = ROOT / (
    "internal/earnalism_intelligence/"
    "sprint1_audiobook_acceptance_v3_90_policy_decision.json"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/"
    "internal/earnalism_intelligence/locks/paid_tts.lock"
)
NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/earnalism_intelligence/bengali_audiobook_campaign_state.json",
)


class GiftVoxCPM2Error(RuntimeError):
    """Raised when the bounded representative contract is not exact."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GiftVoxCPM2Error(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GiftVoxCPM2Error(f"Invalid JSON: {path}") from exc
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def verify_hash(path: Path, expected: str, label: str) -> None:
    require(path.is_file(), f"{label} is missing: {path}")
    observed = sha256_file(path)
    require(
        observed == expected,
        f"{label} SHA-256 mismatch: expected {expected}, observed {observed}",
    )


def parse_section_indices(raw: str) -> tuple[int, ...]:
    try:
        values = tuple(dict.fromkeys(int(item.strip()) for item in raw.split(",")))
    except ValueError as exc:
        raise GiftVoxCPM2Error("section indices must be comma-separated integers") from exc
    require(bool(values), "at least one section index is required")
    invalid = sorted(set(values) - set(REPRESENTATIVE_SECTION_INDICES))
    require(
        not invalid,
        "non-representative section index requested: "
        + ", ".join(str(value) for value in invalid),
    )
    return values


def select_sections(
    sections: Sequence[Mapping[str, Any]],
    indices: Sequence[int],
) -> list[dict[str, Any]]:
    by_index = {int(section["section_index"]): dict(section) for section in sections}
    selected = [by_index[index] for index in indices if index in by_index]
    require(len(selected) == len(indices), "controlled representative section missing")
    return selected


def validate_policy(path: Path) -> dict[str, Any]:
    verify_hash(path, POLICY_DECISION_SHA256, "Sprint 1 v3.90 policy decision")
    policy = read_json(path)
    gate = policy.get("listening_gate") or {}
    objective = policy.get("objective_gates_unchanged") or {}
    require(policy.get("status") == "ACTIVE_BY_OWNER_POLICY_UPDATE", "v3.90 policy is not active")
    require(policy.get("policy_name") == POLICY_NAME, "v3.90 policy name changed")
    require(float(gate.get("overall_listening_score_min") or 0) == 9.0, "overall listening floor changed")
    require(float(gate.get("confidence_score_min") or 0) == 0.9, "confidence floor changed")
    require(float(gate.get("per_dimension_score_min") or 0) == 8.9, "per-dimension floor changed")
    require(float(gate.get("anti_robotic_texture_score_min") or 0) == 9.2, "anti-robotic floor changed")
    require(float(gate.get("anti_choppy_join_score_min") or 0) == 9.2, "anti-choppy floor changed")
    require(gate.get("fatal_flags_required_false") is True, "fatal-flag policy changed")
    require(float(objective.get("asr_manuscript_score_min") or 0) == 9.7, "ASR floor changed")
    require(float(objective.get("coverage_min") or 0) == 0.98, "coverage floor changed")
    require(objective.get("ordered_content_integrity_required") is True, "ordered-content gate changed")
    require(objective.get("measured_sync_required") is True, "measured sync gate changed")
    require(objective.get("estimated_sync_forbidden") is True, "estimated-sync prohibition changed")
    return policy


def fingerprint_payload(
    sections: Sequence[Mapping[str, Any]],
    reference_audio: Path,
) -> dict[str, Any]:
    return {
        "contract": SCHEMA,
        "slug": SLUG,
        "source_sha256": gift.FULL_SOURCE_SHA256,
        "section_hashes": {
            section["passage_id"]: section["text_sha256"]
            for section in sections
        },
        "engine": "speech",
        "engine_version": SPEECH_VERSION,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_sha256": MODEL_SHA256,
        "reference_audio_sha256": REFERENCE_SHA256,
        "reference_audio_path": str(reference_audio.resolve()),
        "settings": SETTINGS,
        "policy_name": POLICY_NAME,
        "policy_decision_sha256": POLICY_DECISION_SHA256,
        "asr_model": gift.WHISPER_MODEL,
        "asr_model_sha256": gift.WHISPER_SHA256,
        "asr_settings": gift.ASR_SETTINGS,
        "synthesis_implementation_sha256": hashlib.sha256(
            inspect.getsource(synthesize).encode("utf-8")
        ).hexdigest(),
        "scope": "private_bounded_representative_no_upload_or_publication",
    }


def attempt_fingerprint(
    sections: Sequence[Mapping[str, Any]],
    reference_audio: Path,
) -> str:
    return canonical_hash(fingerprint_payload(sections, reference_audio))


def _fingerprints(value: Any, key: str = "") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for child_key, child in value.items():
            matches.extend(_fingerprints(child, str(child_key)))
    elif isinstance(value, list):
        for child in value:
            matches.extend(_fingerprints(child, key))
    elif "fingerprint" in key.lower() and isinstance(value, str):
        matches.append(value)
    return matches


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    for path in NO_REPEAT_FILES:
        if path.is_file():
            require(
                fingerprint not in set(_fingerprints(read_json(path))),
                f"attempt fingerprint already exists in {path}",
            )
    if output.is_file():
        prior = read_json(output)
        prior_fingerprint = str((prior.get("engine") or {}).get("attempt_fingerprint") or "")
        generated = bool((prior.get("safety") or {}).get("audio_generated"))
        require(
            not (prior_fingerprint == fingerprint and generated),
            "this exact representative attempt already generated audio",
        )


def recover_bound_preflight(
    output: Path,
    sections: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    """Recover an immutable preflight when synthesis finished before writing."""

    if not output.is_file():
        return {}
    prior = read_json(output)
    if prior.get("status") != "READY_FOR_PRIVATE_VOXCPM2_REPRESENTATIVE":
        return {}
    engine = prior.get("engine") or {}
    safety = prior.get("safety") or {}
    source = prior.get("source") or {}
    expected_sections = [
        {
            key: section[key]
            for key in (
                "passage_id",
                "section_index",
                "text_sha256",
                "characters",
                "word_count",
            )
        }
        for section in sections
    ]
    require(source.get("sections") == expected_sections, "recovery preflight source changed")
    require(engine.get("model_sha256") == MODEL_SHA256, "recovery preflight model changed")
    require(engine.get("reference_audio_sha256") == REFERENCE_SHA256, "recovery reference changed")
    require(engine.get("settings") == SETTINGS, "recovery settings changed")
    require(safety.get("audio_generated") is False, "recovery preflight already generated")
    fingerprint = str(engine.get("attempt_fingerprint") or "")
    payload_hash = str(engine.get("fingerprint_payload_sha256") or "")
    require(len(fingerprint) == 64 and len(payload_hash) == 64, "recovery fingerprint missing")
    return {
        "attempt_fingerprint": fingerprint,
        "fingerprint_payload_sha256": payload_hash,
        "preflight_sha256": sha256_file(output),
    }


def speech_command(
    *,
    speech_bin: Path,
    reference_audio: Path,
    output: Path,
    text: str,
) -> list[str]:
    return [
        str(speech_bin),
        "speak",
        "--engine",
        "voxcpm2",
        "--voxcpm2-variant",
        "int8",
        "--voxcpm2-ref-audio",
        str(reference_audio),
        "--voxcpm2-cfg-value",
        str(SETTINGS["cfg_value"]),
        "--voxcpm2-timesteps",
        str(SETTINGS["timesteps"]),
        "--voxcpm2-max-tokens",
        str(SETTINGS["max_tokens"]),
        "--voxcpm2-min-tokens",
        str(SETTINGS["min_tokens"]),
        "--output",
        str(output),
        text,
    ]


def wav_metrics(path: Path) -> dict[str, Any]:
    """Validate the native VoxCPM2 48 kHz PCM output without resampling."""

    try:
        import numpy as np  # noqa: PLC0415
        import soundfile as sf  # noqa: PLC0415
    except ImportError as exc:
        raise GiftVoxCPM2Error("numpy and soundfile are required") from exc
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="int16", always_2d=True)
    frames = int(data.shape[0])
    channels = int(data.shape[1])
    require(
        rate == SAMPLE_RATE
        and channels == 1
        and info.subtype == "PCM_16"
        and frames > 0,
        f"invalid VoxCPM2 private WAV format: {path}",
    )
    samples = data[:, 0].astype(np.int64)
    absolute = np.abs(samples)
    peak = int(absolute.max())
    clipped = int(np.count_nonzero(absolute >= 32760))
    rms = float(np.sqrt(np.mean(np.square(samples))))
    return {
        "sample_rate_hz": rate,
        "channels": channels,
        "sample_width_bytes": 2,
        "duration_seconds": round(frames / rate, 6),
        "size_bytes": path.stat().st_size,
        "audio_sha256": sha256_file(path),
        "peak_fraction": round(peak / 32767, 6),
        "rms_fraction": round(rms / 32767, 6),
        "clipped_sample_fraction": round(clipped / frames, 8),
        "objective_format_pass": bool(
            clipped == 0 and peak > 0 and rms / 32767 >= 0.001
        ),
    }


def synthesize(
    *,
    sections: Sequence[Mapping[str, Any]],
    speech_bin: Path,
    reference_audio: Path,
    private_dir: Path,
) -> list[dict[str, Any]]:
    private_dir = gift.assert_private_path(private_dir)
    private_dir.mkdir(parents=True, exist_ok=True)
    samples: list[dict[str, Any]] = []
    for section in sections:
        output = private_dir / f"{section['passage_id']}.wav"
        recovered = False
        if output.is_file():
            expected = RECOVERABLE_EXISTING_AUDIO_HASHES.get(
                str(section["passage_id"])
            )
            require(
                bool(expected) and sha256_file(output) == expected,
                f"unbound existing audio refuses overwrite: {output}",
            )
            recovered = True
        else:
            command = speech_command(
                speech_bin=speech_bin,
                reference_audio=reference_audio,
                output=output,
                text=str(section["text"]),
            )
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=900,
            )
            require(
                completed.returncode == 0,
                f"VoxCPM2 failed for {section['passage_id']}: "
                f"{completed.stderr.strip()[-4000:]}",
            )
        require(output.is_file() and output.stat().st_size > 44, f"missing WAV: {output}")
        metrics = wav_metrics(output)
        require(
            metrics.get("objective_format_pass") is True,
            f"invalid generated WAV: {section['passage_id']}",
        )
        samples.append(
            {
                "passage_id": section["passage_id"],
                "section_index": section["section_index"],
                "source_text_sha256": section["text_sha256"],
                "characters": section["characters"],
                "word_count": section["word_count"],
                "recovered_after_validator_repair": recovered,
                "audio_path": str(output),
                **metrics,
            }
        )
    return samples


def preflight(
    *,
    asset_root: Path,
    policy_decision: Path,
    reference_audio: Path,
    model_cache: Path,
    whisper_cache: Path,
    speech_bin: Path,
    paid_lock: Path,
    output: Path,
    section_indices: Sequence[int],
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    _chapter, _manuscript, all_sections = gift.controlled_source(asset_root)
    sections = select_sections(all_sections, section_indices)
    policy = validate_policy(policy_decision)
    verify_hash(reference_audio, REFERENCE_SHA256, "AI-generated reference audio")
    verify_hash(model_cache, MODEL_SHA256, "VoxCPM2 int8 model")
    verify_hash(
        whisper_cache / gift.representative.WHISPER_FILENAME,
        gift.WHISPER_SHA256,
        "Whisper medium.en model",
    )
    require(speech_bin.is_file() and os.access(speech_bin, os.X_OK), f"speech binary is not executable: {speech_bin}")
    lock_before = paid_lock.read_bytes()
    lock = read_json(paid_lock)
    require(lock.get("status") == "active", "paid_tts.lock is not active")
    require(lock.get("current_holder") == "none", "paid_tts.lock is held")
    require(lock.get("allowed_next_holders") == [], "paid_tts.lock has a scheduled holder")
    recovery = recover_bound_preflight(output, sections)
    calculated_fingerprint = attempt_fingerprint(sections, reference_audio)
    fingerprint = recovery.get("attempt_fingerprint", calculated_fingerprint)
    fingerprint_payload_sha256 = recovery.get(
        "fingerprint_payload_sha256",
        canonical_hash(fingerprint_payload(sections, reference_audio)),
    )
    ensure_not_repeated(fingerprint, output)
    payload = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": "READY_FOR_PRIVATE_VOXCPM2_REPRESENTATIVE",
        "scope": {
            "slug": SLUG,
            "title": TITLE,
            "author": AUTHOR,
            "private_only": True,
            "section_indices": list(section_indices),
            "representative_section_indices": list(REPRESENTATIVE_SECTION_INDICES),
            "adversarial_fail_fast": tuple(section_indices) == DEFAULT_SECTION_INDICES,
        },
        "source": {
            "full_source_sha256": gift.FULL_SOURCE_SHA256,
            "normalized_source_sha256": gift.NORMALIZED_SOURCE_SHA256,
            "sections": [
                {
                    key: section[key]
                    for key in (
                        "passage_id",
                        "section_index",
                        "text_sha256",
                        "characters",
                        "word_count",
                    )
                }
                for section in sections
            ],
        },
        "policy": {
            "path": str(policy_decision),
            "sha256": POLICY_DECISION_SHA256,
            "name": policy["policy_name"],
            "overall_listening_score_min": 9.0,
            "confidence_score_min": 0.9,
            "per_dimension_score_min": 8.9,
            "anti_robotic_texture_score_min": 9.2,
            "anti_choppy_join_score_min": 9.2,
            "fatal_flags_required_false": True,
            "asr_source_score_min": 9.7,
            "coverage_min": 0.98,
        },
        "engine": {
            "family": "open_weight_local_tts",
            "command": "speech speak",
            "version": SPEECH_VERSION,
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "model_sha256": MODEL_SHA256,
            "license": "Apache-2.0",
            "reference_kind": "AI_GENERATED_NO_REAL_PERSON_REFERENCE",
            "reference_audio_path": str(reference_audio),
            "reference_audio_sha256": REFERENCE_SHA256,
            "settings": SETTINGS,
            "attempt_fingerprint": fingerprint,
            "fingerprint_payload_sha256": fingerprint_payload_sha256,
            "recovered_preflight_sha256": recovery.get("preflight_sha256"),
            "current_runner_fingerprint": calculated_fingerprint,
        },
        "cost": {
            "tts_provider_cost_usd": 0.0,
            "asr_provider_cost_usd": 0.0,
            "listening_provider_calls": 0,
        },
        "safety": {
            "paid_tts_lock_path": str(paid_lock),
            "paid_tts_lock_sha256_before": sha256_bytes(lock_before),
            "paid_tts_lock_touched": False,
            "audio_generated": False,
            "uploaded": False,
            "published": False,
            "release_gate_mutated": False,
            "public_audio_status": "AUDIO_HIDDEN",
            "browser_or_system_speech_fallback": False,
        },
        "blockers_to_release": [
            "BOUNDED_REPRESENTATIVE_AUDIO_NOT_GENERATED",
            "REPRESENTATIVE_OBJECTIVE_QA_NOT_RUN",
            "REPRESENTATIVE_LISTENING_QA_NOT_RUN",
            "FULL_TITLE_NOT_AUTHORIZED",
            "DOWNSTREAM_DELIVERY_GATES_NOT_RUN",
        ],
        "next_exact_command": (
            "EARNALISM_APPROVE_GIFT_VOXCPM2_V390_REPRESENTATIVE=true "
            f"PYTHONDONTWRITEBYTECODE=1 {sys.executable} "
            "internal/audiobook_lab/scripts/"
            "sprint1_gift_voxcpm2_v390_representative.py --execute"
        ),
    }
    return payload, sections, fingerprint


def execute(
    payload: dict[str, Any],
    *,
    sections: Sequence[Mapping[str, Any]],
    fingerprint: str,
    speech_bin: Path,
    reference_audio: Path,
    private_dir: Path,
    whisper_cache: Path,
    paid_lock: Path,
) -> dict[str, Any]:
    require(
        os.environ.get("EARNALISM_APPROVE_GIFT_VOXCPM2_V390_REPRESENTATIVE") == "true",
        "EARNALISM_APPROVE_GIFT_VOXCPM2_V390_REPRESENTATIVE=true is required",
    )
    lock_before = paid_lock.read_bytes()
    samples = synthesize(
        sections=sections,
        speech_bin=speech_bin,
        reference_audio=reference_audio,
        private_dir=private_dir,
    )
    asr = gift.run_asr(samples, sections, whisper_cache, fingerprint)
    lock_after = paid_lock.read_bytes()
    require(lock_after == lock_before, "paid_tts.lock changed during local execution")
    objective_pass = asr.get("status") == "PASS"
    payload.update(
        {
            "generated_at": utc_now(),
            "status": (
                "PRIVATE_ADVERSARIAL_SAMPLE_OBJECTIVE_PASS_LISTENING_PENDING"
                if objective_pass
                else "PRIVATE_ADVERSARIAL_SAMPLE_OBJECTIVE_FAIL_AUDIO_HIDDEN"
            ),
            "samples": samples,
            "objective_qa": asr,
            "release_eligible": False,
            "safety": {
                **payload["safety"],
                "paid_tts_lock_sha256_after": sha256_bytes(lock_after),
                "paid_tts_lock_unchanged": True,
                "audio_generated": True,
            },
            "blockers_to_release": (
                [
                    "REPRESENTATIVE_LISTENING_QA_NOT_RUN",
                    "REMAINING_REPRESENTATIVE_PASSAGES_NOT_RUN",
                    "FULL_TITLE_NOT_AUTHORIZED",
                    "DOWNSTREAM_DELIVERY_GATES_NOT_RUN",
                ]
                if objective_pass
                else [
                    "REPRESENTATIVE_OBJECTIVE_QA_FAILED",
                    "VOXCPM2_V390_EXPANSION_STOPPED",
                    "FULL_TITLE_NOT_AUTHORIZED",
                    "DOWNSTREAM_DELIVERY_GATES_NOT_RUN",
                ]
            ),
            "next_exact_command": (
                "PYTHONDONTWRITEBYTECODE=1 python3 "
                "internal/audiobook_lab/scripts/"
                "sprint1_gift_voxcpm2_v390_listening_qa.py --preflight"
                if objective_pass
                else "Select a materially different commercially permitted narration family."
            ),
        }
    )
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--section-indices",
        default=",".join(str(value) for value in DEFAULT_SECTION_INDICES),
    )
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--policy-decision", type=Path, default=DEFAULT_POLICY_DECISION)
    parser.add_argument("--reference-audio", type=Path, default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument("--model-cache", type=Path, default=DEFAULT_MODEL_CACHE)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument(
        "--speech-bin",
        type=Path,
        default=Path(shutil.which("speech") or "/opt/homebrew/bin/speech"),
    )
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    parser.add_argument("--private-dir", type=Path, default=DEFAULT_PRIVATE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        indices = parse_section_indices(args.section_indices)
        payload, sections, fingerprint = preflight(
            asset_root=args.asset_root.resolve(),
            policy_decision=args.policy_decision.resolve(),
            reference_audio=args.reference_audio.resolve(),
            model_cache=args.model_cache.resolve(),
            whisper_cache=args.whisper_cache.resolve(),
            speech_bin=args.speech_bin.resolve(),
            paid_lock=args.paid_lock.resolve(),
            output=args.output.resolve(),
            section_indices=indices,
        )
        if args.execute:
            payload = execute(
                payload,
                sections=sections,
                fingerprint=fingerprint,
                speech_bin=args.speech_bin.resolve(),
                reference_audio=args.reference_audio.resolve(),
                private_dir=args.private_dir.resolve(),
                whisper_cache=args.whisper_cache.resolve(),
                paid_lock=args.paid_lock.resolve(),
            )
        write_json(args.output.resolve(), payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if (not args.execute or payload["objective_qa"]["status"] == "PASS") else 2
    except (
        GiftVoxCPM2Error,
        gift.GiftFullTitleError,
        gift.representative.KokoroTitlePilotError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
