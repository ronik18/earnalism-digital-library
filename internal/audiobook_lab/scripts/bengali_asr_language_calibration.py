#!/usr/bin/env python3
"""Run a bounded, non-release Bengali ASR language calibration.

The calibration probes the opening chunk with each requested language option,
then evaluates the best option against the middle and ending chunks. Provider
calls are disabled unless --execute is supplied and the budget, credential,
and paid_tts.lock checks all pass.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional, Tuple


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = Path(__file__).resolve().parent / "factory_hooks"
sys.path.insert(0, str(HOOK_DIR))

import asr_sync_hook  # noqa: E402


DEFAULT_LOCK = ROOT / "internal/earnalism_intelligence/locks/paid_tts.lock"
EXPECTED_HOLDER = "audiobook_public_access_sprint_1_bn_066_asr_calibration"
DEFAULT_OPTIONS = ["auto", "bn", "ben", "bengali"]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def chunk_id(chunk: dict[str, Any]) -> str:
    return asr_sync_hook.asr_checkpoint_id(chunk, int(chunk.get("index") or 0))


def selected_chunks(manifest: dict[str, Any], requested_ids: list[str]) -> list[dict[str, Any]]:
    chunks = manifest.get("chunks") if isinstance(manifest.get("chunks"), list) else []
    by_id = {chunk_id(chunk): chunk for chunk in chunks}
    missing = [item for item in requested_ids if item not in by_id]
    if missing:
        raise ValueError(f"Unknown chunk ids: {', '.join(missing)}")
    return [by_id[item] for item in requested_ids]


def estimated_cost(duration_seconds: float, environ: dict[str, str]) -> float:
    raw_rate = environ.get("EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE", "").strip()
    rate = float(raw_rate) if raw_rate else asr_sync_hook.ASR_SYNC_DEFAULT_ESTIMATED_USD_PER_MINUTE
    return round((max(duration_seconds, 0.0) / 60.0) * max(rate, 0.0), 4)


def build_plan(
    manifest: dict[str, Any],
    requested_ids: list[str],
    language_options: list[str],
    environ: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    env = environ if environ is not None else dict(os.environ)
    chunks = selected_chunks(manifest, requested_ids)
    opening = chunks[0]
    followups = chunks[1:]
    calls = [
        {
            "phase": "opening_language_probe",
            "chunk_id": chunk_id(opening),
            "language_option": option,
            "duration_seconds": float(opening.get("duration_seconds") or 0.0),
        }
        for option in language_options
    ]
    calls.extend(
        {
            "phase": "best_option_validation",
            "chunk_id": chunk_id(chunk),
            "language_option": "BEST_FROM_OPENING_PROBE",
            "duration_seconds": float(chunk.get("duration_seconds") or 0.0),
        }
        for chunk in followups
    )
    total_duration = sum(float(item["duration_seconds"]) for item in calls)
    return {
        "slug": manifest.get("slug") or "bn-066",
        "strategy": "probe_all_language_options_on_opening_then_validate_best_on_middle_and_ending",
        "language_options": language_options,
        "selected_chunks": [
            {
                "chunk_id": chunk_id(chunk),
                "index": chunk.get("index"),
                "path": chunk.get("path"),
                "duration_seconds": chunk.get("duration_seconds"),
                "source_text_chars": len(str(chunk.get("text") or "")),
                "source_text_hash": asr_sync_hook.sha256_text(str(chunk.get("text") or "")),
            }
            for chunk in chunks
        ],
        "planned_provider_calls": len(calls),
        "planned_transcribed_seconds": round(total_duration, 3),
        "estimated_cost_usd": estimated_cost(total_duration, env),
        "calls": calls,
    }


def numeric_env(environ: dict[str, str], name: str) -> Tuple[Optional[float], Optional[str]]:
    raw = environ.get(name, "").strip()
    if not raw:
        return None, f"{name} is missing"
    try:
        value = float(raw)
    except ValueError:
        return None, f"{name} must be numeric"
    if value < 0:
        return None, f"{name} must be nonnegative"
    return value, None


def preflight(
    plan: dict[str, Any],
    environ: Optional[dict[str, str]] = None,
    lock: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    env = environ if environ is not None else dict(os.environ)
    lock_payload = lock if lock is not None else read_json(DEFAULT_LOCK)
    blockers: list[str] = []
    if env.get("EARNALISM_STOP_ON_BUDGET_EXCEEDED", "").strip().lower() != "true":
        blockers.append("EARNALISM_STOP_ON_BUDGET_EXCEEDED=true is required")
    total_cap, total_error = numeric_env(env, "MAX_TTS_BUDGET_USD")
    asr_cap, asr_error = numeric_env(env, "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD")
    if total_error:
        blockers.append(total_error)
    if asr_error:
        blockers.append(asr_error)
    estimate = float(plan.get("estimated_cost_usd") or 0.0)
    if total_cap is not None and estimate > total_cap:
        blockers.append(f"estimated calibration cost {estimate:.4f} exceeds MAX_TTS_BUDGET_USD={total_cap:.4f}")
    if asr_cap is not None and estimate > asr_cap:
        blockers.append(
            f"estimated calibration cost {estimate:.4f} exceeds EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD={asr_cap:.4f}"
        )
    if not env.get("OPENAI_API_KEY", "").strip():
        blockers.append("OPENAI_API_KEY is missing")
    if lock_payload.get("status") != "active":
        blockers.append("paid_tts.lock is not active")
    if lock_payload.get("current_holder") != EXPECTED_HOLDER:
        blockers.append(f"paid_tts.lock current_holder must be {EXPECTED_HOLDER}")
    allowed_slugs = lock_payload.get("allowed_slugs") if isinstance(lock_payload.get("allowed_slugs"), list) else []
    if plan.get("slug") not in allowed_slugs:
        blockers.append(f"paid_tts.lock allowed_slugs must include {plan.get('slug')}")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "provider_calls_allowed": not blockers,
        "estimated_cost_usd": estimate,
        "total_cap_usd": total_cap,
        "asr_cap_usd": asr_cap,
        "lock_status": lock_payload.get("status"),
        "lock_holder": lock_payload.get("current_holder"),
        "expected_lock_holder": EXPECTED_HOLDER,
        "blockers": blockers,
    }


def result_payload(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return json.loads(result.json())


def transcribe_option(client: Any, audio_path: Path, language_option: str) -> dict[str, Any]:
    params: dict[str, Any] = {"model": asr_sync_hook.ASR_MODEL, "response_format": "verbose_json"}
    if language_option != "auto":
        params["language"] = language_option
    with audio_path.open("rb") as handle:
        result = asr_sync_hook.transcribe_with_fallbacks(client, handle, params)
    return result_payload(result)


def evaluate_transcript(chunk: dict[str, Any], language_option: str, payload: dict[str, Any]) -> dict[str, Any]:
    transcript = str(payload.get("text") or "").strip()
    source = str(chunk.get("text") or "").strip()
    profile = asr_sync_hook.transcript_script_profile(transcript)
    alignment = asr_sync_hook.transcript_similarity(source, transcript)
    return {
        "chunk_id": chunk_id(chunk),
        "language_option": language_option,
        "status": "PASS" if transcript else "EMPTY_TRANSCRIPT",
        "transcript_text": transcript,
        "transcript_chars": len(transcript),
        "script_profile": profile,
        "alignment": alignment,
    }


def best_opening_result(results: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    usable = [item for item in results if item.get("status") == "PASS"]
    if not usable:
        return None
    return max(
        usable,
        key=lambda item: (
            float(item.get("script_profile", {}).get("ratios", {}).get("bengali") or 0.0),
            float(item.get("alignment", {}).get("score") or 0.0),
            int(item.get("transcript_chars") or 0),
        ),
    )


def execute_calibration(plan: dict[str, Any], manifest: dict[str, Any], requested_ids: list[str]) -> dict[str, Any]:
    from openai import OpenAI

    chunks = selected_chunks(manifest, requested_ids)
    client = OpenAI(timeout=asr_sync_hook.asr_request_timeout_seconds(), max_retries=0)
    opening_results: list[dict[str, Any]] = []
    for option in plan["language_options"]:
        path = ROOT / str(chunks[0].get("path") or "")
        try:
            opening_results.append(evaluate_transcript(chunks[0], option, transcribe_option(client, path, option)))
        except Exception as exc:  # noqa: BLE001
            opening_results.append(
                {
                    "chunk_id": chunk_id(chunks[0]),
                    "language_option": option,
                    "status": "PROVIDER_ERROR",
                    "error": str(exc)[:500],
                }
            )
    best = best_opening_result(opening_results)
    followup_results: list[dict[str, Any]] = []
    if best:
        option = str(best["language_option"])
        for chunk in chunks[1:]:
            path = ROOT / str(chunk.get("path") or "")
            try:
                followup_results.append(evaluate_transcript(chunk, option, transcribe_option(client, path, option)))
            except Exception as exc:  # noqa: BLE001
                followup_results.append(
                    {
                        "chunk_id": chunk_id(chunk),
                        "language_option": option,
                        "status": "PROVIDER_ERROR",
                        "error": str(exc)[:500],
                    }
                )
    evaluated = ([best] if best else []) + followup_results
    calibration_usable = bool(evaluated) and all(
        item.get("status") == "PASS"
        and float(item.get("script_profile", {}).get("ratios", {}).get("bengali") or 0.0) >= 0.9
        and float(item.get("alignment", {}).get("score") or 0.0) >= 7.0
        for item in evaluated
    )
    return {
        "status": "CALIBRATION_SETTING_IDENTIFIED" if calibration_usable else "ASR_LANGUAGE_CONFIG_REPAIR_REQUIRED",
        "public_release_approval": "NONE",
        "best_language_option": best.get("language_option") if best else None,
        "opening_results": opening_results,
        "followup_results": followup_results,
        "calibration_usable_for_full_asr_plan": calibration_usable,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", default="bn-066")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--chunk-ids", default="group_0000,group_0076,group_0151")
    parser.add_argument("--language-options", default=",".join(DEFAULT_OPTIONS))
    parser.add_argument("--output", default="")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir
    manifest_path = run_dir / "tts_chunk_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("slug") and manifest.get("slug") != args.slug:
        raise SystemExit(f"Manifest slug {manifest.get('slug')} does not match {args.slug}")
    requested_ids = [item.strip() for item in args.chunk_ids.split(",") if item.strip()]
    language_options = [item.strip().lower() for item in args.language_options.split(",") if item.strip()]
    plan = build_plan(manifest, requested_ids, language_options)
    plan["slug"] = args.slug
    guard = preflight(plan)
    output_path = Path(args.output) if args.output else run_dir / "asr_language_calibration_report.json"
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    report: dict[str, Any] = {
        "schema_version": 1,
        "slug": args.slug,
        "mode": "EXECUTE" if args.execute else "DRY_RUN",
        "plan": plan,
        "preflight": guard,
        "provider_calls_ran": False,
        "public_release_approval": "NONE",
    }
    if args.execute:
        if not guard["provider_calls_allowed"]:
            report["status"] = "PREFLIGHT_BLOCKED"
            write_json(output_path, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2
        report["result"] = execute_calibration(plan, manifest, requested_ids)
        report["provider_calls_ran"] = True
        report["status"] = report["result"]["status"]
    else:
        report["status"] = "DRY_RUN_READY" if guard["provider_calls_allowed"] else "DRY_RUN_BLOCKED_PAID_GATES"
    report["report_path"] = str(output_path.relative_to(ROOT)) if output_path.is_relative_to(ROOT) else str(output_path)
    write_json(output_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
