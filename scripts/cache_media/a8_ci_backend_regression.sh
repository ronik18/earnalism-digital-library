#!/usr/bin/env bash
set -euo pipefail

# Invoked only by the disposable local/CI UAT launcher after /healthz passes.
# It deliberately uses the launcher-provided loopback backend URL.
export REACT_APP_BACKEND_URL="${UAT_API_BASE_URL%/api}"
: "${ADMIN_EMAIL:?launcher must provide synthetic admin identity}"
: "${ADMIN_PASSWORD:?launcher must provide synthetic admin credential}"
pytest -q backend/tests/backend_test.py backend/tests/test_phase2_user_reader.py backend/tests/test_chapter_gating_security.py backend/tests/test_payments_razorpay.py
pytest -q backend/tests/cache_media
CI=true npm test --prefix frontend -- --watchAll=false --runInBand
