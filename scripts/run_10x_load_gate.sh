#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if ! command -v k6 >/dev/null 2>&1; then
  echo "k6 is required for the 10X load gate. Install with: brew install k6" >&2
  exit 1
fi

FRONTEND_URL="${FRONTEND_URL:-https://theearnalism.com}" \
API_URL="${API_URL:-https://api.theearnalism.com}" \
K6_LOAD_VUS="${K6_LOAD_VUS:-1000}" \
K6_LOAD_DURATION="${K6_LOAD_DURATION:-3m}" \
K6_LOAD_SLEEP_SECONDS="${K6_LOAD_SLEEP_SECONDS:-1}" \
k6 run scripts/k6_load_100.js
