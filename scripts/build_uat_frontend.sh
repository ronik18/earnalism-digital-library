#!/usr/bin/env bash
# Build the local UAT frontend without writing generated SEO assets to source.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${1:?UAT runtime directory is required}"
case "$RUNTIME_DIR" in
  "$ROOT_DIR"/uat/evidence/system-final/*) ;;
  *) echo "UAT frontend output must stay under uat/evidence/system-final" >&2; exit 64 ;;
esac

UAT_SEO_ASSETS_DIR="$RUNTIME_DIR/seo-assets"
rm -rf "$ROOT_DIR/frontend/build" "$UAT_SEO_ASSETS_DIR"
SEO_ASSETS_OUTPUT_DIR="$UAT_SEO_ASSETS_DIR" node "$ROOT_DIR/frontend/scripts/generate-seo-assets.mjs"
(cd "$ROOT_DIR/frontend" && GENERATE_SOURCEMAP=false ./node_modules/.bin/craco build)
node "$ROOT_DIR/frontend/scripts/generate-static-seo-snapshots.mjs"
node "$ROOT_DIR/frontend/scripts/verify-static-seo-snapshots.mjs"
cp "$UAT_SEO_ASSETS_DIR/sitemap.xml" "$ROOT_DIR/frontend/build/sitemap.xml"
cp "$UAT_SEO_ASSETS_DIR/robots.txt" "$ROOT_DIR/frontend/build/robots.txt"
