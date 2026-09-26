#!/usr/bin/env python3
"""Bounded non-production worker used by the coordination bridge."""
import argparse, json, subprocess, time
from pathlib import Path

ALLOWED = {"reader-benchmark": ("scripts", "frontend/src")}

def main():
    p = argparse.ArgumentParser(); p.add_argument("--task-id", required=True); p.add_argument("--candidate-head", required=True); p.add_argument("--output", type=Path, required=True); a=p.parse_args()
    if a.task_id not in ALLOWED: raise SystemExit(f"task not approved for autonomous worker: {a.task_id}")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if actual != a.candidate_head: raise SystemExit(f"stale candidate: expected {a.candidate_head}, got {actual}")
    result = {"task_id": a.task_id, "tested_revision": actual, "files_changed": [], "actions_completed": ["isolated worker started", "candidate identity validated"], "tests": [], "artifacts": [], "unresolved_findings": ["Reader browser benchmark PR is not yet on the trusted default branch"], "proposed_next_action": "WAIT_FOR_READER_BENCHMARK_MERGE", "generated_at": int(time.time())}
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

if __name__ == "__main__": main()
