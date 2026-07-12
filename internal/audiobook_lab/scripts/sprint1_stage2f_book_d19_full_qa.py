#!/usr/bin/env python3
"""Run bounded ASR and listening QA for the private book-d19e96859f candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py"
SCRIPT_DIR = ROOT / "internal/audiobook_lab/scripts"
HOOK_DIR = SCRIPT_DIR / "factory_hooks"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(HOOK_DIR))

from bengali_tts_provider_bakeoff import google_safe_tts_text  # noqa: E402
from common import sha256_file, sha256_text  # noqa: E402
from tts_hook import chunk_text  # noqa: E402

DEFAULT_RUN_DIR = ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_stage2f_full_tts"
RESULT_PATH = ROOT / "internal/audiobook_lab/sprint1_publication/title_runs/book-d19e96859f_stage2f_full_qa.json"
HOLDER = "sprint1_publication_stage2f_book_d19_qa"
SLUG = "book-d19e96859f"
EXPECTED_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE": "0.008",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
    "EARNALISM_LISTENING_POLICY_VERSION": "bengali_audiobook_acceptance_v2_92",
}
POSITIVE_CAP_ENV = (
    "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD",
    "EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD",
)
FATAL_FLAGS = {
    "robotic_texture_detected",
    "mechanical_cadence_detected",
    "choppy_joins_detected",
    "fallback_tts_detected",
    "list_reading_rhythm_detected",
    "repeated_identical_sentence_endings_detected",
    "abrupt_tts_resets_detected",
    "placeholder_audio_detected",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def runtime_gate_errors() -> list[str]:
    errors = [f"{name} must equal {expected}" for name, expected in EXPECTED_ENV.items() if os.environ.get(name) != expected]
    for name in POSITIVE_CAP_ENV:
        try:
            value = float(os.environ.get(name, ""))
            if not math.isfinite(value) or value <= 0:
                errors.append(f"{name} must be a positive number")
        except ValueError:
            errors.append(f"{name} must be a positive number")
    if not os.environ.get("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is required")
    return errors


def load_lock(raw: bytes) -> dict:
    payload = json.loads(raw)
    if payload.get("status") != "active" or payload.get("current_holder") != "none":
        raise RuntimeError("paid_tts.lock is not available")
    if payload.get("allowed_next_holders") != []:
        raise RuntimeError("paid_tts.lock allowed_next_holders must be empty")
    return payload


def acquired_lock_payload(lock: dict, estimate: dict, slug: str = SLUG) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": f"sprint1_publication_full_qa:{slug}",
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": 30,
            "approved_scope": (
                f"{slug} private candidate only; bounded OpenAI ASR and listening QA; "
                f"estimated {estimate['estimated_current_qa_usd']:.4f} USD; no upload or publication"
            ),
            "allowed_slugs": [slug],
            "stop_conditions": [
                "Any runtime gate or OPENAI_API_KEY is missing",
                "The TTS result or audio hash changes",
                "ASR or listening QA estimate exceeds its cap",
                "Any upload, publication, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def resolve_artifact(value: str, run_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    root_path = ROOT / path
    return root_path if root_path.exists() else run_dir / path


def materialize_google_compatibility(run_dir: Path, slug: str = SLUG) -> dict:
    manifest_path = run_dir / "google_bengali_full_tts_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("slug") != slug or manifest.get("provider") != "google":
        raise RuntimeError("Google manifest slug/provider mismatch")
    source_meta = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    source_path = run_dir / str(source_meta.get("file") or "sanitized_manuscript.txt")
    source = source_path.read_text(encoding="utf-8")
    if sha256_text(source) != source_meta.get("sha256"):
        raise RuntimeError("D19 Google source hash mismatch")
    chunking = manifest.get("chunking") if isinstance(manifest.get("chunking"), dict) else {}
    rebuilt = chunk_text(source, max_chars=int(chunking.get("max_characters") or 1200))
    recorded = manifest.get("chunks") if isinstance(manifest.get("chunks"), list) else []
    if len(rebuilt) != len(recorded) or not rebuilt:
        raise RuntimeError("D19 Google chunk count mismatch")
    compatibility_chunks = []
    for index, (source_chunk, audio_record) in enumerate(zip(rebuilt, recorded)):
        if source_chunk.get("index") != index or audio_record.get("index") != index:
            raise RuntimeError("D19 Google chunks are not contiguous and ordered")
        text = str(source_chunk.get("text") or "")
        if sha256_text(text) != audio_record.get("text_sha256"):
            raise RuntimeError(f"D19 Google source hash mismatch for chunk {index}")
        if sha256_text(google_safe_tts_text(text)) != audio_record.get("tts_text_sha256"):
            raise RuntimeError(f"D19 Google prepared-text hash mismatch for chunk {index}")
        audio = run_dir / str(audio_record.get("file") or "")
        if not audio.is_file() or audio.stat().st_size <= 0 or sha256_file(audio) != audio_record.get("audio_sha256"):
            raise RuntimeError(f"D19 Google audio hash mismatch for chunk {index}")
        compatibility_chunks.append(
            {
                "index": index,
                "text": text,
                "text_hash": sha256_text(text),
                "path": str(audio),
                "sha256": sha256_file(audio),
                "duration_seconds": audio_duration_seconds(audio),
                "status": "PASS",
            }
        )
    final_meta = manifest.get("final_audio") if isinstance(manifest.get("final_audio"), dict) else {}
    final_audio = run_dir / str(final_meta.get("file") or "")
    if not final_audio.is_file() or final_audio.stat().st_size <= 0 or sha256_file(final_audio) != final_meta.get("sha256"):
        raise RuntimeError("D19 Google final audio hash mismatch")
    clean_path = run_dir / "clean_manuscript.txt"
    atomic_write(clean_path, source.encode("utf-8"))
    chunk_manifest = {
        "schema_version": 1,
        "slug": slug,
        "provider": "google",
        "model": manifest.get("model"),
        "voice": manifest.get("voice"),
        "chunks": compatibility_chunks,
        "final_audio_path": str(final_audio),
        "final_audio_hash": sha256_file(final_audio),
        "tts_source_sanitization": {
            "frontmatter_stripped": True,
            "forbidden_source_terms_in_prepared_text": [],
        },
        "group_repair": {
            "status": "NOT_REQUESTED",
            "repair_requested": False,
        },
    }
    atomic_write(run_dir / "tts_chunk_manifest.json", json.dumps(chunk_manifest, ensure_ascii=False, indent=2).encode() + b"\n")
    result = {
        "status": "PASS",
        "ready_for_next_stage": True,
        "artifacts": {
            "final_audio_path": str(final_audio),
            "tts_chunk_manifest": str(run_dir / "tts_chunk_manifest.json"),
            "clean_manuscript": str(clean_path),
        },
        "metrics": {
            "provider": "google",
            "model": manifest.get("model"),
            "voice": manifest.get("voice"),
            "final_audio_hash": sha256_file(final_audio),
            "fallback_tts_used": False,
            "local_audio_reused": False,
            "stale_audio_reused": False,
            "estimated_tts_usd": (manifest.get("budget") or {}).get("estimated_google_tts_usd"),
        },
        "updated_fields": {
            "final_audio_path": str(final_audio),
            "final_audio_hash": sha256_file(final_audio),
            "fallback_tts_used": False,
            "local_audio_reused": False,
            "stale_audio_reused": False,
        },
        "compatibility_source": str(manifest_path),
    }
    atomic_write(run_dir / "tts_hook_result.json", json.dumps(result, ensure_ascii=False, indent=2).encode() + b"\n")
    return result


def tts_evidence(
    run_dir: Path,
    slug: str = SLUG,
    expected_google_voice: str = "bn-IN-Chirp3-HD-Aoede",
) -> tuple[dict, Path, str]:
    result_path = run_dir / "tts_hook_result.json"
    result = read_json(result_path) if result_path.exists() else materialize_google_compatibility(run_dir, slug)
    if result.get("status") != "PASS" or result.get("ready_for_next_stage") is not True:
        raise RuntimeError("D19 TTS evidence is not ready for QA")
    metrics = result.get("metrics") or {}
    if metrics.get("provider") not in {"sarvam", "google"}:
        raise RuntimeError("D19 provider evidence is unsupported")
    if metrics.get("provider") == "sarvam" and metrics.get("voice") != "pooja":
        raise RuntimeError("D19 Sarvam voice evidence changed")
    if metrics.get("provider") == "google" and metrics.get("voice") != expected_google_voice:
        raise RuntimeError("Google voice evidence changed")
    audio = resolve_artifact(str((result.get("artifacts") or {}).get("final_audio_path") or ""), run_dir)
    if not audio.is_file() or audio.stat().st_size <= 0:
        raise RuntimeError("D19 final audio is missing")
    return result, audio, hashlib.sha256(audio.read_bytes()).hexdigest()


def audio_duration_seconds(audio: Path) -> float:
    process = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(audio)],
        text=True,
        capture_output=True,
        check=True,
    )
    return float(process.stdout.strip())


def budget_estimate(duration_seconds: float, tts_estimated_usd: float = 0.0) -> dict:
    asr = round(duration_seconds / 60.0 * float(os.environ["EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE"]), 4)
    listening = round(6 * float(os.environ["EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD"]), 4)
    current = round(asr + listening, 4)
    blockers = []
    if asr > float(os.environ["EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD"]):
        blockers.append("ASR estimate exceeds its cap")
    if asr > float(os.environ["EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD"]):
        blockers.append("ASR estimate exceeds its retry cap")
    if listening > float(os.environ["EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD"]):
        blockers.append("Listening QA estimate exceeds its cap")
    if tts_estimated_usd + current > float(os.environ["SPRINT1_MAX_USD_PER_TITLE"]):
        blockers.append("D19 estimate exceeds the per-title cap")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "estimated_asr_usd": asr,
        "estimated_listening_qa_usd": listening,
        "estimated_current_qa_usd": current,
        "estimated_title_total_usd": round(tts_estimated_usd + current, 4),
        "blockers": blockers,
    }


def tts_cost_from_metrics(tts: dict) -> float:
    metrics = tts.get("metrics") if isinstance(tts.get("metrics"), dict) else {}
    return float(metrics.get("estimated_tts_usd") or metrics.get("tts_estimated_cost") or 0)


def owner_listening_gate(samples: list[dict]) -> dict:
    scores = [float((item.get("scores") or {}).get("overall_listening_score") or 0) for item in samples]
    confidences = [float((item.get("scores") or {}).get("confidence_score") or item.get("confidence") or 0) for item in samples]
    fatal = sorted({field for item in samples for field in FATAL_FLAGS if (item.get("judge_flags") or {}).get(field)})
    minimum_score = min(scores) if scores else 0.0
    minimum_confidence = min(confidences) if confidences else 0.0
    return {
        "passes": len(samples) >= 4 and minimum_score >= 9.4 and minimum_confidence >= 0.9 and not fatal,
        "sample_count": len(samples),
        "scores": scores,
        "minimum_overall_score": minimum_score,
        "minimum_confidence": minimum_confidence,
        "fatal_flags": fatal,
    }


def effective_source_gate(hook: dict, diagnosis: dict, construction: dict) -> dict:
    hook_metrics = hook.get("metrics") if isinstance(hook.get("metrics"), dict) else {}
    construction_pass = construction.get("tts_by_construction_verified") is True
    score = float(diagnosis.get("score") or 0)
    first_words_match = diagnosis.get("first_words_match") is True
    last_words_match = diagnosis.get("last_words_match") is True
    return {
        "passes": score >= 9.7 and first_words_match and last_words_match,
        "score": score,
        "method": "asr_transcript",
        "construction_verified": construction_pass,
        "construction_source_match_score": float(hook_metrics.get("source_match_score") or 0),
        "construction_boundary_pass": construction.get("first_last_tts_input_boundary_pass") is True,
        "first_words_match": first_words_match,
        "last_words_match": last_words_match,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path, default=RESULT_PATH)
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--title", default="গিন্নি")
    parser.add_argument("--author", default="রবীন্দ্রনাথ ঠাকুর")
    parser.add_argument("--expected-google-voice", default="bn-IN-Chirp3-HD-Aoede")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2
    run_dir = args.run_dir.expanduser().resolve()
    tts, audio, audio_hash = tts_evidence(run_dir, args.slug, args.expected_google_voice)
    duration = audio_duration_seconds(audio)
    estimate = budget_estimate(duration, tts_cost_from_metrics(tts))
    if estimate["status"] != "PASS":
        print(json.dumps({"status": "BLOCKED_BUDGET", **estimate}, indent=2))
        return 3
    original_lock = args.lock_path.expanduser().resolve().read_bytes()
    lock = load_lock(original_lock)
    preflight = {
        "slug": args.slug,
        "audio_path": str(audio),
        "audio_hash": audio_hash,
        "audio_size_bytes": audio.stat().st_size,
        "audio_duration_seconds": duration,
        "tts_hook_status": tts.get("status"),
        **estimate,
        "provider_calls_ran": False,
        "publication_performed": False,
        "lock_sha256_before": hashlib.sha256(original_lock).hexdigest(),
    }
    if args.dry_run:
        print(json.dumps({**preflight, "status": "DRY_RUN_PASS"}, indent=2))
        return 0

    command = [
        sys.executable,
        str(HOOK),
        "--slug",
        args.slug,
        "--run-dir",
        str(run_dir),
        "--manifest",
        str(ROOT / "book_import_manifest.json"),
        "--language",
        "Bengali",
        "--title",
        args.title,
        "--author",
        args.author,
        "--max-attempts",
        "1",
        "--fail-closed",
    ]
    process: subprocess.CompletedProcess | None = None
    error = ""
    started_at = iso_now()
    try:
        atomic_write(
            args.lock_path,
            json.dumps(acquired_lock_payload(lock, estimate, args.slug), ensure_ascii=False, indent=2).encode() + b"\n",
        )
        process = subprocess.run(command, cwd=ROOT, env=os.environ.copy(), check=False)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(args.lock_path, original_lock)

    hook = read_json(run_dir / "asr_sync_hook_result.json") if (run_dir / "asr_sync_hook_result.json").exists() else {}
    diagnosis = read_json(run_dir / "asr_alignment_diagnosis.json") if (run_dir / "asr_alignment_diagnosis.json").exists() else {}
    construction = (
        read_json(run_dir / "bengali_tts_by_construction_report.json")
        if (run_dir / "bengali_tts_by_construction_report.json").exists()
        else {}
    )
    listening = read_json(run_dir / "listening_quality_report.json") if (run_dir / "listening_quality_report.json").exists() else {}
    samples = ((listening.get("listening_quality") or {}).get("samples") or [])
    listening_gate = owner_listening_gate(samples)
    source_gate = effective_source_gate(hook, diagnosis, construction)
    objective_pass = (
        hook.get("status") == "PASS"
        and source_gate["passes"]
        and listening_gate["passes"]
    )
    runtime = {
        **preflight,
        "status": "FULL_RELEASE_QA_PASS" if objective_pass else "FULL_RELEASE_QA_BLOCKED",
        "started_at": started_at,
        "finished_at": iso_now(),
        "provider_calls_ran": process is not None,
        "process_returncode": process.returncode if process else None,
        "hook_status": hook.get("status", "MISSING"),
        "hook_blockers": hook.get("blockers") or [],
        "raw_asr_source_score": diagnosis.get("score"),
        "source_match_score": source_gate["score"],
        "source_verification_method": source_gate["method"],
        "tts_by_construction_verified": source_gate["construction_verified"],
        "first_words_match": source_gate["first_words_match"],
        "last_words_match": source_gate["last_words_match"],
        "owner_listening_gate": listening_gate,
        "error": error or None,
        "actual_provider_billing": "NOT_REPORTED",
        "lock_restored": args.lock_path.read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(args.lock_path.read_bytes()).hexdigest(),
        "publication_performed": False,
    }
    atomic_write(args.result_path, json.dumps(runtime, ensure_ascii=False, indent=2).encode() + b"\n")
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0 if objective_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
