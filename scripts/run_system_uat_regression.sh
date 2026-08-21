#!/usr/bin/env bash
# Execute every frozen, system-executable UAT gate on one isolated local stack.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
export npm_config_cache="$ROOT/.npm-cache" PLAYWRIGHT_BROWSERS_PATH="$ROOT/.playwright-browsers"
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
