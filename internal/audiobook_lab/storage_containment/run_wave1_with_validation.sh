#!/usr/bin/env bash
set -euo pipefail

RUNNER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_sprint1_private_b2_wave1.sh"
VALIDATOR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/validate_sprint1_wave1_private_b2_progress.sh"
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

printf '>>> PRECHECK\n'
bash "$VALIDATOR"

if [[ "$ACTION" == "--execute-reviewed" ]]; then
  bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check_wave1_endpoint_connectivity.sh"
fi

echo "\n>>> EXECUTION ($ACTION)\n"
bash "$RUNNER" "$ACTION" "$@"

echo "\n>>> POSTCHECK\n"
bash "$VALIDATOR"
