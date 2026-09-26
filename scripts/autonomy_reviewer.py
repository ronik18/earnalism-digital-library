#!/usr/bin/env python3
"""Independent reviewer: validates worker evidence and candidate identity."""
import argparse, json, subprocess, time
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument("--task-id",required=True); p.add_argument("--candidate-head",required=True); p.add_argument("--worker-result",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    actual=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(); worker=json.loads(a.worker_result.read_text())
    if actual != a.candidate_head or worker.get("tested_revision") != actual: raise SystemExit("review rejected stale or mismatched revision")
    result={"task_id":a.task_id,"tested_revision":actual,"decision":"BLOCKED_SPECIFIC_FACT","findings":worker.get("unresolved_findings",[]),"next_action":worker.get("proposed_next_action"),"generated_at":int(time.time())}
    a.output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result))

if __name__ == "__main__": main()
