# UX Sprint Learnings

## 2026-07-08 HOME Interactive Phase

- HOME is the only approved UX phase in this sprint.
- The next phase requires a new owner approval file or env approval.

## 2026-07-08 BOOK_DETAIL Approval And READER Discovery

- BOOK_DETAIL is owner-approved for phase progression only; this does not approve launch, paid Listen campaigns, paid TTS, or production mutation.
- READER discovery is active. Before implementation review, remove or prove-inert browser/system speech fallback and tighten static audio derivation so no stale `/audio/...` route can be exposed as an audiobook.

## 2026-07-08 READER Ready For Owner Review

- Reader theme labels should be Light, Sepia, and Night and map to the fixed Earnalism palette.
- Bengali font mode needs explicit customer-facing labels; "Literary Bengali serif" and "Clear Bengali sans" are clearer than a generic font toggle.
- Public Reader audio paths should fail closed from shared approval evidence, not slug, title, language, static path, or local fallback metadata.
- Phase-scoped Reader smoke now verifies reader page/content/settings/TOC, mobile overflow, no audio controls, no generated audio element, no static audio source, and visible reader-ready/audio-hidden state across 10 routes and 9 viewports.

## 2026-07-08 AUDIOBOOK_PLAYER Discovery Active

- AUDIOBOOK_PLAYER discovery starts only after explicit READER owner approval; it does not approve player implementation, paid audio, paid Listen campaigns, or launch.
- Public player implementation must not reuse legacy `AudioPlayer.jsx` or `AudioPlayer 2.jsx` as-is because both derive static `/audio/${lang}/${bookSlug}` assets and mention word-level timestamps.
- Existing active surfaces should keep using `audiobookReleaseState` / `canExposeAudiobookControls`; player controls must render only from approved manifest assets, not slug, language, title, duration, narrator, local fallback metadata, or static paths.

## 2026-07-08 AUDIOBOOK_PLAYER Ready For Owner Review

- The safest player implementation is a fail-closed component that receives a book object and delegates release approval to `audiobookReleaseState`; it should return `null` when evidence is incomplete.
- Same-origin static audiobook paths are not release evidence, even if release-shaped metadata is present.
- Phase-scoped AUDIOBOOK_PLAYER smoke should include approved and blocked book/detail and reader routes so approved pilot behavior and hidden non-approved behavior are validated together.
- SETTINGS must remain blocked until the owner explicitly approves the AUDIOBOOK_PLAYER packet and contact sheet.

## 2026-07-08 BRAND_HEADER_LOGO Ready For Owner Review

- Brand/header experiments should use their own owner-review packet and must not advance the controlled UX phase machine.
- Header-logo text should remain deterministic SVG/HTML/CSS so the `LEarnalism` proofreader correction is crisp, accessible, and not AI-rasterized text.
- The public header should default to the safer tricolor literary badge; exact Indian flag use remains a compliance-review variant only.
- Phase-scoped BRAND_HEADER_LOGO smoke should verify the header in Home, Library, and Book Detail contexts and keep strict full-route smoke unchanged by default.

## 2026-07-08 AUDIOBOOK_PLAYER Approved, SETTINGS Discovery Active

- AUDIOBOOK_PLAYER approval records phase progression only; it does not approve paid TTS, paid Listen, production mutation, launch, or a launch-wide green claim.
- SETTINGS discovery should start from the inline Reader settings in `Reader.jsx`, not from the global `SettingsContext.jsx`.
- Reader settings already cover the requested dimensions, but implementation should harden persistence, focus return, keyboard flow, mobile wrapping, and screen-reader state clarity.
- SETTINGS remains discovery-only until a controlled implementation sprint produces screenshots, validation, and an owner review packet.

## 2026-07-08 SETTINGS Ready For Owner Review

- A pure `readerSettings` helper keeps persistence bounded and testable without widening Reader behavior.
- Settings dialog focus should be tested in browser smoke, not assumed from source; SETTINGS smoke now requires focus containment in every route/viewport check.
- Reset-to-comfort-defaults gives the owner a visible recovery path and provides a concrete persistence test target.
- SETTINGS approval will be a phase-transition approval only; it must not approve preview/deploy, paid TTS, paid Listen campaigns, or launch-wide 10/10.

## 2026-07-08 BRAND_HEADER_LOGO Approved

- BRAND_HEADER_LOGO is approved as a separate brand-header experiment using the Editorial Proofreader direction.
- The safer tricolor literary badge is the approved public default; exact Indian flag use remains compliance-review-only.
- The approval does not advance SETTINGS, alter AUDIOBOOK_PLAYER state, or approve paid audio, release gates, preview/deploy, or launch-wide 10/10.

## 2026-07-08 SETTINGS Approved, MARKETING_LANDING Discovery Active

- SETTINGS is owner-approved for progression only; it does not approve launch, preview/deploy, paid Listen campaigns, paid TTS, or release-gate mutation.
- MARKETING_LANDING implementation should begin from Home, Micro-story, Pricing, About, Contact, Journal, Header/Footer, SEO, JsonLd, and launch fallback copy.
- The next implementation should preserve release-truth-safe audiobook claims, rebalance Dracula-first marketing copy, and keep reader-only states premium.

## 2026-07-08 MARKETING_LANDING Ready For Owner Review

- The marketing phase should be reviewed as Home/About/Pricing/Contact/Journal/Micro-story together because copy truth, SEO, support email, and CTA behavior are shared trust signals.
- About/default SEO now carry the bilingual brand frame; Dracula remains a reader-ready English classic but no longer anchors the brand story.
- MARKETING_LANDING visual smoke passed 24/24 route-viewport checks with zero blockers, using only phase-scoped SPA fallback and local marketing API mocks.
- Owner approval is required before FINAL_INTEGRATION; preview/deploy, paid Listen, paid TTS, and launch-wide green claims remain out of scope.

## 2026-07-08 MARKETING_LANDING Contact Truth Correction

- `sales@reoenterprise.org` is owner-confirmed as the public contact/sales email.
- `.in` contact references were corrected in public contact surfaces, social mailto defaults, marketing tests, smoke checks, and MARKETING_LANDING SEO evidence.
- MARKETING_LANDING remains awaiting owner review; no phase advancement or audio release-gate mutation occurred.

## 2026-07-08 MARKETING_LANDING Approved, FINAL_INTEGRATION Discovery Active

- MARKETING_LANDING approval records phase progression only and does not approve preview/deploy, production validation, paid Listen, paid TTS, or launch-wide green status.
- FINAL_INTEGRATION discovery should start from approved phase packets and focus on source-only reconciliation, release-gate truth, route/SEO/performance/accessibility validation, generated artifact exclusion, and Vercel readiness.
- Vercel CLI upgrade is recommended for the later preview gate, but it was intentionally not run in this owner-review transition.

## 2026-07-17 Premium Dynamic Sprint 1 Home Hero

- Production HTML/CSS can reproduce the premium library ambience without turning a visual mockup into a static banner or inventing book metadata.
- The most credible hero uses exact controlled-publication covers as the decoration; responsive perspective, device shells, and library atmosphere remain CSS-only.
- The header can hold the deterministic proofreader wordmark, a visible tricolor literary medallion, and a full desktop navigation while collapsing to one accessible mobile menu.
- The hero remains reader-facing when release-state details stay in the payload but never render as public copy.
- Responsive evidence passed at 1440x900, 1536x864, 390x844, 430x932, and 768x1024 with no horizontal overflow or broken hero images.

## 2026-07-17 Premium Home Hero Production Gate

- Treat the production hero as incomplete when its canonical curation endpoint is unavailable, even if the static premium shell and Vercel canary are green.
- The UI fails closed without fake titles, covers, or listening controls when curation fetch fails.
- Railway snapshot failures did not change audiobook release truth or the prior healthy backend.

## 2026-07-17 Reference-Accurate Dynamic Hero Follow-up

- Desktop can use the supplied artwork as a low-latency scene only when the interactive areas remain real focusable links and semantic copy remains accessible.
- Canonical opaque cover overlays are necessary because the reference book/device titles are visual direction, not publication truth.
- The closest honest match is exact geometry with intentional catalog-region replacements; claiming literal whole-frame equality would hide those required changes.
- Mobile should use a purpose-built semantic layout instead of shrinking the desktop bitmap, preserving legibility and avoiding the desktop-art transfer.
- The listening phone must be selected from the intersection of approved audio and visually featured books; this excludes hidden titles and cover-audit failures automatically.
- Static and browser regressions must follow the current semantic contract (`data-book-slug`, reference-art geometry, and transparent hotspots) rather than preserve identifiers from the retired CSS-only hero.
- The canonical boot snapshot is also a UX resilience layer: it kept the production hero complete and immediately populated while the backend curation endpoint remained unavailable.

## 2026-07-28 Home Hero And Collage Production Hotfix

- A loaded image is not a visible image: production had four successful canonical Cloudinary responses whose final hero opacity was still `0` because the reference-art masking rule was broader than the intended device-only mask.
- The desktop reference artwork leaves four cover-shaped regions blank, so those regions must be filled by canonical DOM images; hiding them converts a truthful hybrid hero into broken empty panels.
- Responsive collision checks must compare functional grid zones and cover siblings, not only page-level horizontal overflow. The broken cards clipped their own CTA and cover content while the document itself still reported zero horizontal overflow.
- Modifier selectors such as `curated-shelf-collage--missing-short` require an equally specific mobile reset; otherwise a tablet area map can survive below the mobile breakpoint and collapse one tile to a near-zero-width column.
- The bundled Sprint 1 snapshot is a truthful resilience path for hero and shelf books while the runtime curation request is pending or unavailable. Unsupported covers remain omitted and audiobook release truth remains unchanged.

## 2026-07-28 Home Hero Editorial Coverflow v3

- Crossfading whole four-book frames preserves equal visual weight and reads as a flat strip; a premium coverflow needs one stable slide set, a shared perspective, and explicit previous/active/next state.
- Split transform ownership across a slide-position wrapper and an inner jacket wrapper. This keeps circular placement, depth, hover lift, and physical cover construction from overwriting one another.
- A transparent full-stage hit plane can intercept pointer events intended for negative-Z side books. Keep the stage non-interactive and restore pointer events only on the three visible slide wrappers.
- Cover eligibility must remain consistent across curation versions. Reusing the owner-reviewed visual-cover exclusions reduced the live Sprint 1 hero candidates from 26 to 13 without changing reader, audiobook, or shelf truth.
- Six-viewport browser evidence passed with exactly three meaningful slides, zero horizontal overflow, zero hidden focus targets, uniform non-overlapping gaps, and 44px touch controls on tablet and mobile.
- Go-live static assertions must migrate with an intentional component contract. The retired slot selector and per-book perspective string were replaced by checks for the shared coverflow stage, `1100px` perspective, and preserved 3-D context.

## 2026-07-28 Admin cover desk

- Cover remediation is clearer as a dedicated admin workspace than as two
  controls buried inside the general book editor.
- Operators need canonical, private-upload, and review states shown separately;
  otherwise a successful Cloudinary upload can be mistaken for a public catalog
  approval.
- Defaulting the desk to “Needs attention,” with title/author/slug search and
  front/back status chips, keeps the 32-title queue scannable without adding a
  heavy table or another network waterfall.
- Accessible file labels, deterministic cover previews, and client-side
  MIME/size limits provide fast feedback while the backend remains the
  authoritative validator.

## 2026-07-28 Home Hero Devdas Synchronization And Plaque Hotfix

- A hero image can create a false slide-data mismatch even when live carousel records are correct: the historical reference bitmap still contained a Devdas cover underneath a separately indexed dynamic plaque.
- Remove a title from the hero at the curation boundary with a stable slug sequence, while retaining the catalog record and shelf membership. A frontend exclusion remains valuable as a fail-closed defense against stale curation payloads.
- Cover, metadata, route, alt text, accessible label, counter position, and diagnostic IDs should derive from one normalized active-slide object; this makes synchronization browser-verifiable.
- Editorial plaque and 3-D book stage need separate grid regions. A translucent overlay on top of unrelated decorative book art cannot look intentional or remain accessible across breakpoints.
- Failed adjacent-cover preloads must reconcile the pending index to the visible index. Otherwise the next manual navigation can jump even when circular index math is correct.
- Five-viewport browser evidence passed with Devdas absent from the hero DOM, zero hidden focus targets, zero horizontal overflow, synchronized active identities, 44px controls, and one-step pointer and keyboard navigation.

## 2026-08-08 Compact Library Colophon Footer

- Footer compactness must measure both the footer box and its external margin. The live desktop footer used 538 px internally plus a detached 128 px top margin, so the perceived blank area was larger than the component height alone suggested.
- A premium end-of-page experience does not need more content; it needs clearer jobs. Brand promise, fast exploration, one calm contact action, and a consolidated legal rail replaced widely separated low-information rows.
- Wrapping the five core navigation links horizontally preserved 44 px touch targets while materially reducing mobile height. Compactness should come from layout structure and copy editing, not undersized controls.
- Lazy footer imagery must be scrolled into the viewport before visual assertions. Full-page screenshot capture alone can show a valid lazy-loaded wordmark as blank.
- The source candidate reduced the footer to 281 px at 1440 and 553 px at 390, removed the external margin, preserved zero horizontal overflow, and changed no audio, catalog, route, backend, or release-gate truth.
