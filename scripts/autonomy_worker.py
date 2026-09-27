#!/usr/bin/env python3
"""Bounded worker for approved non-production bridge tasks."""
import argparse, json, os, subprocess, time
from pathlib import Path

ALLOWED = {"bridge-fixture", "reader-benchmark", "codex-implementation-fixture", "codex-implementation"}
PROTECTED_PREFIXES = ("backend/", "frontend/", ".github/", "scripts/", "internal/")


def load_codex_result(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict) or not str(result.get("summary", "")).strip():
        raise ValueError("official Codex Action produced no usable implementation result")
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task-id", required=True)
    p.add_argument("--task-type", required=True)
    p.add_argument("--candidate-sha", required=True)
    p.add_argument("--generation", type=int, required=True)
    p.add_argument("--attempt", type=int, required=True)
    p.add_argument("--correction-context", default="")
    p.add_argument("--brief", default="")
    p.add_argument("--acceptance", default="")
    p.add_argument("--codex-result", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.task_type not in ALLOWED:
        raise SystemExit("task type is not approved")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if actual != args.candidate_sha:
        raise SystemExit(f"stale candidate: expected {args.candidate_sha}, got {actual}")
    if args.task_type == "bridge-fixture":
        command = [os.environ.get("PYTHON", "python3"), "-m", "unittest", "scripts.test_autonomy_bridge"]
    elif args.task_type == "reader-benchmark":
        command = ["bash", "scripts/run_reader_benchmark.sh"]
    else:
        if args.codex_result:
            codex_path = args.codex_result
            if not codex_path.exists():
                raise SystemExit("official Codex Action did not produce a result")
            proc = subprocess.CompletedProcess(["official-codex-action"], 0, codex_path.read_text(encoding="utf-8"), "")
            command = ["official-codex-action"]
        else:
            command = ["node", "scripts/run_codex_implementation.mjs", "--task-id", args.task_id, "--task-type", args.task_type, "--attempt", str(args.attempt), "--candidate-sha", args.candidate_sha, "--correction-context", args.correction_context, "--brief", args.brief, "--acceptance", args.acceptance, "--output", "codex-result.json"]
    if args.task_type in {"codex-implementation-fixture", "codex-implementation"} and args.codex_result:
        # The official GitHub Action already performed the edit; this path only
        # runs the focused fixture test and packages its result.
        try:
            load_codex_result(args.codex_result)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
    else:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=240)
    if args.task_type in {"codex-implementation-fixture", "codex-implementation"} and proc.returncode == 0:
        test_proc = subprocess.run([os.environ.get("PYTHON", "python3"), "scripts/codex_fixture_test.py"], text=True, capture_output=True, timeout=30)
        proc = subprocess.CompletedProcess(command, test_proc.returncode, proc.stdout + "\n" + test_proc.stdout, proc.stderr + "\n" + test_proc.stderr)
    result = {
        "task_id": args.task_id,
        "tested_revision": actual, "generation": args.generation, "attempt": args.attempt,
        "state": "REVIEW" if proc.returncode == 0 else "CHANGES_REQUIRED",
        "tests": [{"command": " ".join(command), "exit_code": proc.returncode, "stdout": proc.stdout[-2000:]}],
        "files_changed": subprocess.check_output(["git", "diff", "--name-only"], text=True).splitlines(),
        "artifacts": [],
        "unresolved_findings": [] if proc.returncode == 0 else [proc.stderr[-2000:] or "worker command failed"],
        "proposed_next_action": "REVIEW" if proc.returncode == 0 else "FIX_WORKER",
        "codex": json.loads(Path("codex-result.json").read_text(encoding="utf-8")) if args.task_type in {"codex-implementation-fixture", "codex-implementation"} and Path("codex-result.json").exists() else None,
        "generated_at": int(time.time()),
    }
    if args.task_type == "codex-implementation":
        forbidden = [p for p in result["files_changed"] if p.startswith(("backend/", "frontend/", ".github/", "internal/") ) or any(x in p.lower() for x in ("payment", "entitlement", "secret", "deploy", "catalogue"))]
        if forbidden:
            result.update(state="CHANGES_REQUIRED", unresolved_findings=[f"protected or unrelated paths changed: {', '.join(forbidden)}"], proposed_next_action="FIX_SCOPE")
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if proc.returncode == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
