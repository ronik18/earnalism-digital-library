#!/usr/bin/env bash
# Real HTTP handlers and MongoDB on the existing isolated regression fixture.
# This runner never installs dependencies, starts providers, or targets production.
set -Eeuo pipefail

BENCHMARK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BENCHMARK_ROOT"
BENCHMARK_PYTHON="${READER_BENCHMARK_PYTHON:-$BENCHMARK_ROOT/.venv-uat/bin/python}"
[[ -x "$BENCHMARK_PYTHON" ]] || { echo 'Reader benchmark requires the prepared isolated Python environment' >&2; exit 64; }

"$BENCHMARK_PYTHON" - <<'PY'
import os
from scripts.uat_mongo_fixture import setup_configuration

if os.environ.get('ENVIRONMENT', 'uat') not in {'uat', 'test'}:
    raise SystemExit('Reader benchmark refuses a production environment')
if os.environ.get('READER_SEGMENT_MONGO_INTEGRATION') != '1':
    raise SystemExit('Reader benchmark requires explicit isolated MongoDB integration opt-in')
try:
    setup_configuration(os.environ)
except Exception:
    raise SystemExit('Reader benchmark requires the authenticated loopback UAT fixture') from None
PY

export READER_BENCHMARK_REPORT="${READER_BENCHMARK_REPORT:-$BENCHMARK_ROOT/regression/artifacts/reader-benchmark/report.json}"
env ENVIRONMENT=uat READING_PASS_V2_ENABLED=true ENABLE_STARTUP_DB_MAINTENANCE=false \
  TRUSTED_DEVICE_MAX_ACTIVE_SESSIONS=5 \
  JWT_SECRET=reader-benchmark-isolated-only-jwt-secret \
  READING_PASS_TOKEN_SECRET=reader-benchmark-isolated-only-lease-secret-0123456789 \
  "$BENCHMARK_PYTHON" -m pytest -q backend/tests/test_reader_benchmark_mongo_integration.py

"$BENCHMARK_PYTHON" - <<'PY'
import json, os, subprocess
from pathlib import Path

report = json.loads(Path(os.environ['READER_BENCHMARK_REPORT']).read_text())
assert report['status'] == 'PASS', 'Reader benchmark did not pass'
assert report['tested_revision'] == subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert report['scope'] == 'ISOLATED_ASGI_REAL_MONGO'
assert report['production_verification'] == 'NOT_PERFORMED'
assert report['page_response_timings']['samples'] == 20
print(json.dumps({'reader_benchmark': report['status'], 'scope': report['scope'],
                  'page_response_timings': report['page_response_timings'],
                  'production_verification': report['production_verification']}))
PY
