#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

echo "Wave-1 connectivity preflight"
echo "================================="

check_host() {
  local label="$1"
  local url="$2"
  local host
  host="$(python3 - <<'PY' "$url"
import sys
from urllib.parse import urlparse
url = sys.argv[1]
u = urlparse(url)
print(u.hostname or "")
PY
)"
  if [[ -z "${host}" ]]; then
    echo "[WARN] ${label}: could not parse host from ${url}"
    return 0
  fi

  if python3 - <<'PY' "$host"
import socket, sys
host = sys.argv[1]
try:
    ip = socket.gethostbyname(host)
    print(ip)
    sys.exit(0)
except Exception as e:
    print(f"{type(e).__name__}: {e}")
    sys.exit(1)
PY
  then
    echo "[OK] ${label}: ${host} resolves"
  else
    echo "[FAIL] ${label}: ${host} cannot resolve"
    return 1
  fi
}

ENDPOINTS=()
ENDPOINTS+=("api.theearnalism.com::https://api.theearnalism.com")
ENDPOINTS+=("B2_PROD::${B2_S3_ENDPOINT:-https://s3.us-west-004.backblazeb2.com}")
ENDPOINTS+=("B2_SOURCE::${B2_SOURCE_S3_ENDPOINT:-https://s3.us-west-004.backblazeb2.com}")
ENDPOINTS+=("B2_DR::${B2_AUDIOBOOK_DR_S3_ENDPOINT:-https://s3.us-east-005.backblazeb2.com}")
ENDPOINTS+=("B2_PUBLIC::https://backblaze.com")
ENDPOINTS+=("github::https://api.github.com")

STATUS=0
for pair in "${ENDPOINTS[@]}"; do
  label="${pair%%::*}"
  url="${pair##*::}"
  if ! check_host "$label" "$url"; then
    STATUS=1
  fi
done

if [[ "$STATUS" -ne 0 ]]; then
  echo "Connectivity gate: FAIL"
  echo "Use this when EndpointConnectionError is observed from B2 migration scripts."
  exit 1
fi

echo "Connectivity gate: PASS"
exit 0
