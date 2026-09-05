#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash -n "$root/scripts/start_local_uat.sh" "$root/scripts/run_local_uat.sh"
bash -n "$root/scripts/build_uat_frontend.sh"
node --check "$root/scripts/serve_frontend_build.js"
rg -q 'X-Content-Type-Options' "$root/scripts/serve_frontend_build.js"
rg -q 'X-Frame-Options' "$root/scripts/serve_frontend_build.js"
before_sitemap="$(shasum -a 256 "$root/frontend/public/sitemap.xml" | awk '{print $1}')"
before_robots="$(shasum -a 256 "$root/frontend/public/robots.txt" | awk '{print $1}')"
seo_output="$(mktemp -d "${TMPDIR:-/tmp}/earnalism-uat-seo-assets.XXXXXX")"
trap 'rm -rf "$seo_output"' EXIT
SEO_ASSETS_OUTPUT_DIR="$seo_output" node "$root/frontend/scripts/generate-seo-assets.mjs" >/dev/null
test -s "$seo_output/sitemap.xml"
test -s "$seo_output/robots.txt"
rg -q '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' "$seo_output/sitemap.xml"
rg -q '^Sitemap: ' "$seo_output/robots.txt"
[[ "$(shasum -a 256 "$root/frontend/public/sitemap.xml" | awk '{print $1}')" == "$before_sitemap" ]]
[[ "$(shasum -a 256 "$root/frontend/public/robots.txt" | awk '{print $1}')" == "$before_robots" ]]
rg -q 'build_uat_frontend.sh "\$RUNTIME_DIR"' "$root/scripts/start_local_uat.sh"
rg -q 'SEO_ASSETS_OUTPUT_DIR="\$UAT_SEO_ASSETS_DIR"' "$root/scripts/build_uat_frontend.sh"
rg -q 'node_modules/.bin/craco build' "$root/scripts/build_uat_frontend.sh"
rg -q 'build_uat_frontend.sh "\$UAT_RUNTIME_DIR"' "$root/scripts/run_system_uat_gates.sh"
for port in 13000 13099 18000 18099 27018 27099; do [[ "$port" =~ ^[0-9]+$ ]] || exit 1; done
rg -q 'select_port.*backend 18000 18099' "$root/scripts/start_local_uat.sh"
rg -q 'select_port.*frontend 13000 13099' "$root/scripts/start_local_uat.sh"
rg -q 'pid_matches_file' "$root/scripts/start_local_uat.sh"
rg -q 'kill -0' "$root/scripts/start_local_uat.sh"
rg -q 'earnalism-uat-rs0' "$root/scripts/start_local_uat.sh"
rg -q 'scripts/init_uat_mongodb.py' "$root/scripts/start_local_uat.sh"
rg -q 'scripts/seed_uat_canonical_pages.py' "$root/scripts/start_local_uat.sh"
rg -q 'select_port.*mongodb 27018 27099' "$root/scripts/start_local_uat.sh"
rg -q 'UAT_EXTERNAL_MONGODB' "$root/scripts/start_local_uat.sh"
rg -q 'MongoClient' "$root/scripts/start_local_uat.sh"
! rg -q 'external MongoDB must already listen' "$root/scripts/start_local_uat.sh"
rg -q 'cat "$RUNTIME_DIR/frontend.log"' "$root/scripts/start_local_uat.sh"
echo "local-uAT-launcher-focused-tests: PASS"
