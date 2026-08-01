# Earnalism Live UX Truth Audit

Observed: 2026-07-13
Site: `https://www.theearnalism.com`
Mode: read-only live browser, HTTP/API, repository mapping, axe, and existing workflow evidence
Decision: **MEASURED 10/10 NOT MET**

## Strategy

The audit used ten specialized lanes: route crawl, premium visual UX, API-to-UI truth, release-gate audio truth, bilingual typography, slideshow/card truth, navigation/CTA, accessibility, performance, and fix-prompt generation. Paid providers, release gates, deployments, product source, and remote storage were not changed.

Twenty critical routes were rendered at `1440x900`, `1536x864`, `390x844`, and `430x932`, producing 80 clean viewport screenshots. Mobile navigation and carousel interactions were exercised separately. Live catalog/API sets, reader manifests, approved and denied audiobook endpoints, sidecars, sitemap, raw HTML, direct legacy storage objects, and latest production workflows were checked.

The current worktree is heavily dirty and differs from the deployed bundle. Repository references identify likely ownership surfaces and clean-build risks; they are not treated as proof that dirty local behavior is live.

## Evidence

- Route matrix: `live_site_route_matrix.json`
- API/DOM matrix: `live_site_api_dom_mismatch_matrix.json`
- Release truth: `live_site_release_truth_findings.json`
- Visual scorecard: `live_site_visual_scorecard.json`
- Machine-readable issues: `live_site_ux_anomaly_report.json`
- Ordered prompts: `live_site_fix_prompt_queue.md`
- Clean screenshots: `/tmp/earnalism-live-ux-audit/viewport_screenshots/`
- Contact sheets: `/tmp/earnalism-live-ux-audit/contact_sheets/`
- Raw browser evidence: `/tmp/earnalism-live-ux-audit/route_evidence.json`

## Priority Backlog

| ID | Severity | Confidence | Surface | Finding |
|---|---|---:|---|---|
| UX-001 | P0 | 1.00 | Direct audio storage | Nine unapproved MP3 objects return `206`; bn-066 sidecars are also public. API denial is not storage privacy. |
| UX-002 | P0 | 1.00 | Clean-build release truth | Local allowlists authorize 53/10 audio slugs and include bn-066; immutable HEAD retains static-audio/browser-speech fallback paths. |
| UX-003 | P1 | 1.00 | Library | 26 live reader cards route to Contact; approved-audio filter is empty; approved titles display Audio Hidden. |
| UX-004 | P1 | 1.00 | Catalog/sitemap | `75` sitemap, `43` controlled-live, and `37` catalog slugs disagree; 34 dead, four orphan, two phantom. |
| UX-005 | P1 | 1.00 | Raw SEO/HTTP | Book/Reader raw HTML is generic; readers are not statically noindex; unknown routes are soft 200s; both hosts serve 200. |
| UX-006 | P1 | 1.00 | Bilingual typography | Named font families are not delivered; Bengali language metadata is missing outside reader prose. |
| UX-007 | P1 | 1.00 | Reader comfort | Bengali and English readers default to 16px; A Ghost Story hard line breaks damage reflow and word boundaries. |
| UX-008 | P1 | 0.99 | Approved audio player | Listen intent is dropped, player schema is inconsistent, controls are incomplete, and automated playback advancement was not proven. |
| UX-009 | P1 | 1.00 | Home cards | Frankenstein/Kshudhita state is stale and Approved Audiobooks has no destination despite two approved titles. |
| UX-010 | P1 | 0.99 | Carousel accessibility | Hidden slides retain focusable controls (`aria-hidden-focus`, serious). |
| UX-011 | P1 | 0.99 | Reader dialogs | Contents and Settings do not establish/trap/restore focus; background controls remain tabbable. |
| UX-012 | P1 | 0.99 | Global focus/contrast | Contact focus is imperceptible, SPA focus is lost, and Pricing labels measure `4.06:1`. |
| UX-013 | P1 | 1.00 | Library density | Forty cards and oversized pipeline cover pairs create a 17,864px desktop / 45,303px 320px catalog. |
| UX-014 | P1 | 0.99 | Covers | Flagship 2b art is placeholder-like; Ghost cover identities diverge; 17 catalog records lack physical cover URLs. |
| UX-015 | P1 | 0.99 | First visit | A timed blocking tour obscures the premium literary landing experience. |
| UX-023 | P1 | 1.00 | Contact source truth | Production uses `.org`, but the current dirty source would redeploy a dead `.in` mailbox. |
| UX-024 | P1 | 1.00 | Post-deploy k6 | The latest load ended before Vercel completed, so green k6 did not certify the newly deployed SHA. |
| UX-025 | P1 | 0.95 | Critical-route performance | Mobile Lighthouse measured 3.864s Library and 5.046s Reader LCP; oversized non-responsive covers exceed policy. |
| UX-016 | P2 | 1.00 | Mobile nav | Query-only navigation leaves the menu open and marks four links current. |
| UX-017 | P2 | 1.00 | Library CTA | Reading Circle is clickable but inert. |
| UX-018 | P2 | 0.98 | Book Detail | Full-size front/back stacking makes detail heroes excessively tall; modules are title-agnostic. |
| UX-019 | P2 | 1.00 | Marketing typography | About/Journal/Contact/Pricing heroes exceed the 42-52px policy with 1.0 leading. |
| UX-020 | P2 | 1.00 | Audio proxy | Unsatisfiable GET range returns 502 instead of 416. |
| UX-021 | P2 | 0.98 | Reader semantics/mobile | Initial cover pages lack h1; controls clip at 320px; some tap boxes are too small. |
| UX-026 | P2 | 1.00 | Latency monitoring | Observer thresholds and `MONITOR_FAIL_ON_SLOW=false` can report green despite materially slow API cold paths. |
| UX-022 | P3 | 1.00 | Audit reproducibility | k6 is green, but Lighthouse/Web Vitals evidence is absent and the full audit is not one reproducible command. |

## API-to-UI Truth

The highest customer-visible contradiction is Library availability. `/api/books` returns 37 `LIVE_APPROVED`, reader-enabled records, but a static eleven-slug frontend gate redirects 26 of them to Contact. The same split hides both approved audiobooks from the approved-audio filter and labels them Audio Hidden, while their Book Detail routes correctly show Audiobook Approved and Listen in Reader.

The two approved book-summary APIs also report audio unavailable while their reader manifests report `enabled=true`, `APPROVED`, and `QA_PASSED`. Catalog and detail endpoints disagree on A Ghost Story identity/cover/format fields. Public summaries omit language, forcing regex inference.

## Release-Gate Truth

The production API/DOM boundary fails closed correctly:

- `book-2b9853ec52` and `a-ghost-story` are the only enabled manifests.
- Both approved endpoint-backed audio routes return `206`.
- `bn-066` is reader-enabled, audio-disabled, empty-provider/URL/assets, and its audio route returns `404`.
- Sampled D19/F5/Muchiram/Dracula/Pather routes remain audio-hidden.
- Static `/audio` probing, browser speech tokens, and non-approved AudioObject were not found in the deployed bundle/DOM.

Release truth is still **P0 red** because nine unapproved legacy objects are reachable directly from B2/Cloudinary. The current repository also cannot reproduce the safe deployed state from clean HEAD. Storage containment and clean-build reconciliation precede catalog or visual work.

Approved playback is not marked green: metadata and `206` passed, but the automated browser click did not advance `currentTime` and produced a browser-start toast. Treat this as a browser-gate gap, not proof that endpoint audio is corrupt, until a supported real-browser recheck settles it.

## Visual and Typography

Strengths: the paper/burgundy/gold palette, cover-first composition, restrained non-tour motion, calm shadows/radii, and zero requested-viewport document overflow are coherent and distinct.

The route floor is `6.4`, not `9.8`. Library is the weakest surface because truth, discovery, density, and approved-audio conversion all fail together. Reader defaults violate bilingual reading-size policy. Required webfonts are named but not delivered, so rendering depends on device fallback. Marketing heroes are oversized/tightly led. The approved 2b cover is visually placeholder-like and renders inconsistently between surfaces.

## Slideshow and Cards

The homepage slideshow advances automatically and manually; reduced motion stops movement. It has no persistent Pause control, hidden slides remain focusable, and its static card truth is stale. Library cards have a more severe state problem: badge, href, copy, and CTA are derived from different predicates.

## Navigation and CTA

The mobile menu opens/closes correctly at 390 and 430. Query-only filter navigation leaves it open and marks multiple links current. Reading Circle is inert. Listen in Reader drops listening intent and opens on a cover page with disabled audio controls. Production contact surfaces use `.org`; the dirty local source still contains `.in`, so a shared contact constant/build guard is required before deploying that branch.

## Accessibility

`axe-core 4.11.4` ran against requested critical routes at desktop and 390px. No a11y-green claim is valid.

- Serious: hidden carousel slide focus.
- Serious/manual: Reader modal focus containment.
- Serious/manual: imperceptible Contact focus and lost SPA focus.
- Serious: Pricing contrast `4.06:1`.
- Moderate: reader initial cover lacks h1; Book Detail/Pricing heading skips; Bengali language metadata gaps.
- Passes: no sampled missing image alt, no unlabeled native form controls, reduced motion works, and no requested-width document overflow.

## Performance

Latest main Regression, GO LIVE, and Post-deploy k6 workflows passed. The latest 100-VU, two-minute k6 run recorded:

- `33,360 / 33,360` checks passed;
- `0.00%` HTTP failures;
- overall p95 `1.08s`;
- catalog p95 `1.17s` against `1.20s`;
- reader p95 `1.06s` against `1.80s`.

The k6 workflow ended one second before Vercel completed, so it did not certify the newly deployed frontend SHA; nine of the prior fifteen catalog runs also missed the `1.20s` threshold. Cached Lighthouse `13.4.0` produced mobile lab snapshots of Home `98 / 2.235s LCP`, Library `87 / 3.864s`, and Reader `80 / 5.046s`. Library and Reader CLS were `0.068`, with zero TBT. Oversized cover delivery and a serialized Reader data/cover waterfall are the first evidenced optimization targets.

Field Web Vitals remain unavailable, so Core Web Vitals/performance 10/10 is not claimed. Performance fixes require repeated route-level lab runs plus field evidence; k6 thresholds must not be lowered to hide variance.

## First Fix Prompt

Run queue item 1, `P0_UNAPPROVED_AUDIO_STORAGE_CONTAINMENT`, as a dry-run inventory only. Remote storage mutation requires owner approval after the dry-run proves private-QA retention and isolates the two approved public audiobooks.

## No-Regression Guardrails

1. Public approved audio remains exactly `book-2b9853ec52` and `a-ghost-story` until new evidence passes.
2. `bn-066` remains public reader/audio-hidden.
3. No static `/audio`, browser speech, URL inference, estimated sync, or word-level sync claim.
4. No AudioObject for non-approved audio.
5. Reader availability and audio availability use separate evidence-backed predicates.
6. All unapproved direct media must be inaccessible, not merely absent from the DOM.
7. Clean committed source must reproduce production release truth.
8. No public `.in` contact email.
9. No private/generated media in `frontend/public` or `frontend/build`.
10. Do not claim Lighthouse, accessibility, or deterministic 10/10 green without measured evidence.
