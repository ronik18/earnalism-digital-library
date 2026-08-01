#!/usr/bin/env bash

# Deterministic, fail-closed runner for Sprint 1 package-v2 Wave 1 private-B2 migration.
# It intentionally only runs in explicit execute mode with approved owner controls.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT_PATH="$ROOT_DIR/internal/audiobook_lab/storage_containment/unapproved_direct_audio_remediation_commands.sh"
INVENTORY_SHA256="21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c"
OWNER_TOKEN_SCOPED='AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT.'
OWNER_TOKEN_P0='AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.'

USAGE_MSG="Usage: ALLOW_REMOTE_MUTATION=true OWNER_APPROVAL_TOKEN=<approved_owner_token> REVIEWED_INVENTORY_SHA256=$INVENTORY_SHA256 ... $0 [--dry-run|--execute-reviewed] [slug1 slug2 ...]"

ACTION="${1:-}"
shift || true

if [[ "$ACTION" != "--dry-run" && "$ACTION" != "--execute-reviewed" ]]; then
  echo "$USAGE_MSG" >&2
  exit 2
fi

if [[ "$ACTION" == "--execute-reviewed" ]]; then
  : "${ALLOW_REMOTE_MUTATION:?Set ALLOW_REMOTE_MUTATION=true before execute}"
  : "${OWNER_APPROVAL_TOKEN:?OWNER_APPROVAL_TOKEN required before execute}"
  : "${REVIEWED_INVENTORY_SHA256:?REVIEWED_INVENTORY_SHA256 required before execute}"
  : "${B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE:?B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE=true required before execute}"
  : "${B2_ACCESS_KEY_ID:?Private destination B2 access key required before execute}"
  : "${B2_SECRET_ACCESS_KEY:?Private destination B2 secret required before execute}"
  : "${B2_S3_ENDPOINT:?Private destination B2 endpoint required before execute}"
  : "${B2_REGION:?Private destination B2 region required before execute}"
  : "${B2_PRIVATE_QA_BUCKET:?Private destination QA bucket required before execute}"
  : "${B2_SOURCE_ACCESS_KEY_ID:?Public source B2 access key required before execute}"
  : "${B2_SOURCE_SECRET_ACCESS_KEY:?Public source B2 secret required before execute}"
  : "${B2_SOURCE_S3_ENDPOINT:?Public source B2 endpoint required before execute}"
  : "${B2_SOURCE_REGION:?Public source B2 region required before execute}"

  if [[ "$ALLOW_REMOTE_MUTATION" != "true" ]]; then
    echo "ALLOW_REMOTE_MUTATION must be true" >&2
    exit 2
  fi

  OWNER_APPROVAL_TOKEN="${OWNER_APPROVAL_TOKEN//$'\r'/}"
  if [[ "$OWNER_APPROVAL_TOKEN" != "$OWNER_TOKEN_SCOPED" && "$OWNER_APPROVAL_TOKEN" != "$OWNER_TOKEN_P0" ]]; then
    echo "OWNER_APPROVAL_TOKEN mismatch" >&2
    echo "required_owner_token_candidates=$OWNER_TOKEN_SCOPED,$OWNER_TOKEN_P0" >&2
    echo "actual_owner_token=$OWNER_APPROVAL_TOKEN" >&2
    echo "actual_repr=$(printf '%q' "$OWNER_APPROVAL_TOKEN")" >&2
    echo "actual_len=${#OWNER_APPROVAL_TOKEN}" >&2
    exit 2
  fi
  if [[ "$REVIEWED_INVENTORY_SHA256" != "$INVENTORY_SHA256" ]]; then
    echo "REVIEWED_INVENTORY_SHA256 mismatch" >&2
    exit 2
  fi
  if [[ "$B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE" != "true" ]]; then
    echo "B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE must be true" >&2
    exit 2
  fi

  bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check_wave1_endpoint_connectivity.sh"
fi

if [[ "$#" -gt 0 ]]; then
  TARGETS=("$@")
else
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

if [[ -n "${SPRINT1_CONTAINMENT_TARGETS_JSON:-}" && "$#" -eq 0 ]]; then
  # Optional scoped mode: explicitly drive from a prebuilt target list.
  echo "Wave 1 target count: from target list via SPRINT1_CONTAINMENT_TARGETS_JSON=$SPRINT1_CONTAINMENT_TARGETS_JSON"
  bash "$SCRIPT_PATH" "$ACTION"
else
  echo "Wave 1 target count: ${#TARGETS[@]}"
  for TARGET_SLUG in "${TARGETS[@]}"; do
    echo ">>> TARGET_SLUG=$TARGET_SLUG"
    env TARGET_SLUG="$TARGET_SLUG" \
      bash "$SCRIPT_PATH" "$ACTION"
  done
fi
