#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
launcher="$root/scripts/start_local_uat.sh"

require_literal() {
  local file="$1" literal="$2"
  if ! rg -Fq -- "$literal" "$file"; then
    echo "required literal is missing: $literal" >&2
    return 1
  fi
}

forbid_literal() {
  local file="$1" literal="$2" result_code
  result_code=0
  rg -Fq -- "$literal" "$file" || result_code=$?
  if [[ "$result_code" -eq 0 ]]; then
    echo "forbidden literal is present: $literal" >&2
    return 1
  fi
  if [[ "$result_code" -ne 1 ]]; then
    echo "could not inspect $file for forbidden literal: $literal" >&2
    return "$result_code"
  fi
}

assert_launcher_literals() {
  local file="$1"
  forbid_literal "$file" 'external MongoDB must already listen' || return $?
  require_literal "$file" 'cat "$RUNTIME_DIR/frontend.log"' || return $?
}

launcher_fixture="$(mktemp -d "${TMPDIR:-/tmp}/earnalism-uat-launcher-fixture.XXXXXX")"
seo_output=""
trap 'rm -rf "$seo_output" "$launcher_fixture"' EXIT
bash -n "$root/scripts/start_local_uat.sh" "$root/scripts/run_local_uat.sh"
bash -n "$root/scripts/build_uat_frontend.sh"
bash "$root/scripts/test_build_uat_frontend_containment.sh"
node --check "$root/scripts/serve_frontend_build.js"
rg -q 'X-Content-Type-Options' "$root/scripts/serve_frontend_build.js"
rg -q 'X-Frame-Options' "$root/scripts/serve_frontend_build.js"
before_sitemap="$(shasum -a 256 "$root/frontend/public/sitemap.xml" | awk '{print $1}')"
before_robots="$(shasum -a 256 "$root/frontend/public/robots.txt" | awk '{print $1}')"
seo_output="$(mktemp -d "${TMPDIR:-/tmp}/earnalism-uat-seo-assets.XXXXXX")"
SEO_ASSETS_OUTPUT_DIR="$seo_output" node "$root/frontend/scripts/generate-seo-assets.mjs" >/dev/null
test -s "$seo_output/sitemap.xml"
test -s "$seo_output/robots.txt"
rg -q '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' "$seo_output/sitemap.xml"
rg -q '^Sitemap: ' "$seo_output/robots.txt"
[[ "$(shasum -a 256 "$root/frontend/public/sitemap.xml" | awk '{print $1}')" == "$before_sitemap" ]]
[[ "$(shasum -a 256 "$root/frontend/public/robots.txt" | awk '{print $1}')" == "$before_robots" ]]
rg -q 'build_uat_frontend.sh "\$RUNTIME_DIR"' "$launcher"
rg -q 'SEO_ASSETS_OUTPUT_DIR="\$UAT_SEO_ASSETS_DIR"' "$root/scripts/build_uat_frontend.sh"
rg -q 'node_modules/.bin/craco build' "$root/scripts/build_uat_frontend.sh"
rg -q 'build_uat_frontend.sh "\$UAT_RUNTIME_DIR"' "$root/scripts/run_system_uat_gates.sh"
for port in 13000 13099 18000 18099 27018 27099; do [[ "$port" =~ ^[0-9]+$ ]] || exit 1; done
rg -q 'select_port.*backend 18000 18099' "$launcher"
rg -q 'select_port.*frontend 13000 13099' "$launcher"
rg -q 'pid_matches_file' "$launcher"
rg -q 'kill -0' "$launcher"
rg -q 'earnalism-uat-rs0' "$launcher"
rg -q 'scripts/init_uat_mongodb.py' "$launcher"
rg -q 'scripts/seed_uat_canonical_pages.py' "$launcher"
rg -q 'select_port.*mongodb 27018 27099' "$launcher"
rg -q 'UAT_EXTERNAL_MONGODB' "$launcher"
rg -q 'MongoClient' "$launcher"
assert_launcher_literals "$launcher"

cp "$launcher" "$launcher_fixture/forbidden.sh"
printf '\n# external MongoDB must already listen\n' >> "$launcher_fixture/forbidden.sh"
if assert_launcher_literals "$launcher_fixture/forbidden.sh"; then
  echo "negative control unexpectedly accepted forbidden MongoDB wording" >&2
  exit 1
fi
awk 'index($0, "cat \"$RUNTIME_DIR/frontend.log\"") == 0 { print }' "$launcher" > "$launcher_fixture/missing-frontend-log.sh"
if assert_launcher_literals "$launcher_fixture/missing-frontend-log.sh"; then
  echo "negative control unexpectedly accepted missing frontend-log statement" >&2
  exit 1
fi
if assert_launcher_literals "$launcher_fixture/not-readable-or-present.sh"; then
  echo "negative control unexpectedly accepted an unreadable launcher fixture" >&2
  exit 1
fi
echo "local-uAT-launcher-focused-tests: PASS"
