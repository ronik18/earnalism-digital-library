#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "${UAT_BASE_URL:-}" != "http://127.0.0.1:3000" || "${UAT_API_BASE_URL:-}" != "http://127.0.0.1:8000/api" ]]; then
  echo "Local UAT requires UAT_BASE_URL=http://127.0.0.1:3000 and UAT_API_BASE_URL=http://127.0.0.1:8000/api" >&2
  exit 64
fi

RUNTIME_DIR="$ROOT_DIR/uat/evidence/final-canonical-recovery/runtime-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUNTIME_DIR"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  local code=$?
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  exit "$code"
}
trap cleanup EXIT INT TERM

export ENVIRONMENT=uat PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
export JWT_SECRET=uat-local-only-jwt-secret-do-not-use-outside-this-worktree-20260820
export MONGODB_URL="mongodb://127.0.0.1:27017/earnalism_uat"
export COST_CONTROL_MODE=true ENABLE_BACKGROUND_WORKERS=false ENABLE_AUDIOBOOK_PIPELINE=false
export ENABLE_BOOK_RENDERING_JOBS=false ENABLE_COVER_GENERATION=false ENABLE_SCHEDULED_JOBS=false
export ENABLE_QUEUE_CONSUMER=false ENABLE_ADMIN_MEDIA_UPLOADS=false ENABLE_STARTUP_DB_MAINTENANCE=false
export RAZORPAY_KEY_ID= RAZORPAY_KEY_SECRET= RAZORPAY_WEBHOOK_SECRET= STRIPE_SECRET_KEY= STRIPE_PUBLIC_KEY= STRIPE_WEBHOOK_SECRET=
export RAZORPAY_MODE=test
export REACT_APP_BACKEND_URL=http://127.0.0.1:8000 REACT_APP_API_URL=http://127.0.0.1:8000/api
export npm_config_cache="$ROOT_DIR/.npm-cache"
export PLAYWRIGHT_BROWSERS_PATH="$ROOT_DIR/.playwright-browsers"
VENV_PYTHON="$ROOT_DIR/.venv-uat/bin/python"
REQUIREMENTS_FILE="$ROOT_DIR/backend/requirements.txt"
REQUIREMENTS_STAMP="$ROOT_DIR/uat/.venv-uat-requirements.sha256"

if [[ ! -x "$VENV_PYTHON" ]]; then
  python3 -m venv "$ROOT_DIR/.venv-uat"
fi
requirements_hash="$(shasum -a 256 "$REQUIREMENTS_FILE" | awk '{print $1}')"
if [[ ! -f "$REQUIREMENTS_STAMP" || "$(<"$REQUIREMENTS_STAMP")" != "$requirements_hash" ]]; then
  PIP_CACHE_DIR="$ROOT_DIR/.pip-cache" "$VENV_PYTHON" -m pip install --disable-pip-version-check -r "$REQUIREMENTS_FILE"
  printf '%s' "$requirements_hash" > "$REQUIREMENTS_STAMP"
fi
"$VENV_PYTHON" -c 'import uvicorn' >/dev/null

"$VENV_PYTHON" -m uvicorn backend.server:app --host 127.0.0.1 --port 8000 >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
for _ in $(seq 1 90); do
  kill -0 "$BACKEND_PID" 2>/dev/null || { tail -80 "$BACKEND_LOG" >&2; exit 1; }
  curl -fsS http://127.0.0.1:8000/healthz >/dev/null && break
  sleep 1
done
kill -0 "$BACKEND_PID" 2>/dev/null || { tail -80 "$BACKEND_LOG" >&2; exit 1; }
curl -fsS http://127.0.0.1:8000/healthz >/dev/null || { tail -80 "$BACKEND_LOG" >&2; exit 1; }

rm -rf "$ROOT_DIR/frontend/build"
npm --prefix frontend run build >"$FRONTEND_LOG" 2>&1
node scripts/serve_frontend_build.js >>"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
for _ in $(seq 1 90); do curl -fsS http://127.0.0.1:3000/ >/dev/null && break; sleep 1; done
kill -0 "$FRONTEND_PID" 2>/dev/null || { tail -80 "$FRONTEND_LOG" >&2; exit 1; }
curl -fsS http://127.0.0.1:3000/ >/dev/null || { tail -80 "$FRONTEND_LOG" >&2; exit 1; }

printf 'UAT_RUNTIME_DIR=%s\n' "$RUNTIME_DIR"
wait
