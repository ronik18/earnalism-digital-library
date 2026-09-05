#!/usr/bin/env bash
# Invoked by start_local_uat.sh after it owns the isolated local services.
set -u -o pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
[[ -n "${UAT_RUN_ID:-}" && -n "${UAT_EVIDENCE_DIR:-}" && -n "${UAT_CLEAN_WORKTREE_BEFORE_EXECUTION:-}" ]] || { echo "UAT run identity and clean-worktree status are required" >&2; exit 64; }
MANIFEST="uat/system-run-manifest.json"; overall=0
python3 scripts/generate_system_uat_report.py --init --run-id "$UAT_RUN_ID" --clean-worktree-before-execution "$UAT_CLEAN_WORKTREE_BEFORE_EXECUTION" --manifest "$MANIFEST" --frontend "$UAT_BASE_URL" --api "$UAT_API_BASE_URL" --mongodb "mongodb://127.0.0.1:${UAT_MONGODB_PORT}/earnalism_uat?replicaSet=earnalism-uat-rs0"
npx playwright install chromium firefox webkit >"$UAT_EVIDENCE_DIR/playwright-install.log" 2>&1 || overall=1

run_gate() {
  local id="$1" passed="$2"; shift 2
  local log="$UAT_EVIDENCE_DIR/$id.log" started completed exit_code command_text result_passed result_failed
  started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"; command_text="$*"
  "$@" >"$log" 2>&1; exit_code=$?
  completed="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [[ "$exit_code" -eq 0 ]]; then result_passed="$passed"; result_failed=0; else result_passed=0; result_failed=1; fi
  python3 scripts/generate_system_uat_report.py --manifest "$MANIFEST" --record "$id" --command "$command_text" --started-at "$started" --completed-at "$completed" --exit-code "$exit_code" --passed "$result_passed" --failed "$result_failed" --missing 0 --log "uat/evidence/system-final/$UAT_RUN_ID/$id.log"
  [[ "$exit_code" -eq 0 ]] || overall=1
}

run_gate backend-compile 1 .venv-uat/bin/python -m compileall -q backend
run_gate p1-isolated-preflight 1 .venv-uat/bin/python scripts/verify_p1_isolated_preflight.py
run_gate backend-core 49 env -u READING_PASS_V2_ENABLED .venv-uat/bin/python -m pytest -q backend/tests/test_reading_pass_policy.py backend/tests/test_reading_time_invariants.py backend/tests/test_payments_razorpay.py backend/tests/test_reading_pass_service_concurrency.py backend/tests/test_reading_pass_security_static.py
run_gate p1-v2-contracts 33 .venv-uat/bin/python -m pytest -q backend/tests/test_reading_pass_policy.py backend/tests/test_reading_pass_service_concurrency.py backend/tests/test_reading_pass_security_static.py backend/tests/test_zero_public_audio_contract.py
run_gate backend-policy 8 .venv-uat/bin/python -m pytest -q backend/tests/test_controlled_launch_parity.py
run_gate frontend-full 276 env -u REACT_APP_BACKEND_URL -u REACT_APP_API_URL -u REACT_APP_UAT_LOCAL npm --prefix frontend test -- --watchAll=false --runInBand
run_gate frontend-build 1 npm --prefix frontend run build
run_gate contracts 2 .venv-uat/bin/python scripts/verify_local_uat_contracts.py
run_gate hydration 7 npx playwright test tests/e2e/hydration-routes.spec.js --project=chromium
run_gate responsive 8 npx playwright test tests/e2e/reading-pass-responsive.spec.js --project=chromium
run_gate chromium-journeys 12 npx playwright test tests/e2e/earnalism-real-user-journey.spec.js --project=chromium
run_gate firefox-journeys 12 npx playwright test tests/e2e/earnalism-real-user-journey.spec.js --project=firefox
run_gate webkit-journeys 12 npx playwright test tests/e2e/earnalism-real-user-journey.spec.js --project=webkit
run_gate contrast 36 node scripts/run_contrast_responsive_gate.mjs
if [[ "$overall" -eq 0 ]]; then
  python3 scripts/generate_system_uat_report.py --finalize --manifest "$MANIFEST"
fi
exit "$overall"
