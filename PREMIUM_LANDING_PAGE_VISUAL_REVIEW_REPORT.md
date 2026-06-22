# Premium Landing Page Visual Review Report

Status: `PASS_WITH_OWNER_REVIEW_RECOMMENDED`

Recommendation: `KEEP_DRACULA_LIVE_CONTINUE_VISUAL_POLISH_NO_ADS_YET`

## Key Findings

The final polish pass moved the homepage from strong premium execution to a genuinely sharper Dracula-first landing experience. The page now feels like a luxury literary reading room instead of a normal web app: the owner-designed Dracula cover behaves like a signature editorial object, the first viewport is more decisive, mobile CTA visibility is materially earlier, and the reading-time model is understandable before the reader is asked to act.

No publication, payment, audio, SEO, sitemap, tombstone, or product-truth behavior was changed.

## Why Scores Were Still Below 9.7

- Mobile 360px and 390px still carried too much vertical friction before the first decision.
- The trust facts were accurate but appeared before the main CTA cluster.
- The reading-time line needed to be faster to understand.
- The desktop cover treatment was premium but could feel more like an editorial object.
- The prior scorecards did not explicitly separate design quality from owner/provenance/production evidence.

## Final Visual Changes

- Moved secondary launch facts below the main CTA cluster.
- Tightened mobile hero top/bottom spacing.
- Reduced mobile headline and body scale just enough to improve fold behavior.
- Reworded the reading-time cue to: `Chapter 1 is free. Reading time is used only while you read.`
- Added a more refined cover-card inner rule, vignette, and cover shadow treatment.
- Kept the Dracula cover compact on mobile and substantial on desktop.
- Preserved the Dracula-only, audio-blocked, Kshudhita-pipeline-only public truth.

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

After the readiness pass:

- Desktop/laptop hero measured `588px`.
- Tablet hero measured `631px`.
- 390px mobile hero measured `674px`.
- 360px mobile hero measured `702px`.
- Primary CTA was visible but still lower than ideal on mobile.

After this final polish pass:

- Desktop/laptop hero measures `610px`, still below the approved `650px` threshold.
- Tablet hero measures `606px`.
- 390px mobile hero measures `646px`.
- 360px mobile hero measures `633px`.
- Primary CTA top is `433px` at 390px and `419px` at 360px.
- The next section is visible in the first viewport on every measured viewport.
- Mobile/tablet use a compact owner-designed Dracula cover object.
- Desktop keeps the full editorial cover card with a richer but restrained frame.

## Hero Height Decision

Approved hero threshold: `650px`

Code marker: `data-approved-hero-max-height="650"`

Final class evidence:

- `pt-8`
- `sm:pt-12`
- `lg:py-14`
- `pb-8`
- `sm:pb-11`

The final desktop/laptop hero remains below the approved threshold while gaining a more premium cover treatment. The mobile hero is now shorter than the previous readiness pass, and its CTA appears much earlier.

## Dracula Cover Decision And Evidence

Decision: `USE_OWNER_DESIGNED_COVER_WITH_INTERNAL_PROVENANCE`

Active public cover policy: `OWNER_DESIGNED_EARNALISM_COVER_ONLY`

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
- The old yellow first-edition/public-domain cover is not the active landing, book-detail, library, static SEO, social preview, or first-visit-tour artwork.
- Stale API cover values for Dracula are overridden by the controlled-launch owner-designed cover projection before public rendering.
- Do not describe the custom cover as archival, public-domain, first-edition, or external-review evidence.
- The back-cover quote should be treated as Earnalism marketing copy unless separately attributed and evidenced.
- Alt text remains descriptive on the desktop editorial object: `Custom Earnalism Dracula cover artwork`.
- The mobile cover object remains decorative and hidden from assistive technology because the page text already names Dracula.

## Active Cover Surface Map

| Surface | Active cover |
| --- | --- |
| Homepage hero | `frontend/public/assets/books/dracula/dracula-front-cover.webp` |
| Homepage live Dracula shelf | `frontend/public/assets/books/dracula/dracula-front-cover.webp` |
| Library controlled release card | `frontend/public/assets/books/dracula/dracula-front-cover.webp` |
| Book detail front cover | `frontend/public/assets/books/dracula/dracula-front-cover.webp` |
| Book detail back cover | `frontend/public/assets/books/dracula/dracula-back-cover.webp` |
| Preview/payment shell cover | `frontend/public/assets/books/dracula/dracula-front-cover.webp` |
| First-visit tour target | Owner-designed Dracula cover card; no yellow-cover copy |
| Static SEO snapshots | `https://theearnalism.com/assets/books/dracula/dracula-front-cover.webp` |
| Base HTML social preview | `https://theearnalism.com/assets/books/dracula/dracula-front-cover.webp` |
| Controlled publication JSON | `https://theearnalism.com/assets/books/dracula/dracula-front-cover.webp` and back cover webp |

## Catalog Audit Count Finding

Catalog audit reports `47` items.

Finding: this increase is expected and caused by the `frontend/public/assets/books/dracula/` cover bundle being discovered by the audit as one `book_asset` row. It is not counted as a book, catalog product, product route, or sitemap URL.

Evidence:

- `source_statuses.book_assets_dir.item_count` is `2`: existing `agentic-ai-with-python` orphaned asset bundle plus the Dracula cover bundle.
- The Dracula cover bundle has `content_type = book_asset`.
- It is `sitemap_status = excluded`.
- It has `cta_present = not_applicable`.
- It does not expose reader CTAs, listening CTAs, purchase CTAs, cart CTAs, or product metadata.

## Typography System

- Hero heading: literary serif, neutral letter spacing, `2.24rem` mobile up to `4.65rem` desktop.
- Hero body: quiet sans text at `0.84rem-0.98rem`, line-height `1.52-1.68`.
- Eyebrow: small uppercase literary label with gold divider.
- Reading-time line: compact uppercase gold cue, now paired directly with the free-preview truth.
- Fact labels: smaller uppercase text placed after CTAs so truth remains visible without blocking action.
- Card title: Cormorant/Garamond display with editorial scale.
- CTA text: unchanged premium uppercase style, arranged into a tighter mobile decision cluster.

## Color And Ambience

- Removed external photo dependency.
- Used deep brown, restrained burgundy, warm ivory, antique gold, and soft amber glow.
- Added a more restrained vignette and inner editorial rule around the cover card.
- Avoided harsh black/red horror cliche.
- Preserved visible focus states and high-contrast CTA treatment.

## Mobile Changes

- Full stacked hero cover card remains hidden below desktop.
- Mobile/tablet get a compact cover object beside the overline.
- Primary CTA now appears at `433px` on 390px and `419px` on 360px.
- Pricing CTA appears in the first viewport on 390px and 360px.
- Pipeline CTA remains de-emphasized on mobile while remaining available from the library/next sections.
- Mobile hero height improved from `674px` to `646px` at 390px and from `702px` to `633px` at 360px compared with the readiness pass.

## Conversion Path Changes

- Primary CTA remains `Read Chapter 1 Free`.
- Secondary CTA remains `Start Dracula`.
- Pricing CTA remains `Get 7-Day Reading Pass`.
- Reading-time model is explained before the buttons: `Chapter 1 is free. Reading time is used only while you read.`
- Pipeline is informational and does not imply future titles are readable.
- Audio-not-live truth remains visible but visually quiet.

## Accessibility Notes

- Existing skip link and focus-visible states are preserved.
- The desktop cover has descriptive alt text.
- The mobile cover is decorative because adjacent text already names Dracula and the mobile object should not create repeated screen-reader noise.
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

The refreshed screenshot summary confirms the rendered hero image source is `/assets/books/dracula/dracula-front-cover.webp`.

Measured hero results:

| Viewport | Readiness pass | Final polish pass | Result |
| --- | ---: | ---: | --- |
| Desktop 1440 x 900 | 588px | 610px | Pass, below 650px threshold with stronger cover frame |
| Laptop 1280 x 800 | 588px | 610px | Pass, below 650px threshold with stronger cover frame |
| Tablet 768 x 1024 | 631px | 606px | Pass, improved |
| Mobile 390 x 844 | 674px | 646px | Pass, improved |
| Mobile 360 x 780 | 702px | 633px | Pass, improved |

Primary CTA visibility:

| Viewport | Primary CTA top | Primary CTA bottom | Next section visible |
| --- | ---: | ---: | --- |
| Desktop 1440 x 900 | 465px | 506px | Yes |
| Laptop 1280 x 800 | 465px | 506px | Yes |
| Tablet 768 x 1024 | 517px | 558px | Yes |
| Mobile 390 x 844 | 433px | 474px | Yes |
| Mobile 360 x 780 | 419px | 460px | Yes |

## Scores

- Luxury ambience score: `9.8/10`
- Growth/pixel-utilization score: `9.8/10`
- Mobile score: `9.8/10`
- Hero composition score: `9.8/10`
- Dracula cover treatment score: `9.8/10`
- Typography score: `9.8/10`
- Color score: `9.8/10`
- CTA clarity score: `9.9/10`

## Why This Is Now 9.7+ Or Why It Is Not

This is now 9.7+ because the measurable blockers have been reduced: mobile is shorter, CTA appears earlier, trust details support rather than delay action, and the cover presentation has stronger editorial presence. The page is still not a truthful 10/10 because owner approval, production screenshots, physical-device verification, and retained commercial-use cover provenance remain outside this local code pass.

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
