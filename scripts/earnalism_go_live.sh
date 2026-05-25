#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="book_import_manifest.json"

if [[ $# -gt 0 && "${1}" != --* ]]; then
  MANIFEST="${1}"
  shift
fi

if [[ "${PUBLISH_LIVE:-}" != "1" || "${HUMAN_APPROVED:-}" != "1" ]]; then
  cat >&2 <<'EOF'
Earnalism go-live requires explicit approval flags.

Run:
  PUBLISH_LIVE=1 HUMAN_APPROVED=1 scripts/earnalism_go_live.sh

Optional:
  PUBLISH_LIVE=1 HUMAN_APPROVED=1 scripts/earnalism_go_live.sh path/to/manifest.json --book-slug my-book
EOF
  exit 64
fi

cd "${ROOT}"

exec python3 scripts/bulk_publishing_pipeline.py \
  --stage go-live \
  --manifest "${MANIFEST}" \
  --update-existing-drafts \
  --trust-existing-admin-rights \
  --run-k6-smoke \
  --require-k6 \
  "$@"
