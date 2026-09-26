#!/usr/bin/env python3
"""Bounded worker for approved non-production bridge tasks."""
import argparse, json, os, subprocess, time
from pathlib import Path

ALLOWED = {"bridge-fixture", "reader-benchmark"}

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task-id", required=True)
    p.add_argument("--candidate-head", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.task_id not in ALLOWED:
        raise SystemExit("task type is not approved")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if actual != args.candidate_head:
        raise SystemExit(f"stale candidate: expected {args.candidate_head}, got {actual}")
    if args.task_id == "bridge-fixture":
        command = [os.environ.get("PYTHON", "python3"), "-m", "unittest", "scripts.test_autonomy_bridge"]
    else:
        command = ["bash", "scripts/run_reader_benchmark.sh"]
    proc = subprocess.run(command, text=True, capture_output=True, timeout=120)
    result = {
        "task_id": args.task_id,
        "tested_revision": actual,
        "state": "REVIEW" if proc.returncode == 0 else "CHANGES_REQUIRED",
        "tests": [{"command": " ".join(command), "exit_code": proc.returncode, "stdout": proc.stdout[-2000:]}],
        "files_changed": [],
        "artifacts": [],
        "unresolved_findings": [] if proc.returncode == 0 else [proc.stderr[-2000:] or "worker command failed"],
        "proposed_next_action": "REVIEW" if proc.returncode == 0 else "FIX_WORKER",
        "generated_at": int(time.time()),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if proc.returncode == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
