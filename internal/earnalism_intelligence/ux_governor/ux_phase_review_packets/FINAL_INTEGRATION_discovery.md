# FINAL_INTEGRATION Discovery

Generated: 2026-07-08T12:55:46Z

## Objective

Reconcile all owner-approved UX phases into one release-readiness plan before any preview/deploy or launch-wide green claim. FINAL_INTEGRATION is discovery-only in this step. It does not approve Vercel preview/deploy, production validation, paid Listen campaigns, paid TTS, release-gate mutation, or launch-wide 10/10.

## Approval Context

- Owner decision recorded: `APPROVE_MARKETING_LANDING_AND_PROCEED_TO_FINAL_INTEGRATION`.
- MARKETING_LANDING is frozen as owner-approved for phase progression only.
- Public contact email is owner-confirmed as `sales@reoenterprise.org`.
- Full preview/production validation remains not proven.
- Paid Listen campaigns remain blocked until production route, manifest, and player proof passes.
- `paid_tts.lock` remains active and legitimate; no paid audio work is authorized.

## Approved Phase Evidence

| Phase | Status | Primary Evidence |
| --- | --- | --- |
| HOME | APPROVED_FROZEN | `HOME_review.md`, `HOME_owner_approval_summary.md`, `/tmp/earnalism-ux-review/HOME/HOME_contact_sheet.png` |
| LIBRARY | APPROVED_FROZEN | `LIBRARY_review.md`, DOM/release/smoke evidence, `/tmp/earnalism-ux-review/LIBRARY/LIBRARY_contact_sheet.png` |
| BOOK_DETAIL | APPROVED_FROZEN | `BOOK_DETAIL_review.md`, DOM/release/smoke evidence, `/tmp/earnalism-ux-review/BOOK_DETAIL/BOOK_DETAIL_contact_sheet.png` |
| READER | APPROVED_FROZEN | `READER_review.md`, DOM/release/smoke evidence, `/tmp/earnalism-ux-review/READER/READER_contact_sheet.png` |
| AUDIOBOOK_PLAYER | APPROVED_FROZEN | `AUDIOBOOK_PLAYER_review.md`, release/smoke evidence, `/tmp/earnalism-ux-review/AUDIOBOOK_PLAYER/AUDIOBOOK_PLAYER_contact_sheet.png` |
| SETTINGS | APPROVED_FROZEN | `SETTINGS_review.md`, accessibility/release/smoke evidence, `/tmp/earnalism-ux-review/SETTINGS/SETTINGS_contact_sheet.png` |
| BRAND_HEADER_LOGO | APPROVED_SCOPED_EXPERIMENT | `BRAND_HEADER_LOGO_review.md`, public default safer tricolor badge, exact flag compliance-review-only |
| MARKETING_LANDING | APPROVED_FROZEN | `MARKETING_LANDING_review.md`, DOM/SEO/release/smoke evidence, corrected contact email, `/tmp/earnalism-ux-review/MARKETING_LANDING/MARKETING_LANDING_contact_sheet.png` |

## Source Modification Areas To Reconcile

Current source modifications span the approved UX phases and must be reviewed as one integrated package before source promotion:

- Visual smoke phase support: `frontend/scripts/visual-luxury-smoke.mjs`.
- Audio truth hardening: `frontend/src/components/AudioPlayer.jsx`, removed duplicate `AudioPlayer 2.jsx`, `frontend/src/lib/audioReleaseSafety.js`, `frontend/public/service-worker.js`.
- Catalog/detail/reader presentation: `BookCard.jsx`, `Library.jsx`, `BookDetail.jsx`, `Reader.jsx`, `libraryCatalog`, `libraryFallbackBooks`, `bookDetailPresentation`, `readerSettings`.
- Brand/header: `Header.jsx`, `BrandHeaderLogo.jsx`, `index.css`.
- Marketing/contact/SEO: `useSEO.js`, `About.jsx`, `Pricing.jsx`, `Contact.jsx`, `Journal.jsx`, `controlledLaunch.js`, `ShelfTwoSlideshow.jsx`, `socialLinks.js`.
- Review/governor artifacts: `internal/earnalism_intelligence/ux_governor/**`, ledgers, dashboards, and sprint reports.

Generated artifacts and local-only evidence must remain excluded unless intentionally promoted:

- `frontend/build/`
- `/tmp/earnalism-ux-review/**`
- `ux_visual_regression_report.json`
- `frontend/public/sitemap.xml` unless reviewed as generated SEO output
- `graphical_cover_generation_report.json`
- `book_cover_art_briefs.json`
- transient screenshots/contact sheets

## Merge And Readiness Risks

- Worktree is intentionally broad and dirty from multiple approved phases; final integration needs a source-only staging plan before commit/PR.
- `frontend/public/sitemap.xml` and cover audit reports are generated side effects and can dirty the tree during validation.
- Full/default visual smoke has been kept strict by default, but phase-scoped smoke should not be mistaken for launch-wide coverage.
- Local static smoke uses SPA fallback/API mocks for some review phases; preview/production route behavior still needs direct proof.
- Reader and player release truth is fail-closed locally, but production must prove current API/manifest/player route behavior before any paid Listen campaign.
- `AUDIOBOOK_PLAYER` active code is hardened, but final scan must keep validating no static `/audio/...`, browser speech fallback, word-level sync claim, or AudioObject leakage.
- Brand header exact Indian national flag variant remains compliance-review-only; public default must remain safer tricolor literary badge.
- Public contact email must remain `sales@reoenterprise.org`; previous `.in` contact reference must not reappear in public copy or mailto links.
- CRA client-rendered SEO/static snapshot behavior requires final verification of `index.html`, static snapshots, robots, sitemap, manifest, and route metadata.
- Lighthouse/performance has historical sensitivity to homepage LCP; final integration must rerun performance before any launch-wide 10/10 claim.

## Required Final Validation Gates

- Full-route visual smoke with SPA fallback and API-routing assumptions aligned to the target environment.
- Preview route validation after explicit deploy approval only.
- Production route validation after explicit production approval only.
- Lighthouse/performance and accessibility checks for Home plus critical routes.
- SEO metadata verification for app shell, static snapshots, `robots.txt`, `sitemap.xml`, `site.webmanifest`, OpenGraph/Twitter tags, and structured data.
- Release-gate truth audit for approved and blocked audio titles.
- Cover audit proving zero typographic-only public covers.
- Frontend install, test, build, and `git diff --check`.
- Python/governor validations, including `run_ux_governor_check.py`.
- Public contact email verification for `sales@reoenterprise.org`.
- Generated artifact exclusion check before staging.
- Clean git status/source-only promotion plan.

## Vercel Readiness Discovery

- Current CLI discovered locally: `vercel 54.15.1`.
- Current recommended target from session guidance: `vercel@latest` / `54.21.1` or newer.
- Upgrade recommendation: run `npm i -g vercel@latest` or `pnpm add -g vercel@latest` later, before preview/production validation. This was not run in this discovery step.
- Vercel project files discovered: `frontend/vercel.json`, root `.vercelignore`.
- No `.vercel/` project link directory was found in this worktree during discovery.
- Frontend framework config: Create React App, build command `npm run build`, output directory `build`.
- API rewrite: `/api/(.*)` routes to `https://api.theearnalism.com/api/$1`.
- SPA rewrite excludes `static/`, `assets/`, `audio/`, `asset-manifest.json`, favicon/assets, `site.webmanifest`, `robots.txt`, and `sitemap.xml`, then sends remaining routes to `/index.html`.
- Memory-derived routing caution: Vercel and nginx need explicit exceptions for `/api/`, `robots.txt`, `sitemap.xml`, `site.webmanifest`, and static assets so SPA rewrites do not swallow them.
- Required preview env assumptions to verify later: `REACT_APP_BACKEND_URL` or production default API behavior, `REACT_APP_SITE_URL`, social URL overrides, service worker flag, analytics flags, Google/Razorpay variables if routes are tested.
- Do not run `vercel deploy`, `vercel --prod`, `vercel pull`, or Vercel preview validation until owner explicitly approves the preview/deploy gate.

## Release-Gate Risk Table

| Title / Area | Required Final Integration Truth |
| --- | --- |
| `book-2b9853ec52` | May expose audiobook controls only with approved manifest/release evidence. |
| `a-ghost-story` | Paid Listen remains HOLD until production route, manifest, and player proof passes. |
| `book-d19e96859f` | No public audio UI; repair remains pending. |
| `book-f5d593e1f4` | No public audio UI; repair remains pending. |
| `muchiram-gurer-jibanchorit` | No public audio UI; representative timeout repair remains pending. |
| `pather-panchali` | Audiobook NO-GO until source/rights/cover blockers clear. |
| `bn-066` | Stage 1 only; no audio UI while `paid_tts.lock` is active. |
| Marketing | No unapproved Listen CTA, no paid Listen claim, no fake sync, no stale audio URL. |
| Structured data | No AudioObject for non-approved audio. |
| Contact | Public contact email is `sales@reoenterprise.org`. |

## Discovery Findings

- All phase review packets exist for HOME, LIBRARY, BOOK_DETAIL, READER, AUDIOBOOK_PLAYER, SETTINGS, BRAND_HEADER_LOGO, and MARKETING_LANDING.
- MARKETING_LANDING evidence JSON parses and contact sheet exists.
- Public/evidence scan for the previous incorrect `.in` contact email returned no active public matches in the scoped paths.
- Vercel CLI is installed but outdated for the later preview/production gate.
- No Vercel deploy/preview, CLI upgrade, paid TTS, Sarvam call, publication mutation, release-gate mutation, or paid Listen approval was run.

## Next Implementation Target

The next controlled phase should produce a FINAL_INTEGRATION implementation/validation packet that reconciles source-only changes, runs full-route production-like validation, prepares preview/deploy only after explicit approval, and keeps release-gate truth fail-closed.

## Next Exact Command

```bash
cd /private/tmp/earnalism-parallel-prelaunch && sed -n '1,260p' internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/FINAL_INTEGRATION_discovery.md && git status --short
```
