#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash -n "$root/scripts/start_local_uat.sh" "$root/scripts/run_local_uat.sh"
node --check "$root/scripts/serve_frontend_build.js"
for port in 13000 13099 18000 18099 27018 27099; do [[ "$port" =~ ^[0-9]+$ ]] || exit 1; done
rg -q 'select_port.*backend 18000 18099' "$root/scripts/start_local_uat.sh"
rg -q 'select_port.*frontend 13000 13099' "$root/scripts/start_local_uat.sh"
rg -q 'pid_matches_file' "$root/scripts/start_local_uat.sh"
rg -q 'kill -0' "$root/scripts/start_local_uat.sh"
rg -q 'earnalism-uat-rs0' "$root/scripts/start_local_uat.sh"
rg -q 'scripts/init_uat_mongodb.py' "$root/scripts/start_local_uat.sh"
rg -q 'scripts/seed_uat_canonical_pages.py' "$root/scripts/start_local_uat.sh"
rg -q 'select_port.*mongodb 27018 27099' "$root/scripts/start_local_uat.sh"
echo "local-uAT-launcher-focused-tests: PASS"
