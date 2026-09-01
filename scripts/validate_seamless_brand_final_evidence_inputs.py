#!/usr/bin/env python3
"""Hard gate for the pre-publication PR344 evidence-input population."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

FORBIDDEN = {"PENDING", "NOT RUN", "WORKFLOW RUNNING"}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def production_hash(root):
    files = []
    for directory in [root / "frontend/src", root / "frontend/public"]:
        for path in directory.rglob("*"):
            if path.is_file() and "__tests__" not in path.parts and ".test." not in path.name and ".spec." not in path.name:
                files.append(path)
    files.extend(root / item for item in ["frontend/package.json", "frontend/package-lock.json", "frontend/vercel.json"])
    listing = "".join(f"{sha(path)}  {path.relative_to(root)}\n" for path in sorted(files))
    return hashlib.sha256(listing.encode()).hexdigest()

def contains_forbidden(value):
    if isinstance(value, str): return value in FORBIDDEN
    if isinstance(value, dict): return any(contains_forbidden(item) for item in value.values())
    if isinstance(value, list): return any(contains_forbidden(item) for item in value)
    return False

def require(condition, message, failures):
    if not condition: failures.append(message)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True)
    args = parser.parse_args()
    root = Path.cwd(); inputs_path = Path(args.inputs).resolve(); data = json.loads(inputs_path.read_text())
    failures = []
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    require(data.get("current_pr_head") == head, "recorded head differs from current HEAD", failures)
    require(data.get("production_surface_sha256") == production_hash(root), "production surface hash differs", failures)
    require(data.get("canonical_logo_sha256") == sha(root / "frontend/public/assets/brand/earnalism-brand-lockup.png"), "canonical logo hash differs", failures)
    require(not contains_forbidden(data), "mandatory output contains forbidden pending value", failures)
    for key in ["chromium", "firefox", "webkit", "static_snapshot", "route_hashes", "approval_carry_forward"]:
        item = data.get(key, {}); reference = item.get("summary_path") or item.get("path")
        require(bool(reference) and Path(reference).exists(), f"{key} referenced file is missing", failures)
        if reference and Path(reference).exists() and item.get("summary_sha256", item.get("sha256")):
            require(sha(reference) == item.get("summary_sha256", item.get("sha256")), f"{key} referenced SHA mismatch", failures)
    chromium = data.get("chromium", {})
    require((chromium.get("expected"), chromium.get("captured"), chromium.get("stable")) == (65, 65, 65), "Chromium counts differ from 65/65/65", failures)
    for key in ["firefox", "webkit"]:
        item = data.get(key, {}); require((item.get("expected"), item.get("captured"), item.get("stable")) == (20, 20, 20) and item.get("result") == "PASS", f"{key} result fails", failures)
    static = data.get("static_snapshot", {}); require(static.get("expected") == static.get("inspected") == static.get("passing") and static.get("result") == "PASS", "static snapshot result fails", failures)
    require(data.get("route_hashes", {}).get("result") == "PASS" and data.get("approval_carry_forward", {}).get("result") == "PASS", "route-family hash result fails", failures)
    for key in ["reader_safety_result", "listener_safety_result", "interaction_result", "zoom_result", "error_status_result"]: require(data.get(key) == "PASS", f"{key} fails", failures)
    require(data.get("rendered_ui_defect_count") == 0, "rendered UI defects recorded", failures)
    require(data.get("production_mutation_count") == 0, "production mutations recorded", failures)
    result = "PASS" if not failures else "FAIL"
    print(json.dumps({"FINAL_EVIDENCE_INPUT_VALIDATOR_RESULT": result, "failures": failures}))
    raise SystemExit(0 if not failures else 1)

if __name__ == "__main__": main()
