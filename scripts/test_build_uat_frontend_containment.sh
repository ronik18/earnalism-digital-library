#!/usr/bin/env bash
# Exercise destination containment before the UAT frontend builder can delete or write.
set -Eeuo pipefail

root="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture="$(mktemp -d "${TMPDIR:-/tmp}/earnalism-uat-build-containment.XXXXXX")"
trap 'rm -rf "$fixture"' EXIT

repo="$fixture/repo"
allowed="$repo/uat/evidence/system-final"
outside="$fixture/outside"
sentinel="$outside/sentinel.txt"
invocation_marker="$fixture/invoked.txt"
mkdir -p "$allowed" "$repo/scripts" "$repo/frontend/scripts" "$repo/frontend/node_modules/.bin" "$outside"
printf 'must-survive\n' > "$sentinel"
cp "$root/scripts/build_uat_frontend.sh" "$repo/scripts/build_uat_frontend.sh"
chmod +x "$repo/scripts/build_uat_frontend.sh"

cat > "$repo/frontend/scripts/generate-seo-assets.mjs" <<'EOF'
import fs from 'node:fs';
if (process.env.UAT_TEST_INVOCATION_MARKER) fs.appendFileSync(process.env.UAT_TEST_INVOCATION_MARKER, 'generator\n');
fs.mkdirSync(process.env.SEO_ASSETS_OUTPUT_DIR, { recursive: true });
fs.writeFileSync(`${process.env.SEO_ASSETS_OUTPUT_DIR}/sitemap.xml`, '<urlset/>\n');
fs.writeFileSync(`${process.env.SEO_ASSETS_OUTPUT_DIR}/robots.txt`, 'Sitemap: test\n');
EOF
printf 'process.exit(0);\n' > "$repo/frontend/scripts/generate-static-seo-snapshots.mjs"
printf 'process.exit(0);\n' > "$repo/frontend/scripts/verify-static-seo-snapshots.mjs"
cat > "$repo/frontend/node_modules/.bin/craco" <<'EOF'
#!/usr/bin/env bash
[[ -z "${UAT_TEST_INVOCATION_MARKER:-}" ]] || printf 'build\n' >> "$UAT_TEST_INVOCATION_MARKER"
mkdir -p build
EOF
chmod +x "$repo/frontend/node_modules/.bin/craco"

expect_rejected() {
  local label="$1" runtime="$2" expected_reason="$3"
  rm -f "$invocation_marker"
  if UAT_TEST_INVOCATION_MARKER="$invocation_marker" bash "$repo/scripts/build_uat_frontend.sh" "$runtime" >"$fixture/$label.log" 2>&1; then
    echo "containment control unexpectedly succeeded: $label" >&2
    exit 1
  fi
  rg -Fq "UAT frontend output must stay in the approved disposable destinations: $expected_reason" "$fixture/$label.log" || { echo "containment rejection was not specific: $label" >&2; exit 1; }
  [[ ! -e "$invocation_marker" ]] || { echo "generator or build ran for rejected control: $label" >&2; exit 1; }
  [[ "$(<"$sentinel")" == 'must-survive' ]] || { echo "outside sentinel changed: $label" >&2; exit 1; }
}

mkdir -p "$repo/uat/evidence/system-final-lookalike/run"
expect_rejected prefix-lookalike "$repo/uat/evidence/system-final-lookalike/run" "runtime directory escapes uat/evidence/system-final"
mkdir -p "$repo/uat/evidence/outside/run"
expect_rejected traversal "$allowed/../outside/run" "runtime directory escapes uat/evidence/system-final"
ln -s "$outside" "$allowed/runtime-symlink"
expect_rejected runtime-symlink "$allowed/runtime-symlink" "runtime directory escapes uat/evidence/system-final"

valid="$allowed/valid-run"
mkdir -p "$valid"
ln -s "$outside" "$valid/seo-assets"
expect_rejected seo-destination-symlink "$valid" "refusing symlink destination"
rm "$valid/seo-assets"
ln -s "$outside" "$repo/frontend/build"
expect_rejected build-destination-symlink "$valid" "refusing symlink destination"
rm "$repo/frontend/build"

root_evidence_outside="$fixture/root-evidence-outside"
mkdir -p "$root_evidence_outside/run/seo-assets"
printf 'must-survive\n' > "$root_evidence_outside/run/seo-assets/sentinel.txt"
rm -rf "$repo/uat/evidence/system-final"
ln -s "$root_evidence_outside" "$repo/uat/evidence/system-final"
expect_rejected evidence-root-symlink "$repo/uat/evidence/system-final/run" "evidence root escapes the canonical checkout"
[[ "$(<"$root_evidence_outside/run/seo-assets/sentinel.txt")" == 'must-survive' ]] || { echo "evidence-root sentinel changed" >&2; exit 1; }
rm "$repo/uat/evidence/system-final"
mkdir -p "$repo/uat/evidence/system-final"

ancestor_outside="$fixture/ancestor-outside"
mkdir -p "$ancestor_outside/evidence/system-final/run/seo-assets"
printf 'must-survive\n' > "$ancestor_outside/evidence/system-final/run/seo-assets/sentinel.txt"
rm -rf "$repo/uat"
ln -s "$ancestor_outside" "$repo/uat"
expect_rejected uat-ancestor-symlink "$repo/uat/evidence/system-final/run" "evidence root escapes the canonical checkout"
[[ "$(<"$ancestor_outside/evidence/system-final/run/seo-assets/sentinel.txt")" == 'must-survive' ]] || { echo "ancestor sentinel changed" >&2; exit 1; }
rm "$repo/uat"
mkdir -p "$repo/uat/evidence/system-final/valid-run"

frontend_outside="$fixture/frontend-outside"
mkdir -p "$frontend_outside/build"
printf 'must-survive\n' > "$frontend_outside/build/sentinel.txt"
rm -rf "$repo/frontend"
ln -s "$frontend_outside" "$repo/frontend"
expect_rejected frontend-root-symlink "$repo/uat/evidence/system-final/valid-run" "frontend root escapes the canonical checkout"
[[ "$(<"$frontend_outside/build/sentinel.txt")" == 'must-survive' ]] || { echo "frontend-root sentinel changed" >&2; exit 1; }
rm "$repo/frontend"
mkdir -p "$repo/frontend"
mkdir -p "$repo/frontend/scripts" "$repo/frontend/node_modules/.bin"
cat > "$repo/frontend/scripts/generate-seo-assets.mjs" <<'EOF'
import fs from 'node:fs';
if (process.env.UAT_TEST_INVOCATION_MARKER) fs.appendFileSync(process.env.UAT_TEST_INVOCATION_MARKER, 'generator\n');
fs.mkdirSync(process.env.SEO_ASSETS_OUTPUT_DIR, { recursive: true });
fs.writeFileSync(`${process.env.SEO_ASSETS_OUTPUT_DIR}/sitemap.xml`, '<urlset/>\n');
fs.writeFileSync(`${process.env.SEO_ASSETS_OUTPUT_DIR}/robots.txt`, 'Sitemap: test\n');
EOF
printf 'process.exit(0);\n' > "$repo/frontend/scripts/generate-static-seo-snapshots.mjs"
printf 'process.exit(0);\n' > "$repo/frontend/scripts/verify-static-seo-snapshots.mjs"
cat > "$repo/frontend/node_modules/.bin/craco" <<'EOF'
#!/usr/bin/env bash
[[ -z "${UAT_TEST_INVOCATION_MARKER:-}" ]] || printf 'build\n' >> "$UAT_TEST_INVOCATION_MARKER"
mkdir -p build
EOF
chmod +x "$repo/frontend/node_modules/.bin/craco"

rm -f "$invocation_marker"
UAT_TEST_INVOCATION_MARKER="$invocation_marker" bash "$repo/scripts/build_uat_frontend.sh" "$repo/uat/evidence/system-final/valid-run"
rg -Fq 'generator' "$invocation_marker"
rg -Fq 'build' "$invocation_marker"
test -s "$valid/seo-assets/sitemap.xml"
test -s "$repo/frontend/build/sitemap.xml"
[[ "$(<"$sentinel")" == 'must-survive' ]]

canonical_path() { python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$1"; }
canonical_repo="$(canonical_path "$repo")"
if [[ "$(uname)" == Darwin && -d /tmp && -d /private/tmp && "$(canonical_path /tmp)" == "$(canonical_path /private/tmp)" && "$canonical_repo" == "$(canonical_path /private/tmp)"/* ]]; then
  private_tmp="$(canonical_path /private/tmp)"
  tmp_alias="/tmp${canonical_repo#"$private_tmp"}"
  rm -rf "$repo/frontend/build" "$repo/uat/evidence/system-final/valid-run/seo-assets"
  UAT_TEST_INVOCATION_MARKER="$invocation_marker" bash "$repo/scripts/build_uat_frontend.sh" "$tmp_alias/uat/evidence/system-final/valid-run"
  echo "macos_tmp_alias_control=PASS"
else
  echo "macos_tmp_alias_control=NOT_RUN"
fi
echo "local-uat-frontend-build-containment-tests: PASS"
