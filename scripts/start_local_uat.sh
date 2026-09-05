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
UAT_MONGODB_PORT="${UAT_MONGODB_PORT:-27018}"
UAT_REDIS_PORT="${UAT_REDIS_PORT:-26379}"
UAT_EXTERNAL_MONGODB="${UAT_EXTERNAL_MONGODB:-false}"
[[ "$UAT_FRONTEND_HOST" == 127.0.0.1 && "$UAT_BACKEND_HOST" == 127.0.0.1 ]] || { echo "UAT hosts must be loopback" >&2; exit 64; }
[[ "$UAT_EXTERNAL_MONGODB" == true || "$UAT_EXTERNAL_MONGODB" == false ]] || { echo "UAT_EXTERNAL_MONGODB must be true or false" >&2; exit 64; }

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
if [[ "$UAT_EXTERNAL_MONGODB" == false ]]; then
  UAT_MONGODB_PORT="$(select_port "$UAT_MONGODB_PORT" mongodb 27018 27099)"
fi
UAT_REDIS_PORT="$(select_port "$UAT_REDIS_PORT" redis 26379 26479)"
export UAT_FRONTEND_HOST UAT_BACKEND_HOST UAT_FRONTEND_PORT UAT_BACKEND_PORT UAT_MONGODB_PORT UAT_REDIS_PORT
export UAT_BASE_URL="http://$UAT_FRONTEND_HOST:$UAT_FRONTEND_PORT"
export UAT_API_BASE_URL="http://$UAT_BACKEND_HOST:$UAT_BACKEND_PORT/api"
export REACT_APP_BACKEND_URL="http://$UAT_BACKEND_HOST:$UAT_BACKEND_PORT" REACT_APP_API_URL="$UAT_API_BASE_URL" REACT_APP_UAT_LOCAL=true
# The static UAT build calls the API on a separately allocated loopback port.
# Keep that selected origin in the backend's allowlist; 3000 is only the
# preferred port and may already be occupied on the host running this gate.
export CORS_ORIGINS="$UAT_BASE_URL"
export ENVIRONMENT=uat PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 RAZORPAY_MODE=test
export JWT_SECRET=uat-local-only-jwt-secret-do-not-use-outside-this-worktree-20260820
export READING_PASS_V2_ENABLED=true READING_PASS_TOKEN_SECRET=uat-local-reading-pass-token-secret-20260820
export ADMIN_EMAIL=admin@theearnalism.com ADMIN_PASSWORD=Earnalism@2026
export UAT_MONGODB_URI="mongodb://127.0.0.1:$UAT_MONGODB_PORT/earnalism_uat?replicaSet=earnalism-uat-rs0"
export UAT_REDIS_URL="redis://127.0.0.1:$UAT_REDIS_PORT/0"
export MONGODB_URL="$UAT_MONGODB_URI" REDIS_URL="$UAT_REDIS_URL" COST_CONTROL_MODE=true ENABLE_BACKGROUND_WORKERS=false ENABLE_AUDIOBOOK_PIPELINE=false
export ENABLE_BOOK_RENDERING_JOBS=false ENABLE_COVER_GENERATION=false ENABLE_SCHEDULED_JOBS=false ENABLE_QUEUE_CONSUMER=false ENABLE_ADMIN_MEDIA_UPLOADS=false ENABLE_STARTUP_DB_MAINTENANCE=true
export RAZORPAY_KEY_ID= RAZORPAY_KEY_SECRET= RAZORPAY_WEBHOOK_SECRET= STRIPE_SECRET_KEY= STRIPE_PUBLIC_KEY= STRIPE_WEBHOOK_SECRET=
export npm_config_cache="$ROOT_DIR/.npm-cache" PLAYWRIGHT_BROWSERS_PATH="$ROOT_DIR/.playwright-browsers"

UAT_PYTHON="${UAT_PYTHON:-$(command -v python3.11 || true)}"
[[ -n "$UAT_PYTHON" && -x "$UAT_PYTHON" ]] || { echo "System UAT requires an approved Python 3.11 interpreter" >&2; exit 64; }
"$UAT_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || { echo "System UAT requires Python >= 3.10" >&2; exit 64; }

VENV_PYTHON="$ROOT_DIR/.venv-uat/bin/python"
if [[ -x "$VENV_PYTHON" ]]; then
  "$VENV_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || { echo "Existing .venv-uat uses Python < 3.10; recreate only that disposable environment" >&2; exit 64; }
else
  "$UAT_PYTHON" -m venv "$ROOT_DIR/.venv-uat"
fi
requirements_hash="$(shasum -a 256 backend/requirements.txt | awk '{print $1}')"
if [[ ! -f "$RUNTIME_ROOT/.requirements.sha256" || "$(<"$RUNTIME_ROOT/.requirements.sha256")" != "$requirements_hash" ]]; then
  PIP_CACHE_DIR="$ROOT_DIR/.pip-cache" "$VENV_PYTHON" -m pip install --disable-pip-version-check -r backend/requirements.txt
  printf '%s' "$requirements_hash" > "$RUNTIME_ROOT/.requirements.sha256"
fi

MONGODB_PID=""; REDIS_PID=""; BACKEND_PID=""; FRONTEND_PID=""
write_pid() { printf 'pid=%s\ncategory=%s\nworktree=%s\nport=%s\nlaunched_at=%s\n' "$1" "$2" "$ROOT_DIR" "$3" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$RUNTIME_ROOT/$2.pid"; }
cleanup() {
  local result=$?
  for category in frontend backend redis mongodb; do
    local pid=""
    case "$category" in
      frontend) pid="$FRONTEND_PID" ;;
      backend) pid="$BACKEND_PID" ;;
      redis) pid="$REDIS_PID" ;;
      mongodb) pid="$MONGODB_PID" ;;
    esac
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null && kill -TERM "$pid" 2>/dev/null || true
    rm -f "$RUNTIME_ROOT/$category.pid"
  done
  wait 2>/dev/null || true
  exit "$result"
}
trap cleanup EXIT INT TERM

MONGODB_ROOT="$RUNTIME_ROOT/mongodb"
MONGODB_RUN_DIR="$MONGODB_ROOT/run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
MONGODB_DATA_DIR="$MONGODB_RUN_DIR/data"
MONGODB_LOG="$MONGODB_RUN_DIR/mongod.log"
MONGODB_ENGINE_PIDFILE="$MONGODB_RUN_DIR/mongod.engine.pid"
mkdir -p "$MONGODB_DATA_DIR"
if [[ "$UAT_EXTERNAL_MONGODB" == true ]]; then
  # Container-hosted MongoDB sockets are not necessarily visible to lsof on
  # GitHub runners, so this authenticated ping is the reachability authority.
  "$VENV_PYTHON" -c 'from pymongo import MongoClient; MongoClient("'"$UAT_MONGODB_URI"'", serverSelectionTimeoutMS=5000).admin.command("ping")' > "$RUNTIME_DIR/mongodb-external.log" 2>&1 || { cat "$RUNTIME_DIR/mongodb-external.log" >&2; exit 1; }
else
  MONGOD_BIN="${MONGOD_BIN:-$(command -v mongod || true)}"
  [[ -x "$MONGOD_BIN" ]] || { echo "mongod is required for local transaction UAT" >&2; exit 1; }
  "$MONGOD_BIN" --replSet earnalism-uat-rs0 --bind_ip 127.0.0.1 --port "$UAT_MONGODB_PORT" --dbpath "$MONGODB_DATA_DIR" --logpath "$MONGODB_LOG" --pidfilepath "$MONGODB_ENGINE_PIDFILE" --nounixsocket > "$RUNTIME_DIR/mongodb.log" 2>&1 & MONGODB_PID=$!
  write_pid "$MONGODB_PID" mongodb "$UAT_MONGODB_PORT"
  for _ in $(seq 1 45); do kill -0 "$MONGODB_PID" 2>/dev/null || { tail -80 "$RUNTIME_DIR/mongodb.log" >&2; exit 1; }; [[ "$(port_pid "$UAT_MONGODB_PORT")" == "$MONGODB_PID" ]] && break; sleep 1; done
  [[ "$(port_pid "$UAT_MONGODB_PORT")" == "$MONGODB_PID" ]] || { tail -80 "$RUNTIME_DIR/mongodb.log" >&2; exit 1; }
fi
"$VENV_PYTHON" scripts/init_uat_mongodb.py > "$RUNTIME_DIR/mongodb-primary.log" 2>&1 || { cat "$RUNTIME_DIR/mongodb-primary.log" >&2; exit 1; }

REDIS_BIN="${REDIS_BIN:-$(command -v redis-server || true)}"
[[ -x "$REDIS_BIN" ]] || { echo "redis-server is required for Reading Pass UAT" >&2; exit 1; }
"$REDIS_BIN" --bind 127.0.0.1 --port "$UAT_REDIS_PORT" --save '' --appendonly no --protected-mode yes > "$RUNTIME_DIR/redis.log" 2>&1 & REDIS_PID=$!
write_pid "$REDIS_PID" redis "$UAT_REDIS_PORT"
for _ in $(seq 1 45); do kill -0 "$REDIS_PID" 2>/dev/null || { tail -80 "$RUNTIME_DIR/redis.log" >&2; exit 1; }; "${REDIS_BIN%redis-server}redis-cli" -h 127.0.0.1 -p "$UAT_REDIS_PORT" ping 2>/dev/null | grep -qx PONG && break; sleep 1; done
"${REDIS_BIN%redis-server}redis-cli" -h 127.0.0.1 -p "$UAT_REDIS_PORT" ping | grep -qx PONG || { tail -80 "$RUNTIME_DIR/redis.log" >&2; exit 1; }

"$VENV_PYTHON" scripts/verify_p1_isolated_preflight.py > "$RUNTIME_DIR/p1-preflight.log" 2>&1 || { cat "$RUNTIME_DIR/p1-preflight.log" >&2; exit 1; }

"$VENV_PYTHON" -m uvicorn backend.server:app --host "$UAT_BACKEND_HOST" --port "$UAT_BACKEND_PORT" > "$RUNTIME_DIR/backend.log" 2>&1 & BACKEND_PID=$!
write_pid "$BACKEND_PID" backend "$UAT_BACKEND_PORT"
for _ in $(seq 1 90); do kill -0 "$BACKEND_PID" 2>/dev/null || { tail -80 "$RUNTIME_DIR/backend.log" >&2; exit 1; }; [[ "$(port_pid "$UAT_BACKEND_PORT")" == "$BACKEND_PID" ]] && curl -fsS "http://$UAT_BACKEND_HOST:$UAT_BACKEND_PORT/healthz" >/dev/null 2>&1 && break; sleep 1; done
[[ "$(port_pid "$UAT_BACKEND_PORT")" == "$BACKEND_PID" ]] || { tail -80 "$RUNTIME_DIR/backend.log" >&2; exit 1; }
curl -fsS "http://$UAT_BACKEND_HOST:$UAT_BACKEND_PORT/healthz" >/dev/null
"$VENV_PYTHON" scripts/seed_uat_canonical_pages.py > "$RUNTIME_DIR/canonical-pages.log" 2>&1 || { cat "$RUNTIME_DIR/canonical-pages.log" >&2; exit 1; }

rm -rf "$ROOT_DIR/frontend/build"
if ! npm --prefix frontend run build > "$RUNTIME_DIR/frontend.log" 2>&1; then
  cat "$RUNTIME_DIR/frontend.log" >&2
  exit 1
fi
node scripts/serve_frontend_build.js --host "$UAT_FRONTEND_HOST" --port "$UAT_FRONTEND_PORT" >> "$RUNTIME_DIR/frontend.log" 2>&1 & FRONTEND_PID=$!
write_pid "$FRONTEND_PID" frontend "$UAT_FRONTEND_PORT"
for _ in $(seq 1 90); do kill -0 "$FRONTEND_PID" 2>/dev/null || { tail -80 "$RUNTIME_DIR/frontend.log" >&2; exit 1; }; [[ "$(port_pid "$UAT_FRONTEND_PORT")" == "$FRONTEND_PID" ]] && curl -fsS "$UAT_BASE_URL/" >/dev/null 2>&1 && break; sleep 1; done
[[ "$(port_pid "$UAT_FRONTEND_PORT")" == "$FRONTEND_PID" ]] || { tail -80 "$RUNTIME_DIR/frontend.log" >&2; exit 1; }
curl -fsS "$UAT_BASE_URL/" >/dev/null
printf 'export UAT_FRONTEND_HOST=%q\nexport UAT_BACKEND_HOST=%q\nexport UAT_BASE_URL=%q\nexport UAT_API_BASE_URL=%q\nexport UAT_FRONTEND_PORT=%q\nexport UAT_BACKEND_PORT=%q\nexport UAT_MONGODB_PORT=%q\nexport UAT_MONGODB_URI=%q\nexport UAT_RUNTIME_DIR=%q\n' "$UAT_FRONTEND_HOST" "$UAT_BACKEND_HOST" "$UAT_BASE_URL" "$UAT_API_BASE_URL" "$UAT_FRONTEND_PORT" "$UAT_BACKEND_PORT" "$UAT_MONGODB_PORT" "$UAT_MONGODB_URI" "$RUNTIME_DIR" > "$RUNTIME_ROOT/environment.sh"
printf 'UAT_RUNTIME_DIR=%s\nUAT_BASE_URL=%s\nUAT_API_BASE_URL=%s\nUAT_MONGODB_PORT=%s\n' "$RUNTIME_DIR" "$UAT_BASE_URL" "$UAT_API_BASE_URL" "$UAT_MONGODB_PORT"
if [[ -n "${UAT_COMMAND_FILE:-}" ]]; then
  [[ "$UAT_COMMAND_FILE" == "$ROOT_DIR"/* && -f "$UAT_COMMAND_FILE" ]] || { echo "UAT_COMMAND_FILE must be an existing file in this worktree" >&2; exit 64; }
  bash "$UAT_COMMAND_FILE"
else
  wait
fi
