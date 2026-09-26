#!/usr/bin/env python3
"""Bounded non-production worker used by the coordination bridge."""
import argparse, json, os, subprocess, time
from pathlib import Path

ALLOWED = {"reader-benchmark": ("scripts", "frontend/src")}

def main():
    p = argparse.ArgumentParser(); p.add_argument("--task-id", required=True); p.add_argument("--candidate-head", required=True); p.add_argument("--output", type=Path, required=True); a=p.parse_args()
    if a.task_id not in ALLOWED: raise SystemExit(f"task not approved for autonomous worker: {a.task_id}")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if actual != a.candidate_head: raise SystemExit(f"stale candidate: expected {a.candidate_head}, got {actual}")
    result = {"task_id": a.task_id, "tested_revision": actual, "files_changed": [], "actions_completed": ["isolated worker started", "candidate identity validated"], "tests": [], "artifacts": [], "unresolved_findings": [], "proposed_next_action": "REVIEW", "state": "REVIEW", "generated_at": int(time.time())}
    if os.environ.get("BRIDGE_MODE", "PLAN_ONLY") != "EXECUTION_ENABLED":
        result.update(state="WAITING_DEPENDENCY", unresolved_findings=["execution mode is PLAN_ONLY"], proposed_next_action="WAIT_FOR_EXECUTION_ENABLE")
    elif a.task_id == "reader-benchmark":
        runner = Path("scripts/run_reader_benchmark.sh")
        if not runner.is_file():
            result.update(state="WAITING_DEPENDENCY", unresolved_findings=["approved reader benchmark runner is absent"], proposed_next_action="WAIT_FOR_READER_BENCHMARK_DEPENDENCY")
        else:
            proc = subprocess.run(["bash", str(runner)], text=True, capture_output=True, timeout=900)
            result["tests"].append({"command": str(runner), "exit_code": proc.returncode})
            result["actions_completed"].append("executed approved reader benchmark runner")
            if proc.returncode == 0:
                result.update(state="REVIEW", artifacts=[str(p) for p in Path("uat/evidence").rglob("benchmark.json")], proposed_next_action="REVIEW")
            else:
                result.update(state="CHANGES_REQUIRED", unresolved_findings=[proc.stderr[-2000:] or "benchmark runner failed"], proposed_next_action="FIX_BENCHMARK")
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

if __name__ == "__main__": main()
