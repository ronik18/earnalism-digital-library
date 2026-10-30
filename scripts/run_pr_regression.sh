#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export npm_config_cache="$ROOT/.npm-cache"
export PLAYWRIGHT_BROWSERS_PATH="$ROOT/.playwright-browsers"
export UAT_COMMAND_FILE="$ROOT/scripts/run_pr_regression_gates.sh"

# Isolated recovery qualification must launch its API with effective Redis OFF.
export REDIS_CACHE_ENABLED=false REDIS_PUBLIC_METADATA_ENABLED=false MULTI_REPLICA_ENABLED=false

bash scripts/start_local_uat.sh
