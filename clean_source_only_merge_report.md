# Clean Source-Only Merge Report

Generated: 2026-07-06T19:16:37Z

## Branch

- Source sprint checkout: `/Users/ronikbasak/Documents/GitHub/earnalism-digital-library`
- Clean worktree: `/private/tmp/earnalism-clean-source-only-merge-20260706T191326Z`
- Clean branch: `codex/clean-source-only-merge-20260706T191326Z`
- Base: `origin/main`

## Scope Kept

- Luxury homepage/layout source and calm typography/performance rescue changes.
- Shared graphical cover resolver, cover image component, cover audit script, and visual smoke script.
- Audio release safety utility and unit test.
- Optimized Dracula hardcopy WebP derivatives and small brand logo WebP derivatives.
- Earnalism intelligence/policy docs and concise sprint reports.
- Package lock repair required for `npm ci`; `frontend/package.json` was not changed.
- Minimal header accessibility source fix after clean Lighthouse showed a label/name mismatch and invalid ARIA on the India badge.

## Excluded

- `frontend/build/`
- release_gate run outputs and dashboards
- screenshots, Lighthouse JSON, Playwright traces/videos
- root generated cover audit JSON/CSV
- generated `ux_visual_regression_report.json`
- audio files, sidecars, caches, logs, signed URLs, rollback payloads
- imported book/content noise

## Validation

- `npm ci --prefix frontend`: PASS after lock-only repair.
- `npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false`: PASS.
- `REACT_APP_BACKEND_URL=/api npm --prefix frontend run build`: PASS.
- `node frontend/scripts/audit-book-covers.mjs`: PASS.
- `VISUAL_SMOKE_BASE_URL=http://127.0.0.1:4173 node frontend/scripts/visual-luxury-smoke.mjs`: PASS.
- `npx --yes lighthouse http://127.0.0.1:4173/ --chrome-flags="--headless=new --no-sandbox" --quiet`: PASS.
- `git diff --check`: PASS.

## Lighthouse

- Performance: 96
- Accessibility: 100
- SEO: 100
- LCP: 2694.5 ms
- CLS: 0
- TBT: 10 ms

## Merge Readiness

Ready for PR after selective staging. No generated artifacts are intended for commit.

## Next Command

```bash
cd /private/tmp/earnalism-clean-source-only-merge-20260706T191326Z && git status --short && git diff --cached --stat
```
