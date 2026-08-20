#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
if [[ "${UAT_BASE_URL:-}" != "http://127.0.0.1:3000" || "${UAT_API_BASE_URL:-}" != "http://127.0.0.1:8000/api" ]]; then
  echo "Set exactly UAT_BASE_URL=http://127.0.0.1:3000 UAT_API_BASE_URL=http://127.0.0.1:8000/api" >&2
  exit 64
fi
[[ -x node_modules/.bin/playwright ]] || { echo "Missing pinned root Playwright; run npm ci in this worktree before UAT." >&2; exit 65; }

EVIDENCE_DIR="$ROOT_DIR/uat/evidence/final-canonical-recovery/full-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$EVIDENCE_DIR"
export npm_config_cache="$ROOT_DIR/.npm-cache"
export PLAYWRIGHT_BROWSERS_PATH="$ROOT_DIR/.playwright-browsers"

bash "$ROOT_DIR/scripts/start_local_uat.sh" >"$EVIDENCE_DIR/launcher.log" 2>&1 &
LAUNCHER_PID=$!
cleanup() { kill "$LAUNCHER_PID" 2>/dev/null || true; wait "$LAUNCHER_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
for _ in $(seq 1 120); do
  if ! kill -0 "$LAUNCHER_PID" 2>/dev/null; then
    wait "$LAUNCHER_PID" || true
    echo "Local UAT launcher exited before both loopback services became ready; see $EVIDENCE_DIR/launcher.log" >&2
    exit 1
  fi
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1 && curl -fsS "$UAT_BASE_URL/" >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:8000/healthz >/dev/null
curl -fsS "$UAT_BASE_URL/" >/dev/null

node_modules/.bin/playwright install --list >"$EVIDENCE_DIR/pinned-browser-inventory.log" 2>&1
node frontend/src/scripts/reader-typography-contrast.mjs >"$EVIDENCE_DIR/contrast.log" 2>&1
node_modules/.bin/playwright test tests/e2e/reading-pass-responsive.spec.js tests/e2e/earnalism-real-user-journey.spec.js --project=chromium --project=firefox --project=webkit >"$EVIDENCE_DIR/playwright.log" 2>&1
python3 scripts/generate_real_user_ux_report.py >"$EVIDENCE_DIR/report-generation.log" 2>&1
python3 scripts/generate_local_uat_report.py --evidence-dir "$EVIDENCE_DIR"
