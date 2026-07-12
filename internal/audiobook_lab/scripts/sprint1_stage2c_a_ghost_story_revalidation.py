#!/usr/bin/env python3
"""Run sentence-aligned A Ghost Story listening QA without TTS or ASR."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
sys.path[:0] = [str(ROOT / "internal/audiobook_lab/scripts"), str(HOOK_DIR)]

from asr_sync_hook import (  # noqa: E402
    BINARY_LISTENING_FLAGS,
    LISTENING_THRESHOLDS,
    base_listening_report,
    judge_audio_sample_with_openai,
    openai_listening_qa_budget_guard,
    safe_float,
    validate_listening_quality_report,
)
from common import ffprobe_duration, sha256_file  # noqa: E402


EXPECTED_AUDIO_SHA256 = "00190d747d2894a244545a260f10f4e06ccc597352d2767414acc4edfe6e5a55"
EXPECTED_ENV = {
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
    "SPRINT1_MAX_USD_PER_TITLE": "30",
    "MAX_TTS_BUDGET_USD": "175",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "2",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
}
HOLDER = "sprint1_publication_stage2c"
RESULT_PATH = (
    ROOT
    / "internal/audiobook_lab/sprint1_publication/title_runs/"
    "a-ghost-story_stage2c_listening_qa_runtime.json"
)


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
    if not os.environ.get("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is required")
    return errors


def sample_specs() -> list[dict]:
    return [
        {
            "sample_label": "opening_sentence_aligned",
            "start_time": 0.0,
            "end_time": 60.74,
            "start_word": "A",
            "end_word": "now",
        },
        {
            "sample_label": "middle_sentence_aligned",
            "start_time": 353.66,
            "end_time": 409.68,
            "start_word": "Then",
            "end_word": "eyes",
        },
        {
            "sample_label": "ending_sentence_aligned",
            "start_time": 704.9,
            "end_time": 765.08,
            "start_word": "I",
            "end_word": "bathtub",
        },
    ]


def sample_fingerprint(audio_hash: str, specs: list[dict], model: str) -> str:
    encoded = json.dumps(
        {"audio_hash": audio_hash, "samples": specs, "model": model},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_lock(raw: bytes) -> dict:
    payload = json.loads(raw)
    if payload.get("status") != "active":
        raise RuntimeError("paid_tts.lock must remain active")
    if payload.get("current_holder") != "none":
        raise RuntimeError("paid_tts.lock already has a holder")
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
            "budget_cap_usd": 175,
            "approved_scope": (
                "A Ghost Story sentence-aligned listening QA only; three OpenAI audio judgments, "
                "estimated 0.15 USD, no TTS, ASR, upload, publication, or release-gate mutation."
            ),
            "allowed_slugs": ["a-ghost-story"],
            "stop_conditions": [
                "Any required runtime gate or OPENAI_API_KEY is missing",
                "Audio or sidecar hash validation fails",
                "Sentence boundary validation fails",
                "Listening-QA budget guard blocks",
                "The same sample fingerprint already completed",
                "Any TTS, ASR, upload, publication, or release mutation is attempted",
            ],
            "updated_at": iso_now(),
        }
    )
    return payload


def asset_paths(asset_root: Path) -> dict[str, Path]:
    release_root = asset_root / "internal/audiobook_lab/release_gate"
    return {
        "audio": release_root / "a-ghost-story_20260705T044404Z/a-ghost-story_existing_audio_candidate.mp3",
        "manuscript": release_root / "a-ghost-story_20260705T150049Z/clean_manuscript.txt",
        "timestamps": release_root / "a-ghost-story_20260705T150049Z/reused_timestamps.json",
        "prior_report": release_root / "a-ghost-story_20260705T150049Z/listening_quality_report.json",
        "lock": asset_root / "internal/earnalism_intelligence/locks/paid_tts.lock",
    }


def find_boundary(words: list[dict], *, field: str, value: float, expected_word: str, tolerance: float = 0.03) -> dict:
    matches = [
        word
        for word in words
        if abs(safe_float(word.get(field), -999.0) - value) <= tolerance
        and str(word.get("word") or "").lower() == expected_word.lower()
    ]
    if not matches:
        raise RuntimeError(f"No timestamp boundary for {expected_word!r} at {field}={value}")
    return matches[0]


def verify_assets(paths: dict[str, Path], specs: list[dict]) -> dict:
    for name, path in paths.items():
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"Required {name} artifact is missing or empty: {path}")
    audio_hash = sha256_file(paths["audio"])
    if audio_hash != EXPECTED_AUDIO_SHA256:
        raise RuntimeError("A Ghost Story audio hash changed; refusing cached-evidence revalidation")
    timestamps = json.loads(paths["timestamps"].read_text(encoding="utf-8"))
    if timestamps.get("audio_hash") != audio_hash:
        raise RuntimeError("Timestamp audio hash does not match the candidate audio")
    words = timestamps.get("words") if isinstance(timestamps.get("words"), list) else []
    for spec in specs:
        find_boundary(words, field="start", value=spec["start_time"], expected_word=spec["start_word"])
        find_boundary(words, field="end", value=spec["end_time"], expected_word=spec["end_word"])
    prior = json.loads(paths["prior_report"].read_text(encoding="utf-8"))
    listening = prior.get("listening_quality") if isinstance(prior.get("listening_quality"), dict) else {}
    if prior.get("audio_hash") != audio_hash or listening.get("model_or_judge") != "openai:gpt-audio":
        raise RuntimeError("Prior listening report is not bound to the same audio hash and model")
    cached = {
        sample.get("sample_label"): sample
        for sample in listening.get("samples") or []
        if sample.get("sample_label") in {"random_1", "random_2", "random_3"}
    }
    if set(cached) != {"random_1", "random_2", "random_3"}:
        raise RuntimeError("Three prior random listening samples are required for six-sample schema validation")
    return {
        "audio_hash": audio_hash,
        "audio_duration_seconds": ffprobe_duration(paths["audio"]),
        "cached_samples": [cached[name] for name in ("random_1", "random_2", "random_3")],
    }


def extract_samples(audio_path: Path, output_dir: Path, specs: list[dict]) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    samples: list[dict] = []
    for index, spec in enumerate(specs, start=1):
        target = output_dir / f"sample_{index:02d}_{spec['sample_label']}.mp3"
        duration = round(spec["end_time"] - spec["start_time"], 3)
        completed = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(audio_path),
                "-ss",
                f"{spec['start_time']:.3f}",
                "-t",
                f"{duration:.3f}",
                "-c:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(target),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
        actual_duration = ffprobe_duration(target) if target.exists() else None
        if completed.returncode != 0 or not target.exists() or target.stat().st_size <= 0 or not actual_duration:
            raise RuntimeError(f"Failed to extract {spec['sample_label']}: {completed.stderr[-500:]}")
        samples.append(
            {
                **spec,
                "duration": round(actual_duration, 3),
                "sample_audio_path": str(target),
                "sample_audio_hash": sha256_file(target),
                "sentence_aligned": True,
                "fresh_stage2c_judgment": True,
            }
        )
    return samples


def aggregate_samples(samples: list[dict]) -> tuple[dict, dict]:
    aggregate = {
        field: round(min(safe_float((sample.get("scores") or {}).get(field)) for sample in samples), 4)
        for field in LISTENING_THRESHOLDS
    }
    flags = {
        field: any(bool((sample.get("judge_flags") or {}).get(field)) for sample in samples)
        for field in BINARY_LISTENING_FLAGS
    }
    return aggregate, flags


def owner_minimum_result(samples: list[dict], flags: dict) -> dict:
    minimum_overall = min(safe_float((sample.get("scores") or {}).get("overall_listening_score")) for sample in samples)
    minimum_confidence = min(safe_float((sample.get("scores") or {}).get("confidence_score")) for sample in samples)
    fatal_flags = [field for field, detected in flags.items() if detected]
    return {
        "passes": minimum_overall >= 9.4 and minimum_confidence >= 0.9 and not fatal_flags,
        "minimum_overall_score": round(minimum_overall, 4),
        "minimum_confidence": round(minimum_confidence, 4),
        "fatal_flags": fatal_flags,
    }


def completed_attempt_exists(fingerprint: str) -> bool:
    if not RESULT_PATH.exists():
        return False
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    return payload.get("sample_fingerprint") == fingerprint and payload.get("provider_calls_ran") is True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asset-root",
        default=os.environ.get("EARNALISM_STAGE2C_ASSET_ROOT", str(ROOT)),
        help="Checkout containing the private A Ghost Story evidence and paid lock.",
    )
    parser.add_argument(
        "--output-dir",
        default="/tmp/earnalism-a-ghost-stage2c-middle-repair/revalidation",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = runtime_gate_errors()
    if errors:
        print(json.dumps({"status": "BLOCKED_RUNTIME_GATES", "errors": errors}, indent=2))
        return 2

    specs = sample_specs()
    asset_root = Path(args.asset_root).expanduser().resolve()
    paths = asset_paths(asset_root)
    original_lock = paths["lock"].read_bytes()
    lock = load_lock(original_lock)
    verified = verify_assets(paths, specs)
    fingerprint = sample_fingerprint(
        verified["audio_hash"],
        specs,
        os.environ["EARNALISM_OPENAI_LISTENING_QA_MODEL"],
    )
    if completed_attempt_exists(fingerprint):
        print(json.dumps({"status": "BLOCKED_REPEAT_ATTEMPT", "sample_fingerprint": fingerprint}, indent=2))
        return 4
    budget = openai_listening_qa_budget_guard(sample_count=len(specs))
    if not budget.get("ok"):
        print(json.dumps({"status": "BLOCKED_BUDGET", "budget": budget}, indent=2))
        return 2

    output_dir = Path(args.output_dir).expanduser().resolve()
    fresh_samples = extract_samples(paths["audio"], output_dir, specs)
    preflight = {
        "status": "PASS",
        "owner_decision": "AUTHORIZE_STAGE_2C_A_GHOST_STORY_AUDIO_REPAIR_AND_PUBLICATION_IF_QUALITY_10_TARGET_PASSES",
        "slug": "a-ghost-story",
        "root_cause": "SAMPLE_WINDOW_MISALIGNED",
        "original_middle_start_seconds": 352.787,
        "original_start_word_span_seconds": [352.44, 353.46],
        "corrected_middle_span_seconds": [353.66, 409.68],
        "audio_hash": verified["audio_hash"],
        "audio_duration_seconds": verified["audio_duration_seconds"],
        "sample_fingerprint": fingerprint,
        "fresh_sample_count": len(fresh_samples),
        "cached_random_sample_count": len(verified["cached_samples"]),
        "budget_guard": budget,
        "provider_calls_ran": False,
        "tts_calls_ran": False,
        "asr_calls_ran": False,
        "publication_performed": False,
        "lock_sha256_before": hashlib.sha256(original_lock).hexdigest(),
    }
    if args.dry_run:
        print(json.dumps({**preflight, "status": "DRY_RUN_PASS"}, indent=2))
        return 0

    from openai import OpenAI  # noqa: PLC0415

    class JudgeArgs:
        slug = "a-ghost-story"
        title = "A Ghost Story"
        author = "Mark Twain"
        language = "eng"

    started_at = iso_now()
    report: dict = {}
    error = ""
    provider_calls_ran = False
    try:
        atomic_write(
            paths["lock"],
            json.dumps(acquired_lock_payload(lock), ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
        )
        client = OpenAI()
        judged_fresh = []
        for sample in fresh_samples:
            provider_calls_ran = True
            judged_fresh.append(judge_audio_sample_with_openai(client, JudgeArgs(), sample))
        all_samples = [*judged_fresh, *verified["cached_samples"]]
        aggregate, flags = aggregate_samples(all_samples)
        report = base_listening_report(
            JudgeArgs(),
            paths["audio"],
            verified["audio_hash"],
            all_samples,
            status="PASS",
            blockers=[],
            model_or_judge="openai:gpt-audio",
        )
        listening = report["listening_quality"]
        listening["aggregate"] = aggregate
        listening.update(flags)
        listening["dialogue_emotional_sections_judged"] = True
        listening["stage2c_sentence_aligned_revalidation"] = True
        repo_pass, repo_blockers = validate_listening_quality_report(
            report,
            expected_audio_hash=verified["audio_hash"],
            language="eng",
        )
        if not repo_pass:
            listening["status"] = "BLOCKED"
            listening["blockers"] = sorted(set(repo_blockers))
        report["owner_minimum"] = owner_minimum_result(all_samples, flags)
        report["repo_release_gate_pass"] = repo_pass
        report["sample_fingerprint"] = fingerprint
        report["fresh_judgment_labels"] = [sample["sample_label"] for sample in judged_fresh]
        report["cached_judgment_labels"] = [sample["sample_label"] for sample in verified["cached_samples"]]
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        atomic_write(paths["lock"], original_lock)

    report_path = output_dir / "stage2c_sentence_aligned_listening_quality_report.json"
    if report:
        atomic_write(report_path, json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    release_pass = bool(report.get("repo_release_gate_pass")) and bool((report.get("owner_minimum") or {}).get("passes"))
    runtime = {
        **preflight,
        "status": "LISTENING_QA_PASS" if release_pass else "LISTENING_QA_BLOCKED",
        "started_at": started_at,
        "finished_at": iso_now(),
        "provider_calls_ran": provider_calls_ran,
        "estimated_new_spend_usd": budget.get("estimated_qa_cost_usd"),
        "actual_provider_billing": "NOT_REPORTED",
        "repo_release_gate_pass": report.get("repo_release_gate_pass", False),
        "owner_minimum": report.get("owner_minimum", {}),
        "listening_quality": (report.get("listening_quality") or {}).get("aggregate", {}),
        "blockers": (report.get("listening_quality") or {}).get("blockers", []),
        "error": error or None,
        "report_path": str(report_path),
        "lock_restored": paths["lock"].read_bytes() == original_lock,
        "lock_sha256_after": hashlib.sha256(paths["lock"].read_bytes()).hexdigest(),
        "publication_performed": False,
    }
    atomic_write(RESULT_PATH, json.dumps(runtime, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0 if release_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
