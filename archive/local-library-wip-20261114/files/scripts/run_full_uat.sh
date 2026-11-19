#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ -z "${UAT_BASE_URL:-}" ]]; then
  echo "UAT_BASE_URL is required for full UAT execution." >&2
  echo "Example: UAT_BASE_URL=http://127.0.0.1:3000 bash scripts/run_full_uat.sh" >&2
  exit 1
fi

if [[ -z "${UAT_API_BASE_URL:-}" ]]; then
  echo "UAT_API_BASE_URL is required for full UAT execution." >&2
  echo "Example: UAT_API_BASE_URL=http://127.0.0.1:8000 bash scripts/run_full_uat.sh" >&2
  exit 1
fi

if [[ ! "${UAT_BASE_URL}" =~ ^https?:// ]]; then
  echo "UAT_BASE_URL must be a URL (for example http://127.0.0.1:3000)." >&2
  exit 1
fi

if [[ "${UAT_BASE_URL}" == *"//theearnalism.com"* ]] || [[ "${UAT_BASE_URL}" == *"//www.theearnalism.com"* ]]; then
  echo "UAT_BASE_URL must not target production hostnames theearnalism.com or www.theearnalism.com." >&2
  exit 1
fi

if [[ "${UAT_API_BASE_URL}" == *"//theearnalism.com"* ]] || [[ "${UAT_API_BASE_URL}" == *"//www.theearnalism.com"* ]]; then
  echo "UAT_API_BASE_URL must not target production hostnames theearnalism.com or www.theearnalism.com." >&2
  exit 1
fi

export UAT_BASE_URL
export EARNALISM_FRONTEND_URL="${UAT_BASE_URL}"
export EARNALISM_BASE_URL="${UAT_BASE_URL}"
export FRONTEND_URL="${UAT_BASE_URL}"
export REGRESSION_FRONTEND_URL="${UAT_BASE_URL}"
export FRONTEND_BASE_URL="${UAT_BASE_URL}"
export UAT_API_BASE_URL="${UAT_API_BASE_URL}"

export API_BASE_URL="${UAT_API_BASE_URL%/}"
export API_ORIGIN="$(printf "%s\n" "${UAT_API_BASE_URL%/}" | awk -F/ '{print $1 "//" $3}')"
export EARNALISM_API_URL="${API_BASE_URL}"
export EARNALISM_FRONTEND_API_URL="${API_BASE_URL}"
export BACKEND_BASE_URL="${API_BASE_URL}"

export REACT_APP_API_URL="${EARNALISM_API_URL%/}"
export API_URL="${EARNALISM_API_URL%/}"
export REGRESSION_API_URL="${EARNALISM_API_URL%/}"
export FRONTEND_API_URL="${EARNALISM_API_URL%/}"
BACKEND_BASE_URL="${BACKEND_BASE_URL%/}"

if [[ -n "${PLAYWRIGHT_BROWSERS_PATH:-}" ]]; then
  export PLAYWRIGHT_BROWSERS_PATH
fi

RUN_EVIDENCE_DIR="${ROOT_DIR}/uat/evidence/$(date -u +%Y%m%dT%H%M%SZ)-uat-full"
mkdir -p "${RUN_EVIDENCE_DIR}"

RUN_LOG_FILE="${RUN_EVIDENCE_DIR}/run.log"
export RUN_LOG_FILE

run_step() {
  local label="$1"
  shift
  local log_file="${RUN_EVIDENCE_DIR}/${label}.log"
  if ! { "$@" 2>&1 | tee "${log_file}"; }; then
    echo "[FAIL] ${label}" | tee -a "${RUN_LOG_FILE}" >&2
    return 1
  fi
  echo "[PASS] ${label}" | tee -a "${RUN_LOG_FILE}"
}

run_step_check_playwright_results() {
  local results_file="output/real-user-ux/playwright-results.json"
  if [[ ! -f "${results_file}" ]]; then
    echo "Playwright results file not found: ${results_file}" >&2
    return 1
  fi

  python3 - "$results_file" <<'PY'
import json
import sys

results_path = sys.argv[1]
with open(results_path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

tests = []

def walk_suites(suites):
    for suite in suites or []:
        for spec in suite.get("specs", []) or []:
            for test in spec.get("tests", []) or []:
                result = (test.get("results") or [{}])[-1]
                status = result.get("status", "missing")
                tests.append(
                    {
                        "title": spec.get("title", ""),
                        "status": status,
                    }
                )
        walk_suites(suite.get("suites", []) or [])

walk_suites(data.get("suites") or [])

bad = [test for test in tests if test["status"] != "passed"]
if bad:
    print(f"Playwright has non-pass/skip results ({len(bad)})")
    for item in bad[:50]:
        print(f"- {item['title']}: {item['status']}")
    raise SystemExit(1)
PY
}

run_step_check_regression_results() {
  if [[ ! -f "regression/results.json" ]]; then
    echo "Regression results file not found." >&2
    return 1
  fi
  python3 - <<'PY'
import json

with open("regression/results.json", "r", encoding="utf-8") as handle:
    data = json.load(handle)

if not data.get("pass", False):
    raise SystemExit(1)
if data.get("mandatoryFailures"):
    raise SystemExit(1)
summary = data.get("summary", {})
if summary.get("failedMandatoryModules") not in (None, 0):
    raise SystemExit(1)
PY
}

run_step_regen_final_report() {
  if [[ ! -f "uat/final-report.json" ]]; then
    return 0
  fi
  python3 - "${RUN_EVIDENCE_DIR}" <<'PY'
import json
import pathlib
import sys
from datetime import datetime, timezone

path = pathlib.Path("uat/final-report.json")
data = json.loads(path.read_text(encoding="utf-8"))
data.update(
    {
        "evidence_path": "uat/evidence/" + pathlib.Path(sys.argv[1]).name,
        "commands_executed": [],
        "final_regression_passed": data.get("final_regression_passed", False),
        "last_automated_full_uat_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
)
commands = []
with open(pathlib.Path(sys.argv[1]) / "run.log", "r", encoding="utf-8") as handle:
    for line in handle:
        if line.startswith("[PASS] "):
            commands.append(line.strip().split(" ", 1)[1])
data["commands_executed"] = commands
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

STARTER_PID=""
STARTER_LOG="${RUN_EVIDENCE_DIR}/start_local_uat.log"
bash scripts/start_local_uat.sh >"${STARTER_LOG}" 2>&1 &
STARTER_PID=$!

STARTUP_TIMEOUT_SECONDS=120
STARTUP_READY=0
for _ in $(seq 1 "${STARTUP_TIMEOUT_SECONDS}"); do
  if ! kill -0 "${STARTER_PID}" >/dev/null 2>&1; then
    echo "UAT local launcher failed to start. See ${STARTER_LOG}" >&2
    exit 1
  fi
  if curl -fsS "${BACKEND_BASE_URL}/healthz" >/dev/null 2>&1 && \
     curl -fsS "${UAT_BASE_URL}" >/dev/null 2>&1; then
    STARTUP_READY=1
    break
  fi
  sleep 1
done
if [[ "${STARTUP_READY}" != "1" ]]; then
  echo "Services did not become healthy within ${STARTUP_TIMEOUT_SECONDS} seconds." >&2
  cleanup 1
fi

cleanup() {
  local code=$?
  if [[ -n "${STARTER_PID}" ]] && kill -0 "${STARTER_PID}" >/dev/null 2>&1; then
    kill "${STARTER_PID}" >/dev/null 2>&1 || true
    wait "${STARTER_PID}" >/dev/null 2>&1 || true
  fi
  exit "${code}"
}
trap cleanup EXIT INT TERM

set +e
if ! run_step "reader-typography-contrast" bash -lc "node frontend/scripts/reader-typography-contrast.mjs"; then
  cleanup 1
fi
if ! run_step "playwright-real-user-audit" bash -lc "npx playwright test tests/e2e/earnalism-real-user-journey.spec.js --project=chromium --project=firefox --project=webkit"; then
  cleanup 1
fi
if ! run_step_check_playwright_results; then
  cleanup 1
fi
if ! run_step "regression-suite" bash -lc "CI=true REGRESSION_MODE=pr npm run regression -- --json --outputFile=regression/results.json"; then
  cleanup 1
fi
if ! run_step_check_regression_results; then
  cleanup 1
fi
if ! run_step "ux-report-generator" bash -lc "python3 scripts/generate_real_user_ux_report.py"; then
  cleanup 1
fi
if ! run_step_regen_final_report; then
  echo "Failed to regenerate uat/final-report.json" >&2
  cleanup 1
fi
set -e

echo "Full UAT completed successfully."
echo "UAT evidence directory: ${RUN_EVIDENCE_DIR}" | tee -a "${RUN_LOG_FILE}"
echo "FRONTEND_URL=${UAT_BASE_URL}" | tee -a "${RUN_LOG_FILE}"
echo "FRONTEND_API_URL=${EARNALISM_API_URL}" | tee -a "${RUN_LOG_FILE}"
echo "BACKEND_URL=${BACKEND_BASE_URL}" | tee -a "${RUN_LOG_FILE}"

cleanup 0
