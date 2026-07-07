# PR87 Merge Readiness Report

## Status

`LOCAL REQUIRED CHECKS PASS; PREVIEW CAN BE TRIGGERED AFTER PUSH`

PR #87 was blocked by legacy pipeline selectors, controlled-launch/catalog regression expectations, Vercel preview skipping non-main branches, and a visual smoke script that could fail open. The local blocker fixes are source-only and do not alter Bengali production metadata, audio gates, or generated release artifacts.

## Validation

- `npm ci --prefix frontend`: PASS
- `npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false`: PASS, 4/4
- `REACT_APP_BACKEND_URL=/api npm --prefix frontend run build`: PASS
- `node frontend/scripts/audit-book-covers.mjs`: PASS, 0 typography-only customer-facing covers
- `node frontend/scripts/visual-luxury-smoke.mjs`: PASS as a fail-closed check, exited non-zero without a browser target
- `VISUAL_SMOKE_BASE_URL=http://127.0.0.1:4173 node frontend/scripts/visual-luxury-smoke.mjs`: PASS, Playwright browser executed, 24/24 checks completed
- `npx --yes lighthouse http://127.0.0.1:4173/ --chrome-flags="--headless=new --no-sandbox" --quiet`: PASS, performance 96, accessibility 100, SEO 100, LCP 2803ms
- Targeted regression modules: PASS, 4 suites, 72 tests
- Full local regression suite: PASS, backend 27 tests, frontend 10 tests, browser e2e Kshudhita pipeline cards 4
- Backend publication safety: PASS, 10 tests

Factory audiobook scripts are absent from this source-only PR branch, so factory py_compile/stop-guard tests were skipped as not applicable.

## Remaining Gate

Vercel preview still needs a committed/pushed branch rerun. The local ignoreCommand fix allows PR preview builds; actual same-origin preview validation cannot complete until the updated branch is pushed. If manual CLI inspection is needed, prefer `npx --yes vercel@latest` because the global Vercel CLI is outdated.

## Recommendation

Do not merge until the blocker rescue changes are committed, pushed, and the PR preview/checks rerun. If Vercel still cancels after this patch, treat that as an external Vercel project/check configuration blocker.
