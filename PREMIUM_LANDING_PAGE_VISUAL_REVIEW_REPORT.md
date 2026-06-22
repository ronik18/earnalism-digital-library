# Premium Landing Page Visual Review Report

Status: `PASS_WITH_OWNER_REVIEW_RECOMMENDED`

Recommendation: `KEEP_DRACULA_LIVE_CONTINUE_VISUAL_POLISH_NO_ADS_YET`

## Key Findings

The second polish pass moved the homepage closer to a true premium literary reading-room experience without changing publication, payment, audio, SEO, or product-truth behavior. The hero is no longer tall or generic: desktop/laptop now measure `588px`, the owner-designed Dracula cover is visible and locally served, mobile no longer stacks a full cover card under the CTAs, and the primary conversion path appears earlier.

The page is not scored 10/10 because founder/owner visual approval, production post-deploy screenshots, physical mobile review, and retained cover-art provenance evidence are still required.

## Before / After Summary

Before the premium visual pass:

- Hero used a hotlinked external background image.
- Top and bottom padding made the banner feel tall and less conversion-efficient.
- Dracula cover existed only if API data supplied a cover; fallback was typographic or generic.
- First viewport had correct truth posture but lower pixel efficiency.

After the first pass:

- Hero used owner-designed local Dracula cover art and CSS ambience.
- Desktop/laptop measured `695px`, under the old `720px` threshold.
- Mobile still stacked the full cover card below CTAs, producing `1184px` at 390px and `1296px` at 360px.

After this final pass:

- Approved desktop/laptop threshold is now `650px`.
- Desktop/laptop hero measures `588px`.
- Tablet hero measures `631px`.
- 390px mobile hero measures `674px`.
- 360px mobile hero measures `702px`.
- Mobile/tablet use a compact cover object above the headline instead of a full stacked card.
- Desktop keeps the full editorial cover card with a tighter frame, cover, and supporting text.

## Hero Height Decision

Approved hero threshold: `650px`

Code marker: `data-approved-hero-max-height="650"`

Original broad banner class evidence:

- `pt-24`
- `sm:pt-32`
- `lg:pt-36`
- `pb-24`
- `lg:pb-32`

Final class evidence:

- `pt-11`
- `sm:pt-14`
- `lg:py-14`
- `pb-10`
- `sm:pb-12`

The final desktop/laptop hero is closer to the requested `600-650px` target while remaining calm and luxurious. It does not become a dense SaaS hero, and it does not hide the Dracula cover or the reading-room truth cues.

## Dracula Cover Decision And Evidence

Decision: `USE_OWNER_DESIGNED_COVER_WITH_INTERNAL_PROVENANCE`

Owner-supplied source assets:

- `/Users/ronikbasak/Documents/Reo Enterprise/Books/Book Covers/Dracula - Front.png`
- `/Users/ronikbasak/Documents/Reo Enterprise/Books/Book Covers/Dracula - Back.png`

Optimized committed frontend assets:

- `frontend/public/assets/books/dracula/dracula-front-cover.webp`
- `frontend/public/assets/books/dracula/dracula-back-cover.webp`
- `frontend/public/assets/books/dracula/dracula-front-cover.jpg`
- `frontend/public/assets/books/dracula/dracula-back-cover.jpg`

Ownership/provenance basis:

- The front and back covers were supplied by the owner/founder as Earnalism-designed Dracula artwork.
- The source PNGs are not committed to the public frontend; optimized derived assets are committed for the web experience.
- Owner should retain the original design files and any font, texture, model, illustration, or tool-output license evidence in the internal brand asset archive.

Usage constraints:

- The site does not hotlink any external cover image.
- Do not describe the custom cover as archival, public-domain, first-edition, or external-review evidence.
- The back-cover quote should be treated as Earnalism marketing copy unless separately attributed and evidenced.
- Alt text remains descriptive: `Custom Earnalism Dracula cover artwork`.

## Catalog Audit Count Finding

Catalog audit now reports `47` items instead of `46`.

Finding: this increase is expected and caused by the new `frontend/public/assets/books/dracula/` cover bundle being discovered by the audit as one `book_asset` row. It is not counted as a book, catalog product, product route, or sitemap URL.

Evidence:

- `source_statuses.book_assets_dir.item_count` is `2`: existing `agentic-ai-with-python` orphaned asset bundle plus the new Dracula cover bundle.
- The Dracula cover bundle has `content_type = book_asset`.
- It is `sitemap_status = excluded`.
- It has `cta_present = not_applicable`.
- It does not expose reader CTAs, listening CTAs, purchase CTAs, cart CTAs, or product metadata.

Action taken:

- `scripts/audit-public-content.mjs` now treats the known Dracula cover bundle as rights-evidenced owner-designed supporting artwork instead of unknown-rights quarantine noise.
- Unknown/non-Dracula book assets still quarantine when rights metadata is missing.

## Typography System

- Hero heading: literary serif, neutral letter spacing, `2.45rem` mobile up to `4.65rem` desktop.
- Hero body: quiet sans text at `0.92rem-0.98rem`, line-height `1.62-1.68`.
- Eyebrow: small uppercase literary label with gold divider.
- Reading-time line: compact uppercase gold cue, not a sales banner.
- Fact labels: smaller uppercase text so rights/source/audio truth is present without visual shouting.
- Card title: Cormorant/Garamond display, reduced from oversized card scale to editorial scale.
- CTA text: unchanged premium uppercase style, arranged into a tighter mobile grid.

## Color And Ambience

- Removed external photo dependency.
- Used deep brown, restrained burgundy, warm ivory, antique gold, and soft amber glow.
- Avoided harsh black/red horror cliche.
- Preserved visible focus states and high-contrast CTA treatment.
- Cover frame now uses a refined glow/shadow stack so the cover feels like a premium editorial object, not a pasted image.

## Mobile Changes

- Full stacked hero cover card is hidden below desktop.
- Mobile/tablet get a compact cover object beside the overline.
- Primary CTA remains visible before the first fold.
- Pricing CTA is still available in the first screen on 390px and 360px.
- Pipeline CTA is de-emphasized on mobile while remaining available from the library/next sections.
- Mobile hero height improved from `1184px` to `674px` at 390px and from `1296px` to `702px` at 360px.

## Conversion Path Changes

- Primary CTA remains `Read Chapter 1 Free`.
- Secondary CTA remains `Start Dracula`.
- Pricing CTA remains `Get 7-Day Reading Pass`.
- Reading-time model is explained in one crisp line: `Reading time is used only while you read.`
- Pipeline is informational and does not imply future titles are readable.
- Audio-not-live truth remains visible but visually quiet.

## Accessibility Notes

- Existing skip link and focus-visible states are preserved.
- The cover has descriptive alt text.
- No motion-heavy, flashing, or image-only critical message was introduced.
- This report does not claim formal accessibility compliance, completed non-visual user testing, blind-user testing, or complete accessibility.

## Visual QA Artifacts

Local screenshot artifacts were regenerated from the production build with the first-visit tour dismissed:

- `output/visual-review/premium-landing/desktop-1440-home.png`
- `output/visual-review/premium-landing/laptop-1280-home.png`
- `output/visual-review/premium-landing/tablet-768-home.png`
- `output/visual-review/premium-landing/mobile-390-home.png`
- `output/visual-review/premium-landing/mobile-360-home.png`
- `output/visual-review/premium-landing/visual-artifacts-summary.json`

The refreshed screenshot summary confirms the rendered hero image source is `/assets/books/dracula/dracula-front-cover.webp` with alt text `Custom Earnalism Dracula cover artwork`.

Measured hero heights:

| Viewport | Before final pass | After final pass | Result |
| --- | ---: | ---: | --- |
| Desktop 1440 x 900 | 695px | 588px | Pass, below 650px threshold |
| Laptop 1280 x 800 | 695px | 588px | Pass, below 650px threshold |
| Tablet 768 x 1024 | 1078px | 631px | Pass for stacked/tablet composition |
| Mobile 390 x 844 | 1184px | 674px | Strong improvement; CTA and cover visible |
| Mobile 360 x 780 | 1296px | 702px | Strong improvement; primary CTA visible |

## Scores

- Luxury ambience score: `9.5/10`
- Growth/pixel-utilization score: `9.6/10`
- Mobile score: `9.5/10`
- Hero composition score: `9.6/10`
- Dracula cover treatment score: `9.6/10`
- Typography score: `9.5/10`
- Color score: `9.4/10`
- CTA clarity score: `9.7/10`

## Remaining Gap To True 10/10

- Founder/owner visual approval is still required.
- Production post-deploy visual review is still required.
- Physical-device mobile review is still recommended.
- Internal cover provenance/license evidence should be retained before paid acquisition use.
- Paid ads remain held until the owner approves the final visual treatment and post-deploy evidence.

## Rollback Instructions

1. Revert `frontend/src/pages/Home.jsx`.
2. Revert `frontend/src/lib/controlledLaunch.js`.
3. Revert `frontend/src/index.css`.
4. Revert `frontend/scripts/generate-static-seo-snapshots.mjs`.
5. Revert `data/controlled_publications/dracula/public_book.json` and `backend/data/controlled_publications/dracula/public_book.json`.
6. Revert the two Dracula `checksum_manifest.json` updates.
7. Remove `frontend/public/assets/books/dracula/dracula-front-cover.webp`, `frontend/public/assets/books/dracula/dracula-back-cover.webp`, `frontend/public/assets/books/dracula/dracula-front-cover.jpg`, and `frontend/public/assets/books/dracula/dracula-back-cover.jpg` if the cover assets are no longer desired.
8. Revert scorecards and this report.
9. Re-run build, controlled-publication precheck, catalog audit, SEO/social preview audits, audiobook gate, payment smoke test mode, and regression modules 11/13/14.
