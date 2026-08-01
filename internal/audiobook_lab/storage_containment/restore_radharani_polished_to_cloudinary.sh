#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

LOCAL_MP3="output/bengali_audiobook_polish/bengali-polish-queue-v1/bundles/ben/radharani/radharani.mp3"
CLOUDINARY_PUBLIC_ID="earnalism/audiobooks-polished/ben/radharani/radharani-bengali-polish-queue-v1.mp3"
EXPECTED_URL="https://res.cloudinary.com/dzlrhlfpu/video/upload/v1781264496/earnalism/audiobooks-polished/ben/radharani/radharani-bengali-polish-queue-v1.mp3.mp3"

if [[ ! -f "$LOCAL_MP3" ]]; then
  echo "Local source not found: $LOCAL_MP3" >&2
  echo "Run from the repo after restoring/recreating that output artifact." >&2
  exit 2
fi

if [[ ! -f ".secrets/earnalism-import.env" ]]; then
  echo "Missing .secrets/earnalism-import.env (Cloudinary creds)." >&2
  exit 2
fi

set -a
source .secrets/earnalism-import.env
set +a

if [[ -z "${CLOUDINARY_CLOUD_NAME:-}" || -z "${CLOUDINARY_API_KEY:-}" || -z "${CLOUDINARY_API_SECRET:-}" ]]; then
  echo "Cloudinary credentials not loaded." >&2
  exit 2
fi

export LOCAL_MP3 CLOUDINARY_PUBLIC_ID
python3 - <<'PY'
import os
from pathlib import Path
import cloudinary
import cloudinary.uploader

local_mp3 = os.environ["LOCAL_MP3"]

cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
    secure=True,
)

local_mp3 = Path(local_mp3)
result = cloudinary.uploader.upload(
    str(local_mp3),
    resource_type="video",
    public_id=os.environ["CLOUDINARY_PUBLIC_ID"],
    overwrite=True,
    use_filename=False,
    unique_filename=False,
    invalidate=True,
)

print("upload_result_secure_url=", result.get("secure_url"))
print("public_id=", result.get("public_id"))
print("bytes=", result.get("bytes"))
PY

echo "Expected reviewed locator URL:"
echo "  $EXPECTED_URL"
echo "Now run:"
echo "bash internal/audiobook_lab/storage_containment/run_wave1_one_by_one_with_postcheck.sh --execute-reviewed radharani"
echo "and if still inaccessible, verify with:"
echo "curl -I -H 'Range: bytes=0-0' \"$EXPECTED_URL\""
