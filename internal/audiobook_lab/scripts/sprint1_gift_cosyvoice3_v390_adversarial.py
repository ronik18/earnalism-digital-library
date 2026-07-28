#!/usr/bin/env python3
"""Run one private, hash-bound CosyVoice3 adversarial Gift sample.

The runner is deliberately incapable of expansion or publication. It verifies
the controlled source section, the one-sample reopening decision, every local
model component, the Apache-2.0 runtime, the current paid-work lock, and the
attempt fingerprint before writing one private WAV. It then runs source-blind
local ASR. No reference recording, provider call, upload, public metadata
mutation, release-gate mutation, or listening judgment is permitted.
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


SCHEMA = "earnalism.gift_cosyvoice3_v390_adversarial.v1"
SLUG = "the-gift-of-the-magi"
TITLE = "The Gift of the Magi"
AUTHOR = "O. Henry"
SECTION_INDEX = 13
MODEL_ID = "aufklarer/CosyVoice3-0.5B-MLX-bf16"
MODEL_REVISION = "9b210b2381280b3af1c631d474a250e3e46d7017"
RUNTIME_VERSION = "0.0.23"
RUNTIME_SHA256 = "5e5866f18eb07666ae01ce909fc9699990b31182e79fdadc61ec15875231db50"
REOPENING_SHA256 = "f31617c4caad511193ccf7f24d3fc8abb8e2b479a2a9e429e52da9d1d5e71070"
RECOVERABLE_OUTPUT_SHA256 = (
    "8268ddeb2b83f7e2ab817319e118a73d819ecf9c05580434365abcaa6d6fb2b6"
)
MODEL_FILE_HASHES = {
    "config.json": "b6409141dd25b32d45f1c9aedb8d1b8cebe63cf65ea9193d5358ebf4978f9607",
    "flow.safetensors": "f1685d7e476295b104a675aa7e25a2572d5858879a4be0dfdd25253215b8e3d4",
    "flow_noise.bin": "3ebc526a5163d79f14b760e978e05e86dc83d9685f24a537a494cb1a5cf06c6f",
    "hifigan.safetensors": "840350956a8403245c738504a0da2a0c2047d5e705173930030013f28d4e3a1e",
    "llm.safetensors": "7d40340e3feda51dfe10137bf12690a512a1092d2eccf3b9605357a895c9ba2b",
    "speech_tokenizer.safetensors": "a3b9b816756469673efe84af9190f6cac4a8946cd7a113b76a35375daaea0e26",
    "tokenizer_config.json": "482bd979881423375ca5414e4e0d94cd7c5349dbb17fffd46b4d36d71e62a1bc",
    "vocab.json": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
    "merges.txt": "ac8ff86a72bee70828fbc1119bc4398c6f3a9a6e490d7b0dbe917be025478bd0",
}
SETTINGS = {
    "engine": "cosyvoice",
    "language": "english",
    "seed": 20260728,
    "voice_reference": None,
    "voice_kind": "MODEL_DEFAULT_SYNTHETIC_VOICE_NO_REFERENCE_AUDIO",
    "style_instruction": None,
}
SAMPLE_RATE = 24_000
DEFAULT_MODEL_DIR = Path(
    "/Users/ronikbasak/Library/Caches/qwen3-speech/models/aufklarer/"
    "CosyVoice3-0.5B-MLX-bf16"
)
DEFAULT_PRIVATE_DIR = Path(tempfile.gettempdir()) / (
    "earnalism-cosyvoice3-private/gift-v390-section13"
)
DEFAULT_OUTPUT = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_cosyvoice3_bf16_v390_section13_20260728.json"
)
DEFAULT_REOPENING = ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_cosyvoice3_reopening_v1.json"
)
DEFAULT_PAID_LOCK = common.DEFAULT_PAID_LOCK
DEFAULT_WHISPER_CACHE = common.DEFAULT_WHISPER_CACHE
NO_REPEAT_FILES = common.NO_REPEAT_FILES + (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-gift-of-the-magi_release_gate_evidence.json",
)


class GiftCosyVoiceError(RuntimeError):
    """Raised when the exact one-sample contract cannot be preserved."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GiftCosyVoiceError(message)


def sha256_file(path: Path) -> str:
    return common.sha256_file(path)


def canonical_hash(value: Any) -> str:
    return common.canonical_hash(value)


def evidence_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def verify_hash(path: Path, expected: str, label: str) -> None:
    require(path.is_file(), f"{label} is missing: {path}")
    observed = sha256_file(path)
    require(
        observed == expected,
        f"{label} SHA-256 mismatch: expected {expected}, observed {observed}",
    )


def command_for(
    *,
    speech_bin: Path,
    model_dir: Path,
    output: Path,
    text: str,
) -> list[str]:
    return [
        str(speech_bin),
        "speak",
        "--engine",
        "cosyvoice",
        "--model-id",
        MODEL_ID,
        "--cosy-bundle-dir",
        str(model_dir),
        "--language",
        "english",
        "--seed",
        str(SETTINGS["seed"]),
        "--output",
        str(output),
        text,
    ]


def wav_metrics(path: Path) -> dict[str, Any]:
    try:
        import numpy as np  # noqa: PLC0415
        import soundfile as sf  # noqa: PLC0415
    except ImportError as exc:
        raise GiftCosyVoiceError("numpy and soundfile are required") from exc
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="int16", always_2d=True)
    require(rate == SAMPLE_RATE, f"unexpected sample rate: {rate}")
    require(data.shape[1] == 1, f"unexpected channel count: {data.shape[1]}")
    require(info.subtype == "PCM_16", f"unexpected WAV subtype: {info.subtype}")
    require(data.shape[0] > 0, "empty CosyVoice WAV")
    samples = data[:, 0].astype(np.int64)
    absolute = np.abs(samples)
    peak = int(absolute.max())
    clipped = int(np.count_nonzero(absolute >= 32760))
    rms = float(np.sqrt(np.mean(np.square(samples))))
    frames = int(samples.shape[0])
    return {
        "sample_rate_hz": rate,
        "channels": 1,
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
    model_dir: Path,
    speech_bin: Path,
) -> dict[str, Any]:
    return {
        "contract": SCHEMA,
        "slug": SLUG,
        "full_source_sha256": gift.FULL_SOURCE_SHA256,
        "section_id": section["passage_id"],
        "section_text_sha256": section["text_sha256"],
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_files": MODEL_FILE_HASHES,
        "model_dir": str(model_dir.resolve()),
        "runtime_version": RUNTIME_VERSION,
        "runtime_sha256": RUNTIME_SHA256,
        "runtime_path": str(speech_bin.resolve()),
        "settings": SETTINGS,
        "reopening_sha256": REOPENING_SHA256,
        "asr_model": gift.WHISPER_MODEL,
        "asr_model_sha256": gift.WHISPER_SHA256,
        "asr_settings": gift.ASR_SETTINGS,
        "scope": "private_single_adversarial_no_upload_or_publication",
    }


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    for path in NO_REPEAT_FILES:
        if path.is_file():
            require(
                fingerprint
                not in set(common._fingerprints(common.read_json(path))),
                f"attempt fingerprint already exists in {path}",
            )
    if output.is_file():
        prior = common.read_json(output)
        require(
            not (
                (prior.get("engine") or {}).get("attempt_fingerprint")
                == fingerprint
                and (prior.get("safety") or {}).get("audio_generated") is True
            ),
            "this exact CosyVoice3 attempt already generated audio",
        )


def verify_inputs(
    *,
    asset_root: Path,
    reopening: Path,
    model_dir: Path,
    whisper_cache: Path,
    paid_lock: Path,
    speech_bin: Path,
    output: Path,
) -> tuple[dict[str, Any], str]:
    _chapter, _manuscript, sections = gift.controlled_source(asset_root)
    selected = [
        section for section in sections if section["section_index"] == SECTION_INDEX
    ]
    require(len(selected) == 1, "controlled section-013 is missing")
    section = selected[0]
    verify_hash(reopening, REOPENING_SHA256, "CosyVoice reopening decision")
    decision = common.read_json(reopening)
    require(
        decision.get("decision")
        == "AUTHORIZE_ONE_PRIVATE_COSYVOICE3_BF16_ADVERSARIAL_SAMPLE",
        "CosyVoice reopening decision changed",
    )
    require(
        (decision.get("exact_scope") or {}).get("maximum_generated_samples") == 1,
        "CosyVoice reopening is not one-sample bounded",
    )
    for filename, digest in MODEL_FILE_HASHES.items():
        verify_hash(model_dir / filename, digest, f"CosyVoice {filename}")
    verify_hash(speech_bin, RUNTIME_SHA256, "speech runtime")
    verify_hash(
        whisper_cache / gift.representative.WHISPER_FILENAME,
        gift.WHISPER_SHA256,
        "Whisper medium.en",
    )
    lock_before = paid_lock.read_bytes()
    lock = common.read_json(paid_lock)
    require(lock.get("status") == "active", "paid_tts.lock is not active")
    require(lock.get("current_holder") == "none", "paid_tts.lock is held")
    require(
        lock.get("allowed_next_holders") == [],
        "paid_tts.lock has a scheduled holder",
    )
    fingerprint = canonical_hash(fingerprint_payload(section, model_dir, speech_bin))
    ensure_not_repeated(fingerprint, output)
    payload = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": "READY_FOR_PRIVATE_COSYVOICE3_ADVERSARIAL",
        "scope": {
            "slug": SLUG,
            "title": TITLE,
            "author": AUTHOR,
            "section_index": SECTION_INDEX,
            "private_only": True,
            "maximum_generated_samples": 1,
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
            "upstream_model": "FunAudioLLM/Fun-CosyVoice3-0.5B-2512",
            "upstream_model_license": "Apache-2.0",
            "mlx_conversion_license": "Apache-2.0",
            "runtime_license": "Apache-2.0",
            "reference_kind": SETTINGS["voice_kind"],
            "human_voice_reference_used": False,
            "commercial_use_status": "PERMITTED_BY_RECORDED_LICENSES",
        },
        "engine": {
            "family": "cosyvoice3-mlx-bf16-default-synthetic",
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "model_file_sha256": MODEL_FILE_HASHES,
            "runtime_version": RUNTIME_VERSION,
            "runtime_sha256": RUNTIME_SHA256,
            "settings": SETTINGS,
            "attempt_fingerprint": fingerprint,
        },
        "policy": {
            "reopening_path": evidence_path(reopening),
            "reopening_sha256": REOPENING_SHA256,
            "asr_source_score_min": 9.7,
            "coverage_min": 0.98,
            "ordinary_listening_min": 8.9,
            "anti_robotic_and_anti_choppy_min": 9.2,
            "confidence_min": 0.9,
            "fatal_flags_required_false": True,
        },
        "cost": {
            "new_model_download_bytes": 0,
            "tts_provider_cost_usd": 0.0,
            "asr_provider_cost_usd": 0.0,
            "listening_provider_calls": 0,
        },
        "safety": {
            "paid_tts_lock_path": str(paid_lock),
            "paid_tts_lock_sha256_before": hashlib.sha256(lock_before).hexdigest(),
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
            "EARNALISM_APPROVE_GIFT_COSYVOICE3_V390_ADVERSARIAL=true "
            "PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/"
            "sprint1_gift_cosyvoice3_v390_adversarial.py --execute"
        ),
        "_section_text": section["text"],
    }
    return payload, fingerprint


def run(
    payload: dict[str, Any],
    *,
    fingerprint: str,
    speech_bin: Path,
    model_dir: Path,
    private_dir: Path,
    whisper_cache: Path,
    paid_lock: Path,
) -> dict[str, Any]:
    require(
        os.environ.get("EARNALISM_APPROVE_GIFT_COSYVOICE3_V390_ADVERSARIAL")
        == "true",
        "EARNALISM_APPROVE_GIFT_COSYVOICE3_V390_ADVERSARIAL=true is required",
    )
    section_text = str(payload.pop("_section_text"))
    section = {**payload["source"]["section"], "text": section_text}
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
        completed = subprocess.run(
            command_for(
                speech_bin=speech_bin,
                model_dir=model_dir,
                output=output,
                text=section_text,
            ),
            check=False,
            capture_output=True,
            text=True,
            timeout=900,
        )
        require(
            completed.returncode == 0,
            f"CosyVoice3 failed: {completed.stderr.strip()[-4000:]}",
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
    lock_after = paid_lock.read_bytes()
    require(lock_after == lock_before, "paid_tts.lock changed during local execution")
    if metrics["objective_format_pass"] is not True:
        return {
            **payload,
            "generated_at": utc_now(),
            "status": "PRIVATE_COSYVOICE3_AUDIO_FORMAT_FAIL_CLOSED",
            "samples": [sample],
            "objective_qa": {
                "status": "NOT_RUN",
                "reason": "GENERATED_AUDIO_FORMAT_OR_CLIPPING_FAILURE",
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
                "GENERATED_AUDIO_FORMAT_OR_CLIPPING_FAILURE",
                "COSYVOICE3_GIFT_FAMILY_CLOSED",
                "ASR_AND_LISTENING_SKIPPED",
                "FULL_TITLE_NOT_AUTHORIZED",
            ],
            "next_exact_command": "Keep Gift audio hidden; do not repeat this fingerprint.",
        }
    asr = gift.run_asr([sample], [section], whisper_cache, fingerprint)
    objective_pass = asr.get("status") == "PASS"
    return {
        **payload,
        "generated_at": utc_now(),
        "status": (
            "PRIVATE_COSYVOICE3_ADVERSARIAL_OBJECTIVE_PASS_LISTENING_PENDING"
            if objective_pass
            else "PRIVATE_COSYVOICE3_ADVERSARIAL_OBJECTIVE_FAIL_AUDIO_HIDDEN"
        ),
        "samples": [sample],
        "objective_qa": asr,
        "release_eligible": False,
        "safety": {
            **payload["safety"],
            "paid_tts_lock_sha256_after": hashlib.sha256(lock_after).hexdigest(),
            "paid_tts_lock_unchanged": True,
            "audio_generated": True,
            "recovered_existing_output": recovered_existing_output,
            "recovered_audio_sha256": RECOVERABLE_OUTPUT_SHA256,
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
                "COSYVOICE3_GIFT_FAMILY_CLOSED",
                "FULL_TITLE_NOT_AUTHORIZED",
            ]
        ),
        "next_exact_command": (
            "Create one independent, lock-safe listening packet for this exact sample."
            if objective_pass
            else "Keep Gift audio hidden; do not repeat this fingerprint."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--reopening", type=Path, default=DEFAULT_REOPENING)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
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
            reopening=args.reopening.resolve(),
            model_dir=args.model_dir.resolve(),
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
                model_dir=args.model_dir.resolve(),
                private_dir=args.private_dir.resolve(),
                whisper_cache=args.whisper_cache.resolve(),
                paid_lock=args.paid_lock.resolve(),
            )
        else:
            payload.pop("_section_text", None)
        common.write_json(args.output.resolve(), payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        if not args.execute:
            return 0
        return 0 if (payload.get("objective_qa") or {}).get("status") == "PASS" else 2
    except (
        OSError,
        subprocess.SubprocessError,
        GiftCosyVoiceError,
        common.GiftVoxCPM2Error,
        gift.GiftFullTitleError,
        gift.representative.KokoroTitlePilotError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
