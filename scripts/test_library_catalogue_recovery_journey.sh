#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SEAMLESS_BRAND_TEST_BASE_URL="${SEAMLESS_BRAND_TEST_BASE_URL:-${UAT_BASE_URL:?UAT_BASE_URL is required}}" node scripts/test_library_catalogue_recovery_journey.mjs
