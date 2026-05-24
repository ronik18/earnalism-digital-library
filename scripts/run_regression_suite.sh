#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
FRONTEND_API_URL="${FRONTEND_API_URL:-https://api.theearnalism.com}"
E2E_PORT="${E2E_PORT:-3107}"
E2E_LOCAL_URL="http://127.0.0.1:${E2E_PORT}"
PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-1.60.0}"
PLAYWRIGHT_PREFIX="${PLAYWRIGHT_PREFIX:-/tmp/earnalism-playwright}"
RUN_E2E="${RUN_E2E:-1}"
RUN_LOAD="${RUN_LOAD:-0}"
RUN_LIVE_BACKEND="${RUN_LIVE_BACKEND:-0}"

echo "==> Backend unit regression"
MONGODB_URL="${MONGODB_URL:-mongodb://127.0.0.1:27017/earnalism_regression}" \
JWT_SECRET="${JWT_SECRET:-regression-secret}" \
RATE_LIMIT_ENABLED="${RATE_LIMIT_ENABLED:-false}" \
PYTHONPATH=backend \
"${PYTHON_BIN}" -m pytest -q \
  backend/tests/test_bengali_content_pipeline.py \
  backend/tests/test_content_processor_safety.py \
  scripts/test_bulk_publishing_pipeline.py

if [[ "${RUN_LIVE_BACKEND}" == "1" ]]; then
  echo "==> Live backend integration regression"
  "${PYTHON_BIN}" -m pytest -q \
    backend/tests/backend_test.py \
    backend/tests/test_phase2_user_reader.py \
    backend/tests/test_chapter_gating_security.py \
    backend/tests/test_payments_razorpay.py
fi

echo "==> Frontend unit regression"
CI=true npm test --prefix frontend -- --watchAll=false --passWithNoTests

echo "==> Frontend production build"
REACT_APP_BACKEND_URL="${FRONTEND_API_URL}" \
REACT_APP_API_URL="${FRONTEND_API_URL}" \
npm run build --prefix frontend

ensure_playwright() {
  mkdir -p "${PLAYWRIGHT_PREFIX}"
  if [[ ! -d "${PLAYWRIGHT_PREFIX}/node_modules/playwright" ]]; then
    npm install --prefix "${PLAYWRIGHT_PREFIX}" "playwright@${PLAYWRIGHT_VERSION}"
  fi
  export NODE_PATH="${PLAYWRIGHT_PREFIX}/node_modules${NODE_PATH:+:${NODE_PATH}}"
  if ! NODE_PATH="${NODE_PATH}" node - <<'NODE'
const { chromium } = require("playwright");
chromium.launch({ headless: true }).then((browser) => browser.close()).catch((error) => {
  console.error(error.message);
  process.exit(1);
});
NODE
  then
    "${PLAYWRIGHT_PREFIX}/node_modules/.bin/playwright" install chromium
  fi
}

if [[ "${RUN_E2E}" == "1" ]]; then
  echo "==> Browser e2e regression"
  ensure_playwright
  "${PYTHON_BIN}" -m http.server "${E2E_PORT}" --bind 127.0.0.1 --directory frontend/build >/tmp/earnalism-regression-http.log 2>&1 &
  SERVER_PID=$!
  trap 'kill "${SERVER_PID}" >/dev/null 2>&1 || true' EXIT
  SERVER_READY=0
  for _ in {1..40}; do
    if curl -fsS "${E2E_LOCAL_URL}" >/dev/null; then
      SERVER_READY=1
      break
    fi
    sleep 0.25
  done
  if [[ "${SERVER_READY}" != "1" ]]; then
    echo "Static regression server did not start on ${E2E_LOCAL_URL}" >&2
    cat /tmp/earnalism-regression-http.log >&2 || true
    exit 1
  fi
  E2E_BASE_URL="${E2E_LOCAL_URL}" \
  E2E_API_URL="${FRONTEND_API_URL}" \
  NODE_PATH="${NODE_PATH}" \
  node scripts/e2e_regression.mjs
  kill "${SERVER_PID}" >/dev/null 2>&1 || true
  trap - EXIT
fi

if [[ "${RUN_LOAD}" == "1" ]]; then
  echo "==> 100-user k6 load regression"
  if ! command -v k6 >/dev/null 2>&1; then
    echo "k6 is required for RUN_LOAD=1. Install with: brew install k6" >&2
    exit 1
  fi
  FRONTEND_URL="${FRONTEND_URL:-https://theearnalism.com}" \
  API_URL="${API_URL:-https://api.theearnalism.com}" \
  K6_LOAD_VUS="${K6_LOAD_VUS:-100}" \
  K6_LOAD_DURATION="${K6_LOAD_DURATION:-2m}" \
  k6 run scripts/k6_load_100.js
fi

echo "==> Earnalism regression suite passed"
