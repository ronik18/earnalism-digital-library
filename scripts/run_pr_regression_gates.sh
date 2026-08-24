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

npm run regression:ci
