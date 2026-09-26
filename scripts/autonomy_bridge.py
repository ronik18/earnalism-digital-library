#!/usr/bin/env python3
"""Deterministic, fail-closed coordinator planner.

The workflow supplies current GitHub state as JSON. This module only plans
bounded next actions; it never turns model or issue text into shell commands.
"""
from __future__ import annotations

import argparse, json
from pathlib import Path

TERMINAL = {"DONE", "BLOCKED_EXACT_REASON", "WAITING_OWNER_PROVIDER_UPDATE"}

def plan(state: dict) -> dict:
    tasks = state.get("tasks", [])
    actions = []
    for task in tasks:
        status = task.get("state", "READY")
        if status in TERMINAL:
            continue
        checks = task.get("checks", {})
        if status == "WAITING_CI":
            if checks.get("failed"):
                actions.append({"task_id": task["task_id"], "action": "REVIEW_FAILURE", "reason": checks["failed"]})
            elif checks.get("all_passed"):
                actions.append({"task_id": task["task_id"], "action": "ADVANCE", "next_state": task.get("next_state", "READY_FOR_REVIEW")})
            else:
                actions.append({"task_id": task["task_id"], "action": "WAIT"})
        elif status == "READY":
            actions.append({"task_id": task["task_id"], "action": "DISPATCH", "lane": task.get("lane"), "file_scope": task.get("file_scope", [])})
        elif status == "READY_FOR_REVIEW":
            actions.append({"task_id": task["task_id"], "action": "REVIEW", "revision": task.get("head")})
        elif status == "READY_FOR_MERGE":
            if checks.get("all_passed") and task.get("approved") is True:
                actions.append({"task_id": task["task_id"], "action": "MERGE_PROTECTED"})
            else:
                actions.append({"task_id": task["task_id"], "action": "BLOCK", "reason": "required checks or approval missing"})
        elif status == "VERIFYING_PRODUCTION":
            actions.append({"task_id": task["task_id"], "action": "VERIFY_PRODUCTION"})
    return {"schema_version": 1, "actions": actions}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = plan(json.loads(args.state.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
