#!/usr/bin/env python3
"""Independent reviewer: validates worker evidence and candidate identity."""
import argparse, json, subprocess, time
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument("--task-id",required=True); p.add_argument("--candidate-head",required=True); p.add_argument("--worker-result",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    actual=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(); worker=json.loads(a.worker_result.read_text())
    if actual != a.candidate_head or worker.get("tested_revision") != actual: raise SystemExit("review rejected stale or mismatched revision")
    findings = worker.get("unresolved_findings", [])
    state = worker.get("state")
    decision = {"REVIEW": "ACCEPT_WITHIN_SCOPE", "CHANGES_REQUIRED": "CHANGES_REQUIRED", "WAITING_DEPENDENCY": "WAITING_DEPENDENCY"}.get(state, "BLOCKED_SPECIFIC_FACT")
    tests = worker.get("tests") or []
    required = {"uncached-next", "prefetched-next", "cached-previous", "rapid-navigation", "delayed-response-retains-current-page"}
    scenarios = set(worker.get("scenarios") or [])
    artifact_paths = worker.get("artifacts") or []
    if decision == "ACCEPT_WITHIN_SCOPE":
        if not tests:
            decision, findings = "CHANGES_REQUIRED", ["worker reported review without executable test evidence"]
        elif any(item.get("exit_code") != 0 for item in tests if isinstance(item, dict)):
            decision, findings = "CHANGES_REQUIRED", ["worker reported a non-zero benchmark command as successful"]
        elif scenarios and not required.issubset(scenarios):
            decision, findings = "CHANGES_REQUIRED", ["required Reader benchmark scenarios are missing"]
        elif any(not str(item).startswith("uat/evidence/") for item in artifact_paths):
            decision, findings = "CHANGES_REQUIRED", ["artifact reference escapes the approved current-run evidence directory"]
    result={"task_id":a.task_id,"tested_revision":actual,"decision":decision,"findings":findings,"next_action":worker.get("proposed_next_action"),"state_transition":{"from":"RUNNING","to":decision},"generated_at":int(time.time())}
    a.output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result))

if __name__ == "__main__": main()
