#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PYTHON="${BACKEND_PYTHON:-$REPO_ROOT/.venv-uat/bin/python}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

RUNTIME_DIR="${ROOT_DIR}/uat/runtime"
mkdir -p "${RUNTIME_DIR}"
RUNTIME_LOG_DIR="${RUNTIME_DIR}/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "${RUNTIME_LOG_DIR}"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
DEV_FRONTEND_MODE="${UAT_FRONTEND_DEV_MODE:-0}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-120}"
BACKEND_HEALTH_PATH="${BACKEND_HEALTH_PATH:-/healthz}"

BACKEND_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
FRONTEND_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"
BACKEND_HEALTH_URL="${BACKEND_URL}${BACKEND_HEALTH_PATH}"
API_BASE_URL="${BACKEND_URL}"
API_BASE_URL="${API_BASE_URL%/}"

BACKEND_LOG="${RUNTIME_LOG_DIR}/backend.log"
FRONTEND_LOG="${RUNTIME_LOG_DIR}/frontend.log"

export ENVIRONMENT="${ENVIRONMENT:-uat}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"
export MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-2}"
export COST_CONTROL_MODE="${COST_CONTROL_MODE:-true}"
export ENABLE_BACKGROUND_WORKERS="${ENABLE_BACKGROUND_WORKERS:-false}"
export ENABLE_AUDIOBOOK_PIPELINE="${ENABLE_AUDIOBOOK_PIPELINE:-false}"
export ENABLE_BOOK_RENDERING_JOBS="${ENABLE_BOOK_RENDERING_JOBS:-false}"
export ENABLE_COVER_GENERATION="${ENABLE_COVER_GENERATION:-false}"
export ENABLE_SCHEDULED_JOBS="${ENABLE_SCHEDULED_JOBS:-false}"
export ENABLE_QUEUE_CONSUMER="${ENABLE_QUEUE_CONSUMER:-false}"
export ENABLE_ADMIN_MEDIA_UPLOADS="${ENABLE_ADMIN_MEDIA_UPLOADS:-false}"
export ENABLE_STARTUP_DB_MAINTENANCE="${ENABLE_STARTUP_DB_MAINTENANCE:-false}"
export MONGODB_URL="${MONGODB_URL:-mongodb://127.0.0.1:27017/earnalism_uat}"
export JWT_SECRET="${JWT_SECRET:-uat-local-jwt-secret}"
export MULTI_REPLICA_ENABLED="${MULTI_REPLICA_ENABLED:-false}"
export REDIS_CACHE_ENABLED="${REDIS_CACHE_ENABLED:-false}"
export REDIS_CACHE_FAIL_FAST="${REDIS_CACHE_FAIL_FAST:-false}"
export PUBLIC_CACHE_MAX_ENTRIES="${PUBLIC_CACHE_MAX_ENTRIES:-96}"
export HOME_BOOK_LIMIT="${HOME_BOOK_LIMIT:-120}"
export WEB_CONCURRENCY="${WEB_CONCURRENCY:-1}"
export UVICORN_KEEP_ALIVE="${UVICORN_KEEP_ALIVE:-10}"
export UVICORN_GRACEFUL_TIMEOUT="${UVICORN_GRACEFUL_TIMEOUT:-10}"

unset RAZORPAY_KEY_ID
unset RAZORPAY_KEY_SECRET
unset RAZORPAY_WEBHOOK_SECRET
unset STRIPE_SECRET_KEY
unset STRIPE_PUBLIC_KEY
unset STRIPE_WEBHOOK_SECRET

export REACT_APP_BACKEND_URL="${BACKEND_URL}"
export REACT_APP_API_URL="${API_BASE_URL}"
export EARNALISM_FRONTEND_URL="${FRONTEND_URL}"
export EARNALISM_API_URL="${API_BASE_URL}/api"
export EARNALISM_BASE_URL="${FRONTEND_URL}"

export BACKEND_URL
export FRONTEND_URL
export BACKEND_HEALTH_URL
export BACKEND_PID
export FRONTEND_PID

BACKEND_PID=""
FRONTEND_PID=""

is_running() {
  kill -0 "$1" >/dev/null 2>&1
}

show_recent_logs() {
  local log_file="$1"
  if [[ -s "${log_file}" ]]; then
    tail -n 120 "${log_file}"
  else
    echo "(no log output)"
  fi
}

die_on_child_exit() {
  local label="$1"
  local pid="$2"
  local log_file="$3"

  local child_code=1
  if wait "${pid}" 2>/dev/null; then
    child_code=$?
  fi
  echo "${label} process exited before readiness check (status ${child_code}). Last 120 log lines:" >&2
  show_recent_logs "${log_file}" >&2
  exit 1
}

wait_for_service() {
  local label="$1"
  local url="$2"
  local pid="$3"
  local log_file="$4"
  local timeout_seconds="${5:-${STARTUP_TIMEOUT_SECONDS}}"
  local check_pid="${6:-}"
  local check_pid_log="${7:-}"

  local start_time
  local elapsed
  start_time="$(date +%s)"

  while true; do
    if ! is_running "${pid}"; then
      die_on_child_exit "${label}" "${pid}" "${log_file}"
    fi

    if [[ -n "${check_pid}" ]] && ! is_running "${check_pid}"; then
      die_on_child_exit "${check_pid} peer" "${check_pid}" "${check_pid_log}"
    fi

    if curl -fsS --max-time 2 "${url}" >/dev/null; then
      return 0
    fi

    elapsed=$(( $(date +%s) - start_time ))
    if (( elapsed >= timeout_seconds )); then
      echo "Timed out waiting for ${label} at ${url} after ${timeout_seconds}s." >&2
      show_recent_logs "${log_file}" >&2
      return 1
    fi

    sleep 1
  done
}

cleanup() {
  local code=$?
  if [[ -n "${BACKEND_PID}" ]] && is_running "${BACKEND_PID}"; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
    wait "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONTEND_PID}" ]] && is_running "${FRONTEND_PID}"; then
    kill "${FRONTEND_PID}" >/dev/null 2>&1 || true
    wait "${FRONTEND_PID}" >/dev/null 2>&1 || true
  fi
  exit "${code}"
}

trap cleanup EXIT INT TERM

START_TIME="$(date -u +%s)"


# BEGIN EARNALISM UAT PYTHON PIN
UAT_PYTHON="$REPO_ROOT/.venv-uat/bin/python"

if [[ ! -x "$UAT_PYTHON" ]]; then
  echo "ERROR: Missing UAT Python interpreter: $UAT_PYTHON" >&2
  exit 1
fi

if ! "$UAT_PYTHON" -c 'import uvicorn' >/dev/null 2>&1; then
  echo "ERROR: Uvicorn is not installed in $UAT_PYTHON" >&2
  echo "Run: $UAT_PYTHON -m pip install -r backend/requirements.txt" >&2
  exit 1
fi

# Override every common interpreter variable immediately before backend launch.
BACKEND_PYTHON="$UAT_PYTHON"
PYTHON_BIN="$UAT_PYTHON"
PYTHON="$UAT_PYTHON"
# END EARNALISM UAT PYTHON PIN

echo "==> Starting backend on ${BACKEND_URL}"
(
  cd "${ROOT_DIR}/backend"
  export PYTHONPATH="${ROOT_DIR}/backend:${PYTHONPATH:-}"
  "$UAT_PYTHON" -m uvicorn server:app \
    --host "${BACKEND_HOST}" \
    --port "${BACKEND_PORT}" \
    --workers "${WEB_CONCURRENCY}" \
    --proxy-headers \
    --forwarded-allow-ips '*' \
    --timeout-keep-alive "${UVICORN_KEEP_ALIVE}" \
    --timeout-graceful-shutdown "${UVICORN_GRACEFUL_TIMEOUT}"
) >>"${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!

echo "BACKEND_PID=${BACKEND_PID}"

if ! wait_for_service "backend" "${BACKEND_HEALTH_URL}" "${BACKEND_PID}" "${BACKEND_LOG}" "${STARTUP_TIMEOUT_SECONDS}"; then
  echo "Backend failed to become healthy. Check ${BACKEND_LOG}" >&2
  exit 1
fi

if [[ "${DEV_FRONTEND_MODE}" == "1" ]]; then
  echo "==> Starting frontend in local dev mode for maintenance on ${FRONTEND_URL}"
  (
    BROWSER=none \
    HOST="${FRONTEND_HOST}" \
    PORT="${FRONTEND_PORT}" \
    REACT_APP_BACKEND_URL="${REACT_APP_BACKEND_URL}" \
    REACT_APP_API_URL="${REACT_APP_API_URL}" \
    npm run start --prefix frontend
  ) >>"${FRONTEND_LOG}" 2>&1 &
  FRONTEND_PID=$!
else
  echo "==> Building frontend for local UAT"
  npm run build --prefix frontend

  echo "==> Starting production-like frontend server on ${FRONTEND_URL}"
  (
    FRONTEND_HOST="${FRONTEND_HOST}" \
    FRONTEND_PORT="${FRONTEND_PORT}" \
    node scripts/serve_frontend_build.js
  ) >>"${FRONTEND_LOG}" 2>&1 &
  FRONTEND_PID=$!
fi

echo "FRONTEND_PID=${FRONTEND_PID}"

if ! wait_for_service "frontend" "${FRONTEND_URL}" "${FRONTEND_PID}" "${FRONTEND_LOG}" "${STARTUP_TIMEOUT_SECONDS}" "${BACKEND_PID}" "${BACKEND_LOG}"; then
  echo "Frontend failed to become ready. Check ${FRONTEND_LOG}" >&2
  exit 1
fi

ELAPSED=$(( $(date -u +%s) - START_TIME ))
echo "STARTED"
echo "BACKEND_URL=${BACKEND_URL}"
echo "BACKEND_HEALTH_URL=${BACKEND_HEALTH_URL}"
echo "FRONTEND_URL=${FRONTEND_URL}"
echo "Backend startup time: ${ELAPSED}s"
echo "Log directory: ${RUNTIME_LOG_DIR}"
echo "Backend log: ${BACKEND_LOG}"
echo "Frontend log: ${FRONTEND_LOG}"

wait
