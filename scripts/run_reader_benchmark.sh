#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

case "${UAT_API_BASE_URL:-}" in
  http://127.0.0.1:*/api) ;;
  *) echo "benchmark requires loopback UAT_API_BASE_URL" >&2; exit 64 ;;
esac
[[ "${ENVIRONMENT:-}" == "uat" ]] || { echo "benchmark requires ENVIRONMENT=uat" >&2; exit 64; }
[[ "${RAZORPAY_KEY_SECRET:-}" == "" && "${RAZORPAY_WEBHOOK_SECRET:-}" == "" ]] || { echo "live payment secrets are forbidden" >&2; exit 64; }

OUT="${UAT_RUNTIME_DIR:?UAT_RUNTIME_DIR is required}/reader-benchmark"
mkdir -p "$OUT"

# Existing validator: disposable synthetic accounts, local-only wallet setup,
# protected-page denial without a pass, entitled access, and session cleanup.
"$ROOT_DIR/.venv-uat/bin/python" scripts/verify_p1_all_title_isolated.py \
  --output "$OUT/admission.json"
export READER_BENCHMARK_SLUG="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["titles"][0]["slug"])' "$OUT/admission.json")"
node scripts/run_reader_browser_benchmark.mjs "$OUT/browser.json"
python3 - "$OUT/benchmark.json" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
admission = json.loads((out.parent / "admission.json").read_text())
browser = json.loads((out.parent / "browser.json").read_text())
required = {"uncached-next", "prefetched-next", "cached-previous", "rapid-navigation", "delayed-response-retains-current-page"}
if browser.get("result") != "PASS" or browser.get("mode") != "local-authenticated-reader-controls":
    raise SystemExit("browser evidence is not an authenticated control benchmark")
if set(browser.get("scenarios", [])) != required or len(browser.get("rows", [])) < len(required):
    raise SystemExit("required Reader benchmark scenarios are incomplete")
for row in browser["rows"]:
    if not row.get("canonical_content_nonempty") or not row.get("page_indicator_match"):
        raise SystemExit("sample lacks canonical content/page-indicator evidence")
    if row.get("scenario") == "delayed-response-retains-current-page" and not row.get("delay_intercepted"):
        raise SystemExit("delayed scenario did not intercept its intended request")
if admission.get("result") not in {"PASS", "pass"}:
    raise SystemExit("admission evidence did not pass")
report = {"schema_version":"earnalism.reader-benchmark.v3", "result":"PASS", "admission": admission, "browser": browser, "evidence_validated": True}
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"result":"PASS", "admission":"PASS", "browser_samples":browser.get("samples",0)}))
PY
