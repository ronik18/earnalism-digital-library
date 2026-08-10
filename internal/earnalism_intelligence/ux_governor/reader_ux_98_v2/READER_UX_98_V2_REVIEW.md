# Reader UX 9.8 V2

Status: `SOURCE_VALIDATED_READY_FOR_OWNER_REVIEW_NOT_DEPLOYED`

Weighted local acceptance score: **9.86/10**

## Outcome

The reader now keeps every page inside the unobstructed viewport on mobile and desktop, preserves visible chapter/page orientation on mobile, and uses 44px minimum buttons throughout the primary reader, settings, and contents journeys.

Production HTML line fragments are conservatively reflowed into semantic prose without changing punctuation or word order. Drop caps appear only on the first content page when its first paragraph actually starts with a letter. Split-screen and embedded layouts no longer trigger the unreliable viewport-difference blur heuristic; visibility and explicit secure-reader protections remain intact.

TOC titles use the same normalized display labels as the reading header. Settings use the language-neutral “Font comfort” label while retaining saved themes, typography, focus, motion, and highlight controls.

## Evidence

- 390x844: 122px page-footer clearance above fixed controls; zero horizontal overflow; zero visible buttons below 44px.
- 320x568: 108px page-footer clearance; zero horizontal overflow; zero visible buttons below 44px.
- 1440x900: 65px page-footer clearance; zero horizontal overflow.
- Settings: all visible controls 44px or larger; scrollable 618px viewport over 1398px content.
- Contents: 336px drawer, zero overflow, no stale “continued” labels, all controls 44px or larger.
- Full frontend suite: 40 suites / 233 tests passed.
- UX static regression: 60 / 60 passed.
- Optimized production build: passed.

## Boundary

This score covers the local optimized build rendered with the current public Dracula manifest and chapter payload. No merge, deployment, publication, payment, catalog, rights, or audiobook exposure state changed. Production postchecks remain mandatory after explicit owner approval, merge, and deploy.
