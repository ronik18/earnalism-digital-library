# Premium Dynamic Sprint 1 Home Hero Catalog Truth Report

Generated: 2026-07-17
Decision: `AUTHORIZE_PREMIUM_HOMEPAGE_HERO_DYNAMIC_SPRINT1_CATALOG_IMPLEMENTATION`
Truth source: controlled publication artifacts resolved per slug through `backend/catalog_truth.py`

## Result

- Sprint 1 readers: **32 / 32**.
- Public audiobooks: **3 / 32**.
- Cover-eligible Sprint 1 titles: **19 / 32**.
- Hero visual titles: **6**, all copied exactly from canonical controlled-publication records.
- No title, author, or cover was synthesized.
- No audio release state was changed. No TTS, ASR, audition, upload, or paid-provider action ran.

## Selected hero books

| Rank | Slug | Exact title | Exact author | Canonical front cover | Reader | Public audio | Public CTA |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | `book-2b9853ec52` | দুই বিঘা জমি | রবীন্দ্রনাথ ঠাকুর | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1783267849/earnalism/covers/front/book-2b9853ec52_front_1600x2400.png` | enabled | approved | Start Listening |
| 2 | `bn-066` | আনন্দমঠ | বঙ্কিমচন্দ্র চট্টোপাধ্যায় | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1780682828/earnalism/covers/front/cover_e8c8daa1-3794-45eb-8e01-151456e9ead5.png` | enabled | hidden | Start Reading |
| 3 | `radharani` | রাধারাণী | বঙ্কিমচন্দ্র চট্টোপাধ্যায় | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1780482890/earnalism/covers/front/cover_2a2d7d9c-0f09-4e8a-a262-51c508dbebce.png` | enabled | hidden | Start Reading |
| 4 | `a-ghost-story` | A Ghost Story | Mark Twain | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1779436724/earnalism/covers/front/cover_446c5658-2bdd-4bd6-afbe-f5233f280508.png` | enabled | approved | Start Listening |
| 5 | `pride-and-prejudice` | Pride and Prejudice | Jane Austen | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1780293034/earnalism/covers/front/cover_e54439f8-2bfa-4d96-a4d1-bc7397e76f44.png` | enabled | hidden | Start Reading |
| 6 | `sredni-vashtar` | Sredni Vashtar | Saki | `https://res.cloudinary.com/dzlrhlfpu/image/upload/v1783275475/earnalism/covers/front/sredni-vashtar_front_1600x2400.png` | enabled | approved | Start Listening |

Every public image alt is exactly `{title} by {author}`. The six front-cover URLs are byte-for-byte values from canonical records; the cover audit reported zero broken sources.

## Approved audiobook truth

Only these slugs are returned in `shelves.approved_audiobooks` and only these receive an `audiobook_url`:

- `book-2b9853ec52` → `/api/reader/book/book-2b9853ec52/audiobook`
- `a-ghost-story` → `/api/reader/book/a-ghost-story/audiobook`
- `sredni-vashtar` → `/api/reader/book/sredni-vashtar/audiobook`

The phone visual uses `book-2b9853ec52`, the first approved audiobook in deterministic curation order. `bn-066`, `radharani`, and `pride-and-prejudice` remain reader-first with no Listen CTA or public audio URL. Great Expectations and Jane Eyre are absent from the 32-title Sprint 1 contract and cannot enter the approved audiobook shelf.

## Omitted from visual placement

These reader-enabled Sprint 1 records were omitted because the canonical artifact did not provide a safe front-cover URL: `pather-panchali`, `devdas`, `book-edfcf810c5`, `frankenstein`, `jekyll-and-hyde`, `picture-of-dorian-gray`, `white-fang`, `the-tell-tale-heart`, `the-last-leaf`, `the-masque-of-the-red-death`, `the-yellow-wallpaper`, `the-monkeys-paw`, and `the-necklace`.

## Validation

- Backend home curation: **8 passed**.
- Current audiobook truth suites: **36 passed**.
- B2 routing suite in isolation: **5 passed**.
- Frontend full suite: **18 suites, 90 tests passed**.
- Full repository regression: **27 backend tests, 90 frontend tests, production build, and browser e2e passed** after updating the retired headline assertion to the authorized dynamic-hero contract.
- Cover audit: **71 audited, 0 broken, 0 typography-only customer covers**.
- Production build: **compiled successfully** with `REACT_APP_BACKEND_URL=/api`.
- Browser: dynamic payload loaded six hero books; no broken hero images; no hero engineering copy; fresh-tab console errors: none.
- Route checks: `/`, `/library`, and requested `/book/*` routes resolve through the SPA server. Great Expectations renders unavailable and has no audio CTA; `book-2b9853ec52` renders Listen; Pather Panchali renders reader-only/audio-hidden.

The combined legacy backend aggregate still has ten pre-existing assertions that say Dracula is the only live title. Five B2 tests also fail only when run after that legacy module closes the default event loop; the same B2 file passes 5/5 in isolation. These baseline tests were not rewritten as part of the hero sprint.

## Release state

Source implementation and local validation are complete. Draft PR #125 is open; merge, deployment, and production validation remain gated on required checks. `paid_tts.lock` was not touched.

## Next exact command

`python3 -m json.tool internal/earnalism_intelligence/catalog_truth/home_hero_catalog_truth_report.json >/dev/null && git diff --check`
