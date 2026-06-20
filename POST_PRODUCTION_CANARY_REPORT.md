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
- Owner recommendation: `HOLD_FOR_FIXES`

PR #37 changed backend catalog-truth failure semantics so a missing Dracula API
record recommends `HOLD_FOR_FIXES`, not automatic rollback. Rollback remains
reserved for route canary, production parity, controlled-publication precheck,
focused regression, or frontend build failures that make production unsafe.

This follow-up PR adds the Dracula artifact fallback and the production diagnostic
needed to restore `/api/books/dracula` without broad catalog exposure.

The backend catalog truth failure is not masked by this PR. The new orchestrator correctly exits nonzero when a critical production canary fails.

## Backend Catalog Truth Fix Added

This branch now also hardens backend catalog truth after the reproduced production canary failure:

- `/api/books` fetches only controlled-launch candidate slugs.
- Public book lists no longer request raw audiobook fields.
- `public_book_projection(book)` remains the only public catalog projection.
- Dracula can pass via file-backed approval evidence when DB rights metadata lags.
- Reader/manifest/chapter/audio endpoints verify post-fetch truth gates.
- `data/controlled_launch.json` holds the controlled live/pipeline/audio slugs.
- Public cache version is bumped to `dracula-first-v2`.

Post-deploy, rerun:

```bash
npm run launch:backend-catalog-truth-canary
npm run release:post-production-canary
```

## Backend Truth Fix Validation

Additional validation after the backend truth fix:

- `python3 scripts/check-hidden-unicode.py ...`: PASS
- `python3 -m py_compile backend/catalog_truth.py backend/server.py backend/tests/test_backend_catalog_truth.py scripts/catalog_truth_audit.py scripts/launch_readiness_audit.py`: PASS
- `PYTHONPATH=. pytest backend/tests/test_backend_catalog_truth.py backend/tests/test_dracula_first_truth_gate.py backend/tests/test_launch_readiness_audit.py backend/tests/test_daily_growth_loop.py`: PASS, 69 tests
- `npm run owner:catalog-truth-audit`: PASS, local fixture summary has Dracula as the only live approved slug and zero unapproved audio/sitemap exposure
- `npm run owner:daily-growth-audit`: PASS
- `npm run launch:payment-smoke`: PASS_TEST_MODE
- `npm run controlled-publication:precheck`: PASS
- `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js`: PASS, 35 tests
- `npm run catalog:audit`: PASS, 251 items audited
- `npm run launch:post-deploy-route-canary`: PASS
- `npm run launch:production-parity`: PASS
- `npm run regression:ci`: PASS, 64 tests passed and 4 skipped
- `npm --prefix frontend run build`: PASS

`npm run launch:backend-catalog-truth-canary` was reproduced before this fix and failed against the currently deployed production backend. It must be rerun immediately after this branch is deployed; it is not required to pass before merge because it validates deployed API behavior.
