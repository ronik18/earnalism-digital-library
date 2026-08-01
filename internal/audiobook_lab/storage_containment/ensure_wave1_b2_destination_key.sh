#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   source internal/audiobook_lab/storage_containment/ensure_wave1_b2_destination_key.sh
#   internal/audiobook_lab/storage_containment/ensure_wave1_b2_destination_key.sh --check
#   eval "$(internal/audiobook_lab/storage_containment/ensure_wave1_b2_destination_key.sh --emit-fix)"

MODE="check"
EMIT_FIX=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)
      MODE="check"
      ;;
    --apply)
      MODE="apply"
      ;;
    --emit-fix)
      EMIT_FIX=1
      ;;
    -h|--help)
      cat <<'USAGE'
Usage:
  ensure_wave1_b2_destination_key.sh [--check|--apply]
  ensure_wave1_b2_destination_key.sh --emit-fix

Checks that destination B2 credentials are using the upload keyset and not overridden.

  --check      (default) validate only
  --apply      set exports in current shell (sourcing recommended)
  --emit-fix   emit shell commands to fix env in caller shell
USAGE
      exit 0
      ;;
    *)
      echo "error: unknown arg: $1" >&2
      exit 2
      ;;
  esac
  shift
done

require_var() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "error: required env var not set: $var_name" >&2
    exit 2
  fi
}

# Source of truth for destination credentials
require_var B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID
require_var B2_AUDIOBOOK_PROD_UPLOAD_SECRET_ACCESS_KEY
require_var B2_AUDIOBOOK_PROD_S3_ENDPOINT
require_var B2_AUDIOBOOK_PROD_REGION
require_var B2_AUDIOBOOK_PROD_BUCKET

mismatches=0
fix_cmds=()
fix_export_access_key=0
fix_export_secret_key=0
fix_export_s3_endpoint=0
fix_export_region=0
fix_export_bucket=0
fix_unset_private_qa_access=0
fix_unset_private_qa_secret=0
fix_unset_private_qa_s3=0
fix_unset_private_qa_region=0

check_and_set() {
  local current_name="$1"
  local expected_name="$2"
  local current_value="${!current_name:-}"
  local expected_value="${!expected_name}"

  if [[ "$current_value" == "$expected_value" ]]; then
    echo "$current_name=OK"
  else
    echo "$current_name=MISMATCH expected=$expected_value actual=${current_value:-<empty>}"
    mismatches=$((mismatches + 1))
    case "$current_name" in
      B2_ACCESS_KEY_ID) fix_export_access_key=1 ;;
      B2_SECRET_ACCESS_KEY) fix_export_secret_key=1 ;;
      B2_S3_ENDPOINT) fix_export_s3_endpoint=1 ;;
      B2_REGION) fix_export_region=1 ;;
      B2_PRIVATE_QA_BUCKET) fix_export_bucket=1 ;;
    esac
  fi
}

check_and_set B2_ACCESS_KEY_ID B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID
check_and_set B2_SECRET_ACCESS_KEY B2_AUDIOBOOK_PROD_UPLOAD_SECRET_ACCESS_KEY
check_and_set B2_S3_ENDPOINT B2_AUDIOBOOK_PROD_S3_ENDPOINT
check_and_set B2_REGION B2_AUDIOBOOK_PROD_REGION
check_and_set B2_PRIVATE_QA_BUCKET B2_AUDIOBOOK_PROD_BUCKET

# Remove legacy QA aliasing only when it is populated
for key in \
  B2_PRIVATE_QA_ACCESS_KEY_ID \
  B2_PRIVATE_QA_SECRET_ACCESS_KEY \
  B2_PRIVATE_QA_S3_ENDPOINT \
  B2_PRIVATE_QA_REGION
 do
  if [[ -n "${!key:-}" ]]; then
    echo "$key=CONFLICT set"
    mismatches=$((mismatches + 1))
    case "$key" in
      B2_PRIVATE_QA_ACCESS_KEY_ID) fix_unset_private_qa_access=1 ;;
      B2_PRIVATE_QA_SECRET_ACCESS_KEY) fix_unset_private_qa_secret=1 ;;
      B2_PRIVATE_QA_S3_ENDPOINT) fix_unset_private_qa_s3=1 ;;
      B2_PRIVATE_QA_REGION) fix_unset_private_qa_region=1 ;;
    esac
  else
    echo "$key=OK (empty)"
  fi
done

if (( EMIT_FIX == 1 )); then
  if (( \
    fix_export_access_key + fix_export_secret_key + fix_export_s3_endpoint + fix_export_region + fix_export_bucket + \
    fix_unset_private_qa_access + fix_unset_private_qa_secret + fix_unset_private_qa_s3 + fix_unset_private_qa_region \
    == 0 )); then
    echo "# emitted by ensure_wave1_b2_destination_key.sh"
    echo "# no changes needed"
  else
    echo "# emitted by ensure_wave1_b2_destination_key.sh"
    (( fix_export_access_key == 1 )) && echo "export B2_ACCESS_KEY_ID=$(printf '%q' \"$B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID\")"
    (( fix_export_secret_key == 1 )) && echo "export B2_SECRET_ACCESS_KEY=$(printf '%q' \"$B2_AUDIOBOOK_PROD_UPLOAD_SECRET_ACCESS_KEY\")"
    (( fix_export_s3_endpoint == 1 )) && echo "export B2_S3_ENDPOINT=$(printf '%q' \"$B2_AUDIOBOOK_PROD_S3_ENDPOINT\")"
    (( fix_export_region == 1 )) && echo "export B2_REGION=$(printf '%q' \"$B2_AUDIOBOOK_PROD_REGION\")"
    (( fix_export_bucket == 1 )) && echo "export B2_PRIVATE_QA_BUCKET=$(printf '%q' \"$B2_AUDIOBOOK_PROD_BUCKET\")"
    (( fix_unset_private_qa_access == 1 )) && echo "unset B2_PRIVATE_QA_ACCESS_KEY_ID"
    (( fix_unset_private_qa_secret == 1 )) && echo "unset B2_PRIVATE_QA_SECRET_ACCESS_KEY"
    (( fix_unset_private_qa_s3 == 1 )) && echo "unset B2_PRIVATE_QA_S3_ENDPOINT"
    (( fix_unset_private_qa_region == 1 )) && echo "unset B2_PRIVATE_QA_REGION"
  fi
  exit 0
fi

if [[ "$MODE" == "apply" ]]; then
  echo "# applying fixes in current shell"
  (( fix_export_access_key == 1 )) && export B2_ACCESS_KEY_ID="$B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID"
  (( fix_export_secret_key == 1 )) && export B2_SECRET_ACCESS_KEY="$B2_AUDIOBOOK_PROD_UPLOAD_SECRET_ACCESS_KEY"
  (( fix_export_s3_endpoint == 1 )) && export B2_S3_ENDPOINT="$B2_AUDIOBOOK_PROD_S3_ENDPOINT"
  (( fix_export_region == 1 )) && export B2_REGION="$B2_AUDIOBOOK_PROD_REGION"
  (( fix_export_bucket == 1 )) && export B2_PRIVATE_QA_BUCKET="$B2_AUDIOBOOK_PROD_BUCKET"
  (( fix_unset_private_qa_access == 1 )) && unset B2_PRIVATE_QA_ACCESS_KEY_ID
  (( fix_unset_private_qa_secret == 1 )) && unset B2_PRIVATE_QA_SECRET_ACCESS_KEY
  (( fix_unset_private_qa_s3 == 1 )) && unset B2_PRIVATE_QA_S3_ENDPOINT
  (( fix_unset_private_qa_region == 1 )) && unset B2_PRIVATE_QA_REGION
  echo "fixed: destination env mapped to B2_AUDIOBOOK_PROD_UPLOAD_*"
fi

if (( mismatches > 0 )); then
  if [[ "$MODE" == "check" ]]; then
    echo "error: destination creds not normalized (mismatches: $mismatches)" >&2
    exit 2
  fi
fi

exit 0
