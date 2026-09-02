#!/usr/bin/env bash
set -euo pipefail

# Invoked only by the disposable local/CI UAT launcher after /healthz passes.
# It deliberately uses the launcher-provided loopback backend URL.
export REACT_APP_BACKEND_URL="${UAT_API_BASE_URL%/api}"
: "${ADMIN_EMAIL:?launcher must provide synthetic admin identity}"
: "${ADMIN_PASSWORD:?launcher must provide synthetic admin credential}"
# The older reader-session and chapter-gating suites target a retired contract
# (chapter access without Reading Pass leases).  The loopback checks included
# in cache_media exercise the current canonical-page authorization surface.
pytest -q backend/tests/cache_media
CI=true npm test --prefix frontend -- --watchAll=false --runInBand
