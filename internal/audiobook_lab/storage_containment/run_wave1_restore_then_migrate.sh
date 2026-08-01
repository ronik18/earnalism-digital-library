#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/Users/ronikbasak/Documents/GitHub/earnalism-digital-library"
cd "$ROOT_DIR"

DEFAULT_TARGETS=(
  radharani
  muchiram-gurer-jibanchorit
  book-d19e96859f
  book-f5d593e1f4
  book-edfcf810c5
  the-tell-tale-heart
  the-yellow-wallpaper
  the-necklace
)

if [[ $# -gt 0 ]]; then
  TARGETS=("$@")
else
  TARGETS=("${DEFAULT_TARGETS[@]}")
fi

set -a
source secrets.env
source .secrets/earnalism-import.env
set +a

export OWNER_APPROVAL_TOKEN="AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS."
export REVIEWED_INVENTORY_SHA256="21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c"
export ALLOW_REMOTE_MUTATION=true
export B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE=true
export CLOUDINARY_URL="cloudinary://dummy:dummy@dummy"
export PATH=".venv-audio/bin:$PATH"

if [[ -n "${B2_WAVE1_FORCE_ACCESS_KEY_ID:-}" ]]; then
  export B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID="$B2_WAVE1_FORCE_ACCESS_KEY_ID"
  export B2_AUDIOBOOK_PROD_UPLOAD_SECRET_ACCESS_KEY="$B2_WAVE1_FORCE_SECRET_ACCESS_KEY"
fi

if [[ -n "${B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID:-}" ]]; then
  export B2_ACCESS_KEY_ID="$B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID"
  export B2_SECRET_ACCESS_KEY="$B2_AUDIOBOOK_PROD_UPLOAD_SECRET_ACCESS_KEY"
  export B2_S3_ENDPOINT="$B2_AUDIOBOOK_PROD_S3_ENDPOINT"
  export B2_REGION="$B2_AUDIOBOOK_PROD_REGION"
  export B2_PRIVATE_QA_BUCKET="$B2_AUDIOBOOK_PROD_BUCKET"
fi

unset B2_PRIVATE_QA_ACCESS_KEY_ID
unset B2_PRIVATE_QA_SECRET_ACCESS_KEY
unset B2_PRIVATE_QA_S3_ENDPOINT
unset B2_PRIVATE_QA_REGION

bash internal/audiobook_lab/storage_containment/ensure_wave1_b2_destination_key.sh --apply

python3 internal/audiobook_lab/storage_containment/check_b2_write_entitlement.py

bash internal/audiobook_lab/storage_containment/restore_wave1_targets_cloudinary.sh "${TARGETS[@]}"
bash internal/audiobook_lab/storage_containment/run_wave1_one_by_one_with_postcheck.sh --execute-reviewed "${TARGETS[@]}"
bash internal/audiobook_lab/storage_containment/validate_sprint1_wave1_private_b2_progress.sh

echo "done"
