# Post-Production Canary Automation Report

## Summary

This PR adds `npm run release:post-production-canary`, a safe local orchestrator for running every post-production release canary in the required order and writing a single owner-readable report.

## What Changed

- Added `scripts/post_production_canary.py`.
- Added `release:post-production-canary` to `package.json`.
- Added unit tests for pass, critical failure, non-critical warning, and report writing behavior.
- Added `POST_PRODUCTION_CANARY_RUNBOOK.md`.
- Added committed latest summary placeholders under `output/release-canary/latest/`.

## Safety Confirmation

- Public publishing is not performed.
- Audiobook is not enabled.
- Emails and social posts are not sent.
- Paid provider APIs are not called by the orchestrator.
- Production data is not mutated.
- Critical canary failures make the command exit nonzero.
- Non-critical warning-tolerant checks continue and mark the summary `WARN`.

## Owner Report Fields

The latest summary includes:

- overall status: `PASS`, `WARN`, or `FAIL`
- failed command
- route canary status
- backend catalog truth status
- Dracula live status
- payment smoke status
- SEO status
- audio status
- catalog truth status
- daily growth audit status
- observability status
- regression status
- frontend build status
- owner recommendation: `KEEP_DRACULA_LIVE`, `HOLD_FOR_FIXES`, or `ROLLBACK`

## Validation

Validation commands run:

```bash
python3 -m py_compile scripts/post_production_canary.py
PYTHONPATH=. pytest backend/tests/test_post_production_canary.py
npm run release:post-production-canary
npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js
npm --prefix frontend run build
```

Results:

- `python3 -m py_compile scripts/post_production_canary.py`: PASS
- `PYTHONPATH=. pytest backend/tests/test_post_production_canary.py`: PASS, 6 tests
- `npm run release:post-production-canary`: FAIL as designed because `npm run launch:backend-catalog-truth-canary` found a live production catalog truth blocker
- `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js`: PASS, 35 tests
- `npm --prefix frontend run build`: PASS

Latest canary summary:

- Overall status: `FAIL`
- Failed command: `npm run launch:backend-catalog-truth-canary`
- Route canary: `PASS`
- Backend catalog truth: `FAIL`
- Dracula live: `FAIL`
- Payment smoke: `PASS`
- SEO: `PASS`
- Audio: `PASS`
- Catalog truth: `PASS`
- Daily growth audit: `PASS`
- Observability: `PASS`
- Regression: `PASS`
- Frontend build: `PASS`
- Owner recommendation: `ROLLBACK`

The backend catalog truth failure is not masked by this PR. The new orchestrator correctly exits nonzero when a critical production canary fails.
