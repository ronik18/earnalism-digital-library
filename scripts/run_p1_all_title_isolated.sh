#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/.venv-uat/bin/python" "$ROOT/scripts/verify_p1_all_title_isolated.py" --output "$UAT_RUNTIME_DIR/p1-all-title-isolated.json"
