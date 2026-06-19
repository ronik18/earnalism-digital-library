# Phase 13 Raw Verification

This report records line-normalization evidence for changed runtime, script, and test files. The raw GitHub download counts below were collected from branch `codex/phase13-launch-readiness` after commit `3b517dd2`.

## Local wc -l Evidence

| File | Line Count |
| --- | --- |
| scripts/launch_readiness_audit.py | 1888 |
| scripts/open_source_audiobook_onboarding.py | 1361 |
| backend/tests/test_launch_readiness_audit.py | 153 |
| frontend/src/pages/Pricing.jsx | 264 |
| package.json | 49 |

## Raw GitHub Download Command

```bash
branch=codex/phase13-launch-readiness
for file in scripts/launch_readiness_audit.py scripts/open_source_audiobook_onboarding.py backend/tests/test_launch_readiness_audit.py frontend/src/pages/Pricing.jsx package.json; do
  curl -fsSL "https://raw.githubusercontent.com/ronik18/earnalism-digital-library/${branch}/${file}" | wc -l | awk -v f="$file" '{print f": "$1" lines'}
done
```

## Raw GitHub Download Evidence

| File | Raw GitHub Line Count |
| --- | --- |
| scripts/launch_readiness_audit.py | 1888 |
| scripts/open_source_audiobook_onboarding.py | 1361 |
| backend/tests/test_launch_readiness_audit.py | 153 |
| frontend/src/pages/Pricing.jsx | 264 |
| package.json | 49 |
| PHASE13B_VALIDATION_REPORT.md | 42 |
| PHASE13_RAW_VERIFICATION.md | 22 |
| FINAL_GO_NO_GO_DECISION.md | 22 |
