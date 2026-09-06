#!/usr/bin/env bash
# Directly exercise the runner's fail-closed reporter boundary without UAT services.
set -u -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT
CALL_LOG="$TEMP_DIR/calls.log"
mkdir -p "$TEMP_DIR/bin"

cat >"$TEMP_DIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$CALL_LOG"
exit 7
EOF
chmod +x "$TEMP_DIR/bin/python3"

set +e
CALL_LOG="$CALL_LOG" PATH="$TEMP_DIR/bin:$PATH" \
  UAT_RUN_ID="run-20260906T000000Z-359" \
  UAT_EVIDENCE_DIR="uat/evidence/system-final/run-20260906T000000Z-359" \
  UAT_CLEAN_WORKTREE_BEFORE_EXECUTION=true \
  UAT_PROVENANCE_MODE=ATTACHED_EXPECTED_BRANCH \
  UAT_EXPECTED_REPOSITORY_ROOT="$ROOT" \
  UAT_EXPECTED_COMMIT="$(git -C "$ROOT" rev-parse HEAD)" \
  UAT_EXPECTED_TREE="$(git -C "$ROOT" rev-parse 'HEAD^{tree}')" \
  UAT_EXPECTED_BRANCH="fixture-attached-branch" \
  UAT_BASE_URL="http://127.0.0.1:13000" \
  UAT_API_BASE_URL="http://127.0.0.1:18000/api" \
  UAT_MONGODB_PORT=27018 \
  bash "$ROOT/scripts/run_system_uat_gates.sh" >"$TEMP_DIR/output.log" 2>&1
status=$?
set -e

[[ "$status" -ne 0 ]] || { echo "reporter init failure was converted to success" >&2; exit 1; }
rg -q 'system-uat-reporter=INIT_FAILED' "$TEMP_DIR/output.log"
rg -q -- '--init' "$CALL_LOG"
[[ "$(wc -l <"$CALL_LOG")" -eq 1 ]] || { echo "runner continued after reporter initialization failure" >&2; exit 1; }

# These checked branches protect subsequent stage failures while preserving
# intentional test-command result collection in run_gate.
rg -q 'system-uat-reporter=RECORD_FAILED:' "$ROOT/scripts/run_system_uat_gates.sh"
rg -q 'system-uat-reporter=FINALIZE_FAILED' "$ROOT/scripts/run_system_uat_gates.sh"
rg -q 'system-uat-regression=REPORT_GENERATION_FAILED' "$ROOT/scripts/run_system_uat_regression.sh"
rg -q 'system-uat-regression=REPORT_VALIDATION_FAILED' "$ROOT/scripts/run_system_uat_regression.sh"
echo "system-uat-reporter-failure-propagation=PASS"
