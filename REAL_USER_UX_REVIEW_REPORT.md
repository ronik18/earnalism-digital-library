# Real-User UX Review Report

Date: 2026-06-20

## Scope

This PR adds a Playwright real-user video audit for the live Earnalism website before broader branding and advertising work.

The audit verifies the current controlled-launch truth:

- Dracula is the only live approved Tier A core reading title.
- Dracula audio is disabled.
- Kshudhita Pashan remains pipeline-only.
- Unapproved titles must not show Start Reading, Read Preview, or Listen Now.
- Pricing uses Dracula-first reading-time packs.
- Removed demo/ecommerce routes must not serve a generic Earnalism shell.

## Evidence Capture

Command:

```bash
npx playwright test tests/e2e/earnalism-real-user-journey.spec.js --project=chromium
```

Artifacts are generated locally under:

- `output/real-user-ux/playwright-artifacts/`
- `output/real-user-ux/playwright-results.json`
- `output/real-user-ux/evidence/`

Video and trace artifacts are intentionally not committed because they are large runtime evidence files.

## Journey Coverage

- Homepage desktop
- Homepage mobile
- Carousel / featured Dracula section
- Library desktop
- Library mobile
- Dracula book page
- Dracula reader page
- Pricing page
- Journal page
- Contact page
- Removed demo route canary
- Backend catalog truth API check

## Current Owner Recommendation

`KEEP_DRACULA_LIVE_BUT_HOLD_ADS`

## Validation Summary

| Check | Result |
| --- | --- |
| Playwright real-user journey | PASS, 11/11 |
| Video artifacts | PASS, 10 browser videos |
| Trace artifacts | PASS, 11 traces |
| Screenshots | PASS, 11 screenshots |
| Backend catalog truth canary | PASS |
| Removed route canary | PASS |
| Production parity | PASS |
| Payment smoke | PASS_TEST_MODE |
| Controlled publication precheck | PASS |
| Governance and UX regression | PASS, 35/35 |
| Frontend build | PASS |
| SEO audit | BLOCKED_FOR_BOOK_SEO |
| Full launch readiness | HOLD_FOR_FIXES |

## Main Finding

The hydrated real-user UX is truthful and Dracula-first. The hold is not from the browser journey; it comes from the existing SEO audit finding that CRA book detail metadata is generated client-side after API load. The next smallest fix is prerender/SSR/static snapshot support for the priority book page, especially `/book/dracula`.

Expected decision rule:

- `GO_FOR_BRANDING_AND_ADVERTISEMENT` only if every journey passes and video evidence exists.
- `KEEP_DRACULA_LIVE_BUT_HOLD_ADS` if production is truthful but there are non-critical UX polish items.
- `HOLD_FOR_UX_FIXES` if any public truth, CTA, pricing, or reader issue appears.
- `ROLLBACK_DRACULA` only if the live Dracula reader or catalog truth gate fails.
