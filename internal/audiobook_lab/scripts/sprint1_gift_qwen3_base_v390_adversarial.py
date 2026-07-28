#!/usr/bin/env python3
"""Run one private Qwen3-TTS Base v3.90 adversarial Gift sample.

This is a materially different lane from the closed Qwen3 1.7B VoiceDesign
attempt: it uses the Apache-2.0 0.6B Base MLX 8-bit voice-cloning checkpoint
and an AI-generated, non-person reference voice.  The exact controlled
section, local weights, reference audio, policy and Whisper model are
hash-bound before synthesis.

The runner performs local synthesis plus source-blind ASR only.  It cannot
call a listening provider, upload, publish, or mutate release truth.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
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
import sprint1_gift_voxcpm2_v390_representative as common  # noqa: E402


SCHEMA = "earnalism.gift_qwen3_base_v390_adversarial.v1"
SLUG = "the-gift-of-the-magi"
TITLE = "The Gift of the Magi"
AUTHOR = "O. Henry"
SECTION_INDEX = 13
MODEL_ID = "aufklarer/Qwen3-TTS-12Hz-0.6B-Base-MLX-8bit"
MODEL_REVISION = "2a20f4adf0436810367cea5a51aa7eb1bc50b6d8"
MODEL_SHA256 = "9488e7005cc0cf44f8804eb543668d0763bb1c649ce6f1eddc663519524b3182"
CONFIG_SHA256 = "cf55a8f542f56123b253833c77cde387c8953a1b9454c11c735880edeb835e39"
INDEX_SHA256 = "7829f1cc24f5cbd7d7a3ba888bb08c7cf52d82ba79a4f0f3756d41f8bf5e52b4"
README_SHA256 = "8af09ca57d099199574ac7c1bda32d7db0ce0d00f66928d9736000434c373aef"
REFERENCE_SHA256 = common.REFERENCE_SHA256
RECOVERABLE_OUTPUT_SHA256 = (
    "da573f24abea837e30a5a8b2ac9d1082f692c66661f17a2e3589840bd29729bf"
)
SAMPLE_RATE = 24_000
SETTINGS = {
    "engine": "qwen3",
    "model": "base-8bit",
    "language": "english",
    "temperature": 0.3,
    "top_k": 50,
    "max_tokens": 900,
    "voice_sample_only": True,
    "instruction": None,
}
DEFAULT_MODEL_DIR = Path(
    "/Users/ronikbasak/Library/Caches/qwen3-speech/models/aufklarer/"
    "Qwen3-TTS-12Hz-0.6B-Base-MLX-8bit"
)
DEFAULT_REFERENCE_AUDIO = common.DEFAULT_REFERENCE_AUDIO
DEFAULT_PRIVATE_DIR = Path(tempfile.gettempdir()) / (
    "earnalism-qwen3-base-private/gift-v390-section13"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_qwen3_base_8bit_v390_section13_20260727.json"
)
DEFAULT_PAID_LOCK = common.DEFAULT_PAID_LOCK
DEFAULT_WHISPER_CACHE = common.DEFAULT_WHISPER_CACHE
DEFAULT_POLICY_DECISION = common.DEFAULT_POLICY_DECISION
NO_REPEAT_FILES = common.NO_REPEAT_FILES


class GiftQwen3BaseError(RuntimeError):
    """Raised when the adversarial Qwen3 Base contract is not exact."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GiftQwen3BaseError(message)


def sha256_file(path: Path) -> str:
    return common.sha256_file(path)


def canonical_hash(value: Any) -> str:
    return common.canonical_hash(value)


def qwen_command(
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
        "qwen3",
        "--model",
        "base-8bit",
        "--language",
        "english",
        "--voice-sample",
        str(reference_audio),
        "--temperature",
        str(SETTINGS["temperature"]),
        "--top-k",
        str(SETTINGS["top_k"]),
        "--max-tokens",
        str(SETTINGS["max_tokens"]),
        "--output",
        str(output),
        text,
    ]


def wav_metrics(path: Path) -> dict[str, Any]:
    try:
        import numpy as np  # noqa: PLC0415
        import soundfile as sf  # noqa: PLC0415
    except ImportError as exc:
        raise GiftQwen3BaseError("numpy and soundfile are required") from exc
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="int16", always_2d=True)
    frames = int(data.shape[0])
    channels = int(data.shape[1])
    require(
        rate == SAMPLE_RATE
        and channels == 1
        and info.subtype == "PCM_16"
        and frames > 0,
        f"invalid Qwen3 private WAV: {path}",
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


def fingerprint_payload(
    section: Mapping[str, Any],
    reference_audio: Path,
) -> dict[str, Any]:
    return {
        "contract": SCHEMA,
        "slug": SLUG,
        "full_source_sha256": gift.FULL_SOURCE_SHA256,
        "section_id": section["passage_id"],
        "section_text_sha256": section["text_sha256"],
        "engine": "speech",
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_sha256": MODEL_SHA256,
        "config_sha256": CONFIG_SHA256,
        "index_sha256": INDEX_SHA256,
        "reference_audio_sha256": REFERENCE_SHA256,
        "reference_audio_path": str(reference_audio.resolve()),
        "settings": SETTINGS,
        "policy": common.POLICY_NAME,
        "policy_sha256": common.POLICY_DECISION_SHA256,
        "asr_model": gift.WHISPER_MODEL,
        "asr_model_sha256": gift.WHISPER_SHA256,
        "asr_settings": gift.ASR_SETTINGS,
        "scope": "private_single_adversarial_no_upload_or_publication",
    }


def attempt_fingerprint(
    section: Mapping[str, Any],
    reference_audio: Path,
) -> str:
    return canonical_hash(fingerprint_payload(section, reference_audio))


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    for path in NO_REPEAT_FILES:
        if path.is_file():
            require(
                fingerprint not in set(common._fingerprints(common.read_json(path))),
                f"attempt fingerprint already exists in {path}",
            )
    if output.is_file():
        prior = common.read_json(output)
        require(
            not (
                (prior.get("engine") or {}).get("attempt_fingerprint") == fingerprint
                and (prior.get("safety") or {}).get("audio_generated") is True
            ),
            "this exact Qwen3 Base attempt already generated audio",
        )


def verify_inputs(
    *,
    asset_root: Path,
    policy_decision: Path,
    model_dir: Path,
    reference_audio: Path,
    whisper_cache: Path,
    paid_lock: Path,
    speech_bin: Path,
    output: Path,
) -> tuple[dict[str, Any], str]:
    _chapter, _manuscript, sections = gift.controlled_source(asset_root)
    selected = [section for section in sections if section["section_index"] == SECTION_INDEX]
    require(len(selected) == 1, "controlled section-013 is missing")
    section = selected[0]
    common.validate_policy(policy_decision)
    common.verify_hash(reference_audio, REFERENCE_SHA256, "AI-generated reference audio")
    common.verify_hash(model_dir / "model.safetensors", MODEL_SHA256, "Qwen3 Base model")
    common.verify_hash(model_dir / "config.json", CONFIG_SHA256, "Qwen3 Base config")
    common.verify_hash(
        model_dir / "model.safetensors.index.json",
        INDEX_SHA256,
        "Qwen3 Base model index",
    )
    common.verify_hash(model_dir / "README.md", README_SHA256, "Qwen3 Base model card")
    model_card = (model_dir / "README.md").read_text(encoding="utf-8")
    require("license: apache-2.0" in model_card.lower(), "model card license changed")
    common.verify_hash(
        whisper_cache / gift.representative.WHISPER_FILENAME,
        gift.WHISPER_SHA256,
        "Whisper medium.en",
    )
    require(speech_bin.is_file() and os.access(speech_bin, os.X_OK), "speech binary unavailable")
    lock_raw = paid_lock.read_bytes()
    lock = common.read_json(paid_lock)
    require(lock.get("status") == "active", "paid_tts.lock is not active")
    require(lock.get("current_holder") == "none", "paid_tts.lock is held")
    require(lock.get("allowed_next_holders") == [], "paid_tts.lock has a scheduled holder")
    fingerprint = attempt_fingerprint(section, reference_audio)
    ensure_not_repeated(fingerprint, output)
    payload = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": "READY_FOR_PRIVATE_QWEN3_BASE_ADVERSARIAL",
        "scope": {
            "slug": SLUG,
            "title": TITLE,
            "author": AUTHOR,
            "section_index": SECTION_INDEX,
            "private_only": True,
            "materially_distinct_from_qwen3_voice_design": True,
        },
        "source": {
            "full_source_sha256": gift.FULL_SOURCE_SHA256,
            "normalized_source_sha256": gift.NORMALIZED_SOURCE_SHA256,
            "section": {
                key: section[key]
                for key in (
                    "passage_id",
                    "section_index",
                    "text_sha256",
                    "characters",
                    "word_count",
                )
            },
        },
        "rights": {
            "model_license": "Apache-2.0",
            "official_base_model": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "official_model_card": "https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            "mlx_model_card": f"https://huggingface.co/{MODEL_ID}",
            "reference_kind": "AI_GENERATED_NO_REAL_PERSON_REFERENCE",
        },
        "engine": {
            "family": "qwen3-tts-base-voice-clone",
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "model_sha256": MODEL_SHA256,
            "config_sha256": CONFIG_SHA256,
            "index_sha256": INDEX_SHA256,
            "reference_audio_path": str(reference_audio),
            "reference_audio_sha256": REFERENCE_SHA256,
            "settings": SETTINGS,
            "attempt_fingerprint": fingerprint,
            "fingerprint_payload_sha256": canonical_hash(
                fingerprint_payload(section, reference_audio)
            ),
        },
        "policy": {
            "name": common.POLICY_NAME,
            "decision_sha256": common.POLICY_DECISION_SHA256,
            "asr_source_score_min": 9.7,
            "coverage_min": 0.98,
            "overall_listening_score_min": 9.0,
            "fatal_flags_required_false": True,
        },
        "cost": {
            "model_download_bytes": 1_300_000_000,
            "tts_provider_cost_usd": 0.0,
            "asr_provider_cost_usd": 0.0,
            "listening_provider_calls": 0,
        },
        "safety": {
            "paid_tts_lock_path": str(paid_lock),
            "paid_tts_lock_sha256_before": hashlib.sha256(lock_raw).hexdigest(),
            "paid_tts_lock_touched": False,
            "audio_generated": False,
            "uploaded": False,
            "published": False,
            "release_gate_mutated": False,
            "public_audio_status": "AUDIO_HIDDEN",
        },
        "blockers_to_release": [
            "ADVERSARIAL_AUDIO_NOT_GENERATED",
            "OBJECTIVE_QA_NOT_RUN",
            "LISTENING_QA_NOT_RUN",
            "REPRESENTATIVE_EXPANSION_NOT_AUTHORIZED",
            "FULL_TITLE_NOT_AUTHORIZED",
            "DOWNSTREAM_DELIVERY_GATES_NOT_RUN",
        ],
        "next_exact_command": (
            "EARNALISM_APPROVE_GIFT_QWEN3_BASE_V390_ADVERSARIAL=true "
            "PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/"
            "sprint1_gift_qwen3_base_v390_adversarial.py --execute"
        ),
    }
    return {**payload, "_section_text": section["text"]}, fingerprint


def run(
    payload: dict[str, Any],
    *,
    fingerprint: str,
    speech_bin: Path,
    reference_audio: Path,
    private_dir: Path,
    whisper_cache: Path,
    paid_lock: Path,
) -> dict[str, Any]:
    require(
        os.environ.get("EARNALISM_APPROVE_GIFT_QWEN3_BASE_V390_ADVERSARIAL")
        == "true",
        "EARNALISM_APPROVE_GIFT_QWEN3_BASE_V390_ADVERSARIAL=true is required",
    )
    section_text = str(payload.pop("_section_text"))
    section = {
        **payload["source"]["section"],
        "text": section_text,
    }
    private = gift.assert_private_path(private_dir)
    private.mkdir(parents=True, exist_ok=True)
    output = private / "section-013.wav"
    lock_before = paid_lock.read_bytes()
    recovered_existing_output = output.is_file()
    if recovered_existing_output:
        require(
            sha256_file(output) == RECOVERABLE_OUTPUT_SHA256,
            f"unbound existing output refuses recovery: {output}",
        )
    else:
        command = qwen_command(
            speech_bin=speech_bin,
            reference_audio=reference_audio,
            output=output,
            text=section_text,
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
            f"Qwen3 Base failed: {completed.stderr.strip()[-4000:]}",
        )
    metrics = wav_metrics(output)
    sample = {
        "passage_id": section["passage_id"],
        "section_index": SECTION_INDEX,
        "source_text_sha256": section["text_sha256"],
        "characters": section["characters"],
        "word_count": section["word_count"],
        "audio_path": str(output),
        **metrics,
    }
    if metrics["objective_format_pass"] is not True:
        lock_after = paid_lock.read_bytes()
        require(lock_after == lock_before, "paid_tts.lock changed during local execution")
        return {
            **payload,
            "generated_at": utc_now(),
            "status": "PRIVATE_QWEN3_BASE_ADVERSARIAL_AUDIO_FORMAT_FAIL_CLOSED",
            "samples": [sample],
            "objective_qa": {
                "status": "NOT_RUN",
                "reason": "GENERATED_AUDIO_CLIPPING_EXCEEDS_ZERO_TOLERANCE",
                "asr_provider_cost_usd": 0.0,
                "listening_provider_cost_usd": 0.0,
            },
            "release_eligible": False,
            "safety": {
                **payload["safety"],
                "paid_tts_lock_sha256_after": hashlib.sha256(lock_after).hexdigest(),
                "paid_tts_lock_unchanged": True,
                "audio_generated": True,
                "recovered_existing_output": recovered_existing_output,
                "recovered_audio_sha256": RECOVERABLE_OUTPUT_SHA256,
            },
            "blockers_to_release": [
                "GENERATED_AUDIO_CLIPPING_EXCEEDS_ZERO_TOLERANCE",
                "QWEN3_BASE_GIFT_FAMILY_CLOSED",
                "ASR_AND_LISTENING_SKIPPED_TO_AVOID_WASTED_SPEND",
                "FULL_TITLE_NOT_AUTHORIZED",
                "DOWNSTREAM_DELIVERY_GATES_NOT_RUN",
            ],
            "next_exact_command": (
                "Create the source-bound professional narration/import packet for "
                "the-gift-of-the-magi; do not run another local-model audition."
            ),
        }
    asr = gift.run_asr([sample], [section], whisper_cache, fingerprint)
    lock_after = paid_lock.read_bytes()
    require(lock_after == lock_before, "paid_tts.lock changed during local execution")
    objective_pass = asr.get("status") == "PASS"
    return {
        **payload,
        "generated_at": utc_now(),
        "status": (
            "PRIVATE_QWEN3_BASE_ADVERSARIAL_OBJECTIVE_PASS_LISTENING_PENDING"
            if objective_pass
            else "PRIVATE_QWEN3_BASE_ADVERSARIAL_OBJECTIVE_FAIL_AUDIO_HIDDEN"
        ),
        "samples": [sample],
        "objective_qa": asr,
        "release_eligible": False,
        "safety": {
            **payload["safety"],
            "paid_tts_lock_sha256_after": hashlib.sha256(lock_after).hexdigest(),
            "paid_tts_lock_unchanged": True,
            "audio_generated": True,
        },
        "blockers_to_release": (
            [
                "ADVERSARIAL_LISTENING_QA_NOT_RUN",
                "REPRESENTATIVE_EXPANSION_NOT_AUTHORIZED",
                "FULL_TITLE_NOT_AUTHORIZED",
                "DOWNSTREAM_DELIVERY_GATES_NOT_RUN",
            ]
            if objective_pass
            else [
                "ADVERSARIAL_OBJECTIVE_QA_FAILED",
                "QWEN3_BASE_EXPANSION_STOPPED",
                "FULL_TITLE_NOT_AUTHORIZED",
                "DOWNSTREAM_DELIVERY_GATES_NOT_RUN",
            ]
        ),
        "next_exact_command": (
            "Create and run the one-sample Qwen3 Base v3.90 listening packet."
            if objective_pass
            else "Select a materially different commercially permitted model family."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--policy-decision", type=Path, default=DEFAULT_POLICY_DECISION)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--reference-audio", type=Path, default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument("--whisper-cache", type=Path, default=DEFAULT_WHISPER_CACHE)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    parser.add_argument("--private-dir", type=Path, default=DEFAULT_PRIVATE_DIR)
    parser.add_argument(
        "--speech-bin",
        type=Path,
        default=Path(shutil.which("speech") or "/opt/homebrew/bin/speech"),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload, fingerprint = verify_inputs(
            asset_root=args.asset_root.resolve(),
            policy_decision=args.policy_decision.resolve(),
            model_dir=args.model_dir.resolve(),
            reference_audio=args.reference_audio.resolve(),
            whisper_cache=args.whisper_cache.resolve(),
            paid_lock=args.paid_lock.resolve(),
            speech_bin=args.speech_bin.resolve(),
            output=args.output.resolve(),
        )
        if args.execute:
            payload = run(
                payload,
                fingerprint=fingerprint,
                speech_bin=args.speech_bin.resolve(),
                reference_audio=args.reference_audio.resolve(),
                private_dir=args.private_dir.resolve(),
                whisper_cache=args.whisper_cache.resolve(),
                paid_lock=args.paid_lock.resolve(),
            )
        else:
            payload.pop("_section_text", None)
        common.write_json(args.output.resolve(), payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if (not args.execute or payload["objective_qa"]["status"] == "PASS") else 2
    except (
        OSError,
        GiftQwen3BaseError,
        common.GiftVoxCPM2Error,
        gift.GiftFullTitleError,
        gift.representative.KokoroTitlePilotError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
