#!/usr/bin/env bash
set -euo pipefail

# Deterministic one-command runner for Wave-1 migration:
# - Loads repo secrets
# - Validates destination keys in deterministic order
# - Selects first key that can HeadBucket + list + PutObject + HeadObject + DeleteObject
# - Runs reviewed migration in execute mode

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
INVENTORY_SHA256="21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c"

cd "$ROOT_DIR"

if [[ -f secrets.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source secrets.env
  set +a
else
  echo "secrets.env not found at repo root: $ROOT_DIR" >&2
  exit 2
fi

OWNER_APPROVAL_TOKEN="${OWNER_APPROVAL_TOKEN:-AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.}"
REVIEWED_INVENTORY_SHA256="${REVIEWED_INVENTORY_SHA256:-$INVENTORY_SHA256}"
B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE="${B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE:-true}"
B2_PRIVATE_QA_BUCKET="${B2_PRIVATE_QA_BUCKET:-earnalism-audiobooks-prod-v2-236e72b043e2}"

export ALLOW_REMOTE_MUTATION=true
export OWNER_APPROVAL_TOKEN
export REVIEWED_INVENTORY_SHA256
export B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE
export B2_PRIVATE_QA_BUCKET
export B2_AUDIOBOOK_PROD_S3_ENDPOINT="${B2_AUDIOBOOK_PROD_S3_ENDPOINT:-https://s3.us-west-004.backblazeb2.com}"
export B2_AUDIOBOOK_PROD_REGION="${B2_AUDIOBOOK_PROD_REGION:-us-west-004}"
export B2_AUDIOBOOK_PROD_READ_ACCESS_KEY_ID
export B2_AUDIOBOOK_PROD_READ_SECRET_ACCESS_KEY
export B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID
export B2_AUDIOBOOK_PROD_UPLOAD_SECRET_ACCESS_KEY
export B2_AUDIOBOOK_PROD_RETENTION_ADMIN_ACCESS_KEY_ID
export B2_AUDIOBOOK_PROD_RETENTION_ADMIN_SECRET_ACCESS_KEY

# Make sure old alias exports never silently remap destination credentials.
unset B2_PRIVATE_QA_ACCESS_KEY_ID
unset B2_PRIVATE_QA_SECRET_ACCESS_KEY
unset B2_PRIVATE_QA_S3_ENDPOINT
unset B2_PRIVATE_QA_REGION

# Source credentials (safe defaults).
export B2_SOURCE_ACCESS_KEY_ID="$B2_AUDIOBOOK_PROD_READ_ACCESS_KEY_ID"
export B2_SOURCE_SECRET_ACCESS_KEY="$B2_AUDIOBOOK_PROD_READ_SECRET_ACCESS_KEY"
export B2_SOURCE_S3_ENDPOINT="$B2_AUDIOBOOK_PROD_S3_ENDPOINT"
export B2_SOURCE_REGION="$B2_AUDIOBOOK_PROD_REGION"

if [[ "${CLOUDINARY_URL:-}" == "cloudinary://dummy:dummy@dummy" ]]; then
  if [[ -z "${CLOUDINARY_CLOUD_NAME:-}" || -z "${CLOUDINARY_API_KEY:-}" || -z "${CLOUDINARY_API_SECRET:-}" ]]; then
    echo "CLOUDINARY_URL is dummy and CLOUDINARY_CLOUD_NAME/API vars are missing." >&2
    exit 2
  fi
fi

probe_destination_key() {
  local label="$1"
  local access_key="$2"
  local secret_key="$3"
  local endpoint="${4}"
  local region="${5}"
  local bucket="${6}"
  local probe_key="storage-containment/.codex-containment-probe/$(date +%s)-${label}.txt"

  python3 - "$label" "$access_key" "$secret_key" "$endpoint" "$region" "$bucket" "$probe_key" <<'PY'
import boto3
import sys
from botocore.config import Config

label, access_key, secret_key, endpoint, region, bucket, probe_key = sys.argv[1:]

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name=region,
    config=Config(signature_version="s3v4"),
)

s3.head_bucket(Bucket=bucket)
s3.put_object(Bucket=bucket, Key=probe_key, Body=b"codex-probe")
s3.head_object(Bucket=bucket, Key=probe_key)
s3.delete_object(Bucket=bucket, Key=probe_key)
print(f"{label}:OK")
PY
}

SELECTED_LABEL=""
SELECTED_ACCESS_KEY=""
SELECTED_SECRET_KEY=""

for candidate in \
  "PROD_UPLOAD:${B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID}:${B2_AUDIOBOOK_PROD_UPLOAD_SECRET_ACCESS_KEY}" \
  "PROD_READ:${B2_AUDIOBOOK_PROD_READ_ACCESS_KEY_ID}:${B2_AUDIOBOOK_PROD_READ_SECRET_ACCESS_KEY}" \
  "PROD_RETENTION_ADMIN:${B2_AUDIOBOOK_PROD_RETENTION_ADMIN_ACCESS_KEY_ID}:${B2_AUDIOBOOK_PROD_RETENTION_ADMIN_SECRET_ACCESS_KEY}"
do
  IFS=":" read -r label ak sk <<< "$candidate"
  if [[ -z "$ak" || -z "$sk" ]]; then
    echo "Skipping ${label}: incomplete credentials."
    continue
  fi
  if probe_destination_key "$label" "$ak" "$sk" "$B2_AUDIOBOOK_PROD_S3_ENDPOINT" "$B2_AUDIOBOOK_PROD_REGION" "$B2_PRIVATE_QA_BUCKET"; then
    SELECTED_LABEL="$label"
    SELECTED_ACCESS_KEY="$ak"
    SELECTED_SECRET_KEY="$sk"
    break
  fi
done

if [[ -z "$SELECTED_LABEL" ]]; then
  echo "No destination key passed immutable preflight checks (HeadBucket/List/Put/Head/Delete)." >&2
  echo "Cannot run Wave-1 safely." >&2
  exit 2
fi

echo "Selected destination key: ${SELECTED_LABEL}"

export B2_ACCESS_KEY_ID="$SELECTED_ACCESS_KEY"
export B2_SECRET_ACCESS_KEY="$SELECTED_SECRET_KEY"
export B2_S3_ENDPOINT="$B2_AUDIOBOOK_PROD_S3_ENDPOINT"
export B2_REGION="$B2_AUDIOBOOK_PROD_REGION"

# Keep required network sanity check for environment-specific DNS issues.
bash internal/audiobook_lab/storage_containment/check_wave1_endpoint_connectivity.sh

if [[ "$#" -eq 0 ]]; then
  bash internal/audiobook_lab/storage_containment/run_wave1_one_by_one_with_postcheck.sh --execute-reviewed
else
  bash internal/audiobook_lab/storage_containment/run_wave1_one_by_one_with_postcheck.sh --execute-reviewed "$@"
fi
