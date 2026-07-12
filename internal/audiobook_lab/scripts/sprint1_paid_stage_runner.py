#!/usr/bin/env python3
"""Run one paid Sprint 1 command while holding and restoring paid_tts.lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


REQUIRED_ENV = (
    "SPRINT1_TOTAL_AUDIO_BUDGET_USD",
    "SPRINT1_MAX_USD_PER_TITLE",
    "MAX_TTS_BUDGET_USD",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED",
)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_positive_float(name: str, raw: str | None) -> float:
    if raw is None or not raw.strip():
        raise ValueError(f"{name} is missing")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def budget_guard(estimated_usd: float, prior_spend_usd: float, env: dict[str, str]) -> dict[str, float]:
    missing = [name for name in REQUIRED_ENV if not env.get(name)]
    if missing:
        raise ValueError("required paid environment gates are missing: " + ", ".join(missing))
    if env["EARNALISM_STOP_ON_BUDGET_EXCEEDED"].strip().lower() not in {"1", "true", "yes"}:
        raise ValueError("EARNALISM_STOP_ON_BUDGET_EXCEEDED must be true")
    sprint_cap = parse_positive_float("SPRINT1_TOTAL_AUDIO_BUDGET_USD", env.get("SPRINT1_TOTAL_AUDIO_BUDGET_USD"))
    title_cap = parse_positive_float("SPRINT1_MAX_USD_PER_TITLE", env.get("SPRINT1_MAX_USD_PER_TITLE"))
    max_tts_cap = parse_positive_float("MAX_TTS_BUDGET_USD", env.get("MAX_TTS_BUDGET_USD"))
    if estimated_usd < 0 or prior_spend_usd < 0:
        raise ValueError("estimated and prior spend must be non-negative")
    if estimated_usd > title_cap:
        raise ValueError(f"estimated title-stage cost ${estimated_usd:.4f} exceeds per-title cap ${title_cap:.4f}")
    effective_total_cap = min(sprint_cap, max_tts_cap)
    if prior_spend_usd + estimated_usd > effective_total_cap:
        raise ValueError(
            f"estimated cumulative spend ${prior_spend_usd + estimated_usd:.4f} exceeds total cap ${effective_total_cap:.4f}"
        )
    return {
        "sprint_cap_usd": sprint_cap,
        "per_title_cap_usd": title_cap,
        "max_tts_cap_usd": max_tts_cap,
        "effective_total_cap_usd": effective_total_cap,
        "estimated_stage_usd": estimated_usd,
        "prior_estimated_spend_usd": prior_spend_usd,
        "estimated_cumulative_spend_usd": prior_spend_usd + estimated_usd,
    }


def load_available_lock(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("paid_tts.lock is not valid UTF-8 JSON") from exc
    if payload.get("status") != "active":
        raise ValueError("paid_tts.lock status must be active")
    if payload.get("current_holder") != "none":
        raise ValueError("paid_tts.lock already has a holder")
    if payload.get("allowed_next_holders") != []:
        raise ValueError("paid_tts.lock allowed_next_holders must be empty")
    return payload


def acquired_lock_payload(
    lock: dict[str, Any], *, holder: str, slug: str, scope: str, estimated_usd: float, budget: dict[str, float]
) -> dict[str, Any]:
    return {
        **lock,
        "status": "active",
        "current_holder": holder,
        "allowed_next_holders": [],
        "holder_started_at": iso_now(),
        "approved_scope": scope,
        "allowed_slugs": [slug],
        "budget_cap_usd": budget["effective_total_cap_usd"],
        "estimated_stage_spend_usd": estimated_usd,
        "updated_at": iso_now(),
    }


def run_paid_stage(args: argparse.Namespace, *, env: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
    process_env = dict(os.environ if env is None else env)
    started_at = iso_now()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    report: dict[str, Any] = {
        "status": "BLOCKED_BEFORE_PROVIDER_CALL",
        "started_at": started_at,
        "finished_at": None,
        "holder": args.holder,
        "slug": args.slug,
        "scope": args.scope,
        "estimated_stage_usd": args.estimated_usd,
        "prior_estimated_spend_usd": args.prior_spend_usd,
        "command": command,
        "provider_command_started": False,
        "process_returncode": None,
        "timed_out": False,
        "actual_provider_billing": "NOT_REPORTED",
        "lock_restored": False,
        "lock_sha256_before": None,
        "lock_sha256_after": None,
        "blockers": [],
    }
    original_lock: bytes | None = None
    acquired = False
    returncode = 2
    try:
        if not command:
            raise ValueError("a subprocess command is required after --")
        budget = budget_guard(args.estimated_usd, args.prior_spend_usd, process_env)
        report["budget"] = budget
        if not args.lock_path.is_file():
            raise ValueError(f"paid_tts.lock is missing: {args.lock_path}")
        original_lock = args.lock_path.read_bytes()
        report["lock_sha256_before"] = sha256_bytes(original_lock)
        lock = load_available_lock(original_lock)
        acquired_payload = acquired_lock_payload(
            lock,
            holder=args.holder,
            slug=args.slug,
            scope=args.scope,
            estimated_usd=args.estimated_usd,
            budget=budget,
        )
        args.lock_path.write_text(json.dumps(acquired_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        acquired = True
        report["provider_command_started"] = True
        try:
            completed = subprocess.run(
                command,
                cwd=str(args.workdir),
                env=process_env,
                timeout=args.timeout_seconds,
                check=False,
            )
            returncode = int(completed.returncode)
            report["process_returncode"] = returncode
            report["status"] = "PASS" if returncode == 0 else "SUBPROCESS_FAILED"
            if returncode != 0:
                report["blockers"].append(f"paid subprocess exited with status {returncode}")
        except subprocess.TimeoutExpired:
            returncode = 124
            report["process_returncode"] = returncode
            report["timed_out"] = True
            report["status"] = "PROVIDER_TIMEOUT"
            report["blockers"].append(f"paid subprocess exceeded timeout of {args.timeout_seconds} seconds")
    except (OSError, ValueError) as exc:
        report["blockers"].append(str(exc))
    finally:
        if acquired and original_lock is not None:
            args.lock_path.write_bytes(original_lock)
        if original_lock is not None and args.lock_path.is_file():
            after = args.lock_path.read_bytes()
            report["lock_sha256_after"] = sha256_bytes(after)
            report["lock_restored"] = after == original_lock
            if acquired and not report["lock_restored"]:
                report["status"] = "LOCK_RESTORE_FAILED"
                report["blockers"].append("paid_tts.lock was not restored byte-for-byte")
                returncode = 2
        report["finished_at"] = iso_now()
        write_json(args.report, report)
    return returncode, report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--holder", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--estimated-usd", type=float, required=True)
    parser.add_argument("--prior-spend-usd", type=float, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    returncode, report = run_paid_stage(args)
    print(json.dumps({"status": report["status"], "report": str(args.report), "blockers": report["blockers"]}, ensure_ascii=False))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
