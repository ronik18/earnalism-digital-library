#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RUNNER="$ROOT_DIR/internal/audiobook_lab/storage_containment/run_wave1_with_validation.sh"

ACTION="${1:---dry-run}"
shift || true

case "$ACTION" in
  --dry-run|--execute-reviewed)
    ;;
  *)
    echo "Usage: $0 [--dry-run|--execute-reviewed] [slug ...]"
    exit 2
    ;;
esac

if [[ "$ACTION" == "--execute-reviewed" ]]; then
  # Backward-compatible credential aliases: allow either generic PRIVATE_QA creds
  # or explicit B2_* credentials to be populated.
  if [[ -n "${B2_PRIVATE_QA_ACCESS_KEY_ID:-}" && -z "${B2_ACCESS_KEY_ID:-}" ]]; then
    export B2_ACCESS_KEY_ID="$B2_PRIVATE_QA_ACCESS_KEY_ID"
    export B2_SECRET_ACCESS_KEY="${B2_PRIVATE_QA_SECRET_ACCESS_KEY:-}"
    export B2_S3_ENDPOINT="${B2_PRIVATE_QA_S3_ENDPOINT:-}"
    export B2_REGION="${B2_PRIVATE_QA_REGION:-}"
  fi
  if [[ -n "${B2_PRIVATE_QA_ACCESS_KEY_ID:-}" && -z "${B2_SOURCE_ACCESS_KEY_ID:-}" ]]; then
    export B2_SOURCE_ACCESS_KEY_ID="${B2_ACCESS_KEY_ID:-}"
    export B2_SOURCE_SECRET_ACCESS_KEY="${B2_SECRET_ACCESS_KEY:-}"
    export B2_SOURCE_S3_ENDPOINT="${B2_S3_ENDPOINT:-}"
    export B2_SOURCE_REGION="${B2_REGION:-}"
  fi

  echo "Validating owner+runtime approvals for execute-reviewed..."
  : "${ALLOW_REMOTE_MUTATION:?Set ALLOW_REMOTE_MUTATION=true before execute}"
  : "${OWNER_APPROVAL_TOKEN:?Set OWNER_APPROVAL_TOKEN before execute}"
  : "${REVIEWED_INVENTORY_SHA256:?Set REVIEWED_INVENTORY_SHA256 before execute}"
  : "${B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE:?Set B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE=true before execute}"
  : "${B2_ACCESS_KEY_ID:?Set B2_ACCESS_KEY_ID before execute}"
  : "${B2_SECRET_ACCESS_KEY:?Set B2_SECRET_ACCESS_KEY before execute}"
  : "${B2_S3_ENDPOINT:?Set B2_S3_ENDPOINT before execute}"
  : "${B2_REGION:?Set B2_REGION before execute}"
  : "${B2_PRIVATE_QA_BUCKET:?Set B2_PRIVATE_QA_BUCKET before execute}"
  : "${B2_SOURCE_ACCESS_KEY_ID:?Set B2_SOURCE_ACCESS_KEY_ID before execute}"
  : "${B2_SOURCE_SECRET_ACCESS_KEY:?Set B2_SOURCE_SECRET_ACCESS_KEY before execute}"
  : "${B2_SOURCE_S3_ENDPOINT:?Set B2_SOURCE_S3_ENDPOINT before execute}"
  : "${B2_SOURCE_REGION:?Set B2_SOURCE_REGION before execute}"

  if [[ "$ALLOW_REMOTE_MUTATION" != "true" ]]; then
    echo "ALLOW_REMOTE_MUTATION must be true for execution." >&2
    exit 2
  fi
  if [[ "${REVIEWED_INVENTORY_SHA256}" != "21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c" ]]; then
    echo "REVIEWED_INVENTORY_SHA256 mismatch. Expected 21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c" >&2
    exit 2
  fi
  OWNER_APPROVAL_TOKEN="${OWNER_APPROVAL_TOKEN//$'\r'/}"
  owner_token_scoped='AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT.'
  owner_token_p0='AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.'
  if [[ "${OWNER_APPROVAL_TOKEN}" != "$owner_token_scoped" && "${OWNER_APPROVAL_TOKEN}" != "$owner_token_p0" ]]; then
    echo "OWNER_APPROVAL_TOKEN mismatch." >&2
    echo "required_owner_tokens=$owner_token_scoped,$owner_token_p0" >&2
    echo "actual_owner_token=$OWNER_APPROVAL_TOKEN" >&2
    echo "actual_repr=$(printf '%q' "$OWNER_APPROVAL_TOKEN")" >&2
    exit 2
  fi
  if [[ "$B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE" != "true" ]]; then
    echo "B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE must be true." >&2
    exit 2
  fi
fi

echo "wave1_guarded_action=$ACTION"
if [[ "$#" -gt 0 ]]; then
  echo "wave1_targets=$*"
else
  echo "wave1_targets=radharani,muchiram-gurer-jibanchorit,book-d19e96859f,book-f5d593e1f4,book-edfcf810c5,the-tell-tale-heart,the-yellow-wallpaper,the-necklace"
fi

if [[ "$ACTION" == "--execute-reviewed" ]]; then
  bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check_wave1_endpoint_connectivity.sh"
fi

exec bash "$RUNNER" "$ACTION" "$@"
