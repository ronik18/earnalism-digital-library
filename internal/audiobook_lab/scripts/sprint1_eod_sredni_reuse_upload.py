#!/usr/bin/env python3
"""Checksum-verify and upload the approved Sredni Vashtar reuse package."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
UPLOAD_HOOK = ROOT / "internal/audiobook_lab/scripts/factory_hooks/upload_hook.py"
HOLDER = "eod_sredni_reuse_upload"
SLUG = "sredni-vashtar"
EXPECTED_AUDIO_HASH = "2b328a80b90684ddf2fe3df1a1447481067c6cb277484f97432e882c7844d31a"
EXPECTED_SOURCE_HASH = "44e3bebedecc69c907b8739b5c6996932505df2cb140c05a4d55b9ca9d2bfd21"
EXPECTED_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_APPROVE_EOD_SREDNI_REUSE_UPLOAD": "true",
    "EARNALISM_B2_MULTIPART_CHUNK_BYTES": "5242880",
}
REQUIRED_STORAGE_ENV = (
    "B2_ACCESS_KEY_ID",
    "B2_SECRET_ACCESS_KEY",
    "B2_BUCKET",
    "B2_S3_ENDPOINT",
    "B2_REGION",
)
FATAL_FLAGS = {
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "list_reading_rhythm_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
    "placeholder_audio_detected",
}
TIMING_RE = re.compile(
    r"^(?P<sh>\d{2}):(?P<sm>\d{2}):(?P<ss>\d{2})\.(?P<sms>\d{3}) --> "
    r"(?P<eh>\d{2}):(?P<em>\d{2}):(?P<es>\d{2})\.(?P<ems>\d{3})$"
)


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def write_json(path: Path, payload: dict) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_gate_errors() -> list[str]:
    errors = [
        f"{name} must equal {expected}"
        for name, expected in EXPECTED_ENV.items()
        if os.environ.get(name) != expected
    ]
    errors.extend(f"{name} is required" for name in REQUIRED_STORAGE_ENV if not os.environ.get(name))
    return errors


def load_lock(raw: bytes) -> dict:
    payload = json.loads(raw)
    if payload.get("status") != "active" or payload.get("current_holder") != "none":
        raise RuntimeError("paid_tts.lock is not available")
    if payload.get("allowed_next_holders") != []:
        raise RuntimeError("paid_tts.lock allowed_next_holders must be empty")
    return payload


def acquired_lock_payload(lock: dict) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": 0,
            "approved_scope": (
                "Sredni Vashtar existing-audio checksum upload only; no TTS, ASR, "
                "release-state mutation, deployment, or unrelated title work."
            ),
            "allowed_slugs": [SLUG],
            "stop_conditions": [
                "Any runtime or B2 credential gate is missing",
                "Reuse QA, audio, source, or sidecar binding changes",
                "Any remote checksum does not match",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def vtt_seconds(parts: tuple[str, ...]) -> float:
    hours, minutes, seconds, milliseconds = (int(value) for value in parts)
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def validate_vtt(path: Path, duration: float, expected_cues: int) -> list[str]:
    blockers: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "WEBVTT":
        return ["highlight.vtt is missing the WEBVTT header"]
    cue_count = 0
    previous_start = -1.0
    for line in lines:
        match = TIMING_RE.fullmatch(line.strip())
        if not match:
            continue
        cue_count += 1
        values = match.groupdict()
        start = vtt_seconds((values["sh"], values["sm"], values["ss"], values["sms"]))
        end = vtt_seconds((values["eh"], values["em"], values["es"], values["ems"]))
        if start < previous_start or end < start or start < 0 or end > duration + 0.05:
            blockers.append(f"highlight.vtt has invalid cue timing at cue {cue_count}")
            break
        previous_start = start
    if cue_count != expected_cues:
        blockers.append(f"highlight.vtt cue count {cue_count} does not match timestamps {expected_cues}")
    return blockers


def validate_release_evidence(args: argparse.Namespace) -> dict:
    full_qa = read_json(args.full_qa)
    if isinstance(full_qa.get("results"), list):
        matches = [item for item in full_qa["results"] if isinstance(item, dict) and item.get("slug") == SLUG]
        if len(matches) != 1:
            return {
                "status": "BLOCKED",
                "slug": SLUG,
                "blockers": ["Aggregate reuse QA must contain exactly one Sredni result"],
            }
        full_qa = matches[0]
    meta = read_json(args.artifact_dir / "meta.json")
    timestamps = read_json(args.artifact_dir / "timestamps.json")
    chapters = read_json(args.artifact_dir / "chapters.json")
    audio = args.artifact_dir / "sredni-vashtar_openai_tts_final.mp3"
    vtt = args.artifact_dir / "highlight.vtt"
    blockers: list[str] = []

    if full_qa.get("slug") != SLUG or full_qa.get("candidate_id") != "candidate-61355c7842dbcbae":
        blockers.append("Reuse QA does not identify the canonical Sredni candidate")
    if full_qa.get("audio_sha256") != EXPECTED_AUDIO_HASH:
        blockers.append("Reuse QA audio hash changed")
    if full_qa.get("source_sha256") != EXPECTED_SOURCE_HASH:
        blockers.append("Reuse QA source hash changed")
    if float(full_qa.get("asr_source_score") or 0) < 9.7:
        blockers.append("ASR/source score is below 9.7")
    if full_qa.get("first_words_match") is not True or full_qa.get("last_words_match") is not True:
        blockers.append("First/last checks are not PASS")
    if float(full_qa.get("minimum_listening_score") or 0) < 9.4:
        blockers.append("A listening sample is below 9.4")
    if float(full_qa.get("minimum_confidence") or 0) < 0.9:
        blockers.append("Listening confidence is below 0.9")
    fatal = sorted(set(full_qa.get("fatal_flags") or []) & FATAL_FLAGS)
    if fatal:
        blockers.append(f"Fatal listening flags present: {', '.join(fatal)}")

    if not audio.is_file() or audio.stat().st_size <= 0:
        blockers.append("Canonical audio is missing or empty")
    elif sha256_file(audio) != EXPECTED_AUDIO_HASH:
        blockers.append("Canonical audio hash changed")
    duration = float(meta.get("duration_seconds") or 0)
    if duration <= 0:
        blockers.append("Audio duration is missing")
    if meta.get("audio_hash") != EXPECTED_AUDIO_HASH or meta.get("source_text_hash") != EXPECTED_SOURCE_HASH:
        blockers.append("meta.json is not bound to the canonical audio/source")
    if timestamps.get("audio_hash") != EXPECTED_AUDIO_HASH or timestamps.get("source_text_hash") != EXPECTED_SOURCE_HASH:
        blockers.append("timestamps.json is not bound to the canonical audio/source")
    if timestamps.get("auto_estimated_sync") is not False or meta.get("auto_estimated_sync") is not False:
        blockers.append("Sidecar timing is estimated")
    if timestamps.get("alignment_method") != "openai_verbose_json_word_timestamps":
        blockers.append("Sidecar alignment method is not provider-measured")

    words = timestamps.get("words") or []
    if len(words) < 100:
        blockers.append("timestamps.json contains too few measured words")
    previous_start = -1.0
    for index, word in enumerate(words):
        try:
            start = float(word["start"])
            end = float(word["end"])
        except (KeyError, TypeError, ValueError):
            blockers.append(f"timestamps.json has invalid word timing at index {index}")
            break
        if not math.isfinite(start) or not math.isfinite(end) or start < previous_start or end < start:
            blockers.append(f"timestamps.json has invalid word timing at index {index}")
            break
        if start < 0 or end > duration + 0.05:
            blockers.append(f"timestamps.json exceeds audio bounds at index {index}")
            break
        previous_start = start

    chapters_list = chapters.get("chapters") if isinstance(chapters, dict) else chapters
    if not isinstance(chapters_list, list) or not chapters_list:
        blockers.append("chapters.json has no chapters")
    else:
        last_end = float(chapters_list[-1].get("end", chapters_list[-1].get("end_seconds", 0)) or 0)
        if abs(last_end - duration) > 0.05:
            blockers.append("chapters.json does not end at the audio duration")
    if vtt.is_file():
        blockers.extend(validate_vtt(vtt, duration, len(words)))
    else:
        blockers.append("highlight.vtt is missing")

    selected = {
        "mp3": audio,
        "timestamps": args.artifact_dir / "timestamps.json",
        "vtt": vtt,
        "chapters": args.artifact_dir / "chapters.json",
        "meta": args.artifact_dir / "meta.json",
    }
    for key, path in selected.items():
        if not path.is_file() or path.stat().st_size <= 0:
            blockers.append(f"Selected {key} artifact is missing or empty")
        if path.name.startswith("reused_"):
            blockers.append(f"Stale Piper sidecar selected for {key}")

    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "slug": SLUG,
        "candidate_id": full_qa.get("candidate_id"),
        "audio_path": str(audio),
        "audio_hash": EXPECTED_AUDIO_HASH,
        "source_hash": EXPECTED_SOURCE_HASH,
        "audio_size_bytes": audio.stat().st_size if audio.is_file() else 0,
        "duration_seconds": duration,
        "asr_source_score": full_qa.get("asr_source_score"),
        "first_words_match": full_qa.get("first_words_match"),
        "last_words_match": full_qa.get("last_words_match"),
        "listening_minimum_score": full_qa.get("minimum_listening_score"),
        "listening_minimum_confidence": full_qa.get("minimum_confidence"),
        "fatal_flags": fatal,
        "alignment_method": timestamps.get("alignment_method"),
        "auto_estimated_sync": timestamps.get("auto_estimated_sync"),
        "sidecar_paths": {key: str(path) for key, path in selected.items() if key != "mp3"},
        "blockers": blockers,
    }


def preupload_qa(evidence: dict) -> dict:
    return {
        "slug": SLUG,
        "schema_version": 1,
        "decision": "PREUPLOAD_APPROVED",
        "auto_approval_decision": True,
        "owner_decision": "AUTHORIZE_EOD_GO_LIVE_FOR_SPRINT1_DIGITAL_READERS_AND_APPROVED_AUDIO_ONLY_WITH_ONE_BOUNDED_SREDNI_REUSE_STRETCH",
        "approved_scope": "Existing Sredni reuse package checksum upload only",
        "audio_public_release": "PENDING_VERIFIED_UPLOAD",
        "quality_claim": "MEASURED_RELEASE_MINIMUM_PASS_NO_10_OF_10_CLAIM",
        "measured_evidence": evidence,
        "created_at": iso_now(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", required=True, type=Path)
    parser.add_argument("--artifact-dir", required=True, type=Path)
    parser.add_argument("--full-qa", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2
    evidence = validate_release_evidence(args)
    if evidence["status"] != "PASS":
        print(json.dumps({"status": "BLOCKED_RELEASE_EVIDENCE", **evidence}, indent=2))
        return 3
    if args.dry_run:
        print(json.dumps({**evidence, "status": "DRY_RUN_PASS"}, indent=2))
        return 0

    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "auto_premium_qa.json", preupload_qa(evidence))
    write_json(
        run_dir / "tts_hook_result.json",
        {
            "status": "PASS",
            "ready_for_next_stage": True,
            "artifacts": {"final_audio_path": evidence["audio_path"]},
            "blockers": [],
        },
    )
    write_json(
        run_dir / "asr_sync_hook_result.json",
        {
            "status": "PASS",
            "ready_for_next_stage": True,
            "artifacts": evidence["sidecar_paths"],
            "metrics": {
                "asr_source_score": evidence["asr_source_score"],
                "auto_estimated_sync": False,
                "alignment_method": evidence["alignment_method"],
            },
            "blockers": [],
        },
    )

    lock_path = args.asset_root.resolve() / "internal/earnalism_intelligence/locks/paid_tts.lock"
    original_lock = lock_path.read_bytes()
    lock = load_lock(original_lock)
    command = [
        sys.executable,
        str(UPLOAD_HOOK),
        "--slug",
        SLUG,
        "--run-dir",
        str(run_dir),
        "--catalog-run-dir",
        str(run_dir),
        "--manifest",
        str(ROOT / "book_import_manifest.json"),
        "--language",
        "eng",
        "--title",
        "Sredni Vashtar",
        "--author",
        "Saki",
        "--max-attempts",
        "1",
        "--fail-closed",
    ]
    process: subprocess.CompletedProcess | None = None
    error = ""
    started_at = iso_now()
    try:
        atomic_write(lock_path, json.dumps(acquired_lock_payload(lock), indent=2).encode("utf-8") + b"\n")
        process = subprocess.run(command, cwd=ROOT, env=os.environ.copy(), check=False)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(lock_path, original_lock)

    hook_result = read_json(run_dir / "upload_hook_result.json") if (run_dir / "upload_hook_result.json").exists() else {}
    upload_manifest = read_json(run_dir / "upload_manifest.json") if (run_dir / "upload_manifest.json").exists() else {}
    checks = upload_manifest.get("checksums") or {}
    required = {"mp3", "timestamps", "vtt", "chapters", "meta"}
    checksum_pass = required.issubset(checks) and all(
        checks[name].get("resolves") is True
        and checks[name].get("match") is True
        and int(checks[name].get("local_size") or 0) > 0
        and checks[name].get("local_size") == checks[name].get("remote_size")
        for name in required
    )
    upload_pass = (
        process is not None
        and process.returncode == 0
        and hook_result.get("status") == "PASS"
        and upload_manifest.get("status") == "PASS"
        and checksum_pass
    )
    runtime = {
        "status": "VERIFIED_UPLOAD_PASS" if upload_pass else "VERIFIED_UPLOAD_BLOCKED",
        "slug": SLUG,
        "started_at": started_at,
        "finished_at": iso_now(),
        "release_evidence": evidence,
        "process_returncode": process.returncode if process else None,
        "hook_status": hook_result.get("status", "MISSING"),
        "hook_blockers": hook_result.get("blockers") or [],
        "storage_backend": upload_manifest.get("storage_backend"),
        "urls": upload_manifest.get("urls") or {},
        "checksums": checks,
        "error": error or None,
        "lock_restored": lock_path.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "public_source_mutated": False,
        "publication_performed": False,
        "provider_calls_performed": False,
        "estimated_cost_usd": 0.0,
    }
    write_json(run_dir / "sredni_reuse_upload_runtime.json", runtime)
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0 if upload_pass and runtime["lock_restored"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
