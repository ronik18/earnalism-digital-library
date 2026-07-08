# BOOK_DETAIL Discovery Packet

Generated: 2026-07-08T03:50:54Z

## Phase Status

BOOK_DETAIL is the next active UX phase after owner approval of LIBRARY. This packet is discovery only; no Book Detail redesign has been started.

## Source Files Inspected

- `frontend/src/App.js`
- `frontend/src/pages/BookDetail.jsx`
- `frontend/src/components/BookCoverImage.jsx`
- `frontend/src/components/JsonLd.jsx`
- `frontend/src/hooks/useSEO.js`
- `frontend/src/lib/audioReleaseSafety.js`
- `frontend/src/lib/bookCoverResolver.js`
- `frontend/src/lib/controlledLaunch.js`
- `frontend/src/index.css`
- `frontend/scripts/generate-static-seo-snapshots.mjs`
- `frontend/scripts/generate-seo-assets.mjs`
- `data/controlled_publications/*/public_book.json`
- `data/controlled_publications/*/reader_manifest.json`

## Route And Component Map

- Route: `/book/:slug`.
- Router file: `frontend/src/App.js`.
- Primary component: `frontend/src/pages/BookDetail.jsx`.
- Data source: `api.get(/books/:slug)` with Dracula-only fallback via `DRACULA_FALLBACK_BOOK`.
- Reader route: `/reader/:slug`.
- Listen route entry: `/reader/:slug?listen=1`, rendered only when `audiobookReleaseState(publicBook).canShowControls` is true.
- Cover component: `BookCoverImage`.
- Cover resolver: `bookCoverImageSources` and graphical fallback path, with public cover audit covering typographic-only risk.
- SEO hook: `useSEO`.
- Structured data: `JsonLd` emits `Book` schema only when rights/schema gates allow it.

## Current Information Hierarchy

- Back-to-library link appears above the detail hero.
- Left column shows front cover and back cover.
- Right column shows category, title, author, subtitle, description, metadata row, CTAs, experience truth panel, sharing, chapter list, benefits, author note, and Dracula-specific preview/payment block.
- Title scale is restrained for desktop compared with earlier hero patterns, but Bengali long titles need screenshot validation before approval.
- Reader-first copy exists through the experience panel: `Reader edition ready`, `No public audio controls...`, and `Release truth preserved`.

## CTA And Audio Logic

- Primary reader CTA always links to `/reader/:slug`.
- Dracula also exposes preview and reading-pass CTAs.
- Listen CTA uses `audioState.canShowControls`.
- `audioState` comes from `audiobookReleaseState(publicBook)`.
- Audio controls are not rendered from slug alone.
- Risk: Book Detail does not fetch reader manifest directly. Approved audio visibility depends on `/books/:slug` including approved audio fields or reader-manifest-backed fields.
- Risk: `audiobookReleaseState` labels partially configured audio as `Audiobook held for QA`; this is truthful for non-approved titles, but can become stale if the book endpoint omits current approved reader-manifest evidence.

## SEO And Structured Data

- `useSEO` writes title, description, canonical, OpenGraph, Twitter, and robots.
- `JsonLd` emits only `Book` schema in `BookDetail.jsx`.
- No `AudioObject` is emitted by Book Detail today.
- Book schema is gated by `public_json_ld_enabled`, Dracula fallback, or rights tier approval.
- Risk: static SEO snapshot script still contains Dracula-specific reader copy and should be audited in the BOOK_DETAIL implementation phase before making production SEO claims.

## Typography And Layout Risks

- Bengali typography risk: title and description inherit general serif/UI classes; screenshots must verify Bengali title line breaks, line-height, and fallback font quality.
- English typography risk: Dracula-specific CTA/payment block may keep the page too Dracula-centered compared with the broader bilingual library direction.
- Mobile risk: cover and back-cover stack are constrained, but long Bengali titles, CTA wrapping, and chapter rows need mobile screenshots at `390x844` and `430x932`.
- Accessibility risk: primary CTAs are semantic links; audio Listen CTA includes an icon plus text. The Book Detail phase should verify focus order, heading order, and accessible names.
- Performance risk: front cover is eager/high priority and back cover lazy. Large remote covers should be checked for LCP and layout stability.

## Release-Gate Risk Table

| Slug | Current Discovery Status | Book Detail Audio Risk | Required BOOK_DETAIL Check |
| --- | --- | --- | --- |
| `book-2b9853ec52` | Bengali pilot; local `public_book.json` has `audiobook_enabled=true` and `audio_enabled=true`, but local fields inspected did not include release gate or QA approval. | Could show `Audiobook held for QA` if book API omits reader-manifest approval; could expose Listen only if approved evidence fields are present. | Verify production book API, reader manifest, endpoint, and detail-page copy before claiming approved detail audio. |
| `a-ghost-story` | No local `public_book.json` found in controlled publications during discovery. | Paid/listen claims remain HOLD unless production route and manifest evidence pass. | Verify production `/book/a-ghost-story`, reader manifest, and endpoint before any Listen CTA or campaign copy. |
| `book-d19e96859f` | Local metadata has audio flags true, but canary has ASR/source first/last mismatch repair pending. | Detail page must not expose Listen until gate evidence is repaired and approved. | Confirm `audiobookReleaseState` fails closed when release gate/QA fields are absent or incomplete. |
| `book-f5d593e1f4` | Local metadata has audio flags true, but canary has ASR/source first/last mismatch repair pending. | Detail page must not expose Listen until gate evidence is repaired and approved. | Confirm no narrator, duration, waveform, progress, or Listen CTA appears. |
| `muchiram-gurer-jibanchorit` | Representative timeout repair only; local metadata has audio flags true. | Must remain in preparation/audio-hidden on detail until representative evidence and full gates pass. | Verify detail page avoids Listen and uses premium reader-first copy. |
| `pather-panchali` | Reader exists; audiobook NO-GO pending full-work source/rights scope and cover repair. | No paid audio or Listen CTA allowed. | Verify detail page shows reader path only and does not imply audiobook availability. |
| `bn-066` | Stage 1 ready only; no local `public_book.json` found in discovery path. | No paid audition/full TTS approved; no public audio UI allowed. | Resolve detail route visibility and ensure audio remains hidden while `paid_tts.lock` is active. |
| `dracula` | Controlled English reader release with Dracula-specific fallback and payment block. | Current source copy says audio is in private review; no Listen CTA unless evidence appears. | Verify Dracula no longer dominates broader brand patterns in Book Detail phase. |
| `radharani` | Bengali reader metadata present; audio flags true without approval fields in local sample. | Must fail closed if approval fields are absent. | Verify premium reader-only presentation and no Listen CTA. |
| `nishkriti` | Controlled publication has highlight sync files but no local `public_book.json` in discovery result. | Unknown detail metadata path; must fail closed. | Resolve canonical metadata and verify reader-only/audio-hidden behavior. |
| `the-last-leaf` | Content book exists; controlled publication has highlight sync files but no local `public_book.json` in discovery result. | Must not expose audio unless production approval exists. | Verify cover and SEO sensitivity before paid creative or audio claims. |
| `the-masque-of-the-red-death` | Content book exists; controlled publication has highlight sync files but no local `public_book.json` in discovery result. | Must not expose audio unless production approval exists. | Verify cover and SEO sensitivity before paid creative or audio claims. |

## BOOK_DETAIL Phase Implementation Targets

- Premium literary detail page, not e-commerce clutter.
- Calm cover, metadata, availability, and CTA hierarchy.
- Reader-first titles must feel complete and intentional.
- Bengali and English typography must both feel native and dignified.
- No oversized or claustrophobic typography.
- No typographic-only public covers.
- No audio CTA unless production audiobook evidence passes.
- No stale audio URL.
- No browser/system speech fallback.
- No word-level sync claim unless true word-level sync exists.
- SEO metadata must not claim unavailable audio.
- Structured data must not advertise audio unless the audiobook is approved.
- Mobile must avoid horizontal overflow.
- Accessibility must preserve keyboard navigation, focus visibility, semantic headings, and clear control names.

## Discovery Recommendation

Proceed to BOOK_DETAIL implementation only after this discovery packet is accepted for the next phase. The first implementation pass should prioritize release-state copy, approved-audio evidence handling, Bengali title typography, and mobile CTA wrapping before visual polish.
