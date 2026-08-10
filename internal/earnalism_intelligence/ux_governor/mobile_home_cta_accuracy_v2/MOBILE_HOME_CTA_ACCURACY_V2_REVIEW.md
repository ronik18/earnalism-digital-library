# Mobile Home and CTA Accuracy V2

Status: `SOURCE_VALIDATED_READY_FOR_OWNER_REVIEW_NOT_DEPLOYED`

Weighted local acceptance score: **9.86/10**

## Outcome

The mobile home now fits its complete orientation experience into one viewport after the header: editorial promise, two accurate primary paths, featured-classic proof, and a 44px “Open classic” action. Bengali, English, and approved-audiobook paths follow immediately.

The wider journey now uses exact product language:

- `/library` is “Browse Library,” not “Start Reading.”
- `/pricing` is “Reading Passes,” not “Membership” or seven-day access.
- Dracula exposes one primary “Read Chapter 1 Free” action rather than two links to the same reader.
- The reader upsell describes the real ₹89 / 60-minute pass and makes no unsupported coupon, savings, or countdown claim.
- Account and pricing continuation actions open the reader directly.
- Footer account language reflects authentication state.
- Approved audiobook actions remain limited to release-gated destinations.

## Evidence

- 390x844 hero: 843px
- Horizontal overflow: 0px
- Visible public controls below 44px across eight audited routes: 0
- High-intent CTA destination checks: 7/7 passed
- Focused frontend tests: 29/29 passed
- Optimized production build: passed
- Repository E2E regression: passed
- Full journey smoke: 20 routes, 0 blockers

Review screenshot: `test-results/mobile-home-390-final.png`

Full journey evidence: `output/ux-journey-regression/2026-08-10T18-21-29-928Z`

## Boundary

This is a local production-build acceptance score. No deployment, payment, publication, catalog exposure, or audiobook release state changed. Production geometry, CTA destinations, API behavior, and field performance remain mandatory after an approved merge and deploy.
