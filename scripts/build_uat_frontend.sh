#!/usr/bin/env bash
# Build the local UAT frontend without writing generated SEO assets to source.
set -Eeuo pipefail

ROOT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR_INPUT="${1:?UAT runtime directory is required}"

canonical_path() {
  python3 - "$1" <<'PY'
import os
import sys

print(os.path.realpath(sys.argv[1]))
PY
}

fail_containment() {
  echo "UAT frontend output must stay in the approved disposable destinations: $1" >&2
  exit 64
}

CANONICAL_CHECKOUT_ROOT="$(canonical_path "$ROOT_DIR")"
EVIDENCE_ROOT="$ROOT_DIR/uat/evidence/system-final"
FRONTEND_ROOT="$ROOT_DIR/frontend"
EXPECTED_EVIDENCE_ROOT="$CANONICAL_CHECKOUT_ROOT/uat/evidence/system-final"
EXPECTED_FRONTEND_ROOT="$CANONICAL_CHECKOUT_ROOT/frontend"
[[ -d "$EVIDENCE_ROOT" && -d "$FRONTEND_ROOT" ]] || fail_containment "required roots are missing"
[[ -d "$RUNTIME_DIR_INPUT" ]] || fail_containment "runtime directory does not exist"

CANONICAL_EVIDENCE_ROOT="$(canonical_path "$EVIDENCE_ROOT")"
CANONICAL_RUNTIME_DIR="$(canonical_path "$RUNTIME_DIR_INPUT")"
CANONICAL_FRONTEND_ROOT="$(canonical_path "$FRONTEND_ROOT")"
[[ "$CANONICAL_EVIDENCE_ROOT" == "$EXPECTED_EVIDENCE_ROOT" ]] || fail_containment "evidence root escapes the canonical checkout"
[[ "$CANONICAL_FRONTEND_ROOT" == "$EXPECTED_FRONTEND_ROOT" ]] || fail_containment "frontend root escapes the canonical checkout"
case "$CANONICAL_RUNTIME_DIR" in
  "$CANONICAL_EVIDENCE_ROOT"/*) ;;
  *) fail_containment "runtime directory escapes uat/evidence/system-final" ;;
esac

UAT_SEO_ASSETS_DIR="$CANONICAL_RUNTIME_DIR/seo-assets"
FRONTEND_BUILD_DIR="$CANONICAL_FRONTEND_ROOT/build"
for destination in "$UAT_SEO_ASSETS_DIR" "$FRONTEND_BUILD_DIR"; do
  if [[ -L "$destination" ]]; then
    fail_containment "refusing symlink destination $destination"
  fi
  if [[ -e "$destination" && "$(canonical_path "$destination")" != "$destination" ]]; then
    fail_containment "destination resolves outside its approved path: $destination"
  fi
done

rm -rf "$FRONTEND_BUILD_DIR" "$UAT_SEO_ASSETS_DIR"
SEO_ASSETS_OUTPUT_DIR="$UAT_SEO_ASSETS_DIR" node "$ROOT_DIR/frontend/scripts/generate-seo-assets.mjs"
(cd "$ROOT_DIR/frontend" && GENERATE_SOURCEMAP=false ./node_modules/.bin/craco build)
node "$ROOT_DIR/frontend/scripts/generate-static-seo-snapshots.mjs"
node "$ROOT_DIR/frontend/scripts/verify-static-seo-snapshots.mjs"
cp "$UAT_SEO_ASSETS_DIR/sitemap.xml" "$FRONTEND_BUILD_DIR/sitemap.xml"
cp "$UAT_SEO_ASSETS_DIR/robots.txt" "$FRONTEND_BUILD_DIR/robots.txt"
