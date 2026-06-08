#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
LOG_DIR="$ROOT/output/audio_onboarding/background"
OUTPUT_DIR="$ROOT/output/open_source_audiobooks"
PID_FILE="$LOG_DIR/audiobook_backfill.pid"
STATUS_FILE="$LOG_DIR/audiobook_backfill_status.json"
LOG_FILE="$LOG_DIR/audiobook_backfill_${RUN_ID}.log"
LATEST_LOG="$LOG_DIR/audiobook_backfill_latest.log"

mkdir -p "$LOG_DIR" "$OUTPUT_DIR"

if [[ -f "$PID_FILE" ]]; then
  if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Audiobook backfill is already running with PID $(cat "$PID_FILE")."
    echo "Log: $LATEST_LOG"
    exit 2
  fi
  rm -f "$PID_FILE"
fi

echo "$$" > "$PID_FILE"
ln -sf "$LOG_FILE" "$LATEST_LOG"
exec >>"$LOG_FILE" 2>&1

write_status() {
  local phase="$1"
  local state="$2"
  local updated_at
  updated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '{"run_id":"%s","phase":"%s","state":"%s","updated_at":"%s","pid":%s,"log_file":"%s"}\n' \
    "$RUN_ID" "$phase" "$state" "$updated_at" "$$" "$LOG_FILE" > "$STATUS_FILE"
}

finish() {
  local code=$?
  if [[ $code -eq 0 ]]; then
    write_status "complete" "completed"
  else
    write_status "failed" "failed"
  fi
  rm -f "$PID_FILE"
  exit "$code"
}

terminate() {
  trap - EXIT
  write_status "terminated" "stopped"
  rm -f "$PID_FILE"
  exit 143
}

trap finish EXIT
trap terminate INT TERM HUP

run_step() {
  local phase="$1"
  shift
  write_status "$phase" "running"
  echo
  echo "================================================================================"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $phase"
  echo "================================================================================"
  "$@"
}

PIPER_BINARY="${PIPER_BINARY:-$ROOT/.venv-audio/bin/piper}"
PIPER_MODEL="${PIPER_MODEL_PATH:-$ROOT/.cache/audio_models/piper/en_US-lessac-medium/en_US-lessac-medium.onnx}"
PIPER_CONFIG="${PIPER_CONFIG_PATH:-$ROOT/.cache/audio_models/piper/en_US-lessac-medium/en_US-lessac-medium.onnx.json}"
BENGALI_CHUNK_CHARS="${BENGALI_CHUNK_CHARS:-1000}"
ENGLISH_CHUNK_CHARS="${ENGLISH_CHUNK_CHARS:-1600}"

RAILWAY=(railway run --service earnalism --environment production --)
PY=("$ROOT/.venv-audio/bin/python" -u scripts/open_source_audiobook_onboarding.py)
COMMON=(
  --output-dir "$OUTPUT_DIR"
  --piper-binary "$PIPER_BINARY"
  --piper-model "$PIPER_MODEL"
  --piper-config "$PIPER_CONFIG"
)

echo "Run ID: $RUN_ID"
echo "Root: $ROOT"
echo "Output: $OUTPUT_DIR"
echo "Log: $LOG_FILE"
echo "Started at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

run_step "preflight" "${RAILWAY[@]}" "${PY[@]}" preflight "${COMMON[@]}"

run_step "audit-before" "${RAILWAY[@]}" "${PY[@]}" audit "${COMMON[@]}"

run_step "bengali-backfill" \
  "${RAILWAY[@]}" "${PY[@]}" generate \
  --lang ben \
  --upload-to-cloudinary \
  --sync-flags \
  --skip-alignment \
  --bengali-chunk-chars "$BENGALI_CHUNK_CHARS" \
  --order-shortest-first \
  "${COMMON[@]}"

run_step "english-backfill" \
  "${RAILWAY[@]}" "${PY[@]}" generate \
  --lang en \
  --upload-to-cloudinary \
  --sync-flags \
  --skip-alignment \
  --english-chunk-chars "$ENGLISH_CHUNK_CHARS" \
  --order-shortest-first \
  "${COMMON[@]}"

run_step "audit-after" "${RAILWAY[@]}" "${PY[@]}" audit "${COMMON[@]}"

echo
echo "Completed at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
