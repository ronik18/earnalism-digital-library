#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
INVENTORY="$ROOT/internal/audiobook_lab/storage_containment/unapproved_direct_audio_inventory.json"
EXECUTOR="$ROOT/internal/audiobook_lab/storage_containment/storage_containment_executor.py"
EXPECTED_INVENTORY_SHA256="21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c"
FULL_OWNER_TOKEN_REQUIRED='AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.'
SCOPED_OWNER_TOKEN_REQUIRED='AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT.'

target_list=""
if [[ -n "${SPRINT1_CONTAINMENT_TARGETS_JSON:-}" ]]; then
  if [[ "$SPRINT1_CONTAINMENT_TARGETS_JSON" = /* ]]; then
    target_list="$SPRINT1_CONTAINMENT_TARGETS_JSON"
  else
    target_list="$ROOT/$SPRINT1_CONTAINMENT_TARGETS_JSON"
  fi
  [[ -f "$target_list" ]] || {
    echo "Scoped containment target list not found: $target_list" >&2
    exit 2
  }
fi

actual_sha256="$(shasum -a 256 "$INVENTORY" | awk '{print $1}')"
[[ "$actual_sha256" == "$EXPECTED_INVENTORY_SHA256" ]] || {
  echo "INVENTORY_SHA_MISMATCH expected=$EXPECTED_INVENTORY_SHA256 actual=$actual_sha256" >&2
  exit 2
}

case "${1:-}" in
  --dry-run)
    args=(
      --dry-run
      --inventory "$INVENTORY"
    )
    if [[ -n "${TARGET_SLUG:-}" ]]; then
      args+=(--target-slug "$TARGET_SLUG")
    fi
    if [[ -n "$target_list" ]]; then
      args+=(--target-list "$target_list")
    fi
    args+=(--shard-count "${SHARD_COUNT:-1}" --shard-index "${SHARD_INDEX:-0}")
    exec python3 "$EXECUTOR" "${args[@]}"
    ;;
  --execute-reviewed)
    ;;
  *)
    printf '%s\n' "No action. Use --dry-run or --execute-reviewed."
    exit 0
    ;;
esac

: "${ALLOW_REMOTE_MUTATION:?Set ALLOW_REMOTE_MUTATION=true only after owner approval}"
: "${OWNER_APPROVAL_TOKEN:?Exact owner approval token required}"
: "${REVIEWED_INVENTORY_SHA256:?Reviewed inventory SHA-256 required}"

# Railway stores the private destination under explicit QA-prefixed names. Preserve
# any generic source credentials before mapping those private credentials.
if [[ -n "${B2_PRIVATE_QA_ACCESS_KEY_ID:-}" ]] &&
   [[ -n "${B2_PRIVATE_QA_SECRET_ACCESS_KEY:-}" ]] &&
   [[ -n "${B2_PRIVATE_QA_S3_ENDPOINT:-}" ]] &&
   [[ -n "${B2_PRIVATE_QA_REGION:-}" ]]; then
  if [[ -z "${B2_SOURCE_ACCESS_KEY_ID:-}" ]] && [[ -n "${B2_ACCESS_KEY_ID:-}" ]]; then
    export B2_SOURCE_ACCESS_KEY_ID="$B2_ACCESS_KEY_ID"
    export B2_SOURCE_SECRET_ACCESS_KEY="${B2_SECRET_ACCESS_KEY:-}"
    export B2_SOURCE_S3_ENDPOINT="${B2_S3_ENDPOINT:-}"
    export B2_SOURCE_REGION="${B2_REGION:-}"
  fi
  export B2_ACCESS_KEY_ID="$B2_PRIVATE_QA_ACCESS_KEY_ID"
  export B2_SECRET_ACCESS_KEY="$B2_PRIVATE_QA_SECRET_ACCESS_KEY"
  export B2_S3_ENDPOINT="$B2_PRIVATE_QA_S3_ENDPOINT"
  export B2_REGION="$B2_PRIVATE_QA_REGION"
fi

: "${B2_ACCESS_KEY_ID:?Private destination B2 access key required}"
: "${B2_SECRET_ACCESS_KEY:?Private destination B2 secret required}"
: "${B2_S3_ENDPOINT:?Private destination B2 S3 endpoint required}"
: "${B2_REGION:?Private destination B2 region required}"
: "${B2_PRIVATE_QA_BUCKET:?Private QA bucket required}"
: "${B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE:?Private bucket confirmation required}"

needs_b2_source=true
if [[ -n "$target_list" ]] &&
   ! python3 -c 'import json, sys; document = json.load(open(sys.argv[1])); raise SystemExit(0 if any(row.get("provider") == "B2" for row in document.get("targets", [])) else 1)' "$target_list"; then
  needs_b2_source=false
fi
if [[ "$needs_b2_source" == "true" ]]; then
  : "${B2_SOURCE_ACCESS_KEY_ID:?Public source B2 access key required}"
  : "${B2_SOURCE_SECRET_ACCESS_KEY:?Public source B2 secret required}"
  : "${B2_SOURCE_S3_ENDPOINT:?Public source B2 S3 endpoint required}"
  : "${B2_SOURCE_REGION:?Public source B2 region required}"
fi

[[ "$ALLOW_REMOTE_MUTATION" == "true" ]] || {
  echo "ALLOW_REMOTE_MUTATION must equal true" >&2
  exit 2
}
required_owner_token="$FULL_OWNER_TOKEN_REQUIRED"
if [[ -n "$target_list" ]]; then
  required_owner_token="$SCOPED_OWNER_TOKEN_REQUIRED"
fi

# Normalize accidental CRs that can be introduced by copy/paste or editor artifacts.
OWNER_APPROVAL_TOKEN="${OWNER_APPROVAL_TOKEN//$'\r'/}"

if [[ "$OWNER_APPROVAL_TOKEN" != "$required_owner_token" ]]; then
  echo "Owner approval token mismatch" >&2
  echo "required_owner_token=$required_owner_token" >&2
  echo "actual_owner_token=$OWNER_APPROVAL_TOKEN" >&2
  echo "actual_repr=$(printf '%q' "$OWNER_APPROVAL_TOKEN")" >&2
  echo "required_repr=$(printf '%q' "$required_owner_token")" >&2
  echo "actual_len=${#OWNER_APPROVAL_TOKEN} required_len=${#required_owner_token}" >&2
  echo "required_len_bytes=$(printf '%s' "$required_owner_token" | wc -c) actual_len_bytes=$(printf '%s' "$OWNER_APPROVAL_TOKEN" | wc -c)" >&2
  exit 2
fi
[[ "$OWNER_APPROVAL_TOKEN" == "$required_owner_token" ]] || {
  echo "Owner approval token mismatch" >&2
  exit 2
}
[[ "$REVIEWED_INVENTORY_SHA256" == "$EXPECTED_INVENTORY_SHA256" ]] || {
  echo "Reviewed inventory SHA-256 mismatch" >&2
  exit 2
}
[[ "$B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE" == "true" ]] || {
  echo "Private QA bucket is not explicitly confirmed private" >&2
  exit 2
}

if [[ -z "${CLOUDINARY_URL:-}" ]]; then
  : "${CLOUDINARY_CLOUD_NAME:?Cloudinary cloud name required}"
  : "${CLOUDINARY_API_KEY:?Cloudinary API key required}"
  : "${CLOUDINARY_API_SECRET:?Cloudinary API secret required}"
fi

python3 -c 'import boto3, cloudinary, requests' >/dev/null

args=(
  --execute-reviewed
  --inventory "$INVENTORY"
  --mutation-log "${MUTATION_LOG_PATH:-/tmp/earnalism-storage-containment.jsonl}"
)
if [[ -n "${TARGET_SLUG:-}" ]]; then
  args+=(--target-slug "$TARGET_SLUG")
fi
if [[ -n "$target_list" ]]; then
  args+=(--target-list "$target_list")
fi
args+=(--shard-count "${SHARD_COUNT:-1}" --shard-index "${SHARD_INDEX:-0}")

exec python3 "$EXECUTOR" "${args[@]}"
