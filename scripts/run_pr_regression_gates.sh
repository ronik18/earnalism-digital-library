#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export EARNALISM_BASE_URL="$UAT_BASE_URL"
export REGRESSION_FRONTEND_URL="$UAT_BASE_URL"
export REGRESSION_API_URL="${UAT_API_BASE_URL%/api}"
export CI=true REGRESSION_MODE=pr

case "$REGRESSION_FRONTEND_URL" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *) echo "pre-deploy regression frontend target must be loopback; production fallback is rejected" >&2; exit 64 ;;
esac
case "$REGRESSION_API_URL" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *) echo "pre-deploy regression API target must be loopback; production fallback is rejected" >&2; exit 64 ;;
esac

PYTHON_BIN="$ROOT/.venv-uat/bin/python"
[[ -x "$PYTHON_BIN" ]] || { echo "prepared isolated Python environment is required" >&2; exit 64; }

echo "==> CORS cache contract (backend/tests/test_cors_cache_headers.py)"
env \
  -u CORS_ORIGINS \
  -u FRONTEND_URL \
  ENVIRONMENT=production \
  READING_PASS_V2_ENABLED=false \
  MONGODB_URL="${MONGODB_URL:?isolated MongoDB URL is required}" \
  REDIS_URL="${REDIS_URL:?isolated Redis URL is required}" \
  JWT_SECRET="${JWT_SECRET:?isolated JWT secret is required}" \
  "$PYTHON_BIN" -m pytest -q backend/tests/test_cors_cache_headers.py

npm run regression:ci
