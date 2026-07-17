# Premium Home Hero Visual Validation

Date: 2026-07-17
Browser: Codex in-app Chromium against a production frontend build and the local `/api/home/curated` endpoint.

## Viewports

| Viewport | Result | Evidence |
| --- | --- | --- |
| 1440 × 900 | Pass; hero bottom at 884 px, no horizontal overflow, all desktop zones visible | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-home-1440x900.png` |
| 1536 × 864 | Pass; content bounds stay within viewport, rail begins above the fold and continues by 44 px | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-home-1536x864.png` |
| 390 × 844 | Pass; mobile menu, logo, medallion, headline, two CTAs, and feature chips visible without horizontal overflow | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-home-390x844.png` |
| 430 × 932 | Pass; headline wraps cleanly and the dynamic tablet/phone layer starts within the first viewport | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-home-430x932.png` |
| 768 × 1024 | Pass; tablet hero preserves both CTAs, all four chips, the reading tablet, approved listening phone, and cover stack | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-home-768x1024.png` |

## Browser evidence

- Hero catalog state: ready; six featured classics loaded.
- Images checked in the hero: eight rendered placements, zero broken.
- Exact cover alts were present for all six featured books plus the tablet and approved phone placement.
- Hero-specific scans found no release-gate, QA, approval, or engineering copy.
- Only the approved `/reader/book-2b9853ec52?listen=1` title appeared in the phone/listening slot.
- Fresh browser tab: zero console errors.
- Direct SPA routes returned successfully for `/`, `/library`, `/book/devdas`, `/book/pather-panchali`, `/book/great-expectations`, `/book/book-2b9853ec52`, `/book/a-ghost-story`, and `/book/sredni-vashtar`.
- Great Expectations was unavailable locally and therefore showed no reader or audio CTA. Pather Panchali showed Start Reading only. The approved `book-2b9853ec52` route showed Listen in Reader.

## Accessibility and performance observations

- Header brand is a single accessible image label: “Earnalism — Where Learning Becomes Earning, a Reo Enterprise venture”. Decorative correction marks are hidden from screen readers.
- The tricolor literary medallion is visible at desktop, tablet, and mobile sizes.
- Hero landmarks, headings, links, image alts, focus-visible outlines, reduced-motion behavior, intrinsic image dimensions, eager loading for the first two covers, and lazy loading for the remaining stack are present.
- No horizontal overflow was observed at any requested viewport.

Production validation remains pending deployment.
