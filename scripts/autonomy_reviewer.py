#!/usr/bin/env python3
"""Independent reviewer for bounded worker evidence."""
import argparse, json, subprocess, time
from pathlib import Path
try:
    from scripts.autonomy_scope import forbidden_paths
except ModuleNotFoundError:  # direct ``python scripts/autonomy_reviewer.py`` execution
    from autonomy_scope import forbidden_paths

CODEX_TASKS = {"codex-implementation-fixture", "codex-implementation"}

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task-id", required=True); p.add_argument("--candidate-sha", required=True); p.add_argument("--generation", type=int, required=True); p.add_argument("--attempt", type=int, required=True)
    p.add_argument("--worker-result", type=Path, required=True); p.add_argument("--output", type=Path, required=True); p.add_argument("--task-type", required=True)
    a = p.parse_args()
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    worker = json.loads(a.worker_result.read_text(encoding="utf-8"))
    if actual != a.candidate_sha or worker.get("tested_revision") != actual or worker.get("generation") != a.generation or worker.get("attempt") != a.attempt or worker.get("task_id") != a.task_id:
        raise SystemExit("review rejected stale or mismatched revision")
    tests = worker.get("tests") or []
    decision = "ACCEPT_WITHIN_SCOPE" if worker.get("state") == "REVIEW" and tests and all(t.get("exit_code") == 0 for t in tests) else "CHANGES_REQUIRED"
    findings = [] if decision == "ACCEPT_WITHIN_SCOPE" else ["worker evidence is incomplete or contains a failing command"]
    codex_result = worker.get("codex") or {}
    if a.task_type in CODEX_TASKS and not str(codex_result.get("summary", "")).strip():
        decision = "CHANGES_REQUIRED"
        findings = ["Codex implementation result is missing or empty"]
    if a.task_type == "codex-implementation-fixture" and decision == "ACCEPT_WITHIN_SCOPE":
        fixture = Path("bridge_fixtures/codex_acceptance_fixture.py").read_text(encoding="utf-8")
        if a.attempt == 1:
            decision = "CHANGES_REQUIRED"
            findings = ["format_label must return the uppercase LABEL; apply this correction in the fixture only"]
        elif a.attempt != 2 or 'LABEL = "ready"' not in fixture or "return value.upper()" not in fixture:
            decision = "CHANGES_REQUIRED"
            findings = ["bounded Codex correction did not produce the required fixture implementation"]
    if a.task_type == "codex-implementation":
        changed = worker.get("changed_files") or worker.get("files_changed") or []
        forbidden = forbidden_paths(changed)
        if forbidden:
            decision = "CHANGES_REQUIRED"
            findings = [f"protected or unrelated paths changed: {', '.join(forbidden)}"]
    if a.task_type == "catalogue-processing" and decision == "ACCEPT_WITHIN_SCOPE":
        import hashlib
        evidence = worker.get("catalogue_processing") or {}
        state = Path("internal/earnalism_intelligence/full_catalogue_processing_20260930")
        verified = subprocess.run(["python3", "scripts/process_full_catalogue.py", "--check"], text=True, capture_output=True, timeout=240)
        checksum = hashlib.sha256((state / "processing_checksums.json").read_bytes()).hexdigest()
        if verified.returncode or evidence.get("processing_checksums_sha256") != checksum or evidence.get("read_only_verification") is not True or evidence.get("publication_authorized") is not False:
            decision = "CHANGES_REQUIRED"
            findings = ["catalogue evidence did not reproduce independently; publication remains blocked"]
    result = {"task_id": a.task_id, "tested_revision": actual, "generation": a.generation, "attempt": a.attempt, "decision": decision, "findings": findings, "generated_at": int(time.time())}
    a.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
