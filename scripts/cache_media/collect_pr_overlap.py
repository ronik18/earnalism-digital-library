#!/usr/bin/env python3
"""Collect read-only PR path overlap evidence for the cache/media baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def classify(path: str) -> str:
    if path.startswith(("frontend/", ".github/workflows/")):
        return "PROHIBITED_ACTIVE_UI_OR_WORKFLOW_SURFACE"
    if path.startswith("docs/"):
        return "DOCUMENTATION_ONLY_NON_OVERLAPPING_PATH_REQUIRED"
    if path.startswith("scripts/"):
        return "PROHIBITED_SHARED_SCRIPT_SURFACE"
    if path.startswith("uat/"):
        return "PROHIBITED_ACTIVE_UAT_SURFACE"
    if path.startswith("internal/"):
        return "PROHIBITED_ACTIVE_OWNER_POLICY_SURFACE"
    return "DO_NOT_EDIT_DURING_BASELINE"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, default=344)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    completed = subprocess.run(
        [
            "gh", "pr", "view", str(args.pr),
            "--json", "number,state,isDraft,headRefName,headRefOid,baseRefName,files",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    raw = json.loads(completed.stdout)
    paths = [item["path"] for item in raw["files"]]
    payload = {
        "schema_version": "cache-media-pr-overlap-map.v1",
        "pr": {
            "number": raw["number"], "state": raw["state"], "is_draft": raw["isDraft"],
            "head_ref": raw["headRefName"], "head_sha": raw["headRefOid"], "base_ref": raw["baseRefName"],
        },
        "changed_path_count": len(paths),
        "baseline_owned_roots": ["docs/architecture/cache-media/", "backend/tests/cache_media/", "scripts/cache_media/"],
        "overlap_result": "NO_BASELINE_EDIT_OVERLAP",
        "paths": [{"path": path, "classification": classify(path)} for path in paths],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
