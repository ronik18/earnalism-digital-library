#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
READINESS_FILE="$ROOT/internal/audiobook_lab/sprint1_publication/sprint1_package_v2_readiness.json"
GENERATOR="$ROOT/internal/audiobook_lab/sprint1_publication/generate_sprint1_package_v2_readiness.py"

python3 "$GENERATOR"

python3 - "$READINESS_FILE" <<'PY'
import json, sys
path=sys.argv[1]
d=json.loads(open(path,'r',encoding='utf-8').read())
live_target = 10
private_target = 10

live_count = d.get("live_count",0)
private_count = d.get("live_private_b2_count",0)
not_live_count = d.get("not_live_count",0)

nonprivate_exposed = [r["slug"] for r in d.get("rows",[]) if r.get("audio_enabled") and r.get("can_expose") and not r.get("private_b2")]
hidden_or_waiting = [r["slug"] for r in d.get("rows",[]) if r.get("audio_enabled") and not r.get("can_expose")]

print(f"live_count={live_count}")
print(f"live_private_b2_count={private_count}")
print(f"not_live_count={not_live_count}")
print(f"nonprivate_exposed_count={len(nonprivate_exposed)}")
print(f"hidden_or_waiting_count={len(hidden_or_waiting)}")
print("nonprivate_exposed=" + ", ".join(nonprivate_exposed) if nonprivate_exposed else "nonprivate_exposed=none")

if live_count < 9:
    raise SystemExit(f"FAIL: live_count {live_count} < 9")
if private_count < private_target:
    print(f"INFO: private_target not reached. Expected>= {private_target}, actual={private_count}")

if nonprivate_exposed:
    print("WARN: non-private exposed titles still present:", ",".join(nonprivate_exposed))
PY
