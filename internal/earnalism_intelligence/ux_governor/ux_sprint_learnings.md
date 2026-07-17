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
