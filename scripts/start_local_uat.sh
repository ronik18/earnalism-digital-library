#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
RUNTIME_ROOT="$ROOT_DIR/uat/runtime/system-uat"
RUNTIME_DIR="$ROOT_DIR/uat/evidence/system-final/runtime-final/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUNTIME_ROOT" "$RUNTIME_DIR"

UAT_FRONTEND_HOST="${UAT_FRONTEND_HOST:-127.0.0.1}"
UAT_BACKEND_HOST="${UAT_BACKEND_HOST:-127.0.0.1}"
UAT_FRONTEND_PORT="${UAT_FRONTEND_PORT:-3000}"
UAT_BACKEND_PORT="${UAT_BACKEND_PORT:-8000}"
[[ "$UAT_FRONTEND_HOST" == 127.0.0.1 && "$UAT_BACKEND_HOST" == 127.0.0.1 ]] || { echo "UAT hosts must be loopback" >&2; exit 64; }

port_pid() { lsof -nP -t -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -1 || true; }
pid_cwd() { lsof -a -p "$1" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1; }
pid_matches_file() {
  local file="$1" pid="$2" port="$3"
  [[ -f "$file" ]] || return 1
  grep -Fx "pid=$pid" "$file" >/dev/null && grep -Fx "worktree=$ROOT_DIR" "$file" >/dev/null && grep -Fx "port=$port" "$file" >/dev/null && kill -0 "$pid" 2>/dev/null
}
terminate_owned_listener() {
  local port="$1" category="$2" file="$RUNTIME_ROOT/$category.pid" pid
  pid="$(port_pid "$port")"
  [[ -n "$pid" ]] || return 0
  if pid_matches_file "$file" "$pid" "$port" && [[ "$(pid_cwd "$pid")" == "$ROOT_DIR" ]]; then
    kill -TERM "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do [[ -z "$(port_pid "$port")" ]] && { rm -f "$file"; return 0; }; sleep 1; done
    kill -KILL "$pid" 2>/dev/null || true
    sleep 1
    [[ -z "$(port_pid "$port")" ]] || return 1
    rm -f "$file"
  fi
}
first_free_port() {
  local start="$1" end="$2" port
  for port in $(seq "$start" "$end"); do [[ -z "$(port_pid "$port")" ]] && { printf '%s' "$port"; return 0; }; done
  return 1
}
select_port() {
  local desired="$1" category="$2" start="$3" end="$4"
  terminate_owned_listener "$desired" "$category" || { echo "stale launcher-owned $category port cannot be released" >&2; exit 1; }
  [[ -z "$(port_pid "$desired")" ]] && { printf '%s' "$desired"; return; }
  first_free_port "$start" "$end" || { echo "no free fallback $category port" >&2; exit 1; }
}
UAT_BACKEND_PORT="$(select_port "$UAT_BACKEND_PORT" backend 18000 18099)"
UAT_FRONTEND_PORT="$(select_port "$UAT_FRONTEND_PORT" frontend 13000 13099)"
export UAT_FRONTEND_HOST UAT_BACKEND_HOST UAT_FRONTEND_PORT UAT_BACKEND_PORT
export UAT_BASE_URL="http://$UAT_FRONTEND_HOST:$UAT_FRONTEND_PORT"
export UAT_API_BASE_URL="http://$UAT_BACKEND_HOST:$UAT_BACKEND_PORT/api"
export REACT_APP_BACKEND_URL="http://$UAT_BACKEND_HOST:$UAT_BACKEND_PORT" REACT_APP_API_URL="$UAT_API_BASE_URL"
export ENVIRONMENT=uat PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 RAZORPAY_MODE=test
export JWT_SECRET=uat-local-only-jwt-secret-do-not-use-outside-this-worktree-20260820
export MONGODB_URL="mongodb://127.0.0.1:27017/earnalism_uat" COST_CONTROL_MODE=true ENABLE_BACKGROUND_WORKERS=false ENABLE_AUDIOBOOK_PIPELINE=false
export ENABLE_BOOK_RENDERING_JOBS=false ENABLE_COVER_GENERATION=false ENABLE_SCHEDULED_JOBS=false ENABLE_QUEUE_CONSUMER=false ENABLE_ADMIN_MEDIA_UPLOADS=false ENABLE_STARTUP_DB_MAINTENANCE=false
export RAZORPAY_KEY_ID= RAZORPAY_KEY_SECRET= RAZORPAY_WEBHOOK_SECRET= STRIPE_SECRET_KEY= STRIPE_PUBLIC_KEY= STRIPE_WEBHOOK_SECRET=
export npm_config_cache="$ROOT_DIR/.npm-cache" PLAYWRIGHT_BROWSERS_PATH="$ROOT_DIR/.playwright-browsers"

VENV_PYTHON="$ROOT_DIR/.venv-uat/bin/python"
[[ -x "$VENV_PYTHON" ]] || python3 -m venv "$ROOT_DIR/.venv-uat"
requirements_hash="$(shasum -a 256 backend/requirements.txt | awk '{print $1}')"
if [[ ! -f "$RUNTIME_ROOT/.requirements.sha256" || "$(<"$RUNTIME_ROOT/.requirements.sha256")" != "$requirements_hash" ]]; then
  PIP_CACHE_DIR="$ROOT_DIR/.pip-cache" "$VENV_PYTHON" -m pip install --disable-pip-version-check -r backend/requirements.txt
  printf '%s' "$requirements_hash" > "$RUNTIME_ROOT/.requirements.sha256"
fi

BACKEND_PID=""; FRONTEND_PID=""
write_pid() { printf 'pid=%s\ncategory=%s\nworktree=%s\nport=%s\nlaunched_at=%s\n' "$1" "$2" "$ROOT_DIR" "$3" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$RUNTIME_ROOT/$2.pid"; }
cleanup() {
  local result=$?
  for category in frontend backend; do
    local pid=""; [[ "$category" == backend ]] && pid="$BACKEND_PID" || pid="$FRONTEND_PID"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null && kill -TERM "$pid" 2>/dev/null || true
    rm -f "$RUNTIME_ROOT/$category.pid"
  done
  wait 2>/dev/null || true
  exit "$result"
}
trap cleanup EXIT INT TERM

"$VENV_PYTHON" -m uvicorn backend.server:app --host "$UAT_BACKEND_HOST" --port "$UAT_BACKEND_PORT" > "$RUNTIME_DIR/backend.log" 2>&1 & BACKEND_PID=$!
write_pid "$BACKEND_PID" backend "$UAT_BACKEND_PORT"
for _ in $(seq 1 90); do kill -0 "$BACKEND_PID" 2>/dev/null || { tail -80 "$RUNTIME_DIR/backend.log" >&2; exit 1; }; [[ "$(port_pid "$UAT_BACKEND_PORT")" == "$BACKEND_PID" ]] && curl -fsS "http://$UAT_BACKEND_HOST:$UAT_BACKEND_PORT/healthz" >/dev/null 2>&1 && break; sleep 1; done
[[ "$(port_pid "$UAT_BACKEND_PORT")" == "$BACKEND_PID" ]] || { tail -80 "$RUNTIME_DIR/backend.log" >&2; exit 1; }
curl -fsS "http://$UAT_BACKEND_HOST:$UAT_BACKEND_PORT/healthz" >/dev/null

rm -rf "$ROOT_DIR/frontend/build"
npm --prefix frontend run build > "$RUNTIME_DIR/frontend.log" 2>&1
node scripts/serve_frontend_build.js --host "$UAT_FRONTEND_HOST" --port "$UAT_FRONTEND_PORT" >> "$RUNTIME_DIR/frontend.log" 2>&1 & FRONTEND_PID=$!
write_pid "$FRONTEND_PID" frontend "$UAT_FRONTEND_PORT"
for _ in $(seq 1 90); do kill -0 "$FRONTEND_PID" 2>/dev/null || { tail -80 "$RUNTIME_DIR/frontend.log" >&2; exit 1; }; [[ "$(port_pid "$UAT_FRONTEND_PORT")" == "$FRONTEND_PID" ]] && curl -fsS "$UAT_BASE_URL/" >/dev/null 2>&1 && break; sleep 1; done
[[ "$(port_pid "$UAT_FRONTEND_PORT")" == "$FRONTEND_PID" ]] || { tail -80 "$RUNTIME_DIR/frontend.log" >&2; exit 1; }
curl -fsS "$UAT_BASE_URL/" >/dev/null
printf 'UAT_BASE_URL=%q\nUAT_API_BASE_URL=%q\nUAT_FRONTEND_PORT=%q\nUAT_BACKEND_PORT=%q\nUAT_RUNTIME_DIR=%q\n' "$UAT_BASE_URL" "$UAT_API_BASE_URL" "$UAT_FRONTEND_PORT" "$UAT_BACKEND_PORT" "$RUNTIME_DIR" > "$RUNTIME_ROOT/environment.sh"
printf 'UAT_RUNTIME_DIR=%s\nUAT_BASE_URL=%s\nUAT_API_BASE_URL=%s\n' "$RUNTIME_DIR" "$UAT_BASE_URL" "$UAT_API_BASE_URL"
wait
