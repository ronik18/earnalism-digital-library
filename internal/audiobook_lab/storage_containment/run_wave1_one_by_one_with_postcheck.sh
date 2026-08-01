#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"
GENERATOR="$ROOT_DIR/internal/audiobook_lab/sprint1_publication/generate_sprint1_package_v2_readiness.py"

MODE="${1:---dry-run}"

if [[ "$MODE" != "--dry-run" && "$MODE" != "--execute-reviewed" ]]; then
  echo "Usage: $0 [--dry-run|--execute-reviewed] [slug ...]"
  exit 2
fi

TARGETS=("${@:2}")
if [[ ${#TARGETS[@]} -eq 0 ]]; then
  TARGETS=(
    radharani
    muchiram-gurer-jibanchorit
    book-d19e96859f
    book-f5d593e1f4
    book-edfcf810c5
    the-tell-tale-heart
    the-yellow-wallpaper
    the-necklace
  )
fi

REQUIRED=(
  "ALLOW_REMOTE_MUTATION"
  "OWNER_APPROVAL_TOKEN"
  "REVIEWED_INVENTORY_SHA256"
  "B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE"
  "B2_ACCESS_KEY_ID"
  "B2_SECRET_ACCESS_KEY"
  "B2_S3_ENDPOINT"
  "B2_REGION"
  "B2_PRIVATE_QA_BUCKET"
  "B2_SOURCE_ACCESS_KEY_ID"
  "B2_SOURCE_SECRET_ACCESS_KEY"
  "B2_SOURCE_S3_ENDPOINT"
  "B2_SOURCE_REGION"
)

if [[ "$MODE" == "--execute-reviewed" ]]; then
  for k in "${REQUIRED[@]}"; do
    if [[ -z "${!k:-}" ]]; then
      echo "Missing required env: $k" >&2
      exit 2
    fi
  done
fi

echo "[wave1] mode=$MODE targets=${#TARGETS[@]}"
for SLUG in "${TARGETS[@]}"; do
  echo -e "\n=== TARGET: $SLUG ==="
  if [[ "$MODE" == "--execute-reviewed" ]]; then
    TARGET_SLUG="$SLUG" bash internal/audiobook_lab/storage_containment/unapproved_direct_audio_remediation_commands.sh --execute-reviewed
  else
    TARGET_SLUG="$SLUG" bash internal/audiobook_lab/storage_containment/unapproved_direct_audio_remediation_commands.sh --dry-run
  fi

  python3 internal/audiobook_lab/storage_containment/reconcile_sprint1_private_b2_from_mutation_log.py \
    --mutation-log /tmp/earnalism-storage-containment.jsonl
  python3 "$GENERATOR"

  echo "[wave1] postcheck($SLUG)"
  python3 - "$SLUG" <<'PY'
import sys, json
slug = sys.argv[1]
path='internal/audiobook_lab/sprint1_publication/sprint1_package_v2_readiness.json'
with open(path) as f:
    d=json.load(f)
rows={r['slug']:r for r in d.get('rows',[])}
r=rows.get(slug)
if not r:
    print(f'missing_row:{slug}')
    raise SystemExit(1)
print(f"slug={slug} private_b2={r.get('private_b2')} can_expose={r.get('can_expose')} live_approved={r.get('live_approved')} release={r.get('release')} qa={r.get('qa')}")
PY
done

echo "[wave1] aggregate"
python3 "$GENERATOR"
bash internal/audiobook_lab/storage_containment/validate_sprint1_wave1_private_b2_progress.sh
python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_package_v2_readiness.json
