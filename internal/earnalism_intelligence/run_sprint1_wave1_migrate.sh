#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_sprint1_wave1_migrate.sh [guard|postcheck] [slug1 slug2 ...]

Modes:
  guard     - use run_wave1_with_guard.sh + scoped ownership token
             (default scope targets if slugs omitted)
  postcheck - use run_wave1_one_by_one_with_postcheck.sh + per-title token
             (defaults to 8 remaining slugs when none provided)
EOF
}

MODE=${1:-guard}
shift || true

case "$MODE" in
  guard)
    export OWNER_APPROVAL_TOKEN='AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT.'
    RUNNER='internal/audiobook_lab/storage_containment/run_wave1_with_guard.sh'
    RUNNER_ARGS=(--execute-reviewed "$@")
    ;;
  postcheck)
    export OWNER_APPROVAL_TOKEN='AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS.'
    RUNNER='internal/audiobook_lab/storage_containment/run_wave1_one_by_one_with_postcheck.sh'
    if [[ $# -eq 0 ]]; then
      RUNNER_ARGS=(--execute-reviewed \
        radharani \
        muchiram-gurer-jibanchorit \
        book-d19e96859f \
        book-f5d593e1f4 \
        book-edfcf810c5 \
        the-tell-tale-heart \
        the-yellow-wallpaper \
        the-necklace
      )
    else
      RUNNER_ARGS=(--execute-reviewed "$@")
    fi
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    usage
    exit 2
    ;;
esac

set -a
source secrets.env
source .secrets/earnalism-import.env
set +a

export ALLOW_REMOTE_MUTATION=true
export REVIEWED_INVENTORY_SHA256='21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c'
export B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE=true
export OWNER_TOKEN_SOURCE='Wave-1 migration script'

bash internal/audiobook_lab/storage_containment/check_wave1_endpoint_connectivity.sh

bash "$RUNNER" "${RUNNER_ARGS[@]}"

bash internal/audiobook_lab/storage_containment/validate_sprint1_wave1_private_b2_progress.sh
python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_package_v2_readiness.json
