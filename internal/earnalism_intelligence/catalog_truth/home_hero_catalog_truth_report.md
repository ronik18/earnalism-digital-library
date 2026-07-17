# Reference-Accurate Dynamic Sprint 1 Home Hero Catalog Truth Report

Generated: 2026-07-17
Decision: `AUTHORIZE_PREMIUM_HOMEPAGE_HERO_DYNAMIC_SPRINT1_CATALOG_IMPLEMENTATION`
Truth source: controlled-publication artifacts resolved per slug through `backend/catalog_truth.py`

## Result

- The supplied 1672 × 941 artwork is an optimized WebP desktop LCP layer with exact 16:9 geometry, semantic React content, real links, and keyboard focus retained above it.
- Every title-specific mockup cover/device region is permanently covered by canonical Sprint 1 catalog imagery. No fake title, fake author, or generated public book cover is exposed.
- The home page boots from a generated canonical snapshot and then refreshes from `GET /api/home/curated`; a temporarily unavailable backend no longer empties the hero.
- Sprint 1 readers remain **32 / 32** and approved public audiobooks remain **3 / 32**.
- No audiobook release gate changed. No TTS, ASR, audition, upload, provider call, or paid lock action ran.

## Selected hero books

| Rank | Slug | Exact title | Exact author | Canonical front cover | Reader | Public audio | Public CTA |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | `book-2b9853ec52` | দুই বিঘা জমি | রবীন্দ্রনাথ ঠাকুর | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1783267849/earnalism/covers/front/book-2b9853ec52_front_1600x2400.png` | enabled | approved | Start Listening |
| 2 | `bn-066` | আনন্দমঠ | বঙ্কিমচন্দ্র চট্টোপাধ্যায় | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1780682828/earnalism/covers/front/cover_e8c8daa1-3794-45eb-8e01-151456e9ead5.png` | enabled | hidden | Start Reading |
| 3 | `radharani` | রাধারাণী | বঙ্কিমচন্দ্র চট্টোপাধ্যায় | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1780482890/earnalism/covers/front/cover_2a2d7d9c-0f09-4e8a-a262-51c508dbebce.png` | enabled | hidden | Start Reading |
| 4 | `pride-and-prejudice` | Pride and Prejudice | Jane Austen | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1780293034/earnalism/covers/front/cover_e54439f8-2bfa-4d96-a4d1-bc7397e76f44.png` | enabled | hidden | Start Reading |
| 5 | `sredni-vashtar` | Sredni Vashtar | Saki | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1783275475/earnalism/covers/front/sredni-vashtar_front_1600x2400.png` | enabled | approved | Start Listening |
| 6 | `nishkriti` | নিষ্কৃতি | শরৎচন্দ্র চট্টোপাধ্যায় | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1780482837/earnalism/covers/front/cover_196983c8-bb26-4a88-8fed-e229543d04eb.png` | enabled | hidden | Start Reading |

The desktop art placements use দুই বিঘা জমি in the reading tablet, Sredni Vashtar in the listening phone, and আনন্দমঠ, রাধারাণী, and Pride and Prejudice on the desk. The rendered alt contract is exactly `{title} by {author}` and every source URL is retained as `data-canonical-cover-url`; Cloudinary width transforms are used only in `srcset` for faster delivery.

## Approved audiobook truth

Only these slugs remain in `shelves.approved_audiobooks` and only these receive an `audiobook_url`:

- `book-2b9853ec52` → `/api/reader/book/book-2b9853ec52/audiobook`
- `a-ghost-story` → `/api/reader/book/a-ghost-story/audiobook`
- `sredni-vashtar` → `/api/reader/book/sredni-vashtar/audiobook`

The phone visual uses the approved and featured `sredni-vashtar` record. No hidden-audio title receives a play control, `?listen=1`, an audiobook URL, or a Listen CTA. Great Expectations and Jane Eyre are not represented as Sprint 1 approved audiobooks.

## Omitted or excluded from visual placement

- `a-ghost-story` remains audio-approved, but its canonical cover object visibly says “BHARAT AT THE CROSSROADS — Ronik Basak.” It is therefore `do_not_feature: true` with a catalog evidence reason. This visual exclusion does not modify reader or audio truth.
- These reader-enabled records have no safe canonical front cover and remain omitted: `pather-panchali`, `devdas`, `book-edfcf810c5`, `frankenstein`, `jekyll-and-hyde`, `picture-of-dorian-gray`, `white-fang`, `the-tell-tale-heart`, `the-last-leaf`, `the-masque-of-the-red-death`, `the-yellow-wallpaper`, `the-monkeys-paw`, and `the-necklace`.

## Validation

- Backend home curation: **10 passed**.
- Current audiobook release-truth suite: **81 passed**; B2 routing: **5 passed in isolation**.
- Frontend focused hero/header/home-catalog tests: **18 passed**.
- Frontend full suite: **18 suites, 92 tests passed**.
- Cover audit: **71 audited, 0 broken sources, 0 typography-only customer covers**.
- Production frontend build: **compiled successfully** with `REACT_APP_BACKEND_URL=/api`.
- Browser validation: 1672 × 941, 1440 × 900, 1536 × 864, 390 × 844, 430 × 932, and 768 × 1024; no horizontal overflow, broken hero image, fake metadata, or hidden-audio control.
- Reference comparison outside the intentionally replaced catalog regions: **MAE 4.229**, **PSNR 29.76 dB**, **89.66%** of channels within 10 and **95.58%** within 20. Geometry is exact; WebP/browser color conversion accounts for the remaining pixel delta.
- PR #127 checks: backend/frontend/browser regression **passed**, GO LIVE regression gate **passed**, and Vercel preview **passed** after the regression fixtures were aligned to the canonical snapshot.

The legacy combined backend aggregate still contains ten obsolete Dracula-only assertions. Five B2 tests fail only after that legacy module closes the default event loop; B2 passes 5/5 in isolation. These known baseline tests were not rewritten for the hero.

## Release state

PR [#127](https://github.com/ronik18/earnalism-digital-library/pull/127) merged to `main` as `205a50f9511afc144291906755a1e3f6d59c42dc`. The merged-sha GO LIVE regression, Vercel production deployment, and production canary passed.

Production browser validation passed at 1440 × 900: the 1672 px reference image loaded, catalog state was ready, all five title-specific placements used canonical records, Sredni Vashtar was the only `?listen=1` link, zero hero images were broken, and document width equaled viewport width. Evidence: `/Users/ronikbasak/.codex/visualizations/2026/07/17/019f6ef7-752c-7d23-a0ef-49e3d86a68c5/premium-reference-dynamic-hero-production-1440x900.png`.

Backend production remains unchanged. The Railway job passed its secret check but skipped checkout and deployment because deploy secrets were unavailable; `/api/home/curated` remains HTTP 404. The canonical boot snapshot therefore supplies the production covers as designed. Approved audio routes for `book-2b9853ec52`, `a-ghost-story`, and `sredni-vashtar` return 206; sampled hidden routes `bn-066`, `pather-panchali`, and `the-open-window` return 404.

## Next exact command

`gh secret set RAILWAY_TOKEN --repo ronik18/earnalism-digital-library`
