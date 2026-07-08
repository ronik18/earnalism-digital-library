# FINAL_INTEGRATION Source Reconciliation

Generated: 2026-07-08T13:45:10Z

## Scope

FINAL_INTEGRATION Stage A reconciles approved source work only. It does not approve preview deploy, production deploy, paid Listen campaigns, paid TTS, release-gate mutation, or launch-wide 10/10.

## Approved Frozen Inputs

| Phase | Status |
| --- | --- |
| HOME | APPROVED_FROZEN |
| LIBRARY | APPROVED_FROZEN |
| BOOK_DETAIL | APPROVED_FROZEN |
| READER | APPROVED_FROZEN |
| AUDIOBOOK_PLAYER | APPROVED_FROZEN |
| SETTINGS | APPROVED_FROZEN |
| BRAND_HEADER_LOGO | APPROVED_SCOPED_EXPERIMENT |
| MARKETING_LANDING | APPROVED_FROZEN |

## Source Areas Included In The Release Candidate

- Header and brand lockup: `frontend/src/components/Header.jsx`, `frontend/src/components/BrandHeaderLogo.jsx`, `frontend/src/index.css`.
- Library/catalog presentation: `frontend/src/pages/Library.jsx`, `frontend/src/components/BookCard.jsx`, `frontend/src/lib/libraryCatalog.js`, `frontend/src/lib/libraryFallbackBooks.js`.
- Book detail presentation: `frontend/src/pages/BookDetail.jsx`, `frontend/src/lib/bookDetailPresentation.js`.
- Reader and settings: `frontend/src/pages/Reader.jsx`, `frontend/src/lib/readerSettings.js`.
- Audiobook player hardening: `frontend/src/components/AudioPlayer.jsx`, `frontend/src/components/AudioPlayer.css`, `frontend/src/lib/audioReleaseSafety.js`, deleted duplicate `frontend/src/components/AudioPlayer 2.jsx`, and `frontend/public/service-worker.js`.
- Marketing/contact/SEO: `frontend/src/hooks/useSEO.js`, `frontend/src/pages/About.jsx`, `frontend/src/pages/Contact.jsx`, `frontend/src/pages/Pricing.jsx`, `frontend/src/pages/Journal.jsx`, `frontend/src/components/Footer.jsx`, `frontend/src/config/socialLinks.js`, `frontend/src/lib/controlledLaunch.js`, `frontend/src/components/ShelfTwoSlideshow.jsx`.
- Validation: `frontend/scripts/visual-luxury-smoke.mjs`, source tests added under `frontend/src/**/*.test.js`.
- Governor evidence: `internal/earnalism_intelligence/ux_governor/**`, decision ledgers, sprint learnings, and dashboards.

## Generated Or Local-Only Artifacts To Exclude From Source-Only Commit

- `frontend/build/`
- `/tmp/earnalism-ux-review/**`
- `/tmp/earnalism-visual-smoke-screenshots/**`
- `ux_visual_regression_report.json` unless intentionally attached as local evidence.
- `frontend/public/sitemap.xml` requires explicit SEO-owner review before staging because build regeneration changed dates/order.
- `graphical_cover_generation_report.json`, `book_cover_art_briefs.json`, and root `*_report.json` files should be staged only if they are selected governance evidence.
- Root audiobook daemon logs, heartbeat files, and pipeline status JSON/MD are operational evidence, not frontend release source.
- `frontend/node_modules/` remains dependency installation output and must not be staged.

## Source-Only Staging Plan

Stage intentionally:

- Frontend source and tests listed in the source areas above.
- `frontend/public/service-worker.js` because it is public runtime source and removes static audiobook cache behavior.
- `frontend/scripts/visual-luxury-smoke.mjs` because strict default smoke now covers the FINAL_INTEGRATION route matrix.
- UX governor review/evidence packets and approval state files required to prove owner gates.
- Decision ledger and sprint learning entries that document material release-truth decisions.

Do not stage unless separately reviewed:

- `frontend/public/sitemap.xml` generated churn.
- Root generated JSON reports not directly selected for the PR evidence set.
- Audio daemon logs and transient status files.
- Local screenshots/contact sheets under `/tmp`.

## Cleanup Status

- Temporary visual smoke runner was removed by the smoke script.
- Temporary local SPA server was stopped.
- Generated build output remains under `frontend/build/` and is excluded from source-only staging.
- No commit was created.

## Remaining Integration Risk

The worktree is intentionally broad and dirty from multiple approved phases. Before commit/PR, run a staged diff review that includes only source, tests, public runtime source, and selected governor evidence.
