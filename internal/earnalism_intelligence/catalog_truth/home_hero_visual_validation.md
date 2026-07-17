# Reference-Accurate Home Hero Visual Validation

Date: 2026-07-17
Browser: Codex in-app Chromium against the production frontend build served locally.
Reference: `/Users/ronikbasak/Documents/Personal/b9db4805-66cd-440c-a53c-9afc7780d239.png`

## Viewports

| Viewport | Result | Evidence |
| --- | --- | --- |
| 1672 × 941 | Exact reference geometry; 137 px header and 804 px hero; all fake book/device metadata masked by canonical covers | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-reference-dynamic-hero-1672x941.png` |
| 1440 × 900 | Pass; responsive 16:9 artwork, real header/CTA hotspots, no horizontal overflow | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-reference-dynamic-hero-1440x900.png` |
| 1536 × 864 | Pass; reference frame fills the desktop viewport with no clipping or distortion | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-reference-dynamic-hero-1536x864.png` |
| 390 × 844 | Pass; semantic mobile layout, two CTAs, four canonical covers, and no desktop-art download | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-reference-dynamic-hero-390x844.png` |
| 430 × 932 | Pass; headline and cover stage wrap cleanly without overflow | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-reference-dynamic-hero-430x932.png` |
| 768 × 1024 | Pass; responsive tablet layout retains semantic content and catalog imagery | `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-reference-dynamic-hero-768x1024.png` |

## Reference comparison

- The desktop background has the same 1672 × 941 aspect ratio and exact reference geometry.
- Transparent links align to the painted Start Reading and Explore Audiobooks buttons; all painted navigation items have real semantic link hotspots.
- Reference-only fake title regions are not allowed to leak through. Canonical reader, phone, and three desk-book overlays use opaque masks and exact catalog covers.
- Outside those deliberate dynamic replacement masks, the rendered WebP comparison measured MAE 4.229 and PSNR 29.76 dB; 89.66% of channels are within 10 and 95.58% are within 20.
- Literal whole-frame pixel equality would contradict the catalog-truth requirement because the reference contains invented or mismatched title art. The implementation instead matches its composition exactly while replacing those regions with real Sprint 1 records.

## Browser and accessibility evidence

- The canonical boot snapshot renders immediately; the live endpoint may replace it only after truth validation.
- Only `sredni-vashtar` appears in the phone/listening slot and receives `?listen=1`.
- Hidden-audio covers never render listening controls.
- Desktop artwork is synchronously gated by `matchMedia('(min-width: 1024px)')`, so mobile does not download the 227 KB WebP.
- Header and CTA hotspots are real focusable links with visible focus treatment; the semantic h1, subheadline, feature cards, rail, and alt text remain in the accessibility tree.
- The original deterministic BrandHeaderLogo and accessible mobile navigation remain active below 1024 px and on all non-home routes.
- No hero engineering/release-gate copy or console error was observed. The local static server produced only expected API 404 warnings outside the snapshot-backed hero.

Production validation is pending PR merge and deployment.
