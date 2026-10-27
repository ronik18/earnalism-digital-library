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

echo "==> Protected package publication proof and scope qualification"
"$PYTHON_BIN" -m pytest -q backend/tests/test_api_public_catalog_projection.py backend/tests/test_protected_package_publication.py internal/audiobook_lab/scripts/test_new_title_publication_acceptance.py internal/audiobook_lab/scripts/test_audiobook_active_release_v2.py

echo "==> Isolated owner-accepted US rights intake (no activation)"
"$PYTHON_BIN" -m pytest -q backend/tests/test_us_rights_intake.py

echo "==> Audio transport, current release containment, and revised reader-only manuscript"
env \
  ENVIRONMENT=uat \
  READING_PASS_V2_ENABLED=false \
  ENABLE_STARTUP_DB_MAINTENANCE=false \
  "$PYTHON_BIN" -m pytest -q \
    backend/tests/test_b2_audiobook_routing.py \
    backend/tests/test_audiobook_package_v2_routes.py \
    backend/tests/test_audio_stream_chunking.py \
    backend/tests/test_unapproved_public_audio_asset_safety.py \
    backend/tests/test_agentic_ai_with_python_reader_only.py \
    scripts/test_repair_enchanted_april_reader_preflight.py

echo "==> Reader segment and inspection MongoDB integrations"
env \
  READER_SEGMENT_MONGO_INTEGRATION=1 \
  READING_PASS_V2_ENABLED=true \
  MONGODB_URL="${MONGODB_URL:?isolated MongoDB URL is required}" \
  REDIS_URL="${REDIS_URL:?isolated Redis URL is required}" \
  JWT_SECRET="${JWT_SECRET:?isolated JWT secret is required}" \
  READING_PASS_TOKEN_SECRET="${READING_PASS_TOKEN_SECRET:?isolated Reading Pass token secret is required}" \
  "$PYTHON_BIN" scripts/run_bounded_pytest.py --timeout-seconds 480 --trace-seconds 120 -- -vv \
    backend/tests/test_reader_segment_promotion_mongo_integration.py \
    backend/tests/test_reading_pass_service_concurrency.py \
    backend/tests/test_reading_pass_client_matrix.py \
    backend/tests/test_usage_history.py \
    backend/tests/test_reading_pass_acceptance_budget.py \
    backend/tests/test_reading_pass_negative_balance.py \
    backend/tests/test_payment_local_qualification.py \
    backend/tests/test_package_integrity_and_preview_access.py \
    backend/tests/test_open_window_audio_acceptance_budget.py \
    backend/tests/test_audio_renewal_media_cookies.py \
    backend/tests/test_open_window_audio_cap_installer.py \
    backend/tests/test_open_window_audio_cap_live.py \
    backend/tests/test_open_window_audio_cap_interlock.py \
    backend/tests/test_reader_acceptance_operator.py \
    backend/tests/test_serving_publication_binding.py \
    backend/tests/test_reading_pass_text_admission.py \
    backend/tests/test_reading_pass_text_admission_mongo_integration.py \
    backend/tests/test_reading_pass_revocation_release_preflight.py \
    backend/tests/test_reader_device_session_binding.py \
    backend/tests/test_approved_reader_bootstrap.py \
    backend/tests/test_yugalanguriya_publication_inspection.py

echo "==> Isolated Reader authentication and protected page response benchmark"
env READER_SEGMENT_MONGO_INTEGRATION=1 bash scripts/run_reader_benchmark.sh

echo "==> Local UAT public-release hold seeding contract"
"$PYTHON_BIN" -m unittest \
  scripts.test_seed_uat_canonical_pages \
  scripts.test_run_bounded_pytest \
  scripts.test_india_release_source_preflight \
  scripts.test_india_release_transition \
  scripts.test_build_india_guarded_rollback \
  scripts.test_india_release_provider_adapter \
  scripts.test_india_release_observer \
  scripts.test_india_protected_runner \
  scripts.test_validate_book_commerce_final_review \
  scripts.test_generate_copyright_rights_review_package \
  scripts.test_generate_india_launch_compliance_package \
  scripts.test_process_full_catalogue

echo "==> Current catalogue resource, held-title, chapter-index and SEO invariants"
node scripts/test_regression_asset_isolation.cjs
env ENVIRONMENT=development "$PYTHON_BIN" -m pytest -q \
  backend/tests/test_controlled_launch_parity.py \
  backend/tests/test_chapter_index.py \
  backend/tests/test_yugalanguriya_publication_inspection.py \
  scripts/test_post_deploy_static_seo_canary.py

echo "==> Signed territorial release proxy and public legal/Reader presentation contracts"
"$PYTHON_BIN" -m pytest -q \
  backend/tests/test_release_proxy_auth.py \
  backend/tests/test_release_proxy_country_middleware.py
node --test frontend/scripts/release-proxy.test.js frontend/scripts/release-proxy-streaming.test.js
CI=true npm --prefix frontend test -- --watch=false --runInBand --runTestsByPath \
  src/experiences-v2/__tests__/listener-segment-lifecycle.test.jsx \
  src/experiences-v2/__tests__/listener-resume-authorization.test.jsx \
  src/experiences-v2/__tests__/listener-protected-package-route.test.jsx \
  src/experiences-v2/__tests__/listener-zero-free-audio.test.jsx \
  src/experiences-v2/__tests__/listener-transport-canary.test.jsx \
  src/legalDirectRoutes.test.js \
  src/pages/LegalPages.test.jsx \
  src/bookDetailDirectRoute.test.js \
  src/components/Footer.test.js \
  src/components/ReferencePublicPages.test.jsx \
  src/pages/Library.test.jsx \
  src/pages/Pricing.test.jsx \
  src/authAccountLifecycle.test.jsx \
  src/staticSeoContract.test.js

npm run regression:ci
