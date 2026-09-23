#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export EARNALISM_BASE_URL="$UAT_BASE_URL"
export REGRESSION_FRONTEND_URL="$UAT_BASE_URL"
export REGRESSION_API_URL="${UAT_API_BASE_URL%/api}"
export CI=true REGRESSION_MODE=pr

case "$REGRESSION_FRONTEND_URL" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *) echo "pre-deploy regression frontend target must be loopback; production fallback is rejected" >&2; exit 64 ;;
esac
case "$REGRESSION_API_URL" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *) echo "pre-deploy regression API target must be loopback; production fallback is rejected" >&2; exit 64 ;;
esac

PYTHON_BIN="$ROOT/.venv-uat/bin/python"
[[ -x "$PYTHON_BIN" ]] || { echo "prepared isolated Python environment is required" >&2; exit 64; }

echo "==> CORS cache contract (backend/tests/test_cors_cache_headers.py)"
env \
  -u CORS_ORIGINS \
  -u FRONTEND_URL \
  ENVIRONMENT=production \
  READING_PASS_V2_ENABLED=false \
  MONGODB_URL="${MONGODB_URL:?isolated MongoDB URL is required}" \
  REDIS_URL="${REDIS_URL:?isolated Redis URL is required}" \
  JWT_SECRET="${JWT_SECRET:?isolated JWT secret is required}" \
  "$PYTHON_BIN" -m pytest -q backend/tests/test_cors_cache_headers.py backend/tests/test_reader_manifest_cache_contract.py

echo "==> Reader segment and inspection MongoDB integrations"
env \
  READER_SEGMENT_MONGO_INTEGRATION=1 \
  READING_PASS_V2_ENABLED=true \
  MONGODB_URL="${MONGODB_URL:?isolated MongoDB URL is required}" \
  REDIS_URL="${REDIS_URL:?isolated Redis URL is required}" \
  JWT_SECRET="${JWT_SECRET:?isolated JWT secret is required}" \
  READING_PASS_TOKEN_SECRET="${READING_PASS_TOKEN_SECRET:?isolated Reading Pass token secret is required}" \
  "$PYTHON_BIN" -m pytest -q \
    backend/tests/test_reader_segment_promotion_mongo_integration.py \
    backend/tests/test_reading_pass_service_concurrency.py \
    backend/tests/test_reading_pass_text_admission.py \
    backend/tests/test_reading_pass_text_admission_mongo_integration.py \
    backend/tests/test_reading_pass_revocation_release_preflight.py \
    backend/tests/test_yugalanguriya_publication_inspection.py

echo "==> Local UAT public-release hold seeding contract"
"$PYTHON_BIN" -m unittest \
  scripts.test_seed_uat_canonical_pages \
  scripts.test_validate_book_commerce_final_review \
  scripts.test_generate_copyright_rights_review_package \
  scripts.test_generate_india_launch_compliance_package

echo "==> Current catalogue resource, held-title, chapter-index and SEO invariants"
env ENVIRONMENT=development "$PYTHON_BIN" -m pytest -q \
  backend/tests/test_controlled_launch_parity.py \
  backend/tests/test_chapter_index.py \
  backend/tests/test_backend_catalog_truth.py \
  backend/tests/test_yugalanguriya_publication_inspection.py \
  scripts/test_post_deploy_static_seo_canary.py

echo "==> Signed territorial release proxy and public legal/Reader presentation contracts"
"$PYTHON_BIN" -m pytest -q \
  backend/tests/test_release_proxy_auth.py \
  backend/tests/test_release_proxy_country_middleware.py
node --test frontend/scripts/release-proxy.test.js
CI=true npm --prefix frontend test -- --watch=false --runInBand --runTestsByPath \
  src/legalDirectRoutes.test.js \
  src/bookDetailDirectRoute.test.js \
  src/components/Footer.test.js \
  src/components/ReferencePublicPages.test.jsx \
  src/staticSeoContract.test.js

npm run regression:ci
