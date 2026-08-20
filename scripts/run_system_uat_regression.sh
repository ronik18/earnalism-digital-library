#!/usr/bin/env bash
# Execute the frozen, system-executable UAT scope against the already-launched
# local stack.  This runner deliberately has no production fallback.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source uat/runtime/system-uat/environment.sh

[[ "${UAT_BASE_URL:-}" == http://127.0.0.1:* ]] || { echo "invalid UAT_BASE_URL" >&2; exit 2; }
[[ "${UAT_API_BASE_URL:-}" == http://127.0.0.1:*/api ]] || { echo "invalid UAT_API_BASE_URL" >&2; exit 2; }
export PLAYWRIGHT_BROWSERS_PATH="$ROOT/.playwright-browsers"

.venv-uat/bin/python -m compileall -q backend
.venv-uat/bin/python -m pytest -q \
  backend/tests/test_reading_pass_policy.py \
  backend/tests/test_reading_time_invariants.py \
  backend/tests/test_payments_razorpay.py \
  backend/tests/test_reading_pass_service_concurrency.py \
  backend/tests/test_reading_pass_security_static.py
npm --prefix frontend test -- --watchAll=false --runInBand
.venv-uat/bin/python scripts/verify_local_uat_contracts.py
npx playwright test tests/e2e/hydration-routes.spec.js --project=chromium
npx playwright test tests/e2e/reading-pass-responsive.spec.js --project=chromium
node scripts/run_contrast_responsive_gate.mjs
npx playwright test tests/e2e/earnalism-real-user-journey.spec.js --project=chromium --project=firefox --project=webkit
echo "system-uat-regression=PASS"
