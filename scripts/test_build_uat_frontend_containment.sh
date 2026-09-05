#!/usr/bin/env bash
# Exercise destination containment before the UAT frontend builder can delete or write.
set -Eeuo pipefail

root="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture="$(mktemp -d /private/tmp/earnalism-uat-build-containment.XXXXXX)"
trap 'rm -rf "$fixture"' EXIT

repo="$fixture/repo"
allowed="$repo/uat/evidence/system-final"
outside="$fixture/outside"
sentinel="$outside/sentinel.txt"
mkdir -p "$allowed" "$repo/scripts" "$repo/frontend/scripts" "$repo/frontend/node_modules/.bin" "$outside"
printf 'must-survive\n' > "$sentinel"
cp "$root/scripts/build_uat_frontend.sh" "$repo/scripts/build_uat_frontend.sh"
chmod +x "$repo/scripts/build_uat_frontend.sh"

cat > "$repo/frontend/scripts/generate-seo-assets.mjs" <<'EOF'
import fs from 'node:fs';
fs.mkdirSync(process.env.SEO_ASSETS_OUTPUT_DIR, { recursive: true });
fs.writeFileSync(`${process.env.SEO_ASSETS_OUTPUT_DIR}/sitemap.xml`, '<urlset/>\n');
fs.writeFileSync(`${process.env.SEO_ASSETS_OUTPUT_DIR}/robots.txt`, 'Sitemap: test\n');
EOF
printf 'process.exit(0);\n' > "$repo/frontend/scripts/generate-static-seo-snapshots.mjs"
printf 'process.exit(0);\n' > "$repo/frontend/scripts/verify-static-seo-snapshots.mjs"
cat > "$repo/frontend/node_modules/.bin/craco" <<'EOF'
#!/usr/bin/env bash
mkdir -p build
EOF
chmod +x "$repo/frontend/node_modules/.bin/craco"

expect_rejected() {
  local label="$1" runtime="$2"
  if bash "$repo/scripts/build_uat_frontend.sh" "$runtime" >"$fixture/$label.log" 2>&1; then
    echo "containment control unexpectedly succeeded: $label" >&2
    exit 1
  fi
  [[ "$(<"$sentinel")" == 'must-survive' ]] || { echo "outside sentinel changed: $label" >&2; exit 1; }
}

mkdir -p "$repo/uat/evidence/system-final-lookalike/run"
expect_rejected prefix-lookalike "$repo/uat/evidence/system-final-lookalike/run"
mkdir -p "$repo/uat/evidence/outside/run"
expect_rejected traversal "$allowed/../outside/run"
ln -s "$outside" "$allowed/runtime-symlink"
expect_rejected runtime-symlink "$allowed/runtime-symlink"

valid="$allowed/valid-run"
mkdir -p "$valid"
ln -s "$outside" "$valid/seo-assets"
expect_rejected seo-destination-symlink "$valid"
rm "$valid/seo-assets"
ln -s "$outside" "$repo/frontend/build"
expect_rejected build-destination-symlink "$valid"
rm "$repo/frontend/build"

# macOS resolves /tmp to /private/tmp; containment accepts the canonical alias.
if [[ "$repo" == /private/tmp/* ]]; then
  tmp_alias="/tmp${repo#/private/tmp}"
  bash "$repo/scripts/build_uat_frontend.sh" "$tmp_alias/uat/evidence/system-final/valid-run"
else
  bash "$repo/scripts/build_uat_frontend.sh" "$valid"
fi
test -s "$valid/seo-assets/sitemap.xml"
test -s "$repo/frontend/build/sitemap.xml"
[[ "$(<"$sentinel")" == 'must-survive' ]]
echo "local-uat-frontend-build-containment-tests: PASS"
