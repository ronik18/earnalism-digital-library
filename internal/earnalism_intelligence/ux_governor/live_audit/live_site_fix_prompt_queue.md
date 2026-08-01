# Earnalism Live UX Truth Auditor — Ordered Fix Prompt Queue

Observed: 2026-07-13. This queue is audit output only. No fix is authorized by its presence here.

## 1. P0 Unapproved Audio Storage Containment

Issues: `UX-001`.

```text
You are Earnalism Release Truth Governor.

Execute P0_UNAPPROVED_AUDIO_STORAGE_CONTAINMENT.

Scope:
- Inventory every direct B2/Cloudinary MP3 and sidecar for alices-adventures-in-wonderland, bn-027, lokrahasya, mrinalini, nishkriti, the-wonderful-wizard-of-oz, bn-059, bn-066, and the-art-of-money-getting.
- Record URL ownership, checksum, size, private-QA retention path, and current direct HTTP status.
- Create or restore a dry-run-only remediation tool and evidence packet.
- Prepare the exact object ACL/revocation/delete plan needed to make every unapproved direct URL return 403/404.

Do not:
- mutate remote storage without a separately reviewed owner approval;
- change release gates;
- upload or regenerate audio;
- affect book-2b9853ec52 or a-ghost-story.

Likely files:
- backend/data/controlled_publications/*/public_book.json
- data/controlled_publications/*/public_book.json
- internal/audiobook_lab/scripts/ (new or restored dry-run tool)
- internal/audiobook_lab/sprint1_publication/title_runs/ (evidence only)

Validation:
- API and direct-storage Range matrix for all nine slugs.
- Approved audiobook endpoints remain 206.
- bn-066 remains reader-enabled, audio.disabled, endpoint 404, zero player DOM.
- No generated media enters frontend/public or frontend/build.

PR/merge boundary:
- Evidence and non-destructive guardrail PR is allowed.
- Remote deletion or ACL mutation requires explicit owner approval after dry-run review.
```

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && for slug in alices-adventures-in-wonderland bn-027 lokrahasya mrinalini nishkriti the-wonderful-wizard-of-oz bn-059 bn-066 the-art-of-money-getting; do file="backend/data/controlled_publications/$slug/public_book.json"; url=$(jq -r '.audiobook_assets.mp3 // empty' "$file" 2>/dev/null); status=$(test -n "$url" && curl -sS -o /dev/null -w '%{http_code}' -H 'Range: bytes=0-0' "$url" || printf NA); printf '%s\t%s\n' "$slug" "$status"; done
```

## 2. P0 Clean-HEAD Audio Release Safety

Issues: `UX-002`.

```text
Execute P0_CLEAN_HEAD_AUDIO_RELEASE_SAFETY_RECONCILIATION from a clean origin/main worktree.

Make data/controlled_launch.json and backend/data/controlled_launch.json authorize exactly a-ghost-story and book-2b9853ec52. Remove slug-derived static /audio probing and browser/system speech fallback from the committed Reader. Require enabled=true, release_gate=APPROVED, qa_status=QA_PASSED, explicit endpoint-safe MP3 evidence, and a passing endpoint before any audio UI can render.

Touch only controlled-launch truth, backend audio exposure helpers, Reader/audio release helpers, and focused tests. Do not use the dirty luxury branch as the implementation baseline. Do not approve bn-066 or any unrelated title. Do not alter visual design.

Run backend controlled-launch tests, audioReleaseSafety tests, AudioPlayer release-truth tests, frontend build, public-media scans, and a production manifest sweep. Open a focused PR; merge only after checks and release-governor review pass.
```

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && git fetch origin main && git worktree add /tmp/earnalism-audio-safety-reconciliation origin/main
```

## 3. Canonical Library Reader and Audiobook Truth

Issues: `UX-003`.

```text
Execute LIBRARY_CANONICAL_READER_AND_AUDIO_TRUTH_FIX.

Replace the eleven-slug static reader decision with canonical LIVE_APPROVED + reader_enabled truth. Gate audio independently from strict approved manifest evidence. Fix the 26 Reader Ready cards that route to Contact, populate /library?availability=approved-audiobook with exactly book-2b9853ec52 and a-ghost-story, and make card badge, href, primary CTA, and secondary CTA derive from one shared release-state model.

Likely files: backend/catalog_truth.py, backend/server.py, frontend/src/lib/controlledLaunch.js, frontend/src/components/BookCard.jsx, frontend/src/components/ApprovedAudiobookSpotlight.jsx, frontend/src/pages/Library.jsx, and focused tests.

Do not expose Listen for bn-066 or any other non-approved title. Do not add another static slug list. Validate DOM/API parity plus 1440x900, 390x844, and 430x932 screenshots. PR and merge are allowed only after regression and production rechecks pass.
```

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && rg -n 'LIVE_APPROVED_READER_SLUGS|isLiveApprovedBook|ApprovedAudiobookSpotlight|availability' frontend/src backend
```

## 4. Canonical Catalog, Sitemap, SEO, and HTTP Truth

Issues: `UX-004`, `UX-005`.

```text
Execute CANONICAL_PUBLIC_CATALOG_AND_RAW_SEO_TRUTH_FIX.

Create one rights-aware canonical public-title projection for controlled status, /api/books, Library, detail/manifest routes, and sitemap generation. Resolve 34 dead sitemap slugs, four catalog orphans, and two phantom controlled-live slugs without inventing public eligibility. Generate route-specific raw title, description, canonical, social image, and language metadata. Make reader routes noindex with their book canonical. Return 404/410 for absent content or a deliberate server-side 3xx alias. Redirect one HTTPS hostname to the canonical host.

Likely files: backend/catalog_truth.py, backend/server.py, backend/data/controlled_launch.json, frontend/scripts/generate-seo-assets.mjs, frontend/scripts/generate-static-seo-snapshots.mjs, frontend/src/hooks/useSEO.js, frontend/src/App.js, frontend/vercel.json, and catalog tests.

Do not make a missing-rights title public to equalize sets. Do not add AudioObject for non-approved audio. Do not run a manual Vercel deployment. Owner review is required for title-set changes; generator/test-only changes may merge after preview routing validation.
```

Next exact command:

```bash
comm -3 <(curl -fsS https://www.theearnalism.com/sitemap.xml | rg -o '<loc>https?://[^<]+/book/[^<]+' | sed 's#.*/book/##' | sort -u) <(curl -fsS https://api.theearnalism.com/api/books | jq -r '.[].slug' | sort -u)
```

## 5. Bilingual Fonts, Language, and Reader Reflow

Issues: `UX-006`, `UX-007`, `UX-019`.

```text
Execute BILINGUAL_TYPOGRAPHY_AND_READER_REFLOW_FIX.

Deliver licensed Bengali and English webfonts instead of relying on unnamed device fallbacks. Add canonical language codes, lang=bn to Bengali spans, and separate mixed-script title spans. Remove Latin tracking/uppercase from Bengali metadata. Set Bengali reader defaults to 19-21px with 1.8-2.0 line height and English to 18-20px with 1.65-1.8. Normalize A Ghost Story source-layout line breaks without changing words or paragraph order. Bring marketing heroes to the 42-52px, 1.08-1.16 policy range.

Likely files: frontend/public/index.html, frontend/src/index.css, BookCard.jsx, ShelfTwoSlideshow.jsx, BookDetail.jsx, Reader.jsx, About.jsx, Journal.jsx, Contact.jsx, Pricing.jsx, backend catalog projection, and A Ghost Story normalization tests.

Do not rewrite the manuscript, regenerate audio, alter source hashes silently, claim word-level sync, or use unlicensed fonts. Revalidate source/audio binding if normalized text changes. Owner font-licensing and visual review are required before merge.
```

Next exact command:

```bash
css=$(curl -fsSL https://www.theearnalism.com | rg -o '/static/css/main\.[^"]+\.css' -m1); curl -fsSL "https://www.theearnalism.com$css" | rg '@font-face|fonts\.(googleapis|gstatic)|woff|ttf|otf' || echo NO_DELIVERED_WEBFONT
```

## 6. Approved Reader Listen Handoff and Timestamp Contract

Issues: `UX-008`, `UX-020`.

```text
Execute APPROVED_READER_LISTEN_HANDOFF_AND_TIMESTAMP_CONTRACT_FIX.

Keep the approved set exactly book-2b9853ec52 and a-ghost-story. Consume listen=1 by selecting the first playable content page without autoplay. Define one timestamp schema, safely normalize start/end seconds and start_ms/end_ms, and keep paragraph/stanza cues separate from word indexes. Add seek, progress, elapsed/duration and robust pause/resume controls. Make supported-browser currentTime advancement a hard release test. Return 416 for unsatisfiable GET and HEAD ranges while preserving valid 206 responses.

Likely files: backend/server.py, frontend/src/pages/BookDetail.jsx, frontend/src/pages/Reader.jsx, frontend/src/lib/audioReleaseSafety.js, sidecar fixtures, and focused tests.

Do not fabricate cues, claim word-level sync, use estimated sync, autoplay, or expose any non-approved audio. Customer copy must say Section-following narration. Merge only after both approved titles and bn-066 regression control pass.
```

Next exact command:

```bash
for s in a-ghost-story book-2b9853ec52; do curl -fsS "https://api.theearnalism.com/api/reader/book/$s/audiobook/timestamps" | jq '(.words // .)[0:3]'; done
```

## 7. Homepage Canonical Shelf Truth and Carousel Accessibility

Issues: `UX-009`, `UX-010`, `UX-015`.

```text
Execute HOMEPAGE_CANONICAL_SHELF_AND_ACCESSIBILITY_FIX.

Replace stale Frankenstein/Kshudhita and Approved Audiobooks state with versioned canonical catalog/manifest truth. Preserve exact reader/audio eligibility. Make hidden carousel slides inert with zero focusable descendants, restore focus predictably, add a visible Pause/Play control, and retain runtime reduced-motion handling. Remove the timed blocking first-visit tour or convert it into a user-invoked non-modal orientation affordance.

Likely files: Home.jsx, ShelfTwoSlideshow.jsx, ComingSoonBoard.jsx, ApprovedAudiobookSpotlight.jsx, FirstVisitSiteTour.jsx/CSS, Layout.jsx, bookCoverResolver.js, and tests.

Do not add fake Notify behavior, Dracula-first dominance, unapproved Listen, or unrelated homepage redesign. Validate axe, keyboard, autoplay/pause/reduced-motion, API truth, and 1440/390/430 screenshots. Owner visual review is required before merge.
```

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && rg -n 'frankenstein|kshudhita|Approved Audiobooks|FirstVisitSiteTour|aria-hidden|matchMedia' frontend/src
```

## 8. Reader Dialogs, Global Focus, Contrast, and Small-Viewport Controls

Issues: `UX-011`, `UX-012`, `UX-021`.

```text
Execute ACCESSIBLE_READER_AND_GLOBAL_FOCUS_FIX.

Add correct modal behavior to Reader Contents and Settings: role and accessible name, initial focus, focus trap, Escape close, inert background, and trigger focus restoration. Restore unmistakable focus-visible styling on Contact controls, focus the destination main heading after SPA route changes, raise Pricing duration text to at least 4.5:1, add a semantic Reader h1, and prevent bottom-bar clipping at 320px with practical tap boxes.

Likely files: frontend/src/pages/Reader.jsx, frontend/src/index.css, frontend/src/App.js, frontend/src/components/Layout.jsx, frontend/src/pages/Pricing.jsx, and Playwright/axe tests.

Do not alter release state, reader content, approved-audio eligibility, or palette direction. Validate approved and hidden readers at 320/390/430/1440 plus keyboard and axe runs. Merge only after manual keyboard recheck.
```

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && rg -n 'role=.dialog|aria-modal|focus-visible|reader-bottom-bar__controls|reader-topbar__back|<h1' frontend/src
```

## 9. Library Density, Mobile Navigation, and Real CTA Behavior

Issues: `UX-013`, `UX-016`, `UX-017`.

```text
Execute LIBRARY_DISCOVERY_AND_NAVIGATION_CLARITY_FIX.

Move discovery controls before promotional modules, bound pipeline cover pairs, and paginate or progressively disclose the catalog without hiding titles. Close the mobile menu after query-only navigation and compute exactly one aria-current from pathname plus normalized search. Connect Reading Circle to an existing real signup/contact journey or render an honest unavailable state.

Likely files: frontend/src/pages/Library.jsx, frontend/src/components/Header.jsx, frontend/src/index.css, and focused tests.

Do not change book/audio status, introduce fake forms, or change the palette. Validate 320/390/430/1440 layouts, exact-one aria-current, menu close behavior, CTA outcome, and full catalog discoverability. Owner visual review is required before merge.
```

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && rg -n 'library-pipeline-feature|trackPipelineInterest|loc.pathname|aria-current|mobile-nav' frontend/src
```

## 10. Canonical Premium Covers and Book Detail Composition

Issues: `UX-014`, `UX-018`.

```text
Execute CANONICAL_PREMIUM_COVER_AND_BOOK_DETAIL_FIX.

Reconcile list/detail/manifest cover identity and checksums, audit the two approved audiobook covers against the graphical/content-themed policy, and prepare owner-review replacements only for evidence failures. Use deterministic title/author/imprint overlays. Bound front/back cover pairs into a responsive editorial composition and replace title-agnostic module copy with truthful metadata-driven copy.

Likely files: backend/server.py, frontend/src/lib/bookCoverResolver.js, frontend/src/pages/BookDetail.jsx, frontend/src/pages/Reader.jsx, frontend/src/index.css, cover assets and audit fixtures.

Do not add audiobook claims to covers, use AI-rendered final text, change release gates, or generate replacement art without owner approval. Run cover audit, checksum parity, broken-image checks and approved/hidden desktop/mobile screenshots. Owner visual approval is required before merge.
```

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && node frontend/scripts/audit-book-covers.mjs
```

## 11. Public Contact Email Truth Guard

Issues: `UX-023`.

```text
Execute PUBLIC_CONTACT_EMAIL_TRUTH_GUARD.

Replace duplicated public email literals with one shared sales@reoenterprise.org constant. Remove every public sales@reoenterprise.in reference and add a build/test scan that fails if the .in address returns in source or production bundles.

Likely files: frontend/src/components/Footer.jsx, frontend/src/pages/Contact.jsx, frontend/src/config/socialLinks.js, and focused tests.

Do not change unrelated social destinations, expose private mailbox metadata, or deploy manually. Validate mailto links on desktop/mobile and confirm the production bundle contains .org and no .in. Focused PR/merge allowed after regression and normal deployment checks.
```

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && rg -n 'sales@reoenterprise\.(in|org)' frontend/src README.md
```

## 12. Post-Deploy Performance Truth and Critical-Route LCP

Issues: `UX-024`, `UX-025`, `UX-026`.

```text
Execute POST_DEPLOY_PERFORMANCE_TRUTH_AND_LCP_FIX.

Bind production k6 to successful deploy/canary completion and verify the deployed SHA before load begins. Do not lower thresholds or run 100-VU load outside an approved window. Break the Reader manifest/chapter/cover discovery waterfall, generate fingerprinted responsive cover derivatives within the existing 180KB feature and 80KB card budgets, and make srcset candidates physically distinct. Add route-specific cold/warm latency evidence for /api/home and reader manifests without turning one volatile sample into a deployment blocker.

Likely files: .github/workflows/post-deploy-k6.yml, .github/workflows/go-live-regression-gate.yml, scripts/k6_load_100.js, scripts/production_monitor.mjs, .github/workflows/production-monitor.yml, frontend/src/pages/Reader.jsx, frontend/src/pages/Library.jsx, frontend/src/lib/images.js, frontend/public/service-worker.js, and focused tests.

Do not immutable-cache unversioned covers, lower monitoring thresholds, alter release gates, change visual content, or claim Core Web Vitals green without field evidence. Validate workflow ordering, deployed SHA binding, repeated mobile Lighthouse runs, cover audit, CLS, visual fidelity, and production latency artifacts. Product-performance changes require a focused PR and production observation after normal deployment.
```

Next exact command:

```bash
gh run view 29233987719 -R ronik18/earnalism-digital-library --json headSha,createdAt,updatedAt,jobs
```

## 13. Reproducible Live UX Audit Harness

Issues: `UX-022`.

```text
Execute REPRODUCIBLE_LIVE_UX_AUDIT_HARNESS.

Add a focused Playwright plus axe route matrix and optional Lighthouse/Web Vitals artifacts while reusing existing k6 and regression workflows. Include Home, Library, both approved Book/Reader pairs, bn-066, one hidden English title, Contact, Pricing, mobile navigation and carousel. Persist screenshots outside production assets and output machine-readable route, a11y, release-truth and performance summaries.

Likely files: frontend/scripts/visual-luxury-smoke.mjs, a new narrowly scoped audit script, frontend/package.json only if required, and existing CI workflows.

Do not change product performance, install broad dependency sets, run manual Vercel deployment, or claim Lighthouse/a11y/10-of-10 green without measured evidence. An evidence/test PR may merge when CI remains stable.
```

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && npm ls --prefix frontend @axe-core/playwright axe-core lighthouse --depth=0 || true
```
