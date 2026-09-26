#!/usr/bin/env python3
"""Independent reviewer for bounded worker evidence."""
import argparse, json, subprocess, time
from pathlib import Path

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task-id", required=True); p.add_argument("--candidate-sha", required=True); p.add_argument("--generation", type=int, required=True)
    p.add_argument("--worker-result", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    worker = json.loads(a.worker_result.read_text(encoding="utf-8"))
    if actual != a.candidate_sha or worker.get("tested_revision") != actual or worker.get("generation") != a.generation:
        raise SystemExit("review rejected stale or mismatched revision")
    tests = worker.get("tests") or []
    decision = "ACCEPT_WITHIN_SCOPE" if worker.get("state") == "REVIEW" and tests and all(t.get("exit_code") == 0 for t in tests) else "CHANGES_REQUIRED"
    findings = [] if decision == "ACCEPT_WITHIN_SCOPE" else ["worker evidence is incomplete or contains a failing command"]
    result = {"task_id": a.task_id, "tested_revision": actual, "generation": a.generation, "decision": decision, "findings": findings, "generated_at": int(time.time())}
    a.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
