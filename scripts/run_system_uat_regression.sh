#!/usr/bin/env bash
# Execute every frozen, system-executable UAT gate on one isolated local stack.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
export npm_config_cache="$ROOT/.npm-cache" PLAYWRIGHT_BROWSERS_PATH="$ROOT/.playwright-browsers"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "System UAT requires a clean worktree before execution" >&2
  exit 64
fi
git fetch origin main
EXPECTED_REMOTE_REF="refs/remotes/origin/main"
EXPECTED_COMMIT="$(git rev-parse "$EXPECTED_REMOTE_REF")"
EXPECTED_TREE="$(git rev-parse "${EXPECTED_REMOTE_REF}^{tree}")"
[[ -z "$(git branch --show-current)" ]] || { echo "System UAT exact-main regression requires a detached HEAD" >&2; exit 64; }
[[ "$(git rev-parse HEAD)" == "$EXPECTED_COMMIT" && "$(git rev-parse 'HEAD^{tree}')" == "$EXPECTED_TREE" ]] || { echo "System UAT exact-main regression must start at refreshed origin/main" >&2; exit 64; }
export UAT_CLEAN_WORKTREE_BEFORE_EXECUTION=true
export UAT_PROVENANCE_MODE=DETACHED_EXACT_REMOTE_AUTHORITY
export UAT_EXPECTED_REPOSITORY_ROOT="$ROOT"
export UAT_EXPECTED_COMMIT="$EXPECTED_COMMIT"
export UAT_EXPECTED_TREE="$EXPECTED_TREE"
export UAT_EXPECTED_REMOTE_REF="$EXPECTED_REMOTE_REF"
export UAT_EXPECTED_REMOTE_REF_SHA="$EXPECTED_COMMIT"
export UAT_REMOTE_REF_REFRESHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVIDENCE_DIR="uat/evidence/system-final/$RUN_ID"; mkdir -p "$EVIDENCE_DIR"
ENVIRONMENT_FILE="uat/runtime/system-uat/environment.sh"
if [[ -f "$ENVIRONMENT_FILE" ]]; then
  mv "$ENVIRONMENT_FILE" "${ENVIRONMENT_FILE}.stale-$RUN_ID"
fi
export UAT_RUN_ID="$RUN_ID"
export UAT_EVIDENCE_DIR="$EVIDENCE_DIR"
export UAT_COMMAND_FILE="$ROOT/scripts/run_system_uat_gates.sh"
bash scripts/start_local_uat.sh >"$EVIDENCE_DIR/launcher.log" 2>&1
python3 scripts/generate_system_uat_report.py --manifest uat/system-run-manifest.json
echo "system-uat-regression=PASS"
