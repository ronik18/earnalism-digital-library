#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT_DIR"
export npm_config_cache="$ROOT_DIR/.npm-cache" PLAYWRIGHT_BROWSERS_PATH="$ROOT_DIR/.playwright-browsers"
EVIDENCE_DIR="$ROOT_DIR/uat/evidence/system-final/runtime-final/full-$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$EVIDENCE_DIR"
rm -f uat/runtime/system-uat/environment.sh
bash scripts/start_local_uat.sh > "$EVIDENCE_DIR/launcher.log" 2>&1 & LAUNCHER_PID=$!
cleanup() { kill "$LAUNCHER_PID" 2>/dev/null || true; wait "$LAUNCHER_PID" 2>/dev/null || true; }; trap cleanup EXIT INT TERM
for _ in $(seq 1 120); do kill -0 "$LAUNCHER_PID" 2>/dev/null || { wait "$LAUNCHER_PID" || true; exit 1; }; [[ -f uat/runtime/system-uat/environment.sh ]] && break; sleep 1; done
source uat/runtime/system-uat/environment.sh
curl -fsS "http://$UAT_BACKEND_HOST:$UAT_BACKEND_PORT/healthz" >/dev/null; curl -fsS "$UAT_BASE_URL/" >/dev/null
node_modules/.bin/playwright test tests/e2e/reading-pass-responsive.spec.js tests/e2e/earnalism-real-user-journey.spec.js --project=chromium --project=firefox --project=webkit > "$EVIDENCE_DIR/playwright.log" 2>&1
