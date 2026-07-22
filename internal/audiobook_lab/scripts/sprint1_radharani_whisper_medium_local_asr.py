#!/usr/bin/env python3
"""Zero-cost, hash-bound local Whisper-medium Bengali ASR diagnostic for Radharani."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

from asr_sync_hook import transcript_similarity  # noqa: E402
from bengali_asr_normalization import detect_script_mix, script_counts  # noqa: E402


WHISPER_CLI = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/.venv-audio/bin/whisper"
)
WHISPER_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/.venv-audio/bin/python"
)
MODEL_DIR = Path("/Users/ronikbasak/.cache/whisper")
MODEL_PATH = MODEL_DIR / "medium.pt"
EXPECTED_MODEL_SHA256 = "345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1"
LANGUAGE = "bn"
MODEL_NAME = "medium"
SAMPLE_GROUP_IDS = ("group_0000", "group_0013", "group_0027")
EXPECTED_SAMPLE_AUDIO_HASHES = {
    "group_0000": "2d131c3e2023ca51e8d6f59b193bd3ca206b6783f7124c5c8d1e09aa3e644ad3",
    "group_0013": "668c03ed0b02d47f8de0f4e36e8ccd13c2837bb9b4f85cd394f096a575574edd",
    "group_0027": "43fba4d4251d1ca2673599d1c14746ef2f7ee31562e8b189df980757bb15e896",
}
REQUIRED_SOURCE_HASH = "53b00ba494263f54f97c8c94bb64ed6e07e1819fc8060aafee90f57ea5a9541d"


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def bengali_script_ratio(text: str) -> float:
    counts = script_counts(text)
    denominator = counts["bengali"] + counts["devanagari"] + counts["latin"]
    return round(counts["bengali"] / denominator, 4) if denominator else 0.0


def parse_time_metrics(stderr: str) -> dict[str, float | int | None]:
    first_line = re.search(
        r"^\s*([0-9.]+) real\s+([0-9.]+) user\s+([0-9.]+) sys\s*$",
        stderr,
        flags=re.MULTILINE,
    )

    def integer_metric(label: str) -> int | None:
        match = re.search(rf"^\s*(\d+)\s+{re.escape(label)}\s*$", stderr, flags=re.MULTILINE)
        return int(match.group(1)) if match else None

    return {
        "wall_seconds": float(first_line.group(1)) if first_line else None,
        "user_cpu_seconds": float(first_line.group(2)) if first_line else None,
        "system_cpu_seconds": float(first_line.group(3)) if first_line else None,
        "maximum_resident_set_bytes": integer_metric("maximum resident set size"),
        "peak_memory_footprint_bytes": integer_metric("peak memory footprint"),
        "page_faults": integer_metric("page faults"),
        "swaps": integer_metric("swaps"),
    }


def build_whisper_command(audio_path: Path, output_dir: Path) -> list[str]:
    return [
        "/usr/bin/time",
        "-l",
        str(WHISPER_CLI),
        str(audio_path),
        "--model",
        MODEL_NAME,
        "--model_dir",
        str(MODEL_DIR),
        "--device",
        "cpu",
        "--output_dir",
        str(output_dir),
        "--output_format",
        "json",
        "--verbose",
        "False",
        "--task",
        "transcribe",
        "--language",
        LANGUAGE,
        "--temperature",
        "0",
        "--beam_size",
        "5",
        "--condition_on_previous_text",
        "True",
        "--fp16",
        "False",
        "--temperature_increment_on_fallback",
        "None",
        "--word_timestamps",
        "True",
        "--threads",
        "0",
    ]


def whisper_versions() -> dict[str, str]:
    command = [
        str(WHISPER_PYTHON),
        "-c",
        "import json, torch, whisper; print(json.dumps({'whisper': whisper.__version__, 'torch': torch.__version__}))",
    ]
    completed = subprocess.run(command, text=True, capture_output=True, timeout=30, check=True)
    return json.loads(completed.stdout)


def hardware_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
    }
    for key, sysctl_name in (("physical_cpu_count", "hw.physicalcpu"), ("memory_bytes", "hw.memsize")):
        completed = subprocess.run(
            ["sysctl", "-n", sysctl_name],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        value = completed.stdout.strip()
        snapshot[key] = int(value) if completed.returncode == 0 and value.isdigit() else None
    return snapshot


def selected_chunks(manifest: dict[str, Any], run_dir: Path, group_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    chunks = manifest.get("chunks") if isinstance(manifest.get("chunks"), list) else []
    by_id = {f"group_{int(item.get('index', -1)):04d}": item for item in chunks}
    selected: list[dict[str, Any]] = []
    for group_id in group_ids:
        item = dict(by_id.get(group_id) or {})
        if not item:
            raise RuntimeError(f"Missing chunk manifest row: {group_id}")
        audio_path = Path(str(item.get("path") or ""))
        if not audio_path.is_absolute():
            root_candidate = ROOT / audio_path
            audio_path = root_candidate if root_candidate.exists() else run_dir / audio_path
        if not audio_path.is_file() or audio_path.stat().st_size <= 0:
            raise RuntimeError(f"Missing chunk audio: {group_id}")
        audio_hash = sha256_file(audio_path)
        expected_hash = EXPECTED_SAMPLE_AUDIO_HASHES.get(group_id)
        if expected_hash and audio_hash != expected_hash:
            raise RuntimeError(f"Unexpected audio hash for {group_id}: {audio_hash}")
        item.update(
            {
                "group_id": group_id,
                "audio_path": str(audio_path),
                "audio_sha256": audio_hash,
                "source_text_sha256": sha256_text(str(item.get("text") or "")),
            }
        )
        selected.append(item)
    return selected


def evaluate_transcript(source_text: str, transcript: str, *, word_timestamp_count: int) -> dict[str, Any]:
    similarity = transcript_similarity(source_text, transcript)
    ratio = bengali_script_ratio(transcript)
    blockers: list[str] = []
    if float(similarity["score"]) < 9.7:
        blockers.append(f"source score {similarity['score']} < 9.7")
    if float(similarity["coverage"]) < 0.98:
        blockers.append(f"coverage {similarity['coverage']} < 0.98")
    if float(similarity["token_order_similarity"]) < 0.97:
        blockers.append(f"token order {similarity['token_order_similarity']} < 0.97")
    if similarity["first_words_match"] is not True:
        blockers.append("first narrated span mismatch")
    if similarity["last_words_match"] is not True:
        blockers.append("last narrated span mismatch")
    if ratio < 0.9:
        blockers.append(f"Bengali script ratio {ratio} < 0.9")
    if word_timestamp_count <= 0:
        blockers.append("word timestamps missing")
    return {
        **similarity,
        "script_profile": {
            "detected": detect_script_mix(transcript),
            "counts": script_counts(transcript),
            "bengali_script_ratio": ratio,
        },
        "word_timestamp_count": word_timestamp_count,
        "pass": not blockers,
        "blockers": blockers,
    }


def word_timestamp_count(payload: dict[str, Any]) -> int:
    count = 0
    for segment in payload.get("segments") or []:
        for word in segment.get("words") or []:
            if str(word.get("word") or "").strip() and word.get("start") is not None and word.get("end") is not None:
                count += 1
    return count


def run_chunk(chunk: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    audio_path = Path(str(chunk["audio_path"]))
    command = build_whisper_command(audio_path, output_dir)
    output_json = output_dir / f"{audio_path.stem}.json"
    if output_json.exists():
        raise RuntimeError(f"Refusing to reuse pre-existing local Whisper output: {output_json}")
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONHASHSEED": "0"},
        check=False,
    )
    resources = parse_time_metrics(completed.stderr)
    if completed.returncode != 0 or not output_json.is_file():
        return {
            "group_id": chunk["group_id"],
            "status": "ERROR",
            "returncode": completed.returncode,
            "command": command,
            "stderr_sha256": sha256_text(completed.stderr),
            "stderr_tail": completed.stderr[-2000:],
            "resource_usage": resources,
        }
    payload = read_json(output_json)
    transcript = str(payload.get("text") or "").strip()
    timestamps = word_timestamp_count(payload)
    evaluation = evaluate_transcript(str(chunk.get("text") or ""), transcript, word_timestamp_count=timestamps)
    return {
        "group_id": chunk["group_id"],
        "status": "PASS" if evaluation["pass"] else "BELOW_THRESHOLD",
        "audio_path": str(chunk["audio_path"]),
        "audio_sha256": chunk["audio_sha256"],
        "audio_duration_seconds": chunk.get("duration_seconds"),
        "source_text_sha256": chunk["source_text_sha256"],
        "transcript": transcript,
        "transcript_sha256": sha256_text(transcript),
        "transcript_chars": len(transcript),
        "whisper_output_json": str(output_json),
        "whisper_output_sha256": sha256_file(output_json),
        "command": command,
        "returncode": completed.returncode,
        "stderr_sha256": sha256_text(completed.stderr),
        "resource_usage": resources,
        "evaluation": evaluation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    private_output_dir = args.private_output_dir.expanduser().resolve()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    lock_path = args.lock_path.expanduser().resolve()
    required_files = (WHISPER_CLI, WHISPER_PYTHON, MODEL_PATH, run_dir / "tts_chunk_manifest.json", lock_path)
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise SystemExit("Missing required files: " + ", ".join(missing))
    model_hash = sha256_file(MODEL_PATH)
    if model_hash != EXPECTED_MODEL_SHA256:
        raise SystemExit(f"Whisper medium model checksum mismatch: {model_hash}")
    manifest = read_json(run_dir / "tts_chunk_manifest.json")
    if manifest.get("source_hash") != REQUIRED_SOURCE_HASH:
        raise SystemExit(f"Unexpected source hash: {manifest.get('source_hash')}")
    chunks = selected_chunks(manifest, run_dir, SAMPLE_GROUP_IDS)
    versions = whisper_versions()
    lock_before = lock_path.read_bytes()
    fingerprint = {
        "slug": "radharani",
        "scope": "opening_middle_ending_sample",
        "provider": "local_openai_whisper",
        "model": MODEL_NAME,
        "model_path": str(MODEL_PATH),
        "model_sha256": model_hash,
        "whisper_cli": str(WHISPER_CLI),
        "whisper_version": versions["whisper"],
        "torch_version": versions["torch"],
        "language": LANGUAGE,
        "source_hash": manifest["source_hash"],
        "chunks": [
            {
                "group_id": chunk["group_id"],
                "audio_sha256": chunk["audio_sha256"],
                "source_text_sha256": chunk["source_text_sha256"],
            }
            for chunk in chunks
        ],
        "decoder": {
            "device": "cpu",
            "temperature": 0,
            "beam_size": 5,
            "condition_on_previous_text": True,
            "fp16": False,
            "temperature_increment_on_fallback": None,
            "word_timestamps": True,
            "initial_prompt": None,
        },
    }
    if output.exists():
        prior = read_json(output)
        if prior.get("fingerprint") == fingerprint and prior.get("local_asr_ran") is True:
            raise SystemExit("Identical local Whisper diagnostic already ran; refusing duplicate execution")
    preflight = {
        "generated_at": iso_now(),
        "status": "DRY_RUN_PASS",
        "slug": "radharani",
        "cost_usd": 0.0,
        "diagnostic_only": True,
        "release_evidence_sufficient": False,
        "provider_calls_ran": False,
        "paid_lock_mutated": False,
        "lock_sha256_before": sha256_bytes(lock_before),
        "fingerprint": fingerprint,
        "hardware": hardware_snapshot(),
        "local_asr_ran": False,
        "results": [],
    }
    if not args.execute:
        atomic_write_json(output, preflight)
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 0

    private_output_dir.mkdir(parents=True, exist_ok=False)
    results = [run_chunk(chunk, private_output_dir) for chunk in chunks]
    lock_after = lock_path.read_bytes()
    all_pass = len(results) == len(SAMPLE_GROUP_IDS) and all(item.get("status") == "PASS" for item in results)
    resource_rows = [item.get("resource_usage") or {} for item in results]
    payload = {
        **preflight,
        "generated_at": iso_now(),
        "status": "SAMPLE_PASS_FULL_LOCAL_ASR_AUTHORIZED" if all_pass else "LOCAL_WHISPER_MEDIUM_UNSUITABLE_FOR_RADHARANI_AUDIO",
        "local_asr_ran": True,
        "results": results,
        "sample_gate_pass": all_pass,
        "full_28_group_local_asr_run": False,
        "stop_reason": "" if all_pass else "At least one fixed-setting sample failed exact objective gates; decoder-tuning loops are prohibited.",
        "resource_usage_total": {
            "wall_seconds": round(sum(float(row.get("wall_seconds") or 0) for row in resource_rows), 2),
            "user_cpu_seconds": round(sum(float(row.get("user_cpu_seconds") or 0) for row in resource_rows), 2),
            "system_cpu_seconds": round(sum(float(row.get("system_cpu_seconds") or 0) for row in resource_rows), 2),
            "maximum_resident_set_bytes": max((int(row.get("maximum_resident_set_bytes") or 0) for row in resource_rows), default=0),
            "peak_memory_footprint_bytes": max((int(row.get("peak_memory_footprint_bytes") or 0) for row in resource_rows), default=0),
        },
        "lock_sha256_after": sha256_bytes(lock_after),
        "paid_lock_mutated": lock_before != lock_after,
        "next_action": (
            "Run the same fixed local Whisper medium/bn fingerprint over all 28 fresh groups with measured word timestamps."
            if all_pass
            else "Do not repeat or tune local Whisper medium for this audio. Keep Radharani audio hidden and use a materially different Bengali ASR provider or source-bound replacement narration."
        ),
    }
    atomic_write_json(output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if all_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
