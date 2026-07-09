# Visual Regression Policy

Visual validation must catch both browser failures and source-level regressions.

## Required Checks

- Home, Library, Book Detail, Reader, and representative Bengali reader-only routes.
- Desktop, laptop, tablet, and mobile viewports.
- No horizontal overflow.
- No invisible text.
- No cover clipping.
- No console errors.
- No unapproved audio controls.
- No Vercel login shell treated as app content.

## Smoke Script Expectations

- `frontend/scripts/visual-luxury-smoke.mjs` must remain fail-closed for real UX blockers.
- Expected gated or unavailable states should be distinguished from JavaScript errors.
- Protected preview validation must use bypass secrets only through environment variables and must not log them.

## Claiming Green

Do not claim a surface is green if only source inspection passed. Browser smoke, cover audit, audio safety, build, and release-gate truth must pass.
