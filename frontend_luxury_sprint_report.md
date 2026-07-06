# Frontend Luxury Sprint Report

Generated: 2026-07-06

## Status

UX SPRINT YELLOW. The frontend/product UX has a strong second-pass luxury foundation, but the branch does not yet meet the 9.7 final claim threshold.

## Implemented

- Release-gate-safe audiobook visibility helper.
- Reader-manifest-aware approved audiobook spotlight for `a-ghost-story`.
- Premium coming-soon board and controlled shelf messaging.
- Book card audio-hidden/listen-approved badges.
- Book detail trust panel and premium loading/error states.
- Reader audio fallback suppression so browser/system TTS is not exposed as audiobook.
- Reader typography and theme polish.
- Accessibility contrast and ARIA fixes.
- Audiobook safety unit tests.

## Luxury UX Index

- Current measured score: 9.53 / 10.
- Target: 9.7 / 10.
- Lowest category: `no_regressions` at 8.7.

## Why It Is Not Green Yet

- Same-origin deployed preview validation is still required for API-backed reader/detail/audiobook pages.
- Lighthouse/Core Web Vitals evidence has not been collected on a deployed preview.
- The worktree contains unrelated generated/imported catalog files and is not PR-clean.
- Continue-reading/listening retention polish is still basic.
- Motion and microinteraction system is tasteful but not final.

## Release-Gate Truth

Changed UI hides unapproved audio. The approved audiobook spotlight renders only after reader-manifest evidence proves provider-backed, versioned, enabled audio with assets.

## Next Exact Command

```bash
npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false
npm --prefix frontend run build
```

After that, run same-origin preview browser/Lighthouse validation before claiming 9.7.

## Latest Validation

- `npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false` - PASS.
- `npm --prefix frontend run build` - PASS.
- Local static HTTP checks for `/`, `/library/`, `/book/dracula/`, and `/reader/dracula/` - PASS.

## Graphical Covers + Calm Typography Follow-Up

- Added shared graphical cover resolver and removed customer-facing typography-only cover fallback behavior.
- Added `frontend/scripts/audit-book-covers.mjs`: 164 controlled/visible cover records audited; 0 typography-only covers found; 105 missing cover sources now use graphical runtime fallback.
- Added `frontend/scripts/visual-luxury-smoke.mjs`: PASS in source mode and browser mode against `http://127.0.0.1:4173`.
- Calmed homepage/library hero and shelf typography.
- Replaced the 374KB Dracula hero image with the existing 65KB hardcopy asset and removed the photographic hero background layer.
- Removed blocking/duplicate Google Font imports and added a small home-route critical shell to reduce empty SPA first paint.

### Current Status

PARTIAL. Build, audio safety, visual smoke, accessibility, SEO, and release-gate truth pass. Lighthouse performance is 90 with LCP 3.6s, which remains below the requested >=94 guardrail, so no 9.7+ claim is justified from this pass.

## Remaining Exact Command

```bash
npx vercel@latest --prod=false
```

Then run same-origin browser, axe, and Lighthouse checks against the preview URL.

## Performance Rescue - 2026-07-07

- Activated achievement-aware cost governor and froze Bengali reader-only, Sarvam provider-limit, graphical cover, visual smoke, and audio-safety wins.
- Root cause: Lighthouse LCP was held by the mobile hero image, then by automatic first-visit tour text and early idle prefetch/settings work.
- Fix: responsive compressed Dracula hero variants, mobile procedural cover face, lazy/delayed first-visit tour, delayed route prefetch/settings fetch, optimized bundled brand mark.
- Lighthouse: performance `90` -> `96`, LCP `3.6 s` -> `2.7 s`, total byte weight `Total size was 417 KiB` -> `Total size was 239 KiB`.
- Cover audit remains PASS: 164 covers, 0 typography-only covers.
- Visual smoke remains PASS. Audio safety remains PASS. Accessibility and SEO remain 100.
- No paid operations, provider calls, Bengali mutations, deployments, or broad catalog waves were run.
