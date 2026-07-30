#!/usr/bin/env python3
"""Generate one private, four-passage Indic Parler audition for Ginni.

This adapter is deliberately narrower than the audiobook production pipeline:

* it accepts only the four source-bound passages in the merged D19 packet;
* it loads only the pinned local model and tokenizer snapshots, offline;
* it consumes the exact attempt fingerprint before model loading;
* it writes PCM WAV files only under an approved private/temp directory;
* it records format, duration, byte-size, and SHA-256 evidence;
* it cannot run ASR, listening QA, sync estimation, upload, publication,
  release mutation, browser/system speech, or paid-provider work.

An execution failure consumes the fingerprint. Do not retry it; select a
materially different model, voice, prompt, settings, or passage contract.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import traceback
from typing import Any, Mapping, Sequence


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent


def _load_preflight():
    path = SCRIPT_DIR / "sprint1_d19_indic_parler_private_preflight.py"
    spec = importlib.util.spec_from_file_location(
        "earnalism_d19_indic_parler_preflight", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load D19 preflight module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREFLIGHT = _load_preflight()

SLUG = PREFLIGHT.SLUG
PROFILE = PREFLIGHT.PROFILE
MODEL_REVISION = PREFLIGHT.MODEL_REVISION
EXPECTED_ATTEMPT_FINGERPRINT = (
    "0a5d983bf199e0288557c80840402a00f9160e17e533e327fdf950d81006c05a"
)
EXPECTED_PASSAGE_IDS = (
    "opening_character_control",
    "satirical_punctuation",
    "play_scene_dialogue",
    "ending_emotional_release",
)

RUNTIME_ROOT = Path("/private/tmp/earnalism-d19-indic-parler-runtime")
RUNTIME_PACKAGES = {
    "torch": "2.13.0",
    "transformers": "4.46.1",
    "parler-tts": "0.2.2",
    "accelerate": "1.14.0",
    "scipy": "1.17.1",
    "soundfile": "0.14.0",
    "sentencepiece": "0.2.2",
    "huggingface-hub": "0.36.2",
    "numpy": "2.4.6",
    "safetensors": "0.8.0",
    "tokenizers": "0.20.3",
}

MODEL_SNAPSHOT = Path(
    "/Users/ronikbasak/.cache/huggingface/hub/"
    "models--ai4bharat--indic-parler-tts/snapshots/"
    f"{MODEL_REVISION}"
)
DESCRIPTION_TOKENIZER_REVISION = "0613663d0d48ea86ba8cb3d7a44f0f65dc596a2a"
DESCRIPTION_TOKENIZER_SNAPSHOT = Path(
    "/Users/ronikbasak/.cache/huggingface/hub/"
    "models--google--flan-t5-large/snapshots/"
    f"{DESCRIPTION_TOKENIZER_REVISION}"
)
DESCRIPTION_TOKENIZER_ARTIFACTS = {
    "special_tokens_map.json": {
        "size_bytes": 2_201,
        "sha256": "5c87151ef0f72a99d1f766a4c418bd2a1f90aaa30a8e22fe5eca9641daebb64f",
    },
    "spiece.model": {
        "size_bytes": 791_656,
        "sha256": "d60acb128cf7b7f2536e8f38a5b18a05535c9e14c7a355904270e15b0945ea86",
    },
    "tokenizer.json": {
        "size_bytes": 2_424_064,
        "sha256": "fe2ebbbbde2985be723e0ce18217853e4020c5e9d35bd07be2c27ab9d3ead57a",
    },
    "tokenizer_config.json": {
        "size_bytes": 2_539,
        "sha256": "5d19985330a9123285cc583fc60616d083aa9df7435812b5d8bb3e749f435d56",
    },
}

DEFAULT_PRIVATE_OUTPUT = Path(
    "/private/tmp/earnalism-d19-indic-parler-private-pilot-audio-v1"
)
DEFAULT_EVIDENCE_OUTPUT = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "book-d19e96859f_indic_parler_aditi_private_generation_v1.json"
)
ATTEMPT_MARKER_NAME = "attempt_manifest.json"
MAX_NEW_TOKENS_POLICY = "pinned_decoder_max_position_embeddings"
OUTPUT_SUBTYPE = "PCM_16"
MIN_DURATION_SECONDS = 1.0


class D19IndicParlerGeneratorError(RuntimeError):
    """Raised when the one-shot private generation contract is violated."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def canonical_sha256(value: Mapping[str, Any]) -> str:
    rendered = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _artifact_contract(
    root: Path, expected: Mapping[str, Mapping[str, Any]], label: str
) -> dict[str, dict[str, Any]]:
    resolved = root.expanduser().resolve()
    observed: dict[str, dict[str, Any]] = {}
    for relative, contract in expected.items():
        path = resolved / relative
        if not path.is_file():
            raise D19IndicParlerGeneratorError(f"{label} artifact missing: {relative}")
        size = path.stat().st_size
        digest = PREFLIGHT.sha256_file(path)
        if size != contract["size_bytes"] or digest != contract["sha256"]:
            raise D19IndicParlerGeneratorError(
                f"{label} artifact binding changed: {relative}"
            )
        observed[relative] = {"size_bytes": size, "sha256": digest}
    return observed


def _assert_exact_snapshot(path: Path, expected: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    expected_resolved = expected.expanduser().resolve()
    if resolved != expected_resolved:
        raise D19IndicParlerGeneratorError(
            f"{label} must be the exact pinned local snapshot: {expected_resolved}"
        )
    return resolved


def runtime_contract(*, require_exact_runtime: bool) -> dict[str, Any]:
    prefix = Path(sys.prefix).resolve()
    expected_prefix = RUNTIME_ROOT.resolve()
    packages: dict[str, str | None] = {}
    package_mismatches: list[str] = []
    for name, expected in RUNTIME_PACKAGES.items():
        try:
            observed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            observed = None
        packages[name] = observed
        if observed != expected:
            package_mismatches.append(f"{name}={observed!r} expected {expected!r}")

    runtime_matches = prefix == expected_prefix and not package_mismatches
    if require_exact_runtime and not runtime_matches:
        details = []
        if prefix != expected_prefix:
            details.append(f"sys.prefix={prefix}, expected {expected_prefix}")
        details.extend(package_mismatches)
        raise D19IndicParlerGeneratorError(
            "exact isolated runtime required: " + "; ".join(details)
        )

    try:
        import torch  # noqa: PLC0415

        mps_available = bool(
            getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
        )
    except ImportError:
        mps_available = False
    device = "mps" if mps_available else "cpu"
    contract = {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "sys_prefix": str(prefix),
        "packages": packages,
        "package_mismatches": package_mismatches,
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "device": device,
        "mps_available": mps_available,
        "deterministic_algorithms_required": True,
        "offline_model_loading_required": True,
        "runtime_matches_pinned_contract": runtime_matches,
    }
    return {**contract, "runtime_contract_sha256": canonical_sha256(contract)}


def _code_contract() -> dict[str, Any]:
    preflight_path = Path(PREFLIGHT.__file__).resolve()
    contract = {
        "generator_path": str(SCRIPT_PATH),
        "generator_sha256": PREFLIGHT.sha256_file(SCRIPT_PATH),
        "preflight_path": str(preflight_path),
        "preflight_sha256": PREFLIGHT.sha256_file(preflight_path),
    }
    return {**contract, "code_contract_sha256": canonical_sha256(contract)}


def _passage_contract(passages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    items = [
        {
            "ordinal": index,
            "passage_id": str(item["passage_id"]),
            "source_text_sha256": str(item["text_sha256"]),
            "characters": int(item["characters"]),
            "start_offset": int(item["start_offset"]),
            "end_offset": int(item["end_offset"]),
        }
        for index, item in enumerate(passages, start=1)
    ]
    observed_ids = tuple(item["passage_id"] for item in items)
    if observed_ids != EXPECTED_PASSAGE_IDS or len(items) != 4:
        raise D19IndicParlerGeneratorError(
            f"representative passage contract changed: {observed_ids}"
        )
    contract = {
        "source_sha256": PREFLIGHT.RAW_SOURCE_SHA256,
        "passage_count": 4,
        "representative_characters": PREFLIGHT.PASSAGE_CHARACTERS,
        "passages": items,
    }
    return {**contract, "passage_contract_sha256": canonical_sha256(contract)}


def _engine_contract(
    *,
    model_artifacts: Mapping[str, Any],
    description_tokenizer_artifacts: Mapping[str, Any],
) -> dict[str, Any]:
    contract = {
        "provider": "indic-parler-tts",
        "family": "open_source_local_tts",
        "model_repo": PREFLIGHT.MODEL_REPO,
        "model_revision": MODEL_REVISION,
        "model_artifacts": model_artifacts,
        "description_tokenizer_repo": "google/flan-t5-large",
        "description_tokenizer_revision": DESCRIPTION_TOKENIZER_REVISION,
        "description_tokenizer_artifacts": description_tokenizer_artifacts,
        "voice": PREFLIGHT.VOICE,
        "voice_description": PREFLIGHT.VOICE_DESCRIPTION,
        "generation_settings": PREFLIGHT.GENERATION_SETTINGS,
        "random_seed": PREFLIGHT.RANDOM_SEED,
        "max_new_tokens_policy": MAX_NEW_TOKENS_POLICY,
        "output_subtype": OUTPUT_SUBTYPE,
        "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
        "network_access_allowed": False,
        "browser_or_system_speech_fallback": False,
    }
    return {**contract, "engine_contract_sha256": canonical_sha256(contract)}


def build_execution_preflight(
    *,
    asset_root: Path,
    slug: str,
    profile: str,
    model_snapshot: Path,
    description_tokenizer_snapshot: Path,
    private_output_dir: Path,
    evidence_output: Path,
    require_exact_runtime: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    model_snapshot = _assert_exact_snapshot(
        model_snapshot, MODEL_SNAPSHOT, "model snapshot"
    )
    description_tokenizer_snapshot = _assert_exact_snapshot(
        description_tokenizer_snapshot,
        DESCRIPTION_TOKENIZER_SNAPSHOT,
        "description tokenizer snapshot",
    )
    private_dir = PREFLIGHT.assert_private_path(private_output_dir)
    if private_dir.exists() and any(private_dir.iterdir()):
        raise D19IndicParlerGeneratorError(
            f"private output already contains an attempted run: {private_dir}"
        )

    base = PREFLIGHT.build_preflight(
        asset_root=asset_root,
        slug=slug,
        profile=profile,
        private_output_dir=private_dir,
        output=evidence_output,
        model_snapshot_dir=model_snapshot,
        verify_runtime=True,
    )
    _chapter, _manuscript, passages, _covers = PREFLIGHT.controlled_source(
        asset_root, slug
    )
    observed_fingerprint = PREFLIGHT.attempt_fingerprint(passages)
    if observed_fingerprint != EXPECTED_ATTEMPT_FINGERPRINT:
        raise D19IndicParlerGeneratorError(
            "attempt fingerprint changed: "
            f"expected {EXPECTED_ATTEMPT_FINGERPRINT}, observed {observed_fingerprint}"
        )
    runtime = runtime_contract(require_exact_runtime=require_exact_runtime)
    model_artifacts = _artifact_contract(
        model_snapshot, PREFLIGHT.MODEL_ARTIFACTS, "model"
    )
    description_artifacts = _artifact_contract(
        description_tokenizer_snapshot,
        DESCRIPTION_TOKENIZER_ARTIFACTS,
        "description tokenizer",
    )
    code = _code_contract()
    passage = _passage_contract(passages)
    engine = _engine_contract(
        model_artifacts=model_artifacts,
        description_tokenizer_artifacts=description_artifacts,
    )
    generation_contract = {
        "schema": "earnalism.indic_parler.d19_private_generation_contract.v1",
        "slug": SLUG,
        "profile": PROFILE,
        "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
        "code_contract_sha256": code["code_contract_sha256"],
        "runtime_contract_sha256": runtime["runtime_contract_sha256"],
        "passage_contract_sha256": passage["passage_contract_sha256"],
        "engine_contract_sha256": engine["engine_contract_sha256"],
    }
    payload = {
        "schema": "earnalism.indic_parler.d19_private_generation.v1",
        "generated_at": utc_now(),
        "status": "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION",
        "go_no_go": "GO_PRIVATE_REPRESENTATIVE_ONLY",
        "scope": {
            "slug": SLUG,
            "title": PREFLIGHT.TITLE,
            "author": PREFLIGHT.AUTHOR,
            "language": PREFLIGHT.LANGUAGE,
            "profile": PROFILE,
            "representative_only": True,
            "passage_count": 4,
            "full_title_generation_allowed": False,
        },
        "source": {
            "raw_source_sha256": PREFLIGHT.RAW_SOURCE_SHA256,
            "passage_contract": passage,
        },
        "code": code,
        "runtime": runtime,
        "engine": engine,
        "generation_contract": {
            **generation_contract,
            "generation_contract_sha256": canonical_sha256(generation_contract),
        },
        "private_output_dir": str(private_dir),
        "samples": [],
        "objective_audio_format": {"status": "NOT_RUN", "reports": []},
        "asr": {"status": "NOT_RUN_BY_GENERATION_ADAPTER"},
        "listening_qa": {"status": "NOT_RUN_BY_GENERATION_ADAPTER"},
        "sync": {
            "status": "NOT_RUN_BY_GENERATION_ADAPTER",
            "estimated_sync_generated": False,
        },
        "safety": {
            "attempt_consumed": False,
            "executor_run": False,
            "audio_generated": False,
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "network_access_allowed": False,
            "browser_or_system_speech_fallback": False,
            "paid_tts_lock_inspected": False,
            "paid_tts_lock_touched": False,
            "asr_run": False,
            "listening_qa_run": False,
            "sync_generated": False,
            "upload_performed": False,
            "catalog_mutated": False,
            "release_gate_mutated": False,
            "publication_performed": False,
            "public_audio_status": "AUDIO_HIDDEN_NOT_PUBLIC",
        },
        "blockers_to_release": [
            "REPRESENTATIVE_AUDIO_GENERATION_NOT_EXECUTED",
            "REPRESENTATIVE_ASR_NOT_RUN",
            "INDEPENDENT_LISTENING_QA_NOT_RUN",
            "FULL_TITLE_NOT_GENERATED",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "PRIVATE_UPLOAD_CHECKSUM_NOT_RUN",
            "PRODUCTION_ENDPOINT_NOT_RUN",
            "BROWSER_PLAYBACK_GATE_NOT_RUN",
        ],
    }
    return payload, passages


def _write_attempt_marker(private_dir: Path, payload: Mapping[str, Any]) -> Path:
    private_dir.mkdir(parents=True, exist_ok=False)
    marker = private_dir / ATTEMPT_MARKER_NAME
    record = {
        "schema": "earnalism.indic_parler.private_attempt_marker.v1",
        "generated_at": utc_now(),
        "status": "EXECUTION_STARTED_FINGERPRINT_CONSUMED",
        "attempt_consumed": True,
        "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
        "generation_contract_sha256": payload["generation_contract"][
            "generation_contract_sha256"
        ],
        "retry_policy": "DO_NOT_RETRY_THIS_FINGERPRINT_AFTER_ANY_EXECUTION_RESULT",
    }
    PREFLIGHT.atomic_write_json(marker, record)
    return marker


def _select_device(torch: Any, expected: str) -> Any:
    observed = (
        "mps"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
        else "cpu"
    )
    if observed != expected:
        raise D19IndicParlerGeneratorError(
            f"execution device changed after preflight: {expected} -> {observed}"
        )
    return torch.device(observed)


def _seed_runtime(torch: Any, numpy: Any, device_name: str) -> None:
    random.seed(PREFLIGHT.RANDOM_SEED)
    numpy.random.seed(PREFLIGHT.RANDOM_SEED % (2**32))
    torch.manual_seed(PREFLIGHT.RANDOM_SEED)
    if device_name == "mps" and hasattr(torch, "mps"):
        torch.mps.manual_seed(PREFLIGHT.RANDOM_SEED)
    torch.use_deterministic_algorithms(True)


def _ffprobe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size,format_name:stream=codec_name,codec_type,"
        "sample_rate,channels,channel_layout,duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(
        command, text=True, capture_output=True, check=False, timeout=30
    )
    if result.returncode != 0:
        raise D19IndicParlerGeneratorError(
            f"ffprobe failed for {path.name}: {result.stderr.strip()[:240]}"
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise D19IndicParlerGeneratorError(
            f"ffprobe returned invalid JSON for {path.name}"
        ) from exc
    streams = [
        stream
        for stream in data.get("streams", [])
        if stream.get("codec_type") == "audio"
    ]
    if len(streams) != 1:
        raise D19IndicParlerGeneratorError(
            f"expected exactly one audio stream in {path.name}"
        )
    stream = streams[0]
    fmt = data.get("format") or {}
    duration = float(stream.get("duration") or fmt.get("duration") or 0.0)
    size = int(fmt.get("size") or path.stat().st_size)
    report = {
        "codec_name": str(stream.get("codec_name") or ""),
        "sample_rate_hz": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "channel_layout": str(stream.get("channel_layout") or ""),
        "duration_seconds": round(duration, 6),
        "size_bytes": size,
        "format_name": str(fmt.get("format_name") or ""),
    }
    if (
        report["codec_name"] != "pcm_s16le"
        or report["sample_rate_hz"] != 44_100
        or report["channels"] != 1
        or report["duration_seconds"] < MIN_DURATION_SECONDS
        or report["size_bytes"] != path.stat().st_size
    ):
        raise D19IndicParlerGeneratorError(
            f"objective WAV format failed for {path.name}: {report}"
        )
    return report


def _tensor_to_mono_float32(generation: Any, numpy: Any, passage_id: str) -> Any:
    audio = generation.detach().to("cpu").float().numpy().squeeze()
    if audio.ndim != 1 or audio.size == 0:
        raise D19IndicParlerGeneratorError(
            f"model returned invalid waveform shape for {passage_id}: {audio.shape}"
        )
    if not numpy.isfinite(audio).all():
        raise D19IndicParlerGeneratorError(
            f"model returned non-finite waveform for {passage_id}"
        )
    peak = float(numpy.max(numpy.abs(audio)))
    if not math.isfinite(peak) or peak <= 0.0 or peak > 1.5:
        raise D19IndicParlerGeneratorError(
            f"model returned invalid waveform peak for {passage_id}: {peak}"
        )
    return audio


def synthesize_passages(
    *,
    passages: Sequence[Mapping[str, Any]],
    model_snapshot: Path,
    description_tokenizer_snapshot: Path,
    private_dir: Path,
    expected_device: str,
) -> list[dict[str, Any]]:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    try:
        import numpy as np  # noqa: PLC0415
        import soundfile as sf  # noqa: PLC0415
        import torch  # noqa: PLC0415
        from parler_tts import (  # noqa: PLC0415
            ParlerTTSForConditionalGeneration,
        )
        from transformers import AutoTokenizer  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - exact runtime guard
        raise D19IndicParlerGeneratorError(
            f"pinned local runtime import failed: {type(exc).__name__}: {exc}"
        ) from exc

    device = _select_device(torch, expected_device)
    _seed_runtime(torch, np, device.type)
    model = ParlerTTSForConditionalGeneration.from_pretrained(
        str(model_snapshot),
        local_files_only=True,
        torch_dtype=torch.float32,
    )
    model.eval()
    model.to(device)
    prompt_tokenizer = AutoTokenizer.from_pretrained(
        str(model_snapshot), local_files_only=True
    )
    description_tokenizer = AutoTokenizer.from_pretrained(
        str(description_tokenizer_snapshot), local_files_only=True
    )
    description_inputs = description_tokenizer(
        PREFLIGHT.VOICE_DESCRIPTION, return_tensors="pt"
    ).to(device)
    max_new_tokens = int(model.config.decoder.max_position_embeddings)
    if max_new_tokens != 4_096:
        raise D19IndicParlerGeneratorError(
            f"pinned decoder token limit changed: {max_new_tokens}"
        )
    sample_rate = int(model.config.sampling_rate)
    if sample_rate != 44_100:
        raise D19IndicParlerGeneratorError(
            f"pinned model sampling rate changed: {sample_rate}"
        )

    samples: list[dict[str, Any]] = []
    with torch.inference_mode():
        for ordinal, passage in enumerate(passages, start=1):
            passage_id = str(passage["passage_id"])
            prompt_inputs = prompt_tokenizer(
                str(passage["text"]).strip(), return_tensors="pt"
            ).to(device)
            generation = model.generate(
                input_ids=description_inputs.input_ids,
                attention_mask=getattr(description_inputs, "attention_mask", None),
                prompt_input_ids=prompt_inputs.input_ids,
                prompt_attention_mask=getattr(prompt_inputs, "attention_mask", None),
                max_new_tokens=max_new_tokens,
                **PREFLIGHT.GENERATION_SETTINGS,
            )
            audio = _tensor_to_mono_float32(generation, np, passage_id)
            target = private_dir / f"{ordinal:02d}-{passage_id}.wav"
            sf.write(str(target), audio, sample_rate, subtype=OUTPUT_SUBTYPE)
            ffprobe = _ffprobe(target)
            samples.append(
                {
                    "ordinal": ordinal,
                    "passage_id": passage_id,
                    "source_text_sha256": passage["text_sha256"],
                    "characters": passage["characters"],
                    "prompt_tokens": int(prompt_inputs.input_ids.shape[-1]),
                    "max_new_tokens": max_new_tokens,
                    "audio_filename": target.name,
                    "audio_sha256": PREFLIGHT.sha256_file(target),
                    "audio_size_bytes": target.stat().st_size,
                    "duration_seconds": ffprobe["duration_seconds"],
                    "sample_rate_hz": ffprobe["sample_rate_hz"],
                    "channels": ffprobe["channels"],
                    "codec_name": ffprobe["codec_name"],
                    "format_name": ffprobe["format_name"],
                    "objective_format_pass": True,
                }
            )
    return samples


def execute(
    *,
    payload: dict[str, Any],
    passages: Sequence[Mapping[str, Any]],
    model_snapshot: Path,
    description_tokenizer_snapshot: Path,
    private_dir: Path,
) -> dict[str, Any]:
    if payload["engine"]["attempt_fingerprint"] != EXPECTED_ATTEMPT_FINGERPRINT:
        raise D19IndicParlerGeneratorError("execution fingerprint changed")
    if payload["runtime"]["runtime_matches_pinned_contract"] is not True:
        raise D19IndicParlerGeneratorError("execution requires exact pinned runtime")
    private_dir = PREFLIGHT.assert_private_path(private_dir)
    marker = _write_attempt_marker(private_dir, payload)
    artifacts_before = {
        "model": _artifact_contract(model_snapshot, PREFLIGHT.MODEL_ARTIFACTS, "model"),
        "description_tokenizer": _artifact_contract(
            description_tokenizer_snapshot,
            DESCRIPTION_TOKENIZER_ARTIFACTS,
            "description tokenizer",
        ),
    }
    samples = synthesize_passages(
        passages=passages,
        model_snapshot=model_snapshot,
        description_tokenizer_snapshot=description_tokenizer_snapshot,
        private_dir=private_dir,
        expected_device=str(payload["runtime"]["device"]),
    )
    artifacts_after = {
        "model": _artifact_contract(model_snapshot, PREFLIGHT.MODEL_ARTIFACTS, "model"),
        "description_tokenizer": _artifact_contract(
            description_tokenizer_snapshot,
            DESCRIPTION_TOKENIZER_ARTIFACTS,
            "description tokenizer",
        ),
    }
    if artifacts_before != artifacts_after:
        raise D19IndicParlerGeneratorError(
            "pinned model or tokenizer artifacts changed during execution"
        )
    observed_ids = tuple(item["passage_id"] for item in samples)
    if observed_ids != EXPECTED_PASSAGE_IDS or len(samples) != 4:
        raise D19IndicParlerGeneratorError(
            f"generated sample order changed: {observed_ids}"
        )
    result = {
        **payload,
        "generated_at": utc_now(),
        "status": "PRIVATE_REPRESENTATIVE_AUDIO_GENERATED_AWAITING_ASR",
        "go_no_go": "NO_GO_RELEASE_QA_PENDING",
        "samples": samples,
        "objective_audio_format": {
            "status": "PASS",
            "reports": [
                {
                    "passage_id": item["passage_id"],
                    "audio_sha256": item["audio_sha256"],
                    "duration_seconds": item["duration_seconds"],
                    "sample_rate_hz": item["sample_rate_hz"],
                    "channels": item["channels"],
                    "codec_name": item["codec_name"],
                    "pass": item["objective_format_pass"],
                }
                for item in samples
            ],
        },
        "artifact_integrity": {
            "before": artifacts_before,
            "after": artifacts_after,
            "unchanged": True,
        },
        "safety": {
            **payload["safety"],
            "attempt_consumed": True,
            "attempt_marker_path": str(marker),
            "executor_run": True,
            "audio_generated": True,
        },
        "blockers_to_release": [
            "REPRESENTATIVE_ASR_NOT_RUN",
            "INDEPENDENT_LISTENING_QA_NOT_RUN",
            "FULL_TITLE_NOT_GENERATED",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "PRIVATE_UPLOAD_CHECKSUM_NOT_RUN",
            "PRODUCTION_ENDPOINT_NOT_RUN",
            "BROWSER_PLAYBACK_GATE_NOT_RUN",
        ],
        "next_exact_command": (
            "PYTHONDONTWRITEBYTECODE=1 python3 "
            "internal/audiobook_lab/scripts/"
            "sprint1_d19_indic_parler_private_objective_qa.py "
            "--preflight --generation-evidence "
            f"{DEFAULT_EVIDENCE_OUTPUT}"
        ),
    }
    PREFLIGHT.atomic_write_json(marker, result)
    return result


def failure_payload(
    *,
    base: Mapping[str, Any] | None,
    private_dir: Path,
    exc: BaseException,
) -> dict[str, Any]:
    error = f"{type(exc).__name__}: {exc}"
    return {
        **(dict(base) if base else {}),
        "schema": "earnalism.indic_parler.d19_private_generation.v1",
        "generated_at": utc_now(),
        "status": "PRIVATE_GENERATION_FAILED_FINGERPRINT_CONSUMED",
        "go_no_go": "NO_GO_DO_NOT_RETRY_EXACT_FINGERPRINT",
        "error": error[:1000],
        "failure_traceback_sha256": hashlib.sha256(
            traceback.format_exc().encode("utf-8")
        ).hexdigest(),
        "private_output_dir": str(PREFLIGHT.assert_private_path(private_dir)),
        "asr": {"status": "NOT_RUN_BY_GENERATION_ADAPTER"},
        "listening_qa": {"status": "NOT_RUN_BY_GENERATION_ADAPTER"},
        "sync": {
            "status": "NOT_RUN_BY_GENERATION_ADAPTER",
            "estimated_sync_generated": False,
        },
        "safety": {
            **((base or {}).get("safety") or {}),
            "attempt_consumed": True,
            "executor_run": True,
            "provider_calls": 0,
            "paid_tts_lock_inspected": False,
            "paid_tts_lock_touched": False,
            "asr_run": False,
            "listening_qa_run": False,
            "sync_generated": False,
            "upload_performed": False,
            "catalog_mutated": False,
            "release_gate_mutated": False,
            "publication_performed": False,
            "public_audio_status": "AUDIO_HIDDEN_NOT_PUBLIC",
        },
        "blockers_to_release": [
            "PRIVATE_REPRESENTATIVE_GENERATION_FAILED",
            "REPRESENTATIVE_ASR_NOT_RUN",
            "INDEPENDENT_LISTENING_QA_NOT_RUN",
            "FULL_TITLE_NOT_GENERATED",
            "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
            "PRIVATE_UPLOAD_CHECKSUM_NOT_RUN",
            "PRODUCTION_ENDPOINT_NOT_RUN",
            "BROWSER_PLAYBACK_GATE_NOT_RUN",
        ],
        "next_materially_different_step": (
            "Record this fingerprint as consumed. Diagnose the exact failure and "
            "prepare a new hash-bound packet only if model, voice, prompt, "
            "settings, runtime, or passage contract changes materially."
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--profile", default=PROFILE)
    parser.add_argument("--asset-root", type=Path, default=PREFLIGHT.ROOT)
    parser.add_argument("--model-snapshot-dir", type=Path, default=MODEL_SNAPSHOT)
    parser.add_argument(
        "--description-tokenizer-dir",
        type=Path,
        default=DESCRIPTION_TOKENIZER_SNAPSHOT,
    )
    parser.add_argument(
        "--private-output-dir", type=Path, default=DEFAULT_PRIVATE_OUTPUT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output = args.output.expanduser().resolve()
    private_dir = PREFLIGHT.assert_private_path(args.private_output_dir)
    payload: dict[str, Any] | None = None
    try:
        payload, passages = build_execution_preflight(
            asset_root=args.asset_root.expanduser().resolve(),
            slug=args.slug,
            profile=args.profile,
            model_snapshot=args.model_snapshot_dir,
            description_tokenizer_snapshot=args.description_tokenizer_dir,
            private_output_dir=private_dir,
            evidence_output=output,
            require_exact_runtime=True,
        )
        if args.execute:
            payload = execute(
                payload=payload,
                passages=passages,
                model_snapshot=args.model_snapshot_dir.expanduser().resolve(),
                description_tokenizer_snapshot=(
                    args.description_tokenizer_dir.expanduser().resolve()
                ),
                private_dir=private_dir,
            )
        PREFLIGHT.atomic_write_json(output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "go_no_go": payload["go_no_go"],
                    "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
                    "generation_contract_sha256": payload["generation_contract"][
                        "generation_contract_sha256"
                    ],
                    "device": payload["runtime"]["device"],
                    "audio_generated": payload["safety"]["audio_generated"],
                    "asr_run": False,
                    "listening_qa_run": False,
                    "upload_performed": False,
                    "release_gate_mutated": False,
                    "publication_performed": False,
                    "output": str(output),
                    "private_output_dir": str(private_dir),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except (
        D19IndicParlerGeneratorError,
        PREFLIGHT.D19IndicParlerPreflightError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        if args.execute and private_dir.exists():
            failure = failure_payload(base=payload, private_dir=private_dir, exc=exc)
            PREFLIGHT.atomic_write_json(private_dir / ATTEMPT_MARKER_NAME, failure)
            PREFLIGHT.atomic_write_json(output, failure)
        print(
            json.dumps(
                {
                    "status": "BLOCKED_FAIL_CLOSED",
                    "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
                    "error": f"{type(exc).__name__}: {exc}",
                    "retry_exact_fingerprint_allowed": (
                        False if args.execute and private_dir.exists() else True
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
