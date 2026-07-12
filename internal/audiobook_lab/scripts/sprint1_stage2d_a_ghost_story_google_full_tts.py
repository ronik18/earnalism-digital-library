#!/usr/bin/env python3
"""Generate one private Google Studio-C A Ghost Story candidate."""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

from common import ffprobe_duration, sha256_file, sha256_text  # noqa: E402
from tts_hook import chunk_text  # noqa: E402


AUDITION_SCRIPT = Path(__file__).with_name("sprint1_stage2d_a_ghost_story_google_audition.py")
SPEC = importlib.util.spec_from_file_location("stage2d_google_audition", AUDITION_SCRIPT)
audition = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(audition)

OWNER_DECISION = "AUTHORIZE_STAGE_2D_A_GHOST_STORY_ALTERNATE_PROVIDER_REPAIR_AND_PUBLICATION_IF_PASS"
EXPECTED_SOURCE_SHA256 = "0f1e3de7855169bddac8ddca288aa3a63f8d6a742ce63c0b91aa947e5e2786d4"
HOLDER = "sprint1_publication_stage2d"
VOICE = "en-GB-Studio-C"
PRIOR_ESTIMATED_SPEND_USD = 2.9510
RESULT_PATH = ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_stage2d_google_full_tts_runtime.json"
AUDITION_PATH = ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/a-ghost-story_stage2d_google_audition_en_gb_studio_c_prosody_repair.json"
EXPECTED_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_APPROVE_GOOGLE_FULL_TTS": "true",
    "EARNALISM_GOOGLE_TTS_FULL_MAX_ESTIMATED_USD": "1",
    "EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS": "0.02",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def runtime_gate_errors() -> list[str]:
    errors = [
        f"{name} must equal {expected}"
        for name, expected in EXPECTED_ENV.items()
        if os.environ.get(name) != expected
    ]
    for name in ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT"):
        if not os.environ.get(name):
            errors.append(f"{name} is required")
    return errors


def load_lock(raw: bytes) -> dict:
    return audition.load_lock(raw)


def acquired_lock_payload(lock: dict, estimate: dict) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": 175,
            "approved_scope": (
                f"A Ghost Story Stage 2D private full Google TTS only; {VOICE}; source-preserving SSML; "
                f"estimated {estimate['estimated_full_tts_usd']:.4f} USD; no ASR, upload, publication, or release mutation."
            ),
            "allowed_slugs": ["a-ghost-story"],
            "stop_conditions": [
                "Any runtime gate or Google credential is missing",
                "Audition evidence no longer passes the owner minimum",
                "Source, rights, or content-integrity hash changes",
                "Estimated spend exceeds the Google, title, or sprint cap",
                "The same full generation fingerprint already reached Google",
                "Any ASR, upload, publication, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def audition_evidence() -> dict:
    evidence = json.loads(AUDITION_PATH.read_text(encoding="utf-8"))
    if evidence.get("voice") != VOICE or evidence.get("prosody_repair") is not True:
        raise RuntimeError("Stage 2D audition voice/prosody evidence changed")
    judgments = evidence.get("judgments") or []
    if len(judgments) != 3:
        raise RuntimeError("Stage 2D audition does not cover three passages")
    for item in judgments:
        scores = item.get("scores") or {}
        if float(scores.get("overall_listening_score") or 0) < 9.4:
            raise RuntimeError("Stage 2D audition is below the owner listening minimum")
        if float(scores.get("confidence_score") or 0) < 0.9:
            raise RuntimeError("Stage 2D audition confidence is below the owner minimum")
        if any((item.get("judge_flags") or {}).get(field) for field in audition.BINARY_LISTENING_FLAGS):
            raise RuntimeError("Stage 2D audition has a fatal listening flag")
    return evidence


def budget_estimate(manuscript: str) -> dict:
    rate = float(os.environ["EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS"])
    estimate = round(len(manuscript) / 1000.0 * rate, 4)
    cumulative = round(PRIOR_ESTIMATED_SPEND_USD + estimate, 4)
    blockers = []
    if estimate > float(os.environ["EARNALISM_GOOGLE_TTS_FULL_MAX_ESTIMATED_USD"]):
        blockers.append("Full Google TTS estimate exceeds its sub-cap")
    if cumulative > float(os.environ["SPRINT1_MAX_USD_PER_TITLE"]):
        blockers.append("A Ghost Story cumulative estimate exceeds the per-title cap")
    if cumulative > float(os.environ["SPRINT1_TOTAL_AUDIO_BUDGET_USD"]):
        blockers.append("Cumulative estimate exceeds the sprint cap")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "estimated_full_tts_usd": estimate,
        "estimated_stage2b_through_full_tts_usd": cumulative,
        "blockers": blockers,
    }


def full_fingerprint(manuscript: str, chunks: list[dict]) -> str:
    payload = json.dumps(
        {
            "provider": "google",
            "voice": VOICE,
            "prosody": "source_preserving_ssml_88_percent",
            "source_hash": sha256_text(manuscript),
            "chunk_hashes": [item["text_hash"] for item in chunks],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalized_spoken_text(ssml: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", ssml))).strip()


def concat_audio(paths: list[Path], target: Path) -> None:
    concat_path = target.with_suffix(".concat.txt")
    concat_path.write_text("\n".join(f"file '{path}'" for path in paths) + "\n", encoding="utf-8")
    completed = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", str(target)],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {completed.stderr[-500:]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", default=os.environ.get("EARNALISM_STAGE2D_ASSET_ROOT", str(ROOT)))
    parser.add_argument("--run-dir", default="/tmp/earnalism-a-ghost-stage2d-google-full-tts")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2
    selector = audition_evidence()
    asset_root = Path(args.asset_root).expanduser().resolve()
    manuscript_path = asset_root / "internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/clean_manuscript.txt"
    integrity_path = asset_root / "internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/content_integrity_report.json"
    rights_path = asset_root / "internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/rights_metadata_report.json"
    lock_path = asset_root / "internal/earnalism_intelligence/locks/paid_tts.lock"
    manuscript = manuscript_path.read_text(encoding="utf-8")
    if sha256_text(manuscript) != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("A Ghost Story source hash changed")
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    rights = json.loads(rights_path.read_text(encoding="utf-8"))
    if integrity.get("status") != "PASS" or rights.get("status") != "PASS":
        raise RuntimeError("Content integrity or rights gate is not PASS")
    chunks = chunk_text(manuscript, max_chars=1600)
    rebuilt = " ".join(item["text"] for item in chunks)
    if re.sub(r"\s+", " ", rebuilt).strip() != re.sub(r"\s+", " ", manuscript).strip():
        raise RuntimeError("Sentence-safe chunks do not preserve the manuscript")
    for item in chunks:
        if normalized_spoken_text(audition.source_preserving_ssml(item["text"])) != item["text"]:
            raise RuntimeError("SSML changes spoken manuscript text")
    estimate = budget_estimate(manuscript)
    if estimate["status"] != "PASS":
        print(json.dumps({"status": "BLOCKED_BUDGET", **estimate}, indent=2))
        return 3
    fingerprint = full_fingerprint(manuscript, chunks)
    if RESULT_PATH.exists():
        prior = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        if prior.get("attempt_fingerprint") == fingerprint and prior.get("provider_calls_ran") is True:
            print(json.dumps({"status": "BLOCKED_REPEAT_FULL_TTS", "attempt_fingerprint": fingerprint}, indent=2))
            return 4
    original_lock = lock_path.read_bytes()
    lock = load_lock(original_lock)
    run_dir = Path(args.run_dir).expanduser().resolve()
    preflight = {
        "status": "PASS",
        "owner_decision": OWNER_DECISION,
        "slug": "a-ghost-story",
        "provider": "google",
        "model": "google-cloud-texttospeech",
        "voice": VOICE,
        "language_code": "en-GB",
        "prosody": "source_preserving_ssml_88_percent",
        "source_hash": EXPECTED_SOURCE_SHA256,
        "source_chars": len(manuscript),
        "chunk_count": len(chunks),
        "max_chars_per_chunk": 1600,
        "selector_minimum_overall": min((item.get("scores") or {}).get("overall_listening_score", 0) for item in selector["judgments"]),
        "selector_minimum_confidence": min((item.get("scores") or {}).get("confidence_score", 0) for item in selector["judgments"]),
        "attempt_fingerprint": fingerprint,
        **estimate,
        "provider_calls_ran": False,
        "publication_performed": False,
        "lock_sha256_before": hashlib.sha256(original_lock).hexdigest(),
    }
    if args.dry_run:
        print(json.dumps({**preflight, "status": "DRY_RUN_PASS"}, indent=2))
        return 0

    from google.cloud import texttospeech  # noqa: PLC0415

    run_dir.mkdir(parents=True, exist_ok=True)
    chunk_dir = run_dir / "tts_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "clean_manuscript.txt").write_text(manuscript, encoding="utf-8")
    (run_dir / "content_integrity_report.json").write_text(json.dumps(integrity, indent=2) + "\n", encoding="utf-8")
    generated: list[dict] = []
    errors_run: list[str] = []
    provider_calls_ran = False
    started_at = iso_now()
    try:
        atomic_write(lock_path, json.dumps(acquired_lock_payload(lock, estimate), indent=2).encode("utf-8") + b"\n")
        client = texttospeech.TextToSpeechClient()
        available = {voice.name for voice in client.list_voices(language_code="en-GB").voices}
        if VOICE not in available:
            raise RuntimeError(f"Selected Google voice is unavailable: {VOICE}")
        offset = 0.0
        for chunk in chunks:
            target = chunk_dir / f"chunk_{chunk['index']:03d}.mp3"
            sidecar = target.with_suffix(".json")
            cache_key = sha256_text(f"{VOICE}|source_preserving_ssml_88_percent|{chunk['text_hash']}")
            cached = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
            duration = ffprobe_duration(target) if cached.get("cache_key") == cache_key and target.exists() else None
            if not duration or cached.get("audio_hash") != (sha256_file(target) if target.exists() else ""):
                provider_calls_ran = True
                response = client.synthesize_speech(
                    input=texttospeech.SynthesisInput(ssml=audition.source_preserving_ssml(chunk["text"])),
                    voice=texttospeech.VoiceSelectionParams(language_code="en-GB", name=VOICE),
                    audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3),
                )
                target.write_bytes(response.audio_content)
                for _ in range(3):
                    duration = ffprobe_duration(target)
                    if duration:
                        break
                    time.sleep(0.2)
                if not response.audio_content or not duration:
                    raise RuntimeError(f"Google returned invalid full TTS chunk {chunk['index']}")
                atomic_write(
                    sidecar,
                    json.dumps({"cache_key": cache_key, "text_hash": chunk["text_hash"], "audio_hash": sha256_file(target), "duration_seconds": duration}, indent=2).encode("utf-8") + b"\n",
                )
            generated.append(
                {
                    "index": chunk["index"],
                    "path": str(target),
                    "text": chunk["text"],
                    "text_hash": chunk["text_hash"],
                    "sha256": sha256_file(target),
                    "offset_seconds": round(offset, 3),
                    "duration_seconds": round(float(duration), 3),
                }
            )
            offset += float(duration)
        final_audio = run_dir / "a-ghost-story_google_studio_c_prosody_final.mp3"
        concat_audio([Path(item["path"]) for item in generated], final_audio)
        final_duration = ffprobe_duration(final_audio)
        if not final_audio.exists() or final_audio.stat().st_size <= 0 or not final_duration:
            raise RuntimeError("Final Google audio is missing or invalid")
        manifest = {
            "slug": "a-ghost-story",
            "provider": "google",
            "model": "google-cloud-texttospeech",
            "voice": VOICE,
            "prosody": "source_preserving_ssml_88_percent",
            "source_text_hash": EXPECTED_SOURCE_SHA256,
            "final_audio_path": str(final_audio),
            "final_audio_hash": sha256_file(final_audio),
            "duration_seconds": final_duration,
            "chunks": generated,
        }
        atomic_write(run_dir / "tts_chunk_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
        hook_result = {
            "status": "PASS",
            "stage": "tts",
            "artifacts": {"final_audio_path": str(final_audio), "chunk_manifest": str(run_dir / "tts_chunk_manifest.json")},
            "metrics": {
                "provider": "google",
                "model": "google-cloud-texttospeech",
                "voice": VOICE,
                "prosody": "source_preserving_ssml_88_percent",
                "fallback_tts_used": False,
                "local_audio_reused": False,
                "stale_audio_reused": False,
                "audio_regenerated": True,
                "tts_estimated_cost": estimate["estimated_full_tts_usd"],
                "chunk_count": len(generated),
                "duration_seconds": final_duration,
                "final_audio_hash": sha256_file(final_audio),
            },
            "updated_fields": {"final_audio_path": str(final_audio), "fallback_tts_used": False},
        }
        atomic_write(run_dir / "tts_hook_result.json", json.dumps(hook_result, indent=2).encode("utf-8") + b"\n")
    except Exception as exc:  # noqa: BLE001
        errors_run.append(f"{type(exc).__name__}: {exc}")
    finally:
        atomic_write(lock_path, original_lock)

    hook_path = run_dir / "tts_hook_result.json"
    hook = json.loads(hook_path.read_text(encoding="utf-8")) if hook_path.exists() else {}
    final_value = (hook.get("artifacts") or {}).get("final_audio_path") or ""
    final_path = Path(final_value) if final_value else Path()
    runtime = {
        **preflight,
        "status": "FULL_TTS_PASS_QA_PENDING" if hook.get("status") == "PASS" and final_path.is_file() else "FULL_TTS_BLOCKED",
        "started_at": started_at,
        "finished_at": iso_now(),
        "provider_calls_ran": provider_calls_ran,
        "generated_chunk_count": len(generated),
        "final_audio_path": final_value,
        "final_audio_exists": bool(final_value and final_path.is_file()),
        "final_audio_size_bytes": final_path.stat().st_size if final_value and final_path.is_file() else 0,
        "final_audio_hash": sha256_file(final_path) if final_value and final_path.is_file() else "",
        "final_audio_duration_seconds": ffprobe_duration(final_path) if final_value and final_path.is_file() else None,
        "errors": errors_run,
        "actual_provider_billing": "NOT_REPORTED",
        "lock_restored": lock_path.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "publication_performed": False,
    }
    atomic_write(RESULT_PATH, json.dumps(runtime, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0 if runtime["status"] == "FULL_TTS_PASS_QA_PENDING" else 3


if __name__ == "__main__":
    raise SystemExit(main())
