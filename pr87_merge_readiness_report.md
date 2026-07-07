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

## Preview Validation Update - Vercel Protection

The PR preview deployment is `Ready`, but browser validation is blocked by Vercel Deployment Protection. `curl -I` returns a `302` to `vercel.com/sso-api`, and the Playwright smoke now detects the Vercel login shell on 24/24 route/viewport checks.

This is not an Earnalism app visual regression: the browser is testing Vercel's login page, not the app. The visual smoke script now fails closed and reports `Vercel login shell` explicitly.

Next command after obtaining the Vercel automation bypass secret:

```bash
cd /private/tmp/earnalism-clean-source-only-merge-20260706T191326Z && \
VERCEL_AUTOMATION_BYPASS_SECRET=<redacted> \
VISUAL_SMOKE_BASE_URL=https://earnalism-git-codex-clean-source-on-6b7ae3-sales-8498s-projects.vercel.app \
VISUAL_SMOKE_SCREENSHOT_DIR=/tmp/pr87-preview-visual-smoke \
node frontend/scripts/visual-luxury-smoke.mjs
```

Do not mark PR87 preview-validated until that command passes against real Earnalism content, or the owner explicitly accepts local production-equivalent validation plus post-merge production verification.

## Preview Validation Blocker Rescue - 2026-07-07T05:01:21+00:00

### Root Cause

The protected preview bypass worked (`vercelLoginShellDetected=false`), but the deployed bundle called `https://api.theearnalism.com/api/...` directly from the Vercel preview origin. The production API rejected those browser calls by CORS, which caused visual smoke console blockers and prevented reader/detail app selectors from becoming visible.

### Fix

- `frontend/src/lib/api.js`: production default is same-origin `/api`; explicit backend URLs are still honored.
- `frontend/public/index.html`: PostHog only loads when `REACT_APP_ENABLE_POSTHOG=true`.
- `frontend/src/components/ApprovedAudiobookSpotlight.jsx`: no default `a-ghost-story` manifest probe unless an approved spotlight slug is configured.
- `frontend/scripts/visual-luxury-smoke.mjs`: remains fail-closed, waits for reader/unavailable states, and separates expected gated 404 resources from JS console failures.

### Local Validation After Fix

- Build: PASS.
- Audio safety: PASS, 4/4.
- Visual smoke: PASS, 24/24 routes completed, 0 blockers.
- Lighthouse: performance 96, LCP 2708.0ms, accessibility 100, SEO 100, CLS 0, TBT 0ms.
- `git diff --check`: PASS.

### Remaining Action

Push this patch and let Vercel rebuild the PR preview. The currently deployed URL will keep failing until the new commit is deployed.
