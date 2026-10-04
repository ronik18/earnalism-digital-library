# Sprint Learnings

- Bengali reused local audio repeatedly failed manuscript match; do not rerun stale audio blindly.
- Bengali reader-only publication is a valid customer-facing outcome when content, rights, covers, and reader pass.
- OpenAI Bengali TTS has not met premium literary listening expectations; Sarvam remains promising but unproven for full release.
- Objective gates remain strict even with tiered listening and paragraph/stanza sync policy.
- Customer-facing book covers must never fall back to plain typography panels. Use approved graphical covers first and lightweight graphical runtime fallback only when source art is missing.
- Deterministic HTML text is safer than generated image text for covers because it avoids misspellings, supports Bengali/English typography, and prevents heavy raster churn.
- Homepage performance in the CRA shell is still constrained by client-render LCP; hero asset/font/background optimizations improved local Lighthouse from 66 to 90 but did not restore the requested >=94 guardrail.
- Indira's eight canonical chapters were compared against pinned 1873 Wikisource revisions; five apparent token mismatches were scan-confirmed page-boundary splits. This resolves text integrity only, not CC BY-SA distribution conditions or publication QA; keep the title unpublished until those independent gates pass.
- Muchiram's identified 1944 source exposes fourteen chapters while the repository package contains only two. Treat this as a concrete source-completeness hold, not a cover or underlying-term issue; never reconstruct the missing chapters.
- 2026-09-24 rapid catalogue triage: The Gift of the Magi is an India `FAST_GREEN` candidate. Because it was published under O. Henry's pseudonym, evaluate section 23 as well as section 22; both possible expiry branches are long expired. Current Project Gutenberg eBook 7256 story body exactly matches the canonical chapter after whitespace folding only. Its publication manifest is `READY_FOR_APPROVAL` with `exposed=false`; keep it outside the three-title `PILOT_FULL_FREE` scope until commercial cutover. Reader/audio release remains separate.
- 2026-09-24 rapid catalogue triage: A White Heron is India `FAST_GREEN`; Jewett's ordinary section 22 term expired after her 1909 death. The exact canonical story matches Project Gutenberg eBook 74980, *The Best Stories of Sarah Orne Jewett, Volume 2 (of 2)* (originally 1899; 1925 Mayflower printing), after whitespace/pagination folding only (normalized SHA-256 `88f400bb...92bf06`). The 1886 scan has three documented variants; the canonical text follows the identified 1925 edition, unchanged. Cather's preface and other compilation matter are excluded, and the evidence does not attribute individual wording changes to her. First-party cover provenance is supported by the owner-supplied design statement and internal asset audit. Corrected stale package state to unexposed/not live and audio disabled; prior audio QA/production evidence remains historical. Manifest is a commercial-cutover candidate, not part of the free pilot.
- 2026-09-24 rapid catalogue triage: classify Bankim Cohort 1 title-by-title instead of holding the cohort as one unit. Indira alone remains deterministic `FIX_AND_GREEN`; quarantine the five titles with exact substantive source/editorial blockers. Removed stale audio URLs/provider claims from all six held packages in both artifact roots without changing literary text or release state; add a checksum/live-admission regression test.

## Achievement-Aware Cost Governor - 2026-07-06T18:44:02.494690+00:00

- Added `achievement_ledger.json` to prevent rerunning achieved goals when source hashes are unchanged.
- Latest Bengali integration evidence supersedes older prompt state: all 31 route-live Bengali titles are reader-only approved/audio-hidden; the six former rights blockers are rights `PASS` and audiobook endpoints are hidden/non-200.
- Current graphical-cover and calm-type pass is visually safe and cover-complete, but current evidence-based UX index is 9.66 with Lighthouse performance 90/LCP 3.6s, so a new GREEN claim is not justified without a targeted performance fix.
- Sarvam/Bengali audiobook work remains deferred behind explicit paid/provider approval and higher-priority merge/performance blockers.

## Performance Rescue - 2026-07-07

- Do not trust an old GREEN UX score after cover/type source changes; rerun the specific active Lighthouse route only when performance is the blocker.
- The LCP regression was not caused by paid/generated covers. The solvable causes were the mobile hero image candidate, automatic first-visit tour timing, early idle prefetch/settings work, and an oversized header logo asset.
- Eager-loading Home into the main bundle was tested and rejected because it worsened Lighthouse; delaying noncritical work restored performance with less risk.
- Final local production-equivalent evidence: Lighthouse performance 96, LCP 2.7s, accessibility 100, SEO 100, cover audit 164/0 typography-only, visual smoke PASS, audio safety PASS.

## Bengali Audio Closure - 2026-07-07

- Sarvam `bulbul:v3` remains technically usable, but the `pooja` seed did not generalize to representative Bengali narration.
- Do not use an isolated 9.6 sample as release evidence. Representative evidence scored 7.9 with confidence 0.85 and list-reading/mechanical cadence red flags.
- Automated Bengali audiobook spend is paused under `AUDIO_PROVIDER_QUALITY_LIMIT_CONFIRMED`.
- Keep the 31 Bengali reader-only/audio-hidden titles protected. Do not rerun their production mutations unless regression evidence appears.
- Reopen Bengali audio only through a materially new provider/model, human/professional narration, licensed audiobook import, or manually approved representative sample set.


## Bengali Audiobook 9.2 Rescue - 2026-07-06T21:48:08Z

- Owner-approved `bengali_audiobook_acceptance_v2_92` reopened automated Bengali auditioning without relaxing objective gates.
- A grouping bug in the bakeoff summary previously mixed different style profiles for the same voice; style-aware aggregation is required for fair representative scoring.
- Sarvam `bulbul:v3` with `ratan` / `literary_warm_pacing` passed representative Bengali listening at 9.3 confidence 0.95 with no fatal flags.
- This is not a live audiobook: full-pilot TTS, ASR/manuscript, sync, upload/checksum, metadata, endpoint, and browser gates have not run.
- Continue with exactly one guarded pilot for `book-2b9853ec52`; do not scale to more Bengali audiobooks until that pilot passes all gates.

## Bengali Audiobook Campaign Activation - 2026-07-06T21:54:41Z

- Installed persistent Bengali audiobook campaign state and queue for 31 reader-ready titles.
- One title is representative-passed under `bengali_audiobook_acceptance_v2_92`: Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`, score `9.3`, confidence `0.95`.
- Full pilot is not live and must not be published until full-book listening, ASR/manuscript, measured sync, upload/checksum, metadata, endpoint, and browser gates pass.
- Duplicate attempt cache contains `192` prior passage/settings entries.
- No paid/provider/ASR/upload/metadata/production mutation calls were run in this activation.

## Bengali Full-Pilot Blocked - 2026-07-07T04:13:11Z

- Exactly one Sarvam full pilot was generated for `book-2b9853ec52` using `bulbul:v3` / `ratan` / `literary_warm_pacing`.
- The generated audio remains hidden and is not production-live.
- Objective ASR/manuscript verification failed after a newer text-only ASR retry: score `7.0199`, below the required `9.7`; first/last boundary checks failed and no word/segment timestamps were returned.
- Upload, metadata approval, endpoint exposure, and browser gates were not run.
- The TTS hook now strips source/frontmatter lines from future TTS-only Bengali narration text, but the current generated audio was produced before that fix and remains blocked.
- Do not generate a second repaired full pilot unless the owner explicitly approves a one-title repair run; do not scale to 3-title/10-title/31-title waves.

## Visual Brand System Hardening - 2026-07-07T04:54:30+00:00

- No customer-facing cover may rely on a typographic-only/plain fallback; deterministic graphical fallback is safer than generating large unreviewed raster assets.
- Front/back cover resolution now needs side-aware handling so detail and reader surfaces can show graphical backs even when a physical back-cover source is missing.
- Calmer typography can raise perceived premium quality without new libraries or assets when display maxima and card metadata tracking are reduced conservatively.
- Plain static serving is not production-equivalent for this CRA app because `/api` can fall back to `index.html`; use the same-origin static proxy for browser validation.
- Preview validation remains blocked by Vercel Deployment Protection unless an automation bypass secret or shareable link is provided.

## 2026-07-07T05:06:15.040184+00:00 Bengali ASR Forensics: book-2b9853ec52
- Current Sarvam full pilot remains blocked: the generated TTS input included author/source/publication frontmatter before the audiobook-clean opening.
- ASR weakness/no timestamps is real, but it is not enough to justify a by-construction publish while TTS input provenance fails.
- Keep ratan/literary_warm_pacing as the frozen repaired-pilot candidate because representative audition passed 9.3/0.95 and full-book generation was low cost.
- Next safe action: one repaired pilot or affected-group regeneration using stripped frontmatter, then rerun ASR/provenance/measured-sync/full-listening gates before any upload or metadata approval.

## Bengali Pilot Clean Group Repair - 2026-07-07T05:21:38.249911+00:00
- Root cause: opening Sarvam group contained author/collection/page/title-page frontmatter before the literary body.
- Code fix: Bengali TTS frontmatter stripping now removes the pilot title-page line when it follows source metadata, while preserving real comma-ended body stanzas.
- Repair path: regenerate group 0 only; reuse groups 1 and 2; planned clean sequence has 100% TTS input coverage and tts_by_construction_verified=true.
- Stop condition: paid Sarvam regeneration/listening/upload/metadata/browser gates were not run because explicit approval/budget envs are missing locally.

## Bengali ASR/Sync Hook Repair - 2026-07-07T05:47:51Z

- The owner-approved Railway repair regenerated group 0 and reused groups 1 and 2, but the factory still blocked at `asr_sync_lane` before listening/upload/metadata because Bengali ASR scored `1.0375` with mixed-script transcript and first/last boundary failures.
- Added a fail-closed TTS-by-construction path for Bengali only: it requires clean saved TTS input, chunk and final audio hashes, nonzero measured group durations, no stale/local/fallback TTS, first/final literary boundaries, and 100% clean manuscript coverage.
- Paragraph/stanza sync can now be written only from measured generated group durations with `auto_estimated_sync=false`; weak ASR is retained as diagnostic evidence, not hidden.
- Full listening QA remains mandatory before upload/checksum, metadata approval, endpoint exposure, or browser gate; this patch did not publish audio or mutate production.
- Local no-provider probe against `book-2b9853ec52_20260707T053510Z` now passes TTS-by-construction verification: coverage `100.0%`, canonical-to-clean-TTS match `1.0`, and first/last literary boundary pass.

## Bengali Pilot Audio QA PASS - 2026-07-07T05:54:36Z

- The repaired `book-2b9853ec52` pilot now passes `asr_sync_hook`: clean TTS-by-construction verification true, source match `10.0`, measured paragraph/stanza sync `PARAGRAPH_OR_STANZA_SYNC_PREMIUM`, and `auto_estimated_sync=false`.
- Bengali ASR remains weak (`asr_transcript_match_score=1.1258`) and is retained as `SUPPORTING_DIAGNOSTIC_WEAK`; it is not used as sole release proof.
- Full listening QA passed under `bengali_audiobook_acceptance_v2_92`: overall `9.4`, confidence `0.95`, no robotic/mechanical/list-reading/choppy/fallback fatal flags.
- The pilot is still not live: upload/checksum, metadata approval, audiobook endpoint, and browser gates have not run. Do not start 3-title canary or 31-title wave until this single pilot passes those final gates.

## Bengali Pilot QA Policy Repair - 2026-07-07T06:12:00Z

- The latest single-pilot resume advanced past ASR/sync and blocked in `qa_lane`, not because of audio quality, but because factory auto-QA still used 9.7 flagship thresholds for Bengali release audio.
- `build_auto_qa` now separates 0-1 listening confidence from 10-point release scores and applies `bengali_audiobook_acceptance_v2_92`: overall listening `>=9.2`, confidence `>=0.90`, and fatal red flags still block.
- The patch keeps objective gates strict: manuscript/content, rights, non-estimated measured sync, upload/checksum, metadata, endpoint, and browser still must pass before publish.
- The actual `book-2b9853ec52_20260707T053510Z` state now dry-evaluates to pre-upload QA PASS with no blockers: listening `9.4`, confidence `0.95`, overall release score `9.2`.
- Next action remains a single-pilot upload/metadata/browser resume only; do not rerun TTS, ASR, auditions, or start a 3-title canary until this pilot is production-live.

## Bengali Pilot Final Gate Blocked - 2026-07-07T07:27:10Z

- `book-2b9853ec52` upload/checksum passed using the repaired Sarvam audio and measured paragraph/stanza sidecars.
- The metadata hook needed two final-gate fixes: preserve Sarvam provenance instead of hardcoding OpenAI, and reset partial audiobook metadata before the book-rights PUT so retries are idempotent after a partial production write.
- Production metadata now accepts the Sarvam audio payload, but the public audiobook endpoint still returns `404`; browser gate was not run and the pilot is not live.
- Do not rerun TTS, ASR, sync, provider bakeoff, listening QA, or canary waves for this blocker. The next safe action is backend deploy/restart or controlled-launch/audio-route refresh, then resume metadata/browser only.

## Bengali Pilot Endpoint Materialization - 2026-07-07T07:43:30Z

- Admin API sees `book-2b9853ec52` with Sarvam provider metadata and all five uploaded assets; direct storage HEAD checks pass.
- Public `/api/books/book-2b9853ec52`, `/api/reader/book/book-2b9853ec52`, and `/api/reader/book/book-2b9853ec52/audiobook` still return `404`.
- Diagnosis: root `data/controlled_launch.json` contains the pilot in live/audio allowlists, but packaged `backend/data/controlled_launch.json` does not; the deployed backend truth gate hides the slug before endpoint/browser gates can run.
- Do not use `railway up` from the current dirty workspace. Prepare a clean backend data/source deploy, or implement a release-gate-aware route resolver, then resume metadata/browser only.

## Homepage Figma Alignment - 2026-07-07T10:45:00Z

- The live Dracula-first problem was partly source and partly static shell: `frontend/public/index.html` and `frontend/scripts/generate-static-seo-snapshots.mjs` can reintroduce stale homepage positioning even after React source is corrected.
- Production-equivalent smoke must catch runtime page errors; the leftover `readingPassUrl` reference made the hydrated home root empty until fixed.
- Plain static serving can return `index.html` for `/api/books/:slug`; book detail pages must validate API payload shape before accepting it as a book.
- The approved homepage direction is hybrid editorial hero plus three action cards. Dracula is acceptable as an English Classics tile, but not as the global headline or header CTA.
- Release-gate-safe audiobook copy should be explicit: no default A Ghost Story probe, no audio CTA unless manifest/endpoint evidence proves approval.
## 2026-07-07 Figma Home/Library/Reader UX Pass

- The live production shell can lag behind source and still present Dracula-first SEO/static copy even when local source has been corrected; future audits must distinguish live deployed state from source state.
- Library discovery needs language and availability controls to make Bengali reader-ready titles feel intentional instead of hiding behind a Dracula-controlled launch taxonomy.
- Reader audiobook UI must say `Section-following narration` or `Paragraph/Stanza Sync` for paragraph/stanza releases; never imply word-level sync unless sidecar evidence supports it.
- Small muted-gold text on ivory can fail Lighthouse contrast. Use a darker text-safe gold for overlines and brand taglines while keeping muted gold as an accent.
- PostHog must remain opt-in via `REACT_APP_ENABLE_POSTHOG=true`; first-party funnel events should use the sanitized allowlisted analytics helper.
- DARK_PREMIUM_PUBLIC_SYSTEM_V1 keeps public surfaces coherent without inferring conversion metrics: absent an approved public-safe aggregate with cohort, sample, period, exclusions, calculation version, and reviewer approval, render only verified operational facts.
- EARNALISM_GILDED_BURGUNDY_V1 changes colour authority only: replace green public-surface values with the controlled burgundy, beige, and gold roles while preserving layout, CTA, product-truth, and analytics-fallback contracts.

## 2026-07-07 Parallel Go-Live Acceleration

- Backend endpoint materialization for `book-2b9853ec52` is no longer the active blocker: live API detail/manifest expose the approved pilot audio, the audiobook endpoint returns `206`, and a non-pilot Bengali sample remains audio-hidden.
- The active Bengali pilot blocker is browser/frontend: the production frontend bundle does not render the current reader-manifest audio controls, so the factory browser gate cannot see controls or measure audio start latency.
- PR87 is ship-ready by GitHub/Vercel/protected-preview evidence, but PR87 does not include `Reader.jsx` or `audioReleaseSafety.js` reader-manifest audio support; merging it alone is unlikely to publish the Bengali pilot.
- The requested `bengali_reader_only_rights_repair.py` path is absent in this workspace. Existing intelligence says the six previously blocked slugs were already repaired, with 31 reader-only approved and 0 rights blockers, so no production mutation should be repeated without regression evidence.
- The next 3 Bengali canary candidates are prepped only. Do not start canary TTS until the pilot browser gate passes; two candidates need audiobook-clean opening/frontmatter stripping before representative auditions.

## 2026-07-07 Bengali Audiobook Pilot Live

- `book-2b9853ec52` is now production-live as the first Bengali audiobook; total audiobook-live count is `2`, Bengali audiobook-live count is `1`.
- The final blocker was not audio quality, upload, metadata, or endpoint availability. It was production frontend/readiness tooling: the live bundle needed approved reader-manifest audio rendering, and the browser hook needed non-eval polling plus metadata readiness before scoring latency.
- The release factory had stale blocker accumulation on resumed runs. Passing metadata/browser evidence must clear stale blocker categories before final QA recomputation, and published go-live evidence must be refreshed after the state is marked published.
- Production release truth remained intact: the pilot endpoint/browser gate passed, while sample unapproved Bengali title `book-ac5a71075e` remained audio-hidden.
- Do not rerun this pilot’s TTS, ASR, sync, upload, or metadata. The next productive action is source cleanup/PR for the frontend reader patch and factory/browser hook patches, then owner-approved 3-title canary prep.

## 2026-07-07 Repo Hygiene Clean Integration Rule

- Dirty workspace is no longer an acceptable unresolved blocker by itself. Classify every changed/untracked path into source/test/policy/report/content/evidence/generated/cache/secret/owner-review categories, then work from a clean source-only worktree.
- The clean integration worktree is `/private/tmp/earnalism-source-only-clean-integration` on branch `sprint/source-only-clean-integration`.
- Validation passed in that clean worktree: Python release factory checks, backend route tests, `npm ci`, audioReleaseSafety, frontend build, cover audit, visual smoke with real Playwright browser execution, and `git diff --check`.
- Do not promote dirty `frontend/package-lock.json` drift without reviewing `package.json`; in this run it broke `npm ci` by removing Playwright lock entries required by `origin/main`.
- `frontend/public/sitemap.xml` is a generated validation side effect. Restore it before source-only promotion unless intentionally reviewed.
- Future deploys and production mutations must run from clean source-only worktrees. The original workspace may retain local evidence, rollback payloads, and imported content inputs, but it must not be used for deploy unless `git status --short` is source-only and intentionally staged.

## 2026-07-08 Parallel Prelaunch Unblock

- Created a lock-aware prelaunch daemon state without running paid TTS.
- `bn-066` remains representative-audition-ready only; full TTS still requires representative pass and explicit full-TTS approval.
- `pather-panchali` remains blocked for audiobook by source-scope and cover repair gates.
- HOME UX is the only approved phase; LIBRARY requires a new owner approval record.
## 2026-07-07T20:15:11Z - HOME UX review stabilization

HOME owner-review validation should use phase-scoped visual smoke (`EARNALISM_VISUAL_PHASE=HOME`) when reviewing only `/`. Full route smoke remains required before final integration, but local plain static servers can 404 deep links without proving production route failure. Paid TTS stayed blocked by active `paid_tts.lock`.
## 2026-07-07T20:18:27Z - HOME validation rerun

HOME-scoped visual smoke rerun passed 9/9 viewport checks with zero blockers. Full multi-route smoke remains a separate final-integration check against production-like routing, because plain static servers can 404 deep links. Paid TTS remained blocked by active lock.
## 2026-07-08T03:12:59Z - LIBRARY phase local review pattern

The Library phase can preserve truthful Bengali visibility in a static owner-review build by using deterministic local reader-only fallback metadata sourced from canonical public_book records. This keeps release truth intact while `/api/books` is unavailable. Phase-scoped smoke for `LIBRARY` should remain separate from the default full-route smoke.

## 2026-07-08T03:50:54Z - LIBRARY approval gate

LIBRARY owner approval must be recorded as a phase transition, not a launch-green claim. The next phase is BOOK_DETAIL discovery only; full preview/production route validation, paid Listen campaign approval, and paid TTS remain separate gates.

## 2026-07-08T05:37:51Z - BOOK_DETAIL phase local review

- Book Detail should use shared `audiobookReleaseState(publicBook)`-backed presentation logic, not ad hoc slug/title/language/static-URL inference.
- Local Book Detail review fixtures must fail closed for audio; production-approved audio display remains dependent on the detail API carrying approved evidence or a future shared manifest evidence path.
- Reader-first detail pages should frame availability as a complete reading edition, not a missing audiobook.
- BOOK_DETAIL-scoped visual smoke passed 108 route/viewport checks with zero blockers, but full preview/production validation and paid Listen evidence remain separate gates.

## 2026-07-08T05:55:30Z - BOOK_DETAIL approval and READER discovery

- BOOK_DETAIL owner approval is a phase-transition approval only: it freezes HOME, LIBRARY, and BOOK_DETAIL for progression, activates READER discovery, and does not approve launch, paid Listen, paid TTS, or production mutation.
- Reader discovery found two release-truth risks to address before review: browser/system speech fallback code remains in `Reader.jsx`, and static `/audio/...` derivation must not expose stale audio without explicit approved manifest assets.
- The background audiobook lane is read-only blocked by active legitimate `paid_tts.lock`. A historical `.audiobook_pipeline.run.lock` records PID `40472`, but that process is not running; do not classify this as safe to resume while paid_tts.lock has no allowed next holders.

## 2026-07-08T06:31:11Z - READER implementation ready for owner review

- Reader release truth must be source-enforced: remove public browser/system speech fallback and static `/audio/...` derivation instead of merely hiding controls.
- Reader local smoke should use explicit reader fixtures that fail closed for audio; validated state is no audio controls, no generated audio element, no static audio source, visible reader-ready/audio-hidden copy, settings reachable, TOC reachable, and no mobile horizontal overflow.
- Mobile Reader may collapse long audio-hidden explanatory copy into a compact "Reading edition available" chip, but smoke must still require an audio-unavailable element and keep audio controls/elements/static sources fail-closed.
- READER visual smoke passed 90/90 route/viewport checks. AUDIOBOOK_PLAYER remains blocked until explicit owner approval.

## 2026-07-08T06:48:52Z - READER approval and AUDIOBOOK_PLAYER discovery

- READER owner approval is a phase-transition approval only; it freezes READER for progression and activates AUDIOBOOK_PLAYER discovery without approving launch, paid Listen, paid TTS, production mutation, or player implementation.
- Active Reader, Book Detail, Book Card, and Approved Audiobook Spotlight paths are release-state gated; no new audio UI was introduced in the approval transition.
- Legacy `AudioPlayer.jsx` and `AudioPlayer 2.jsx` remain static `/audio/...` and word-level timestamp risks if reconnected. The AUDIOBOOK_PLAYER implementation phase should quarantine or rewrite them before adding any public player UI.
- `paid_tts.lock` remains active and legitimate, with no allowed next holders; no Sarvam/TTS/audition/canary/publish work was run.

## 2026-07-08T07:13:35Z - AUDIOBOOK_PLAYER implementation ready for owner review

- Public player code must be approval-evidence-driven and fail closed; static same-origin audiobook paths are explicitly rejected by `audioReleaseSafety`.
- `AudioPlayer 2.jsx` was removed, and `AudioPlayer.jsx` no longer derives slug/language static audio paths, claims word-level sync, or exposes browser/system speech fallback.
- The service worker must not cache `/audio/...` as a static asset; approved audio should come from current manifest/release evidence.
- AUDIOBOOK_PLAYER visual smoke passed 108/108 route/viewport checks with zero blockers; only the approved pilot fixture exposed audio controls, while A Ghost Story, Bengali canaries, Pather Panchali, and reader-first titles remained audio-hidden.

## 2026-07-08T07:36:52Z - BRAND_HEADER_LOGO experiment ready for owner review

- Brand/header work should remain a separate `BRAND_HEADER_EXPERIMENT`, not a SETTINGS or AUDIOBOOK_PLAYER phase transition.
- The public header now uses deterministic text for a proofreader-style `LEarnalism` lockup and preserves the existing bundled icon asset as the fixed left anchor.
- The default public badge is a safer India-inspired tricolor literary badge; the exact Indian flag variant exists only for owner/compliance review and is not the production default.
- BRAND_HEADER_LOGO visual smoke passed 27/27 route/viewport checks across Home, Library, and Book Detail with zero blockers, and no paid audio, release-gate, or audiobook exposure behavior changed.

## 2026-07-08T10:02:29Z - AUDIOBOOK_PLAYER approval and SETTINGS discovery

- AUDIOBOOK_PLAYER owner approval is a phase-transition approval only; it freezes AUDIOBOOK_PLAYER and activates SETTINGS discovery without approving launch, paid Listen, paid TTS, or production mutation.
- SETTINGS discovery found Reader settings inline in `Reader.jsx`, with theme, font size, line spacing, reading width, Bengali/English font mode, focus mode, reduced motion, and highlight intensity already represented.
- Next SETTINGS implementation should address preference persistence, settings-sheet focus management, mobile wrapping/overflow, and state announcement before owner review.
- `paid_tts.lock` remains active and legitimate with no allowed next holders; no Sarvam/TTS/audition/canary/publish work was run.

## 2026-07-08T10:14:19Z - SETTINGS implementation ready for owner review

- Reader Settings can stay inline for this phase, but persistence belongs in a pure helper (`readerSettings.js`) so invalid local values are sanitized before reaching UI state.
- Settings owner review should verify calm grouping: Reading tone, Typography, Bengali comfort, Focus and motion, and Highlights.
- SETTINGS smoke now opens the panel across reader routes, verifies focus containment, selected states, reset visibility, mobile overflow safety, and no audio leakage.
- MARKETING_LANDING remains blocked until explicit SETTINGS owner approval; no preview/deploy or Vercel work was run.

## 2026-07-08T10:36:13Z - BRAND_HEADER_LOGO approval recorded

- BRAND_HEADER_LOGO approval is a scoped brand experiment approval, not a UX phase transition or launch approval.
- The Editorial Proofreader lockup is approved with the safer tricolor literary badge as the public default.
- The exact Indian national flag variant remains compliance-review-only and is not approved for production default.
- SETTINGS remains the active owner-review-gated phase; no audio release gates, paid TTS, paid Listen, deploy, preview, or publication state changed.

## 2026-07-08T11:26:02Z - SETTINGS approval and MARKETING_LANDING discovery

- SETTINGS approval is a phase-transition approval only; it freezes SETTINGS and activates MARKETING_LANDING discovery without approving launch, paid Listen, paid TTS, preview/deploy, or production mutation.
- MARKETING_LANDING discovery found Home, Micro-story, Pricing, About, Contact, Journal, Header/Footer, SEO, JsonLd, controlled launch fallback, and Approved Audiobook Spotlight as the relevant marketing surfaces.
- Current release-truth copy is mostly safe, but implementation should fix stale Dracula-first SEO/About language, the controlled-launch "audiobook private review" wording if surfaced, the support email mismatch, and any nonfunctional Notify Me affordance.
- `paid_tts.lock` remains active and legitimate with no allowed next holders; no Sarvam/TTS/audition/canary/publish work was run.

## 2026-07-08T12:32:38Z - MARKETING_LANDING ready for owner review

- Marketing copy should convert through bilingual literary trust, not Dracula-first positioning; default SEO and About now name Bengali and English classics directly.
- Public audio language on marketing surfaces should say evidence-gated/hidden unless approved, not private-review playable.
- Fake conversion affordances are release-truth risks: the Shelf II `Notify Me` button was replaced with a real `Request Update` contact path.
- MARKETING_LANDING smoke needs local static SPA fallback and harmless marketing API mocks for review builds, but full/default smoke remains strict.
- MARKETING_LANDING is ready for owner review; FINAL_INTEGRATION remains blocked until explicit approval.

## 2026-07-08T12:45:05Z - MARKETING_LANDING contact truth correction

- Owner-confirmed `sales@reoenterprise.org` is the canonical public contact/sales email; `sales@reoenterprise.in` is a trust blocker and must not remain in public contact paths.
- Public contact, footer, pricing support copy, social mailto defaults, marketing truth tests, visual smoke source checks, and MARKETING_LANDING SEO evidence now use `.org`.
- This correction does not approve MARKETING_LANDING, FINAL_INTEGRATION, preview/deploy, paid Listen campaigns, paid TTS, or release-gate mutation.

## 2026-07-08T12:55:46Z - MARKETING_LANDING approval and FINAL_INTEGRATION discovery

- MARKETING_LANDING owner approval is a phase-transition approval only; it freezes MARKETING_LANDING and activates FINAL_INTEGRATION discovery without approving preview/deploy, production validation, paid Listen, paid TTS, or launch-wide 10/10.
- FINAL_INTEGRATION must reconcile source-only staging, generated artifact exclusion, full-route smoke, preview/production route proof, Lighthouse/accessibility/SEO, release-gate truth, public contact email, and Vercel readiness.
- Vercel CLI was discovered at `54.15.1`; upgrade to the latest CLI should happen later before preview/production validation, not during this discovery-only gate.
## 2026-07-08 - FINAL_INTEGRATION Stage A source-only validation

- FINAL_INTEGRATION strict/default visual smoke was strengthened to cover the release-candidate route matrix rather than relying on phase-scoped smoke.
- Local source-only validation passed: npm ci, frontend tests, build, cover audit, UX governor check, strict full-route smoke 189/189, and git diff whitespace checks.
- Preview/production validation remains unproven and must stay a separate owner-authorized gate.
- Vercel CLI remains outdated at 54.15.1; upgrade to latest/54.21.1+ should happen before preview/production validation, not during source-only reconciliation.
- `frontend/public/sitemap.xml` is generated by build and should be explicitly reviewed or excluded before source-only staging.
## 2026-07-07 Bengali Post-Go-Live Stabilization

- `book-2b9853ec52` remains the first live Bengali audiobook: endpoint/manifest/sidecars/browser were already PASS, with Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`, listening `9.4`, confidence `0.95`, and `PARAGRAPH_OR_STANZA_SYNC_PREMIUM`.
- The stale detail-page copy was a frontend evidence-merge bug: `/books/book-2b9853ec52` exposes `audiobook_enabled=true`, while release/QA/audio endpoint evidence lives in `/reader/book/book-2b9853ec52/manifest`.
- Source fix: `BookDetail` now enriches the book detail payload from the reader manifest, and `audioReleaseSafety` treats `manifest.audio.url` as a valid approved audio asset. Approved detail copy becomes `Audiobook available`; unapproved Bengali editions keep reader-safe copy.
- Source preservation is complete for the reported factory/browser hook files: hashes in the clean integration branch match the original workspace, so no additional source promotion was required.
- Canary preflight is now prepared-only ready with `muchiram-gurer-jibanchorit`, `book-d19e96859f`, and `book-f5d593e1f4`. `book-2ddbed8293` remains skipped because the clean branch lacks a public controlled-publication source package and production API returns `404`.
- `book-4968248842` is skipped for canary until source/title provenance is reviewed because its clean audiobook body opens with `সংস্কার` while the public title is `বলাই`.
- PR #88 is open at `https://github.com/ronik18/earnalism-digital-library/pull/88`, stacked on `codex/source-only-clean-integration`. Do not merge/deploy stabilization before resolving the source-only base and owner approval.
- Do not run canary TTS until PR #88 production verification passes and owner approval/budget env vars are present.

## 2026-07-07 PR88 Dependency + Canary Readiness

- Source-only base PR #89 is merged into `main` at `04583c6a5d762d6f880ed68038102e0cdf332af4`; PR #88 can now target `main` after its regression patch is pushed.
- The failing PR #88 regression was a stale test expectation, not a homepage source regression: `scripts/e2e_regression.mjs` still waited for retired Dracula-first selector `hero-dracula-card`.
- The regression gate now checks the approved current homepage contract: hybrid editorial hero, three curated action cards, Bengali Classics visible, Dracula as an English Classics action tile, and release-gate-safe Approved Audiobooks copy.
- The 3-title Bengali canary remains prepared-only: `muchiram-gurer-jibanchorit`, `book-d19e96859f`, and `book-f5d593e1f4`. Do not run canary TTS until PR #88 is merged/deployed and production detail-copy verification passes.

## 2026-07-11 bn-066 Public Audio Hide Hotfix

- Public book metadata already hid `bn-066` audio, but the reader manifest still exposed legacy B2/Cloudinary assets because `can_expose_audio` trusted live/audio allowlists without checking `approval_evidence.json`.
- Provider-backed assets and a manifest version are not release approval. Backend manifests and frontend controls now require explicit `PUBLIC_AUDIO_RELEASE_APPROVED` plus passing QA evidence.
- Keep `bn-066` in the live reader allowlist while removing it from both audio allowlists and scrubbing legacy public audiobook fields; do not delete chapters or private QA artifacts.
- Bump the controlled-publication truth-gate cache version whenever release semantics change so Redis cannot preserve stale public manifests after deployment.
- Reader-manifest ETags must include release gate, QA, sync, and truth-gate semantics. Redis invalidation alone is insufficient because browsers can otherwise keep an older manifest body after a `304 Not Modified` response.
- Version frontend manifest request URLs with the release-truth schema. This gives deployed clients an immediate cache boundary when a legacy ETag has already escaped into browser caches.

## 2026-07-12 A Ghost Story Production Release And The Open Window Queue Continuation

- A Ghost Story reached production `Yes + Yes` only after Google Studio-C full narration passed ASR/source `9.88`, first/last checks, and six listening samples at `9.4-9.5`, then B2 checksum, ranged endpoint, manifest, frontend, and production gates passed.
- When release semantics change, bump both backend truth-gate and frontend manifest-request cache versions; otherwise a valid new publication can remain hidden behind a stale manifest body.
- Do not treat in-app media-start failure as title-specific when the same runtime behavior reproduces on an established approved control and both media elements are fully buffered with valid `206` endpoints.
- The Open Window proves provider success is title-specific: Studio-C passed A Ghost Story but scored `8.0-9.4` on baseline Saki passages and `8.5-9.5` after one prosody retry.
- The Open Window twilight transition remains the precise blocker. Do not repeat either Studio-C fingerprint, do not reuse the Piper asset, and do not start full TTS until a fresh representative voice passes every passage.

## 2026-07-12 The Open Window Studio-B Final Audition

- The final bounded Studio-B representative audition scored `9.4`, `9.5`, `7.2`, and `9.4`; the twilight transition introduced robotic texture and mechanical cadence fatal flags.
- Studio quality is title- and passage-specific. Studio-B did not solve the Studio-C twilight weakness and regressed that passage from `8.5` to `7.2`.
- Do not repeat the Studio-B fingerprint `7d8546bba92729e05ba82f665d084c9d7e81cc30d567494ff21c300551dfa5f6` or publish any failed Google/Piper candidate.
- Stop automated Google retries for The Open Window. The cheapest safe alternate path is a source-bound human narration or licensed-audio candidate followed by complete ASR, listening, manifest, endpoint, frontend, and production validation.
- Estimated Stage 2E spend was `$0.2178`; actual provider billing was not reported; the lock restored byte-for-byte.
- Parallel agents can safely audit rights, sanitation, existing assets, and repair commands, but paid provider lanes and publication metadata remain serialized through their locks and the governor must verify every returned gate.

## 2026-07-12 Stage 2F Human Narration Handoff And D19 Preflight

- After repeated provider failures on the same passage, a complete source-bound human narration packet is a real executable repair state, not a dead-end audio-hidden status. It must include delivery, QA, provenance, and exact received-audio validation requirements.
- Do not plan group-only regeneration when the prior chunk manifest and audio files are unavailable. Reject unverifiable reuse and re-estimate a clean full-title regeneration.
- Bengali TTS sanitation must inspect both source frontmatter and trailing standalone edition years. D19's trailing `১২৯৮?` was source residue even though the prior sanitation summary said PASS.
- A title-specific representative sample may authorize only its exact slug/provider/model/voice/style arm. Require explicit opt-in plus score `>=9.2`, confidence `>=0.90`, and no fatal flags; do not generalize the arm catalog-wide.
- D19 non-paid preflight passed at 6,485 prepared characters and five groups; all paid runtime gates were absent, so no lock acquisition or provider call occurred.

## 2026-07-13 Sprint 1 Paid Run Reconciliation

- D19 (`book-d19e96859f`) Google `bn-IN-Chirp3-HD-Aoede` passed private TTS, listening, and measured paragraph/stanza sync: six listening samples scored `9.4` at confidence `0.95` with no fatal flags.
- D19 raw audio-derived ASR/source is `0.6838`, below the strict `>=9.7` gate. The static TTS-by-construction audit score of `10.0` is provenance evidence only and must not be treated as an ASR pass.
- D19 remains audio-hidden in `AUTOMATED_ASR_ARMS_EXHAUSTED_NORMALIZATION_REPAIR_REQUIRED`. Google `latest_long` is unsupported for `bn-IN`; OpenAI `gpt-4o-transcribe` with explicit `bn` peaked at `6.7606`; prior Google default and OpenAI mini arms also stayed below `9.7`. Do not repeat these fingerprints.
- Do not start a Bengali three-title canary or broader wave unless D19 raw ASR/source reaches `>=9.7` and D19 then publishes through every remaining gate.
- Muchiram plateaued after full-book weak passages and bounded targeted/slow repairs; `book-f5d593e1f4` repeated the same punctuation-heavy weakness with Google Aoede and Sarvam Pooja. Both are now `HUMAN_NARRATION_REQUIRED`, with reader-only/audio-hidden state preserved.
- Sredni Vashtar, The Gift of the Magi, and The Tell-Tale Heart all plateaued across their current Google attempt families. No failed English audition authorizes full TTS or publication.
- Contextual English risk sampling fixed false contextlessness in the judged sample selection, but it did not manufacture a pass; the sub-threshold scores remain release blockers.
- Paid calls were serialized. Conservative estimated Sprint 1 spend is `$9.75400`; actual provider billing remains unknown. `paid_tts.lock` was restored byte-for-byte.
- Next generated prompt: `Coordinator: assign one bounded ASR language-configuration repair on existing D19 private audio with an explicit ASR cap and an untried language/model fingerprint. Do not regenerate TTS, repeat listening QA, upload, mutate metadata, or publish; require raw audio-derived ASR/source >= 9.7 before proceeding.`

## 2026-07-13 D19 Stage 2G Sarvam Full-TTS Fail-Closed QA

- A passing representative audition does not guarantee full-title listening quality. D19's Sarvam Pooja full candidate passed generation but three of six samples scored `8.0`, confidence fell to `0.85`, and list-reading rhythm was fatal.
- Raw audio-derived ASR must remain authoritative. The Stage 2G verifier now prevents a `10.0` construction audit or prepared-text boundary check from substituting for raw ASR/source `1.3504` and failed first/last boundaries.
- After Google and Sarvam both fail distinct release gates, another automated retry is not the cheapest safe action. The durable next track is source-bound human narration or licensed audio with the same full QA contract.
- Stage 2G estimated spend is `$0.4226`; cumulative Sprint estimate is `$10.1766 / $175`. Actual provider billing remains unknown.
- No upload, publication, release-state mutation, or public Listen exposure occurred. The lock restored byte-for-byte.

## 2026-07-13 Désirée's Baby Stage 2H Network Recovery And Representative QA

- A provider attempt blocked before synthesis remains retryable; once network recovery produces audio, its completed provider/voice/rate/text fingerprint must be judged and then treated as non-repeatable if quality fails.
- `dsires-baby` Google `en-GB-Studio-C` at `0.94` pacing generated four valid private source-bound samples, but listening scores were `9.4`, `8.4`, `7.5`, and `9.4`; minimum confidence was `0.85` and the risk passage triggered fatal robotic texture and mechanical cadence.
- A successful provider API call is not a representative-audition pass. No full TTS, ASR, upload, release mutation, or publication followed the failed quality gate.
- Stage 2H conservatively estimates `$0.23616` and raises the Sprint checkpoint to `$10.41276 / $175`; actual billing remains unknown and `paid_tts.lock` restored byte-for-byte.
- The cheapest safe next action is one materially different `en-GB-Chirp3-HD-Achird` audition. If it fails, stop automated Google retries and create a source-bound human narration or licensed-audio packet.

## 2026-07-13 Sprint 1 Autonomous V2 Short-Title Queue

- Two materially different Google voice families can still plateau title-by-title. A clean API response or isolated `9.4` sample does not authorize full TTS when any representative passage is below the all-samples threshold.
- Stop after two failed voice families. `the-cop-and-the-anthem`, `the-last-leaf`, `the-masque-of-the-red-death`, `dsires-baby`, `the-necklace`, and `the-yellow-wallpaper` now require source-bound human narration, licensed audio, or a genuinely new provider family; their completed fingerprints must not repeat.
- `the-monkeys-paw` demonstrated why full-candidate QA remains necessary after a passing audition. Its ASR/source and first/last gates passed, but full listening failed; one targeted ending repair fixed the local defect and exposed two different weak samples. Do not publish or keep looping on isolated segments.
- Private generated audio belongs outside the repository. Only manifests, lock reports, QA evidence, and narration/import packets are retained.
- Paid execution stayed serialized and the shared lock restored byte-for-byte. Conservative estimated spend is `$14.90614 / $175`; actual provider billing remains unknown.
- No new public audio was approved. Production truth remains exactly `book-2b9853ec52` and `a-ghost-story` until external candidates complete the full release pipeline.

## 2026-07-13 Sprint 1 Autonomous V3 Reconciliation

- A release-catalog dry run must distinguish audiobook-use authorization from public-audio release approval. Explicit owner scope can permit future source-bound production while `PUBLIC_AUDIO_RELEASE_NOT_APPROVED` keeps manifests and UI fail closed.
- Runtime graphical cover evidence is acceptable only when the audited front/back pair is content-themed, non-typographic, present, and unbroken; a generic placeholder must not satisfy the cover gate.
- Radharani's stale public audio metadata was failed closed. Nishkriti still has an externally reachable unapproved storage object even though API and UI exposure are disabled; storage revocation is a separate cleanup gate.
- Devdas, Kshudhita Pashan, Radharani, and Nishkriti now pass non-paid source, rights, sanitation, and graphical-cover preflight. Bengali paid scaling remains prohibited until the D19 pilot gate and campaign-specific caps open.
- Jekyll and Hyde now has a hash-bound private input with 138,182 characters, but Google ADC requires interactive reauthentication. No provider call, lock mutation, upload, or public release occurred.
- The clean main baseline does not contain bn-066's private 152-chunk run or calibration tool. A private preflight planned six bounded ASR calls only; it did not execute them because the active lock scope and campaign policy do not authorize this branch to do so.
- Removing stale audio URLs from controlled metadata is necessary but does not revoke a known direct storage URL. At least nine historical Cloudinary/B2 MP3 variants across six unapproved titles remain directly reachable and require a separately reviewed destructive-storage workflow.

## 2026-07-14 Sprint 1 Direct Audio Source Cleanup

- Sprint 1 retention-first storage containment completed before source cleanup; runtime cleanup did not perform remote mutation or audio production.
- The 23-record authoritative checklist had baseline drift: two listed root mirrors were absent and two backend mirrors held the effective records. Reconcile the current tree before editing rather than manufacturing missing mirrors.
- F5 and Muchiram contained stale direct MP3/sidecar packages plus historical approval flags that contradicted their actual hidden release state. Both runtime mirrors and approval mirrors now fail closed while their human-narration paths remain intact.
- Alice and Nishkriti had no remaining direct URL but retained stale provider, voice, and asset-slug metadata. Empty those fields so hidden manifests cannot inherit misleading provenance.
- Preserve the exact evidence-gated B2 packages for `book-2b9853ec52` and `a-ghost-story`; approved source references are not part of the unapproved cleanup.
- Post-cleanup controlled-publication serialization has exactly two enabled audio manifests and 30 hidden manifests with empty public audio fields.

## 2026-07-14 EOD Go-Live Freeze And Sredni Reuse Stretch

- A fully QA-passing reuse candidate is still not production-public until the merged backend reaches production and the manifest, proxy, Book UI, and Reader UI pass there. Source approval and production availability must remain separate states.
- Sredni Vashtar passed reuse QA with ASR/source `9.8426`, six listening samples at `9.4-9.5`, confidence `0.95`, no fatal flags, measured sync `9.7997`, and verified sidecars/checksums without new TTS.
- Railway archive upload HTTP `500` is a deployment blocker, not a reason to mutate release truth. Production correctly remains audio-disabled and proxy `404` while the source-ready package waits for retry.
- EOD go-live can be approved for all public readers and existing approved audiobooks when every unapproved title remains fail-closed; incomplete audiobook backlog alone is not a P0 launch blocker.
- Sprint 1 storage containment and source cleanup removed the earlier direct-object bypass blockers. Do not carry superseded revocation requirements forward in title matrices.
- The k6 run had `18,792/18,792` functional checks and `0%` request failures; catalog and reader p95 misses are a separate non-P0 performance backlog and do not justify unrelated changes in an audio release closure.

## 2026-07-17 Premium Dynamic Sprint 1 Home Hero

- Homepage curation should reference canonical slugs and project title, author, covers, reader availability, and audio approval at request time; editorial ordering must not duplicate catalog truth.
- Cover eligibility is a separate hero-visual gate. Reader-enabled books with missing canonical covers stay readable but are omitted from premium visual placement.
- A listening mockup is safe only when it consumes the approved-audiobook shelf; the same UI must fall back to generic listening-room copy when no approved title exists.
- Mobile visual QA is strongest when the exact CSS viewport is measured for overflow and broken images, then paired with a fixed-size rendered frame screenshot.
- The legacy Dracula-only backend catalog tests are stale against the current 32-reader baseline and should be modernized separately; do not distort the hero implementation to satisfy obsolete launch assumptions.
- Browser regression fixtures must evolve with an owner-authorized hero contract: assert the exact dynamic headline, six canonical slugs, cover alt text, approved-audiobook collection route, and the single approved phone listening link instead of retaining a retired static-headline assertion.

## 2026-07-17 Premium Home Hero Deployment Closeout

- A green workflow wrapper is not proof that Railway deployed: the deploy job can pass after its secret check while checkout, CLI installation, and deployment are skipped.
- Vercel production and its canary passed, but production hero completion must remain blocked while `/api/home/curated` is 404.
- Repeated Railway `Failed to create code snapshot` HTTP 500 failures occur before build and do not replace the healthy production instances; stop rather than loop.
- Production audio truth remained stable throughout: the three approved audiobook routes returned 206 and tested hidden-audio routes returned 404.

## 2026-07-17 Reference-Accurate Dynamic Hero Follow-up

- A supplied desktop artwork can be the fast LCP layer without sacrificing semantics: keep headings, alt text, real links, keyboard focus, and responsive mobile markup in React while using transparent hit areas over painted controls.
- “Pixel-perfect” must yield at title-specific regions to catalog truth. Opaque canonical cover/device masks preserve the composition while preventing invented or mismatched books from leaking into public UI.
- URL reachability does not prove cover semantics. Visual inspection caught the canonical `a-ghost-story` object identifying a different book, so the title stays audio-approved but is excluded from hero imagery.
- A generated canonical boot snapshot gives deterministic first paint and prevents an unavailable curation endpoint from emptying the production hero; successful endpoint data still replaces the snapshot.
- Synchronous `matchMedia` rendering prevents the 227 KB desktop reference WebP from being requested on mobile, while Cloudinary width transforms keep dynamic cover downloads proportional to their slots.
- Browser regression fixtures should read the generated canonical home snapshot and assert `data-book-slug` placements; duplicating old featured-book arrays and retired CSS selectors creates false failures and can silently reintroduce rejected cover metadata.
- The production snapshot fallback behaved as intended: frontend deployment and canary passed, `/api/home/curated` remained 404 after Railway skipped deploy, and the customer hero still rendered its full truth-gated catalog stage.

## 2026-07-19 The Open Window Production Audio Closeout

- A 10.0 aspiration must not replace the authorized release contract. This title shipped on measured listening `9.4` against cutoff `9.2`, ASR/source `10.0`, coverage `1.0`, measured paragraph sync `10.0`, confidence `0.95`, and no fatal flags; no public 10.0 listening claim was made.
- Private-object existence is not delivery proof. The release bound all five B2 objects to exact hashes and sizes, retained anonymous HTTP `401` at origin, and exposed them only through release-gated same-origin/API proxy routes.
- Production reader-truth caches need an explicit version bump when controlled audio state changes; query-string cache busting alone did not invalidate the persisted generation cache.
- Browser playback gates must advance past cover/front-matter pages before expecting an enabled Play control, and CSP-safe polling is required because production forbids `unsafe-eval`.
- DOM visibility was insufficient: final proof required real Play interaction, `currentTime` advancement, `144.4 ms` click-to-play, exact AI narration disclosure on Book and Reader, and zero console errors.
- Vercel protected previews can fail with identity-provider `403` while the application build is sound. Promote only the immutable READY deployment after source/unit/build validation, then run the definitive public-domain browser gate.
- Railway code-snapshot failure can occur before build even for a minimized backend-only upload. After two identical pre-build failures, retain the healthy deployment, preserve the exact failure IDs, and publish the validated source/evidence branch instead of looping or weakening release truth.

## 2026-07-19 The Gift of the Magi Kokoro Representative Pilot

- A new provider family must still be title-bound. The Gift pilot pins the current controlled manuscript, four exact representative passages, Kokoro model/config/voice hashes, the local Whisper hash, and a non-repeated attempt fingerprint.
- Shared ASR prompts can create false trailing speech. The initial prompt caused a high-no-speech `Thank you` hallucination on the sacrifice passage; a bounded ASR-only repair used a passage-specific prompt policy and preserved the original failed transcript as evidence.
- Source-equivalent ASR notation may be normalized only when the sound and canonical wording are identical. The accepted transformations were `$1.87` to `one dollar and eighty-seven cents` and `your` to the source dialect spelling `yer`; unexpected speech was never discarded.
- All four representative passages reached audio-derived ASR/source `10.0`, coverage `1.0`, exact first/last boundaries, and no missing, duplicated, reordered, or unexpected content without regenerating audio.
- Independent listening passed the English premium screen with per-passage overall scores `9.6`, `9.6`, `9.5`, and `9.5`, confidence `0.95`, and no fatal flags. Exact `10.0` was not observed and is reported honestly; the weakest dimension was pacing at `9.2`.
- The active listening floor is `9.2`, so exact `10.0` must not become an unnecessary gate for the next private stage. Gift is eligible for one new full-scope private pilot, while remaining audio-hidden until full-title objective, sync, listening, risk, editorial, delivery, endpoint, browser, and publication gates pass.
- A representative platform pass is not a full audiobook release. No full title, measured full-title sync, upload, endpoint, browser proof, or public Listen state was created; the title remains reader-live and audio-hidden.
- Local Kokoro synthesis and Whisper ASR cost `$0.00`; four listening judgments were capped at `$0.20`, with actual provider billing not reported. `paid_tts.lock` was restored byte-for-byte.

## 2026-07-19 The Cop and the Anthem Kokoro Representative Pilot

- Objective fidelity and listener quality are independent gates. The final four Kokoro samples reached ASR/source `10.0`, coverage `1.0`, exact boundaries, and complete ordered-content integrity after a bounded decoder-only repair, but this did not authorize full-title generation.
- Prompted Whisper produced trailing hallucinated speech on the dialogue passage. An unprompted beam-10 decoder removed the false tail without modifying audio or deleting unexpected text; the earlier failed transcripts remain preserved.
- Independent listening scored the four samples `8.7`, `8.3`, `9.5`, and `9.5`; minimum overall was `8.3`, confidence `0.85`, pacing and emotional expression `8.0`, with no fatal flags.
- Because the Kokoro `af_bella` configuration failed both the English premium screen and the owner exact-10 target, close it rather than tuning the same fingerprint. Only a materially different provider, voice, or source-bound narration lane may reopen the title.
- No full title, measured sync, upload, endpoint, browser proof, or public Listen state was created. The reader remains live and audio stays hidden.
- Local Kokoro and Whisper cost `$0.00`; four listening judgments were capped at `$0.20`, actual provider billing was not reported, and `paid_tts.lock` was restored byte-for-byte.

## 2026-07-19 Désirée's Baby Kokoro Representative Pilot

- Strict ASR initially rejected four narrow proper-name, spelling, compound, and token-boundary differences. A bounded ASR-only repair normalized exactly `L’Abri`/`Laubry`, `mamma`/`mama`, two `finger-nails`/`fingernails` occurrences, and the `Désirée’s. It` boundary; no text was deleted and the WAVs were not regenerated.
- The repaired audio-derived reports all reached ASR/source `10.0`, coverage `1.0`, exact first/last boundaries, and complete ordered-content integrity. Original transcripts and alignment operations remain preserved in `asr_history`, and the repair fingerprint cannot repeat.
- The listening run is not a valid four-sample scorecard: three judgments explicitly said no audio was provided, so their numerical zeroes are transport-invalid and must never be represented as narration scores.
- The one audible maternal-dialogue judgment independently raised fatal robotic texture, mechanical cadence, choppy joins, and fallback-like TTS flags. That is sufficient to close this exact Kokoro `af_bella` configuration without paying to repeat the same listening fingerprint.
- No full title, measured sync, upload, endpoint, browser proof, or public Listen state was created. The title remains reader-live and audio-hidden.
- Local Kokoro and Whisper cost `$0.00`; the four attempted listening judgments were capped at `$0.20`, actual provider billing was not reported, and `paid_tts.lock` was restored byte-for-byte.

## 2026-07-19 The Necklace Kokoro af_sarah Representative Pilot

- Material voice difference is necessary but not sufficient. The checksum-bound `af_sarah` voice is distinct from `af_bella`, yet the title still failed strict content integrity before listening.
- A bounded ASR-only repair removed a prompted extra `women` without deleting transcript content and accepted only exact-count theatre/theater, Mathilde/Matilde, paste/paced, and five-hundred/500 acoustic or orthographic equivalents.
- Invitation dialogue and loss panic passed ASR/source `10.0`, coverage `1.0`, and exact ordered integrity. Opening remained `9.9631`/`0.9926` because `had` was missing; the final remained `9.8605`/`0.9815` because opening `I` was missing and source `is` decoded as `has`.
- Beam and greedy decoders produced the same remaining content discrepancies, so another decoder loop is not justified. Those words were not normalized because they are not sound-equivalent evidence.
- No listening, full title, upload, endpoint, browser proof, or release mutation ran. The exact synthesis and repair fingerprints are closed and the title remains audio-hidden.

## 2026-07-20 The Gift of the Magi Kokoro Full-Title Objective Gate

- The bounded private af_bella run generated all 19 losslessly partitioned sections and a 647.825-second recomposed WAV with SHA-256 `c352f9cd960eb37cea37e79fc4d6f288088ea8a07ccc8574b4c8ecc34c5d01cb`; local Kokoro and Whisper cost `$0.00`.
- Aggregate ASR/source reached `9.9545`, coverage `0.9952`, and precision `0.9957`, but exact ordered integrity remained false. Eight sections failed, including real substitutions such as `appertaining/appurting`, `pier/pure`, `I'm me/I mean`, `want to/wanna`, and `'em/them`; these were correctly forbidden from normalization.
- Sections 003, 015, and 017 also contained zero-length audio-derived word timestamps. Numeric section-sync aggregation reached `9.8131` with coverage `0.9813`, but sync correctly failed because exact content and valid timestamp binding are mandatory.
- High aggregates cannot compensate for source substitutions, missing words, duplicate or unexpected words, or invalid timestamps. The full-title and bounded ASR-repair fingerprints are closed, and the af_bella lane must not be retried.
- Six-sample listening, upload, endpoint, browser validation, and publication did not run. The private WAV remains outside public folders and Gift remains reader-live/audio-hidden.

## 2026-07-20 The Last Leaf Kokoro af_sarah Representative Pilot

- Execution first stopped before synthesis because fallback-free G2P could not resolve 12 source-authentic Behrman dialect spellings. Exact deterministic phoneme bindings resolved that preflight blocker without changing the 432-character passage or its hash, and the failed pre-fix fingerprint was closed.
- The new hash-bound af_sarah run generated four private representative WAVs at zero provider cost. Opening passed ASR/source `10.0` and coverage `1.0`; a bounded unprompted decoder also repaired the final reveal to `10.0/1.0` by removing duplicated `it`, while exact-count `to-day/today` was treated as an orthographic equivalent.
- Johnsy still scored `9.8611/0.9861` but failed exact integrity because source `Sudie` decoded as `suitie`. The Behrman dialect passage scored `8.6957/0.8642` with multiple unresolved proper-name and content substitutions, including `Vy do` decoded as `Vite` and `in` decoded as `and`.
- The repair correctly refused to normalize genuine `do/de`, `in/and`, trailing hallucinated speech, or duplicated content. Only two of four passages passed, so the af_sarah synthesis and repair fingerprints are closed.
- No listening, full-title generation, delivery, endpoint, browser, or publication stage ran. All WAVs remain private, the paid lock is unchanged, and The Last Leaf remains reader-live/audio-hidden.

## 2026-07-20 The Gift of the Magi Kokoro bf_emma Alternative Pilot

- The checksum-distinct British `bf_emma` voice passed fallback-free G2P and generated a new four-passage private candidate at zero provider cost. This was a materially different voice/fingerprint, not a repeat of the closed af_bella lane.
- Prompted ASR initially retained trailing `this` and `the end`; both unprompted decoder arms removed the opening hallucination, and the greedy arm removed `the end`. No transcript content was manually deleted.
- Opening and sacrifice passed ASR/source `10.0/1.0`. Hair sale remained `9.6552/0.9655` because `Sofronie` and `practised` decoded as `Saffroni` and `practiced`; the ending remained `9.8776/0.9758` because both arms omitted source phrase `these two were`.
- British `chilly/chilli` was the only new exact-count sound-equivalence allowance. Substantive `were/are`, missing source words, and trailing speech were never normalized away.
- Only two of four passages passed exact content integrity, so listening and all downstream stages were skipped. The bf_emma synthesis and ASR-repair fingerprints are closed; Gift remains audio-hidden.

## 2026-07-20 The Masque of the Red Death Kokoro bf_emma Representative Pilot

- A new checksum-bound British `bf_emma` lane generated four private passages at zero provider cost; no existing Google or Kokoro fingerprint was repeated.
- The bounded retained-WAV repair produced scores `9.7959`, `10.0`, `9.902`, and `9.8824`, with coverages `0.9796`, `1.0`, `0.9902`, and `0.9882`. Only the black-room passage preserved exact ordered source content.
- Opening omitted `an hour` and added trailing `thank you`; the clock passage decoded manuscript `harken` as `hearken`; the finale decoded `mummer/cerements` as `mamma/serments`. These genuine content differences were not normalized away.
- Mean ASR `9.8951` and mean coverage `0.9895` cannot override three exact-integrity failures. Listening and every full-title or delivery stage were skipped, the synthesis and repair fingerprints are closed, and the title remains audio-hidden.

## 2026-07-20 The Tell-Tale Heart Kokoro bf_emma Representative Pilot

- The British `bf_emma` preflight resolved all four source passages with fallback disabled, then generated four private WAVs through the exact pinned local Kokoro runtime at zero provider cost.
- Initial ASR passed opening and heartbeat exactly, while bedroom added trailing `you` and the finale added `thanks for watching`. A single bounded retained-WAV repair removed the bedroom hallucination without deleting transcript text.
- Opening, bedroom, and heartbeat then reached exact `10.0/1.0`. Both bounded finale decoder arms retained `thanks for watching`, producing `9.8605/1.0`; unexpected decoded speech was not manually trimmed or normalized.
- Mean selected ASR `9.9651` does not satisfy ordered-content integrity when one passage contains unexpected words. Listening, full-title generation, upload, endpoint, browser, and publication were skipped; both fingerprints are closed and the title remains audio-hidden.

## 2026-07-20 B2 Live Audio Storage Cleanup

- Catalog truth currently binds four live audiobooks to twenty exact B2 objects: one MP3 plus timestamps, VTT, chapters, and metadata for each title.
- Public playback is range-capable through the Earnalism reader API. All four MP3 routes returned HTTP `206`, all sixteen sidecar routes returned `200`, and sampled hidden-audio routes remained `404`.
- The primary `earnalism-audiobooks` origin was anonymously reachable, while the separate `earnalism-private-qa-audio` origin correctly returned `401`. Historical repository references must not justify retaining a non-live object in the public-origin bucket.
- A version-ID-bound cleanup removed 42 non-live public-origin versions totaling 7,396,374,442 bytes with zero errors. The post-delete inventory contains only fifteen exact live objects in the primary bucket and no further deletion candidate.
- The five Open Window live objects and 249 referenced campaign-evidence versions remain in the private bucket. They are not public-origin clutter: they are anonymous-inaccessible working evidence for release-gated playback and the remaining audiobook campaign.
- A zero-live allowlist is always a hard blocker. The initial inventory exposed a partial-mirror loading issue, performed no deletion, and was replaced by a self-contained controlled-artifact load plus a non-empty allowlist gate.

## 2026-07-22 Sprint 1 Bengali scope and Radharani private reuse screen

- The current Sprint 1 catalog is deterministic: the first ten slugs in `backend/data/home_hero_curation.json` are Bengali. One (`book-2b9853ec52`) is live with audio and nine are reader-live/audio-hidden. The legacy 31-title Bengali queue is broader historical planning evidence and must not be reported as the current Sprint 1 target.
- Radharani is the best next one-title canary because source, text rights, sanitation, direct front/back covers, and reader availability pass, while its source-bound Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing` opening and dialogue audition scored `9.4` at confidence `0.95` with no fatal flags.
- A retained private MP3 matched SHA-256 `4de991f9afc420037ec09683aa4b53e4e62de8a4ae782ebdfb766ec48bb18a56`. That proves candidate identity only. Its retained metadata records `provider=command` and `bn-IN-TanishaaNeural`; no exact paid Azure generation transaction or subscription binding was found, so generic provider terms cannot establish rights for this exact asset.
- A bounded 60-second multilingual Whisper-medium screen failed as an evaluator: it partly recognized the opening phonetically, shifted script, then collapsed into repeated characters. Classify this as `OFFLINE_ASR_TOOL_INADEQUATE_NOT_SOURCE_MISMATCH`, never as evidence that the book is wrong and never as a substitute for the mandatory audio-derived `9.7` score.
- Existing Radharani sidecars are not release evidence because they contain empty cues or estimated timing. Measured paragraph/stanza sync remains mandatory.
- The next safe path is one fresh, source-bound Radharani Sarvam full-title canary only after every explicit campaign approval/budget variable and a Radharani-scoped idle lock are present. The wrapper now refuses to synthesize approvals, rejects stale slug scope, and cannot start a full factory in dry-run mode.
- No provider call, upload, metadata mutation, endpoint exposure, browser release, or publication ran; spend was `$0.00` and `paid_tts.lock` was untouched.

## 2026-07-22 Radharani source-bound full-title canary

- The source-bound Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing` arm produced 28 fresh groups and a 3,563.116-second private MP3 with SHA-256 `defeb886a990c68d297770f5d61c1ee239683c114fe06346751296a81f9476d8`. This proves deterministic generation, not release fidelity.
- Raw OpenAI `whisper-1` with automatic language produced mixed-script output and failed decisively: score `1.0962`, coverage `0.1096`, token order `0.1033`, and both first and last boundaries false. Construction or phonetic projection must never replace this raw audio-derived gate.
- A materially different bounded `gpt-4o-mini-transcribe` calibration with explicit Bengali improved Bengali-script ratios to `0.9875` and `0.9882`, but source scores were only `7.9085` and `9.0441`; the middle ending boundary failed, and the ending sample hit `insufficient_quota`. Do not run full corrected ASR from this arm.
- Google credentials were present but two bounded ADC token probes hung; classify Google as `ADC_REFRESH_UNAVAILABLE_NOT_STARTED`, not provider-ready. No Google paid ASR ran.
- Estimated completed provider work was `$0.7363`; actual billing was not reported. The authoritative lock restored byte-for-byte to Radharani-only idle SHA-256 `24f5a1751ab3124898c0d5436e75ff7ea0244ef6f82718dcb4c461b3b2c3e482`.
- Radharani stays reader-live/audio-hidden, its production audiobook route remains HTTP `404`, and no listening, sync, upload, metadata, browser, or publication stage ran after the ASR failure.

## 2026-07-23 Radharani zero-cost local Whisper medium diagnostic

- The installed multilingual Whisper `medium` model was bound by SHA-256 `345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1`, Whisper `20250625`, torch `2.13.0`, explicit language `bn`, and a single fixed CPU decoder with temperature zero, beam size five, no temperature fallback, no source prompt, and word timestamps enabled.
- The opening, middle, and ending audio hashes matched the fresh Sarvam group evidence. The process was killed with exit `137` during group 0 before JSON, transcript, or timestamps were emitted; groups 13 and 27 did not start.
- `/usr/bin/time` was killed before it could emit an exact wall time. The last process snapshot proved at least 37 seconds elapsed, 255% CPU, and 14.4% process memory on a 16 GiB host. Do not invent a score or runtime beyond this evidence.
- Classify this exact local Whisper medium/bn fingerprint as unsuitable for Radharani audio in the current runtime. Do not repeat it or run decoder-tuning loops. Cost was `$0.00`, no provider call ran, and `paid_tts.lock` stayed byte-identical.

## 2026-07-23 Radharani Saaras ASR closeout and Nishkriti source repair

- Saaras v3 `transcribe` on fresh opening, middle, and ending groups produced diagnostic normalized scores `9.776`, `9.818`, and `9.737`, phonetic scores `9.936`, `9.898`, and `9.883`, and coverage `0.9936`, `0.9898`, and `0.9883`. Raw scores remained only `8.6275`, `8.8971`, and `8.7179`; projection cannot replace the raw 9.7 release gate.
- Strict reanalysis found unexplained missing/extra phonetic spans in all three calibration samples. The historical group-0 pass is superseded: group 0 is raw `8.6275` with two missing and three extra spans, while group 1 is raw `8.3099`, normalized `9.606`, with four missing and five extra spans. Zero attempted groups pass the current policy, so no listening, delivery, or publication stage ran.
- Saaras `transcribe` and a distinct `verbatim` calibration returned measured clip segments, not release-valid word timestamps. The adapter now rejects segment timing when word timing is required; it must never label those segments as word-level or measured paragraph/stanza sync.
- Zero-cost Whisper base scored only `3.416` with coverage `0.3416`, and stable-whisper base failed to align `141/191` words with mean probability `0.0758`. These exact local fingerprints are closed. Conservative Radharani spend is `$0.8895`; actual provider billing is not reported, the production endpoint remains `404`, and the paid lock returned to idle.
- Nishkriti's source resolver previously stopped at an empty root controlled-publication record. The passage builder now deterministically falls back to the canonical backend record, yielding nine chapters, 83,247 manuscript characters, and four hash-bound passages without a provider call.
- Paid Sarvam calls now enforce every campaign approval and positive budget environment variable at the provider boundary. The calibration and full runners bind runner, adapter, and normalizer hashes, conservatively count attempted error calls, reject outputs outside `internal/`, and require the raw 9.7 score plus normalized, phonetic, boundary, and zero-gap predicates.
- Nishkriti is the next bounded canary. Its four-passage artifact is now persisted and hash-verified, but a lock-serialized one-second OpenAI `gpt-audio` probe returned `429 insufficient_quota`. No synthesis ran; restore billing/quota or approve a different independent audio judge before one bounded audition. Do not generate a full title, widen to other Bengali books, or expose audio based on text construction alone.

## 2026-07-23 Live audiobook public-contract reconciliation

- Production returned `audio_enabled=false`, `audiobook_enabled=false`, and `audio_status=NOT_AVAILABLE` from `/api/books/book-2b9853ec52` while the same title's reader manifest returned `audio.enabled=true`, `release_gate=APPROVED`, and `qa_status=QA_PASSED`.
- The inconsistency came from the public book projection forcing every live title's audio fields closed, plus legacy top-level `false` flags in the checked-in reader manifests for all four already-approved audio slugs.
- Public book audio truth must be derived from the existing controlled audio allowlist and release/QA evidence. Raw database booleans, an MP3 URL, or an allowlist entry without approval are insufficient.
- Approved book-detail responses now expose only the gated reader API proxy URL and public release/QA status; raw B2 asset URLs remain stripped. Hidden titles still return false flags, an empty URL, and no approval fields.
- Static reader-manifest flags now match the four approved live audio contracts in both artifact trees, with updated manifest checksums. Revoked or incomplete approval evidence makes those flags fail validation closed.
- No provider call, regeneration, upload, publication, release-gate change, private-audio access, or paid-lock mutation occurred.

## 2026-07-23 Bounded release-pipeline unblock

- The release factory and release-packet builder previously spoke different evidence schemas. A provider-free normalizer now follows raw ASR, listening, measured-sync, upload/checksum, metadata, endpoint, browser, and explicit `lock_restored=true` evidence before atomically emitting the builder's three required documents. A factory `PASS` label alone is insufficient.
- Google Gemini-TTS is now an explicit, opt-in provider lane. The adapter keeps canonical text byte-for-byte, separates delivery direction from source text, enforces Cloud TTS byte limits, validates MP3 output, writes private hash-bound QA-required manifests, and requires both provider approval and title/campaign caps before ADC or synthesis.
- The Google project and authorized-user ADC are detected, but the refresh token is still blocked by `invalid_rapt`. Interactive `gcloud auth application-default login --project=earnalism` is the single external action that can unlock both Gemini-TTS auditions and the independent Vertex listening judge. No synthesis ran while that evidence was unavailable.
- The Monkey's Paw retained B2 object now has a plan-bound, private-only SHA-256 retrieval path. Its filename and title do not prove identity; only an exact match to the repaired candidate hash may advance to fresh QA. Anonymous ranged access correctly returned `401`, and no private audio entered frontend assets.
- `book-edfcf810c5` now has its exact existing graphical Cloudinary cover pair linked in both controlled-publication mirrors. Devdas remains cover-blocked because the retained back cover has overlapping, unreadable Bengali copy; do not begin its audio release lane until a legible matched pair passes.
- Production truth remains 32 public readers and four public audiobooks. All new provider, normalizer, and private-media work stayed source-only or preflight-only; no hidden title gained a public Listen surface.

## 2026-07-23 Bengali reader sanitation and Gemini/Vertex title pilots

- Vertex listening QA and Gemini 2.5 Pro TTS are operational. The silence probe returned a structured zero-score rejection instead of a transport error, proving the independent judge path works without pretending silence is audio.
- Canonical reader frontmatter was removed and all dependent hashes were rebound for `bn-066` (46 chapters, 770 characters), `book-d19e96859f` (54 characters), `book-edfcf810c5` (63 characters), and `book-f5d593e1f4` (73 characters). Their reader availability and audio-hidden state did not change.
- `book-2b9853ec52` has a similar reader-facing wrapper but was excluded because it already has a live, source-bound audiobook. Changing it safely requires one atomic source, audio evidence, sync, delivery, and runtime migration.
- Nishkriti failed representative generalization with Sarvam Ratan scores `9.4/5.5/0/0` and Gemini Charon scores `9.5/7.0/0/0`. Kshudhita Pashan failed three corrected-source Gemini voices with `9.3/9.0/5.5/0`, `5.8/0/0/0`, and `8.8/9.4/7.5/0`.
- Devdas remained cover-blocked and its two bounded Gemini diagnostics failed at `9.2/5.5/0/0` and `9.4/5.5/0/0`. Running even bounded audio diagnostics before repairing that known cover blocker was unnecessary; do not repeat them.
- Adaptive stopping prevented any full-title generation, upload, release-gate mutation, or publication. Isolated high scores never overrode fatal robotic, mechanical, list-reading, or repeated-ending flags.
- The completed provider, model, voice, style, and text-hash fingerprints are closed. The next audiobook attempt must be a genuinely different provider or voice, or source-bound narration, and must still pass raw audio ASR/source, measured sync, delivery checksum, endpoint, and browser gates.

## 2026-07-23 Railway CI and post-deploy load-test ordering

- Railway correctly detected merge `ce7f1edd` and held it in `WAITING`, but the workflow named `Post-deploy k6 smoke test` also ran on the same `push` event before Railway could deploy because `Wait for CI` was enabled.
- The production smoke portion passed 15/15 checks. The 100-user run passed all 17,664 functional checks with a 0% request failure rate, but the previous deployment missed the strict catalog p95 target (`2.48s` vs `1.2s`) and reader p95 target (`2.24s` vs `1.8s`).
- Do not relax those latency targets and do not use the failed old-deployment run as evidence for the new commit. Remove the `push` trigger, keep manual dispatch, and run the unchanged test only after Railway reports the target commit as `SUCCESS`.

## 2026-07-23 Controlled reader artifact precedence

- Production validation found that the reader manifest reflected the newly repaired controlled-publication packet while the chapter endpoint still returned an older MongoDB chapter body. Cache-busting did not help because the endpoint itself preferred the database whenever any content existed.
- Public controlled readers must resolve book access metadata, chapter versions, and chapter bodies from the same canonical artifact. A stale database copy may be used only as a fail-safe when the controlled artifact is unavailable; admin preview remains database-first.
- Incrementing the reader truth-gate cache namespace is required whenever source precedence changes, otherwise Redis may continue serving the old body for up to the chapter cache TTL.
- Focused reader and audio-truth coverage passed 31/31. The change does not alter audiobook approval, QA, storage, metadata, or public Listen state.
- Preview response caches must include the resolved content version in their key. Caching only by slug and chapter lets an unversioned request seed a fallback-version response that is later reused for a manifest-versioned request, even when the body itself is canonical.

## 2026-07-26 Sprint 1 audiobook acceptance v3.90

- The owner lowered only the active overall listening floor from `9.2` to
  `9.0`. Confidence remains `>=0.90`; per-dimension floors, anti-robotic and
  anti-choppy protections, and every fatal-flag rejection remain unchanged.
- Objective release truth is unchanged: ASR/manuscript must remain `>=9.7`,
  coverage `>=0.98`, first/last/order integrity must pass, sync must be
  measured, and rights, covers, checksum, metadata, endpoint, browser, and
  empty-blocker evidence are still mandatory.
- The policy transition creates zero newly release-ready Sprint 1 titles.
  A 9.0 representative sample can authorize only a private full-title pilot;
  it cannot approve public release or expose Listen.
- Historical `bengali_audiobook_acceptance_v2_92` evidence remains immutable.

## 2026-07-27 Home v4 controlled-artifact precedence

- Production Home v4 dropped `book-2b9853ec52` from its approved-audiobook rail and reported only 19 live contracts even though the independent book endpoint still proved its audiobook `APPROVED` and `QA_PASSED`.
- `BOOK_SUMMARY_PROJECTION` intentionally excludes audio release fields. Treating a same-slug database summary as complete prevented the canonical controlled artifact from loading and let incomplete database state shadow release truth.
- Home now overlays validated controlled artifacts for every controlled slug. Only whitelisted editorial fields survive from the database; reader, rights, cover, audio, and QA truth remain artifact-governed.
- The Home cache key must rotate whenever truth precedence changes. Otherwise Redis may continue serving the regressed payload after correct source is deployed.
- Offline reconstruction proves all 32 Sprint 1 readers and the exact four approved audiobooks, with 87 focused tests passing and no audio gate, media, or paid-lock mutation.

## 2026-07-27 The Gift of the Magi VoxCPM2 v3.90 adversarial closeout

- The previously promising VoxCPM2 int8 reference-only opening was not enough to authorize a full-title run. Under the active v3.90 policy, a distinct section-013 adversarial sample was generated from the exact controlled source and an AI-generated, non-person reference voice.
- The sample passed local source-blind Whisper medium.en at `10.0`, coverage `1.0`, exact first/last/order integrity, and valid audio-derived word timestamps. This proves text fidelity for the exact audio hash; it does not prove premium listening quality.
- Independent `gpt-audio` listening QA scored the sample `8.5` overall with confidence `0.92`, and raised `robotic_texture_detected` plus `choppy_joins_detected`. Anti-robotic was `8.4` and anti-choppy was `8.5`, both below the unchanged `9.2` floors.
- Close VoxCPM2 int8 for Gift. Do not generate the other representative samples or the full title with this fingerprint. The next attempt must use a materially different commercially permitted model family. Audio remains private and hidden; no upload, release mutation, or publication occurred.

## 2026-07-27 The Gift of the Magi terminal Qwen3 Base closeout

- The pinned Apache-2.0 Qwen3-TTS 0.6B Base MLX 8-bit checkpoint generated one exact controlled section-013 sample with an AI-generated non-person reference voice.
- The lossless 24 kHz mono PCM-16 output is validly decodable, SHA-256 `da573f24abea837e30a5a8b2ac9d1082f692c66661f17a2e3589840bd29729bf`, and 67.68 seconds long, but 1.417947 percent of samples are full-scale clipped.
- Clipping is irreversible waveform loss, not a harmless validator mismatch. Do not normalize it into a false pass, regenerate this fingerprint, run ASR/listening on it, or widen to representative/full-title generation.
- Gift has exhausted its bounded local synthetic families. Its deterministic next state is source-bound narration or licensed-audio delivery through the existing packet, followed by every unchanged full-title release gate. Public audio remains hidden.

## 2026-07-28 Deterministic Sprint 1 conveyor and Call of the Wild preprovider stop

- The 32-title conveyor now has only five explicit routes: four production-live
  titles, eighteen source-bound-delivery titles, nine titles with one bounded
  four-passage candidate, and one prerequisite-repair title. No title can enter
  an indefinite try-another-model state.
- The finite cap is one new synthetic family, one targeted repair, one
  post-representative full generation, one post-full section repair, and zero
  repeated failed fingerprints per title.
- The Call of the Wild is the first bounded title. Its exact source-bound
  `en-GB-Chirp3-HD-Achird` candidate passed preflight at 2,119 characters and
  an estimated `$0.06357`.
- Both execution starts stopped before a provider call: the first selected
  environment lacked the Google client, and the corrected environment proved
  the Railway-bound authorized-user ADC needs reauthentication. No synthesis
  call ran, the attempt remains unused, actual spend is `$0.00`, and the paid
  lock restored byte-for-byte.
- Listening QA now acquires and restores the paid lock and enforces the active
  v3.90 overall, confidence, per-dimension, anti-robotic, anti-choppy, and fatal
  flag gates. Public audio remains hidden.

## 2026-07-28 Sprint 1 audiobook acceptance v3.89 and Call of the Wild closeout

- The owner lowered only the active overall listening floor from `9.0` to
  `8.9`. Confidence remains `>=0.90`; ordinary dimensions remain `>=8.9`;
  anti-robotic and anti-choppy remain `>=9.2`; fatal flags still disqualify.
- ASR/manuscript remains `>=9.7`, coverage remains `>=0.98`, exact
  first/last/order and measured sync remain mandatory, and rights, covers,
  checksum, metadata, ranged endpoint, browser playback, and an empty blocker
  list remain unchanged.
- The cutoff audit found zero newly full-title release-ready titles. A
  representative score at or above `8.9` can authorize one private full-title
  pilot only; it cannot expose Listen.
- The Call of the Wild consumed its single synthetic-family attempt with four
  private OpenAI `gpt-4o-mini-tts` / `verse` clips. Raw ASR scores were
  `9.6032/9.5000/9.7041/9.5849`, coverage was below `0.98` throughout, and
  exact ordered-content integrity failed throughout. Listening QA and
  full-title generation were correctly skipped.
- The exact Call fingerprint
  `14717669863b52b3aadb2476a6d00e13bfff9b64acc0a965a901809b57683c5d`
  is closed. The title remains audio-hidden and moves to exact rights-cleared
  source-bound delivery. The paid lock restored byte-for-byte.

## 2026-07-28 The Secret Garden bounded Kokoro closeout

- The cover-ready, 27-chapter title used one zero-provider-cost Kokoro
  `bf_emma` candidate with British G2P at speed `0.96`.
- Four representative passages reached exact ASR/source `10.0/1.0`. Independent
  v3.89 listening passed with minimum overall `9.0`, confidence `0.92`,
  anti-robotic `9.3`, anti-choppy `9.2`, and no fatal flags.
- A chapter-one checkpoint prevented wasteful generation of chapters 2-27.
  Its initial aggregate ASR was `9.9161`, but exact order and measured sync
  failed. The single permitted retained-WAV ASR repair left unexpected speech,
  including `The End` and `Thanks for watching`, and measured sync remained
  `9.6262`, below the unchanged `9.7` objective gate.
- The two exact fingerprints
  `a9d329844e54e425fc578f3f4469b934ae85e8ec288223a270309f2bd1eba8fd`
  and
  `8f7221a8d5a5f5a2e446e8f0725eab00f93efbc8695b6f5967111739af7a68a8`
  are closed. Never delete or normalize unexpected speech to manufacture a
  pass. Keep the title audio-hidden and route it to exact source-bound
  delivery.
- No provider synthesis cost, upload, publication, or release-gate mutation
  occurred. Four private `openai:gpt-audio` listening judgments had a maximum
  estimate of `$0.20`; actual billing was not reported. The paid lock remains
  idle and unchanged.

## 2026-07-28 Alice bounded Kokoro closeout

- Alice was the shortest cover-ready Sprint 1 English title with no prior
  synthetic attempt. One four-scene Kokoro `bf_emma` candidate used British
  G2P, speed `0.97`, pinned model revision
  `f3ff3571791e39611d31c381e3a41a3af07b4987`, and exact controlled source
  SHA-256
  `c8cd98430bcaa621dd206b8d3c880b34ca3daf4776e4b89c8a10d8c5f84cb2d3`.
- The retained-WAV repair produced ASR/source scores
  `10.0/9.9408/10.0/10.0` and coverage
  `1.0/0.9882/1.0/1.0`. The `arm-chair`/`armchair` tokenization was a bounded
  source-equivalent pass, but the Caterpillar dialogue still omitted one
  repeated source token `I` under both decoder arms.
- Aggregate ASR above `9.7` cannot override an exact missing-word/order
  failure. Do not invent the missing `I`, delete source text, regenerate the
  same synthesis fingerprint, or repeat the repair fingerprint. Listening QA
  and full-title generation were correctly skipped.
- The local synthesis cost was `$0.00`; no listening provider call, upload,
  publication, release mutation, or public exposure occurred. Alice remains
  audio-hidden and now has a deterministic source-bound import packet. The old
  unapproved remote object must still be revoked before any future release.
## 2026-07-28 Reference-matched dynamic hero carousel

- Painting a narrow divider inside each cover makes four adjacent jackets look merged and consumes real front-cover pixels. The convincing, non-overlapping construction is a separately rendered right-side page block outside the jacket plus a shallow bottom page face.
- The supplied reference measures to a carousel stage beginning at `63.8%` and ending near `94.5%` of the hero artwork. Responsive spine depth of approximately `0.58vw` plus `2–3px` optical clearance keeps transformed fronts disjoint at 1024, 1440, and 1920 pixels.
- Dynamic hero rotation must use the complete reader-enabled, canonical-cover-valid contract set, not a hardcoded four-title list. Cover load failure remains fail-closed and carousel timing pauses for hover, focus, reduced motion, and hidden documents.
- `object-fit: contain` produced conspicuous ivory bars for nonstandard cover proportions and broke the bound-book illusion. The verified stage uses a consistent cover crop so title and focal art remain prominent while the full link hit area and external spine stay intact.
- Responsive AVIF/WebP source selection reduced the hero artwork package versus the prior single 1.7 MB WebP while preserving the full reference aspect and header-safe placement.

## 2026-07-28 Platform-wide unified 8.9 listening gate

- The active policy now uses `8.9` for overall listening and every subjective
  listening dimension, including anti-robotic texture and anti-choppy joins,
  with confidence `>=0.90` and all fatal flags still disqualifying.
- The `9.7` value is the objective ASR/manuscript fidelity gate, not a
  listening score. It remains unchanged with exact first/last/order, coverage
  `>=0.98`, measured sync, rights, covers, checksum, metadata, endpoint,
  browser playback, and an empty blocker list.
- Reclassification produced zero new full-title release-ready titles. Gift,
  Tell-Tale Heart, Time Machine, Radharani, Secret Garden, and Desiree's Baby
  remain blocked by exact-content, fatal-defect, missing-full-title, measured
  sync, or downstream delivery evidence rather than the listening cutoff.
- No provider call, upload, publication, release metadata mutation, or hidden
  audio exposure occurred. Existing raw scores and historical reports remain
  immutable.

## 2026-07-28 Sprint 1 hero carousel refinement

- A release-safe hero carousel needs two membership gates: the backend filters
  eligible cover contracts to `sprint1_active_slugs`, and the frontend fails
  closed to `hero.carousel_books` instead of widening into general shelves.
- Page-index keys and per-cover arrival animations make every four-book change
  dependent on remount and decode timing. Stable frame layers plus a
  pre-decode barrier allow one bounded 420 ms compositor transition.
- Equal CSS columns are not enough when a shared parent perspective projects
  each column differently. Applying the same local perspective to each jacket
  reduced 1440 px width spread from roughly 0.94 px to 0.008 px and clear-gap
  variance from roughly 0.67 px to zero.
- Explicit front, right-page, and bottom-page elements produce a more legible
  hardback than a painted divider. The validated geometry has zero baseline
  spread, approximately 5.13/5.99/7.31 px clear air at 1024/1440/1920, and no
  overlap or horizontal overflow.
- Canonical covers remain fully visible with `object-fit: contain`; varying
  source proportions are framed as physical jacket boards instead of being
  cropped to manufacture uniformity.

## 2026-07-28 `bn-066` preflight and ASR closeout

- A bare single Bengali digit between literary paragraphs can be a stanza or
  section marker, not page boilerplate. The factory now treats explicit
  `পৃষ্ঠা`/`পৃ.` markers and bare three-or-more-digit lines as page artifacts
  while preserving single-digit Bengali structure.
- Audiobook-use authorization permits preparation and private QA; it does not
  approve a public audio release. Public audio remains governed independently
  by the approved release state, QA status, bound assets, and delivery gates.
- All 152 retained ASR checkpoints completed, but the raw audio/manuscript
  score was `0.8403/10` and first/last boundaries failed. Listening QA must not
  run after that objective failure, and the same audio/provider attempt must
  not be repeated.
- The reader stays live and audio stays hidden. The next admissible path is a
  genuinely different exact source-bound delivery followed by the full gate
  sequence; no upload, publication, public Listen, or release mutation
  occurred in this repair.

## 2026-07-28 Pride and Prejudice audiobook-use preflight

- Public-domain text and owner authorization are enough to approve audiobook
  preparation, but they do not prove that any retained recording may be
  released.
- A listening-only lock is not a candidate manifest. Pride's retained Edge,
  Piper, and enhanced files lack a complete combination of exact recording
  provenance, source binding, objective ASR/order evidence, measured sync,
  full listening QA, and downstream delivery proof.
- Record source/adaptation permission separately from public-audio approval.
  The provider-free preflight now passes manuscript, rights, and covers and
  stops at audio reuse because no approved recording is bound. Bind one exact
  rights-clear recording before spending on listening review.
- Pride remains reader-live and audio-hidden; no generation, provider call,
  upload, publication, or release-state mutation occurred.

## 2026-07-28 Sprint 1 admin cover remediation

- Canonical presence and URL reachability are separate checks: all 42 populated
  Sprint 1 cover-side URLs resolved as images, while 11 titles still had no
  canonical front or back URL at all.
- A reachable image can still be wrong. `a-ghost-story` has a populated,
  reachable pair that visibly names another title and author, so semantic cover
  review must remain an independent blocker.
- Direct upload of finished owner art is not cover generation. It should use a
  small authenticated media lane with strict MIME/byte/dimension/aspect
  validation, SHA-256 evidence, concurrency control, and audit logging.
- An admin upload is a candidate, not controlled-publication truth. The cover
  desk distinguishes `MISSING`, `MISMATCH_REVIEW_REQUIRED`,
  `UPLOADED_PENDING_CANONICAL_REVIEW`, and `CANONICAL_READY` so an upload cannot
  silently bypass the catalog review step.
- Cover-only database patches are built from an allowlisted helper and never
  contain reader or audiobook fields. The complete frontend test suite and
  focused backend/catalog tests passed without changing audio release state.

## 2026-07-28 — Gift CosyVoice3 bounded reopening closed on exact content

- A standing owner GO-LIVE authorization was narrowed to one private,
  source-bound `CosyVoice3-0.5B-MLX-bf16` adversarial sample. The upstream
  model, MLX conversion, and `speech 0.0.23` runtime are Apache-2.0; the run
  used the model-default synthetic voice and no reference recording.
- The 24 kHz mono WAV was valid, unclipped, deterministic, private, and cost
  zero. Local Whisper produced ASR/source `9.7758` with `0.982` coverage.
- Numeric thresholds did not manufacture a pass: the opening `It’ll grow`
  became `It took Ro`, so first words and ordered-content integrity failed.
  Listening QA, representative expansion, full-title generation, upload, and
  publication were correctly skipped.
- Preserve fingerprint
  `559d94ef386b741ee489d5dcbfd9df71686cbe9ac634801879d2978afbdcad25`
  as closed. Gift remains audio-hidden and requires an exact source-bound
  narration or licensed-audio delivery.

## 2026-07-28 — The Monkey's Paw retained B2 prefix exhausted

- A preflight binding is not proof that the selected private object contains
  the expected audio. The immutable version selected for the repaired
  candidate matched its inventory size but hashed to
  `ae054cb6464fd228669304080e173268d2d4d37aabaa01a7b9be0b9f5f116600`,
  not the required
  `6b2c7f189bec2c175bb940cdaa218313801ca70bf6025408f0a703205418afa8`.
- Enumerate the complete title prefix before assuming a missing candidate is
  merely under a neighboring key. The prefix contained exactly six immutable
  versions, no delete markers, two audio objects, and four sidecars.
- Both MP3s were structurally valid and matched their listed byte sizes, but
  their hashes and durations were different from the repaired evidence:
  `044cdb5b...a1a7a` at `1769.3761` seconds and
  `ae054cb6...16600` at `1287.778685` seconds versus the expected
  `6b2c7f18...fa8` at `1449.888` seconds.
- Valid media is not interchangeable media. Do not relabel either retained
  object, rerun QA against the wrong bytes, or expose public audio. Recover the
  original repaired build only if provenance and source binding can be
  restored; otherwise use a new rights-clear exact source-bound delivery and
  rerun every release gate.

## 2026-07-28 — Pride Chatterbox V3 bounded pilot closed on canonical-name fidelity

- The pinned local Chatterbox V3 path works offline with the model-bundled
  `conds.pt`, no external reference recording, and no `audio_prompt_path`.
  The resulting private 24 kHz mono WAV was valid and unclipped; its SHA-256 is
  `52f5bfca9253ab29071236ea418a70ebae99d9ada07b83ff9466e77ff596aaf4`.
- A high aggregate number is not sufficient evidence. Both `medium.en` and an
  independent source-blind `small.en` adjudication scored `9.7872` with
  `0.9787` coverage and agreed on the same `Long` to `Wong` substitution.
  Coverage therefore missed the strict `0.98` floor and ordered-content
  integrity failed.
- Listening QA was correctly skipped because it cannot repair missing or
  unexpected manuscript content. Fingerprint
  `1658048f26f8b9ce51c3ff378db4a5be2bc72032157792dd39b40d5a586e9a05`
  is consumed and closed; Pride remains reader-live and audio-hidden.
- A reproducible network-disabled Chatterbox environment also needs the
  `Cangjie5_TC.json` tokenizer file cached locally, the PKUSEG resource
  available offline, and `setuptools<81` for PerTh's current
  `pkg_resources` compatibility.
- No upload, public metadata or release-gate mutation, publication, or paid
  lock mutation occurred. The next admissible path is one genuinely different
  exact source-bound delivery followed by the complete objective gate sequence.

## 2026-07-28 — Jekyll voice selection passed representative gates

- Exact source fidelity and premium listening quality must both select a voice.
  Studio-C at rate 0.88 passed all normalized objective samples, but middle and
  dialogue listening fell to 8.4. That fingerprint is closed and must not be
  repeated or expanded.
- A materially different `en-GB-Chirp3-HD-Charon` arm at rate 0.94 preserved
  all four passages at normalized 10.0 / 1.0 with valid audio-derived word
  timestamps. Its four listening samples all scored 9.4 with confidence 0.95,
  no fatal flags, and no dimension below 9.2.
- Preserve raw ASR truth while adjudicating inaudible formatting. The Charon
  middle sample decoded canonical British `neighbouring` as American
  `neighboring`; raw 9.8438 / 0.9844 remains recorded. Only that explicit
  standalone pair is normalized. No general spelling, stemming, name, or
  content substitution is accepted.
- The production admin cover route previously excluded controlled-publication
  titles absent from Mongo. The repaired source resolves Mongo first, then only
  an exact reader-eligible controlled artifact, and still writes only to the
  private candidate collection. Pending URLs remain absent from public catalog,
  Home, reader, and audio surfaces.
- A representative pass is not a full audiobook. Jekyll remains audio-hidden
  until its private graphical pair is reviewed and promoted to canonical cover
  truth, followed by full-title generation, full ASR and measured sync,
  six-sample listening, private delivery, endpoint 206, and browser proof.

## 2026-07-29 — Immutable audiobook delivery packages are release truth, not approval

- Segmenting audio improves startup, retry, caching, and parallel production,
  but segment existence or upload does not authorize public playback.
- Bind every package to the controlled manuscript hash, exact release-evidence
  version, per-segment audio and timestamp hashes, contiguous word ranges, and
  contiguous cumulative duration. Reject gaps, overlaps, reordered segments,
  stale package versions, and segments longer than 12 minutes.
- Keep raw B2 locations and internal source/release identifiers out of the
  browser payload. Serve only same-origin, controlled-truth-resolved URLs with
  native Range handling; Redis is for small metadata/state, never audio bytes.
- Do not preload MP3 bytes on page load, hover, focus, or touch. Start media
  loading only from explicit playback intent, then advance through immutable
  same-chapter segments without restarting for speed changes.
- Migrate one already-approved audiobook as the first package-v2 canary. A new
  title still requires the full existing rights, content, ASR, sync, listening,
  storage, endpoint, and browser gates before controlled-publication promotion.

## 2026-07-29 — Private package-v2 storage proof is not production migration

- Repackaging the exact approved `book-2b9853ec52` source did not regenerate
  narration. The two-segment plan preserved the approved MP3 hash
  `a974819392d7bc4e7239828e29cf36f31661326ae71c1218273716d16bd462a5`
  and bound 11 assets to release descriptor
  `e00ec647012b90a2f2d5324ac59eec8f755e6353c3a736497495e53d9a21f26a`.
- Private staging proved useful delivery mechanics: all 11 objects received a
  VersionId and passed complete post-upload and receipt-bound re-download
  checksum verification. That is storage-integrity evidence, not a release
  gate.
- Respect the preflight's explicit scope. `PRIVATE_QA_STAGING_ONLY`,
  `release_eligible: false`, one-day staging retention, no independent account
  identity, and no Object Lock mode cannot be relabeled as production-primary
  or DR evidence.
- Derive the final package version only after exact primary and replica
  VersionIds exist. Until those receipts, the final manifest, controlled
  binding, endpoint Range checks, and browser parity exist, keep the current
  approved delivery untouched.
- Public catalog and Home projections must remain an allowlist. Focused tests
  proved that package hashes, immutable keys, buckets, replicas, and VersionIds
  remain absent while the customer sees only the same-origin reader audio URL.

## 2026-07-29 — Construction provenance cannot replace current raw ASR

- Bind revalidation to the exact delivered bytes and exact narrated manuscript
  before comparing models. For `book-2b9853ec52`, the approved audio remained
  `a974819392d7bc4e7239828e29cf36f31661326ae71c1218273716d16bd462a5`;
  the clean manuscript was the controlled chapter content plus one terminal
  newline.
- Cached multilingual Whisper-base is not a viable Bengali validator for this
  audio. It completed in 114.04 seconds but emitted punctuation-only output,
  scoring `0.0` with `0.0` coverage and failed first/last spans.
- CPU Whisper-medium with word alignment is not a cost-effective bounded lane
  on this machine. It reached only 23% after 661.07 seconds and produced no
  transcript JSON. Do not repeat either exact local fingerprint.
- The exact prior audio-derived result remains the release-relevant truth:
  raw ASR `1.1258`, coverage `0.1126`, and failed raw first/last spans,
  classified `SUPPORTING_DIAGNOSTIC_WEAK`. A historical construction score of
  `10.0` proves intended TTS source provenance only; it cannot satisfy the raw
  audio-derived `9.7` objective floor.
- Fail a new package-v2 migration revalidation without retroactively mutating
  the title's existing live state. Keep the current delivery untouched and the
  migration blocker open until a materially different bounded Bengali ASR
  runtime produces qualifying evidence.

## 2026-07-30 — MLX large-v3-turbo does not clear book-2b migration ASR

- Bind the downloaded model to its exact repository revision and file hashes.
  The MLX weights at revision
  `a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb` matched the repository-declared
  SHA-256
  `951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6`.
- Record provenance caveats rather than expanding them into unsupported
  claims. OpenAI's upstream large-v3-turbo card is MIT and includes Bengali;
  the MLX conversion card omits its own license and base-model metadata, so
  this lane is evidence for private QA only.
- The full exact-audio MLX transcript was predominantly Bengali and improved
  the completed raw score from `1.1258` to `3.3775`, but coverage was only
  `0.3377` and both source boundaries failed. Diagnostic phonetic projection
  `7.596` cannot replace the raw `9.7` gate.
- Close this exact model/audio/settings fingerprint. Preserve the current
  approved legacy audiobook and keep package-v2 promotion blocked; do not
  commit model, audio, transcript, cache, runtime, or temporary artifacts.

## 2026-07-29 — Preserve private canary proof without storage identity

- Ephemeral preflight, upload, receipt, and re-verification files are not a
  durable audit trail even when their hashes are recorded. Preserve a
  repository-safe projection while the original files are still available.
- The sanitized `book-2b9853ec52` evidence retains all six source-artifact
  hashes plus exact asset hashes, sizes, MIME types, B2 VersionIds, and
  verification results for all 11 objects.
- Credentials, account identifiers, endpoints, regions, bucket names, object
  keys, and local asset paths are excluded. Sanitization does not change the
  evidence boundary: private staging remains `release_eligible: false`.

## 2026-07-29 — A completed package-v2 canary can remain safely dark

- `the-open-window` now has a finalized package-v2 candidate bound to descriptor
  `0f57074e12efe5e4478e26efec4b619231a22123eb5c5ec630026f7202421ed0`
  and package version
  `sha256-4bf8a83a0181bd10f22cfe32aba18f80e1a357dc7e73aa27c026d6d5c36a83fd`.
- Independent production and DR receipts prove all 14 candidate assets by full
  re-download, exact hash, immutable version, and Governance Object Lock. The
  finalized release manifest was separately verified in both stores.
- Bucket-level Object Lock defaults to a 30-day Governance floor. The upload
  receipts requested and verified at least 29 days for every staged object.
- Keep selection truth separate from storage readiness. The active descriptor
  remains the legacy hash
  `81da7eb58ffe821cf708b7917af13f066929fccbaed0013394b8bf4f013c7ffe`;
  candidate rollout is `0%`, so customers remain on the proven legacy path and
  the truthful public audiobook count remains four.
- The stale package-manifest proxy assertion is resolved. The final combined
  builder, storage, selector, backend package, B2-routing, Sprint 1 cleanup,
  and Redis-policy regression completed with `136 passed / 0 failed` at
  `2026-07-29T20:17:49Z`; the full frontend suite passed `164 / 164` after an
  adversarial backslash-network-path origin-bypass regression was added. Keep the
  candidate at `0%` through the initial deployment checkpoint, then run the
  already-authorized endpoint and browser canary before increasing rollout.

### 2026-07-29 — Package-v2 reader-manifest cache namespace

- The merged 0% checkpoint deployed correctly, but persistent Redis still
  served the pre-package reader manifest under
  `audio-contract-v12`; a URL cache-buster could not change that server-owned
  cache identity.
- The legacy Open Window byte-range route remained healthy at HTTP `206`, the
  package endpoint remained fail-closed at `404` with `private, no-store`, and
  public audiobook truth stayed at four.
- Rotating the controlled-publication truth gate to `audio-contract-v13`
  deterministically ignores the stale v12 object. A regression now seeds only
  the old cache key and proves that the rebuilt reader manifest contains the
  same-origin package-manifest route. Focused backend validation passed
  `92 / 92`.

## 2026-07-30 — Five-percent package-v2 cohorts remain sticky and fail closed

- Preserve the 0% storage-and-selection checkpoint as history; a later rollout
  observation must not rewrite the state that was true at the earlier gate.
- At the completed `the-open-window` 5% production checkpoint, 62 newly issued
  sticky identities produced one candidate cohort and 61 legacy cohorts. The
  candidate cookie repeated the same immutable package at HTTP `200`; the
  legacy cookie repeated HTTP `404` with `private, no-store`.
- Candidate HTTP delivery passed exact package-version binding, a 64-byte
  `206` request over `bytes 0-63/4712013`, the measured timestamp sidecar,
  `416` for an invalid range, and `404` for both a wrong package version and a
  candidate-segment request from the legacy cohort.
- The legacy browser no-regression checkpoint proved `src=null` and
  `preload=none` before intent, then `readyState=4`, active playback, visible
  Pause/Stop controls, and an empty console after intent. Playback was stopped
  after validation.
- Do not convert that legacy-browser proof into a candidate-browser claim.
  Candidate playback was validated at the HTTP layer only, no browser latency
  was measured, the active legacy descriptor remains retained, and the public
  audiobook count remains four.
- A subsequent isolated Chromium `149.0.7827.55` run sampled 19 independent
  production `www` contexts to obtain a candidate cohort. It proved no audio
  source or loading before intent, exact package-segment `206` playback,
  continued playback after a 300-second seek, safe page-advance reset,
  successful re-prime, and successful cached replay after reload.
- Candidate playback produced no console or page errors; only non-error preload
  warnings appeared. Stop reset the source and current time.
- Do not claim cross-segment auto-advance from this checkpoint: the Open Window
  package contains exactly one segment. Test that behavior only on a future
  multi-segment package. No browser latency was measured.

## 2026-07-30 — Twenty-five-percent package-v2 checkpoint supports promotion

- Preserve the completed 0% and 5% checkpoints when recording a wider rollout;
  deployment evidence and observations at 25% are additive, not replacements.
- PR `#181` merged as
  `169b6d7143cf9d54408784b43cef87f65e758050`; the main regression suite, GO
  LIVE regression gate, and repository-linked Railway deployment
  `5d5db8a5-5963-4e8a-ba46-9600c6990472` all completed successfully.
- At 25%, a fresh sample needed only three identities to obtain both delivery
  paths: candidate at index 1 and legacy at index 3. Repeated selection
  remained sticky at HTTP `200` for candidate package discovery and `404` for
  the legacy cohort.
- The candidate manifest remained bound to the exact approved descriptor and
  package version. Segment `HEAD` returned `200` and 4,712,013 bytes; a
  64-byte range returned `206`; timestamps returned 12,839 bytes with the
  expected SHA-256; invalid range returned `416`; wrong version and legacy
  candidate-segment access returned `404`.
- The retained legacy monolith independently returned a 64-byte `206` range
  from 6,283,053 total bytes. Home curation continued to report exactly the
  same four public audiobook slugs.
- Two isolated Chromium contexts, one per cohort, had no audio before intent.
  Candidate playback used the exact package route at `readyState=4`, continued
  after a seek to 180 seconds, and produced no console or page errors. Legacy
  playback used the exact monolith at `readyState=4` with no page errors; its
  only two network-console `404` entries were expected package-manifest
  fallback probes.
- This one-segment title still cannot prove cross-segment auto-advance. The
  successful 25% checkpoint supports the separately prepared 100% active
  pointer promotion, but evidence must not claim that promotion until its own
  deploy and package-only production validation complete.

## 2026-07-30 — Promote only after every prior cohort converges on one package

- Preserve the Open Window 0%, 5%, and 25% history after promotion. The final
  100% record is additive and must distinguish an active package pointer from
  a candidate cohort set to 100%.
- PR `#182` merged as
  `d01482c20b2e9c081ebf5cf0f9334f014566d6ed`; both main workflows and
  Railway deployment `152b8e25-d119-4e5f-9c18-bfdeae74548a` passed. The
  previous 25% deployment is removed.
- Eight fresh identities and an identity retained from the former legacy
  cohort all resolved to the same exact package manifest. This is stronger
  convergence evidence than merely observing no legacy cohort among a small
  random sample.
- Both fresh and former-legacy identities passed a 64-byte package-segment
  range with the exact package header. Invalid range remained `416`, wrong
  package version remained `404`, and the retained legacy monolith remained
  range-readable solely for explicit rollback.
- Reader truth remained audio enabled, `APPROVED`, and `QA_PASSED`, with the
  package-manifest asset present. Its empty `package_version` field is the
  current reader-manifest contract and must not be rewritten or reported as a
  package-version binding.
- Production browser playback retained zero-byte pre-intent behavior, bound
  the exact package segment on first intent, reached `readyState=4`, played on
  second intent with Pause/Stop controls, emitted no developer error logs, and
  reset source, time, and ready state on Stop.
- The active descriptor is now package v2, the candidate slot is cleared, and
  the legacy descriptor is retained only for explicit rollback. Public
  audiobook truth remains the same four titles.
- A one-segment title cannot prove cross-segment auto-advance, even at 100%.
  Carry that validation to a future multi-segment package rather than
  broadening the Open Window claim.
- Close the Open Window rollout and move the next exact audit to Sredni
  Vashtar instead of creating another Open Window rollout stage.

## 2026-07-30 — A Ghost Story package-v2 source recovery

- The exact narrated manuscript can survive in ignored release-gate workspaces
  even when it is absent from a fresh Git worktree. Four retained copies were
  byte-identical at SHA-256 `0f1e3de7855169bddac8ddca288aa3a63f8d6a742ce63c0b91aa947e5e2786d4`.
- The narrated and controlled manuscripts are text-identical after collapsing
  whitespace. Preserve both hashes and both exact byte representations; do not
  relabel one as the other.
- Treat an intraword hyphen as an alignment-token equivalence only when a
  hash-bound contract explicitly permits it. Never rewrite the canonical
  reader text or infer replacement content from ASR.
- Removing the stale root-only estimated `highlight_sync.json` restores
  controlled mirror identity without changing the approved audiobook,
  release gates, public URLs, or customer-facing text.
- A deterministic two-segment package-v2 release candidate now builds with no
  blockers. Storage upload and active-release promotion remain separate,
  explicitly authorized operations.

## 2026-07-30 — Audiobook onboarding must distinguish assets from release truth

- Admin audiobook asset URLs are inventory evidence, not public-release
  approval. The open-source onboarding path must require the controlled
  approval evidence, public-book flag, and reader-manifest flag before it can
  classify a mapped audiobook as `READY`.
- A dry run must compare the live/admin narration text byte-for-byte with the
  controlled-publication chapter text. On divergence, preserve separate live
  and controlled evidence files, report both SHA-256 values, and stop before
  choosing either manuscript for synthesis.
- The Tell-Tale Heart exposed both failure modes: stale mapped audio assets
  existed while controlled audio remained blocked, and the live extracted
  manuscript SHA-256 `316ed82d8ae04a1af3f82ec692e88bc630c4865c06192854a612f29cb017f2bb`
  differed from controlled SHA-256
  `60c275266b007015732fdb9cca5165c9efc0cffae988bed66c5d6ca9fcbeb748`.
  No synthesis, upload, gate mutation, or public action may follow until that
  source divergence is explicitly resolved.

## 2026-07-30 — The Tell-Tale Heart manuscript reconciliation

- The live/admin SHA-256 `316ed82d8ae04a1af3f82ec692e88bc630c4865c06192854a612f29cb017f2bb`
  and controlled SHA-256
  `60c275266b007015732fdb9cca5165c9efc0cffae988bed66c5d6ca9fcbeb748`
  represented identical prose. Their whitespace-collapsed text was identical
  at SHA-256 `acbb67e1d96287a80021202229211ffc8072e80a67cf3274b1f3a00376c22fef`,
  and every non-whitespace character matched.
- Historical Git blobs retained both the sanitized source and the faulty
  chapter representation. The defect was exactly 167 duplicated newlines
  before indented source-wrap continuation lines; it was not source,
  punctuation, spelling, or editorial divergence.
- Remove only the duplicated newline from the exact `\n\n ` continuation
  pattern. This restores 19 real paragraphs from 186 false paragraphs and
  makes the controlled extraction byte-identical to the recovered admin
  manuscript without changing prose.
- Keep the repaired controlled chapter as reader truth and bind any future
  source-bound audio lane to the recovered canonical manuscript SHA-256
  `316ed82d8ae04a1af3f82ec692e88bc630c4865c06192854a612f29cb017f2bb`.
- Manuscript reconciliation does not authorize audio. The title remains
  reader-live and audio-hidden; the closed Kokoro fingerprint remains closed,
  and all objective, listening, delivery, endpoint, and browser gates remain
  mandatory for a future distinct audio candidate.

## 2026-07-30 — Public-domain source art still requires a private editorial boundary

- A retained cover-generator `PASS` is not sufficient cover evidence when the
  visual was code-generated without separate editorial approval. The retained
  Tell-Tale back cover visibly collided manuscript text, so it remained
  ineligible despite exact dimensions and matching Cloudinary checksums.
- Odilon Redon's 1883 *The Tell-Tale Heart* source art is independently
  hash-bound at
  `075f2c285d2f546076e8f1f50f03da43184f4c51d47746fbabc2358f9d37ed56`
  with Public Domain Mark evidence. Preserve the unmodified source beside any
  derivative cover package.
- Deterministic crop, tonal treatment, border, and catalog-text overlay can
  prepare a finished front/back candidate without AI-generated imagery.
  Geometry checks and backend image validation must precede visual review.
- The finished pair remains private and pending owner/editorial review.
  Absence of admin credentials means no upload was attempted; even a successful
  admin upload must remain `ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW` and cannot
  promote the canonical catalog or change audiobook truth.

## 2026-07-30 — The Tell-Tale Heart CosyVoice3 BF16 private pilot

- A distinct four-passage CosyVoice3 BF16 pilot was bound to the reconciled
  normalized manuscript and exact passage hashes, then checked with the pinned
  local MLX Whisper large-v3-turbo model and the repository's strict ordered
  token verifier.
- Only the opening passage passed. The bedroom sample skipped 10 exact source
  tokens inside a parenthetical clause, and the heartbeat sample ended 32
  source tokens early. Aggregate score was `9.3979`, coverage was `0.8908`,
  and ordered content integrity failed.
- A high ASR score on one passage cannot justify a full-title run when another
  representative passage proves synthesis truncation. Reject the configuration
  before listening spend or full generation and close its exact
  model/revision/seed/voice/passage fingerprint.
- Two WAVs also exceeded 0 dBTP and contained many high-amplitude one-sample
  transient clusters. These require audible review but do not change the
  decisive source-omission failure.
- No independent audible reviewer was available, so no listening score or
  absence-of-fatal-flags claim was made. The title remains audio-hidden.

## 2026-07-30 — B2 production lifecycle evidence must use the Native API

- Lifecycle-read capability support is inconsistent across Backblaze B2's
  documented and deployed S3-compatible surfaces. Treating the unsupported S3
  response as optional would create an unsafe evidence gap; treating it as a
  permanent production blocker would make the valid storage design impossible
  to activate.
- Use Native API v4 `b2_authorize_account`, then exact-name
  `b2_list_buckets`, to read the bucket's `lifecycleRules`. Require the
  `listBuckets` capability, exact account identity, and an application key
  restricted to exactly the configured bucket.
- Bind the authorization response to the bucket-list response by exact bucket
  ID as well as account and bucket name. A missing or different returned ID
  must fail closed even when the human-readable bucket name matches.
- Fail closed before the first object write if Native authorization or bucket
  listing fails, if the key is missing the capability or exact bucket scope,
  or if any lifecycle field is malformed.
- Validate all documented Native lifecycle day fields, including unfinished
  large-file cancellation, as either `null` or an integer of at least one.
- Default urllib redirect handling can move an `Authorization` header to a
  second URL. Build Native API requests with a redirect handler that rejects
  every redirect before a second request object can be used, and sanitize the
  resulting failure so neither credential material nor the redirect target is
  reported.
- A lifecycle rule that hides `v1/prod/` is operationally destructive even
  when deletion is delayed. Block both hiding and deletion rules whose prefix
  overlaps the protected production prefix.
- Keep upload and retention-preflight credentials separate. The retention
  profile is read-only despite its legacy `RETENTION_ADMIN` environment name;
  it does not need deletion, governance-bypass, bucket-write, or
  retention-write capabilities.
- This change supplies storage evidence only. It does not upload objects,
  mutate release truth, deploy code, or alter `paid_tts.lock`.

## 2026-07-30 — Jekyll cover art can advance without AI-rights ambiguity

- A visually strong AI-generated private pair is not canonical cover evidence
  when its exact generation receipt, account entitlement, artifact-bound
  commercial-use attestation, and similarity review are absent. Preserve it
  only as superseded private provenance rather than inferring rights from the
  image files.
- Charles Raymond Macauley's Chapter 2 Drawing 1 and Chapter 10 Drawing 2 from
  the Scott-Thaw 1904 edition are exact-title, content-relevant alternatives.
  Preserve their unmodified source files and bind every composition to SHA-256
  `1848b89196669aeb7c0ea097d4821dc20cab09cca968d9bd854f85e68413f374`
  and
  `e48ba094dde8140e7894d6f9963b9674f395a6de98dcaf3766d1eb452e4628be`.
- Public-domain evidence must retain the source record's territorial caveat.
  Do not turn a life-plus-70 statement into an unrestricted-worldwide claim;
  owner/editorial and approved distribution-jurisdiction review remain
  mandatory before canonical promotion.
- Deterministic catalog typography, explicit safe panels, and preserved source
  art resolve title/author accuracy without generated lettering. The exact
  canonical short description is safer than inventing premium back-copy when
  no separately approved editorial field exists.
- Test both geometry and actual delivery derivatives. The 1600 x 2400 masters
  pass the backend cover validator, while 320 x 480 WebP thumbnails stay under
  80 KiB and 800 x 1200 WebP feature images stay under 180 KiB.
- Automated checks plus direct master/thumbnail inspection can advance the
  pair to `PRIVATE_CANDIDATE_EDITORIAL_REVIEW_REQUIRED`; they do not authorize
  upload, canonicalization, public exposure, audiobook generation, or release.

## 2026-07-30 — Reconcile DR by receipts and serialize complete package lifecycles

- The Open Window DR console observation of `15` current files and `48.8 MB`
  reconciles exactly to receipt evidence: `14` package objects plus one final
  release manifest total `48,771,512` bytes (`48.771512` decimal MB). The
  catalog-bound payload and final-manifest replica receipt SHA-256 values are
  `2931065d6cde26e60bc7b4635eb0db20b7c7834d25e269e0461d070562416f1c`
  and
  `e455d8d1395496d75aad287a5b42537cf712f21b04d6b2f692132a8f7bd0cea4`.
- This is exact receipt/UI reconciliation, not a fresh remote bucket audit.
  Production HTTP evidence was supplied by the coordinator rather than rerun
  by this change: the public home truth is `4/32`; The Open Window package
  manifest returns `200` with one segment, a 1024-byte Range request returns
  `206`, invalid Range returns `416`, and stale/cross-title package requests
  return `404`. The other three live titles still return `404` from the
  package-manifest route and remain on legacy delivery.
- `upload` creates a primary receipt; `verify` consumes that existing receipt
  and does not create one. `replicate` creates the DR receipt, which the DR
  verification then consumes. Preserve this distinction for both the payload
  plan and the separately generated one-object final-manifest plan.
- Complete every title serially through payload upload, primary verification,
  DR replication, DR verification, finalization, final-manifest upload, final
  primary verification, final-manifest DR replication, and final DR
  verification. Do not start A Ghost Story until Sredni Vashtar completes.
- The selected Sredni package is descriptor
  `53458d86308f4718d46334d23aff725db31b70ed8f2736f9b731ca429e550fd3`:
  one segment, `15` payload objects, `79,267,278` payload bytes, and `16`
  total immutable objects per store after the final manifest. The selected
  A Ghost Story package is descriptor
  `cec2bb829531e0f820b8fd11d0881ecb42fc2d088adc5e93e7259e41d6026b40`:
  two segments, `20` payload objects, `102,547,050` payload bytes, and `21`
  total immutable objects per store after the final manifest.
- The focused builder/storage suites passed `70/70`. A disposable in-memory
  full lifecycle also passed for payload and final-manifest phases, validating
  report schemas and filenames without cloud calls or candidate mutation.
  Storage completion alone is not publication authorization; catalog
  activation, deployment, endpoint checks, and browser proof remain separate.

## 2026-07-30 Package-v2 Atomic Storage Preflight

- Production and DR configuration form one release unit. The package-v2
  preflight must load and validate both stores and prove their independence
  before constructing either store's S3 client or starting a lifecycle probe.
- A complete production configuration paired with missing DR configuration now
  fails with zero client, lifecycle-reader, or preflight-probe calls. The same
  zero-call rule applies when both stores are configured but not independent.
- Private-QA staging remains an explicit, non-release-eligible single-store
  mode. No cloud, upload, catalog, release-gate, or paid-provider mutation was
  performed while implementing and testing this guard.

## 2026-07-30 — D19 has one untried, provider-free Bengali audition packet

## 2026-09-05 — Reading Pass all-title segmentation is adaptive, not approval-changing

- The 45-title local Reading Pass matrix classified 41 titles as
  `READY_PROTECTED_STANDARD` and four as `READY_PROTECTED_ADAPTIVE`; no source,
  rights, publication, or reader-approval mutation was warranted.
- `book-d19e96859f` (`গিন্নি`) has an approved source/content hash and 27
  semantic blocks. The standard 3200-character target yields three pages, while
  the largest approved target yielding a protected page is 2000 characters.
- The same deterministic policy selects 2000 for Muchiram and The Open Window,
  and 2800 for The Selfish Giant. Production v2 remains disabled pending exact
  head CI, cache, entitlement, and browser evidence.

- After excluding Muchiram's exhausted synthetic lane, `book-d19e96859f`
  (`গিন্নি`) is the shortest Sprint 1 Bengali title with a canonical
  source-bound manuscript, public-domain literary rights, live reader, and
  complete front/back cover pair.
- Google and Sarvam execution evidence remains closed. A materially different
  provider-free packet now binds four exact source passages to
  `ai4bharat/indic-parler-tts` revision
  `7b527af5ee8ed1f9a28d80b19703ed9bb8ba10ca`, Bengali voice `Aditi`, a fixed
  voice description, seed, settings, and attempt fingerprint.
- The local model snapshot was observed and checksum-bound, but the execution
  runtime is not ready: the existing `.venv-audio` has Torch, Transformers,
  SoundFile, SentencePiece, and Hugging Face Hub but lacks `parler-tts`,
  `accelerate`, and `scipy`.
- The official model card identifies the model as permissively licensed under
  Apache-2.0, so the license permits commercial use. Hugging Face's separate
  contact-information/conditions acknowledgement controls repository file
  access; its receipt is not recorded in this packet, but that is a provenance
  note for the already-downloaded, hash-bound snapshot rather than a second
  commercial-rights or private-audition gate.
- This is a packet, not evidence of audio quality. No synthesis, ASR, listening
  QA, provider call, upload, release mutation, public exposure, or paid-lock
  access occurred. D19 remains `HUMAN_NARRATION_REQUIRED` and audio-hidden.

## 2026-07-30 — The four post-D19 synthetic lanes are finite and source-bound

- After excluding Jekyll and Pride, whose single conveyor attempts are already
  consumed, the remaining one-attempt titles are Dorian, Frankenstein, White
  Fang, and Dracula. All four have zero recorded prior attempt fingerprints.
- Jekyll's Charon result selects the strongest evidence-backed first arm, not a
  transferable pass. Every title needs a new exact-text four-passage
  fingerprint; Jekyll's fingerprint must never be reused.
- Canonical source preparation passes for Dorian, Frankenstein, and White Fang.
  Dorian and White Fang match their backend mirrors; Frankenstein does not.
  Dracula fails closed because all 27 canonical chapters omit `bookSlug`, and
  its passing backend mirror produces different text.
- Cover readiness, not manuscript length, determines the immediate order:
  Dorian has a historical differently slugged pair to audit, Frankenstein has
  an unpromoted historical pair plus source divergence, White Fang has no
  retained pair, and Dracula has covers but needs controlled source repair.
- Historical filenames, report paths, and remote object URLs are not retained
  audio evidence. The current tree contains no MP3/WAV/FLAC under
  `internal/audiobook_lab`.
- Dry preflight only produced source hashes, four-passage fingerprints, and
  cost arithmetic. No audio, provider call, upload, release mutation, public
  exposure, or paid-lock access occurred; production remains 4/32.

## 2026-07-30 — Preserve user activation across lazy package-v2 playback

- A media element may correctly have no `src` and transfer zero audio bytes
  before intent, yet still require two clicks if `play()` is deferred through
  animation frames. The first click can load the package to `readyState = 4`
  after the browser's transient user activation has expired without starting
  playback.
- Keep source assignment, `load()`, and the first `play()` request in the
  explicit Play handler's synchronous call stack. Word wrapping, DOM lookup,
  and highlight rendering may remain deferred.
- For synchronized pages, bind the page's measured timestamp offset before
  requesting playback. If metadata is not ready, retain that offset and apply
  it from `loadedmetadata` before media can start, preserving page-correct
  playback without preloading audio.
- Normalize both synchronous `play()` exceptions and asynchronous promise
  rejections into one fail-closed path. The same guarded call now covers
  package-v2, legacy approved audio, resume, and segment auto-advance.
- Local validation passed 63 focused frontend tests and a production build.
  Service-worker audiobook/Range bypass remains unchanged, and no private
  media, catalog, release-gate, cloud, or paid-lock state changed. Post-deploy
  one-click browser proof remains required because the browser runtime was not
  available in this isolated run.

## 2026-07-30 — D19 Indic Parler generated one bounded private audition

- The isolated runtime at
  `/private/tmp/earnalism-d19-indic-parler-runtime` matched every pinned
  package version and loaded `ai4bharat/indic-parler-tts` revision
  `7b527af5ee8ed1f9a28d80b19703ed9bb8ba10ca` fully offline on MPS.
- Attempt fingerprint
  `0a5d983bf199e0288557c80840402a00f9160e17e533e327fdf950d81006c05a`
  is consumed and must never be regenerated. Its code, runtime, model,
  tokenizer, source passages, voice description, settings, seed, and output
  policy are bound by generation-contract SHA-256
  `11aabb9a1bbd82f7e0d675df605dd0d46bdfbae0e3465125c8a80206f964365f`.
- Four exact source-bound representative passages generated four private mono
  44.1 kHz PCM-16 WAV files. Independent hash checks matched the evidence:
  `154ec9fc2aa3513e854d05ac78339994724d5f13858241387ae0658244c248ca`,
  `ce1f1a95f84fa75a4c9a68c919d46b7149b2cb99df9fdea344445cfc5e0e64ad`,
  `aedd8e20c12af01d513d39765d2a846a44d6c395a46cdd363215341fe133aac1`,
  and
  `70f1b9d4a277e9852750569bf985f70a7f180595ad97270a80387f3163db374a`.
  Total duration is `99.300136` seconds and total audio size is `8,758,448`
  bytes.
- Objective container/codec validation is not content validation. ASR,
  listening QA, measured sync, full-title generation, upload, endpoint,
  browser, and release gates remain unrun. D19 remains audio-hidden and is not
  release-ready.
- The next safe stage is one new objective-ASR adapter that verifies these
  four exact WAV hashes before decoding. It must fail closed on ASR/source
  below `9.7`, coverage below `0.98`, first/last mismatch, or any missing,
  duplicated, or reordered content. Do not synthesize timestamps or start
  independent listening QA unless objective ASR passes.

## 2026-07-30 — D19 Indic Parler fails objective source fidelity decisively

- The four private WAV hashes were re-bound to the merged D19 source-passage
  contract before offline decoding. Cached `mlx-whisper 0.4.3` used
  `mlx-community/whisper-large-v3-turbo` revision
  `a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb` with exact weights SHA-256
  `951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6`,
  Bengali language selection, temperature-zero greedy decoding, no prompt,
  and no network model resolution.
- Per-passage raw ASR/source scores were `0.8929`, `1.9643`, `0.7812`, and
  `0.9231`. Strict ordered coverages were `0.0833`, `0.1818`, `0.0735`, and
  `0.0822`. Every passage failed both first and last source boundaries.
- The concatenated aggregate scored `1.2617` against the `9.7` requirement
  with ordered coverage `0.1011` against `0.98`. Only `27` of `267` source
  tokens aligned in strict order; `235` source tokens were missing, repeated
  content was detected, and `100` unexpected tokens remained.
- Bengali normalization and phonetic projection were diagnostic only. Their
  aggregate scores (`3.134` and `3.619`) and projected coverage (`0.3619`)
  also failed and cannot replace the mandatory raw audio-derived gate.
- Stop this exact model/revision/voice/settings/passage fingerprint. Do not
  spend on listening QA, widen to full-title synthesis, create estimated sync,
  upload, or publish it. Keep D19 reader-live and audio-hidden; only a
  materially different exact-source candidate may reopen the title, with the
  existing human-narration packet retained as the deterministic fallback.

## 2026-07-30 — Keep lazy media source ownership outside React

- Moving `play()` into the explicit click stack was necessary but not
  sufficient while React still controlled the hidden audio element's `src`.
  The click handler assigned the approved package URL imperatively, then the
  `generatedAudioPrimed` state update caused React to commit the same URL as a
  newly present `src` prop.
- Setting a media source again restarts the browser's media-selection
  algorithm. That follow-up React commit aborted the first pending `play()`
  request while the resource continued loading, exactly matching the observed
  `readyState = 4`, `paused = true`, `currentTime = 0` result. The audio node
  itself was stable and was not remounted.
- Keep the hidden audio element source-free with `preload="none"` in JSX.
  Approved source assignment, `load()`, and `play()` remain imperative and
  synchronous inside explicit playback intent; segment transitions reuse the
  same exact release-gated path. React rerenders can no longer restart the
  package request.
- Local validation passed 70 focused reader/audio safety tests and an optimized
  production build. Pre-intent source absence, measured timestamps, package-v2
  URL binding, service-worker Range bypass, release truth, and the public
  audiobook count are unchanged. Deployment and one-click production browser
  proof remain required.

## 2026-07-30 — Migrate one approved audiobook through both immutable stores before rollout

- Sredni Vashtar proves the complete package-v2 storage sequence on the
  genuinely separate production and DR accounts: combined no-write preflight,
  production upload with immediate full-download verification, receipt-bound
  production re-verification, replication from verified production bytes,
  receipt-bound DR re-verification, finalization, and the same lifecycle for
  the canonical release manifest.
- Use the bucket's 30-day default Governance retention when writing and require
  at least 29 full days remaining during subsequent verification. This avoids
  false failures from elapsed command time while preserving the configured
  retention floor.
- Bind the existing approved legacy identity before staging the candidate.
  Zero-percent staging must keep the legacy descriptor active and must not
  increase the public audiobook count.
- Store upload/retention operators only in the protected offline profile.
  Railway needs separate read-only runtime credentials; uploading operators or
  retention credentials to Railway would unnecessarily expand blast radius.
- The exact Sredni package has 15 payload objects totaling `79,267,278` bytes,
  one segment, and descriptor
  `53458d86308f4718d46334d23aff725db31b70ed8f2736f9b731ca429e550fd3`.
  Its final manifest is `6,452` bytes with SHA-256
  `d488f114c154dd57ecdf474254d33b07a355a26ed9b3d416bc85ddf1b68117ea`.
  Both stores passed full-download checksum and exact-version verification.
- Do not begin A Ghost Story storage or customer rollout until Sredni's
  serialized 0%, 5%, 25%, and 100% checkpoints are independently green.

## 2026-07-30 — Require production-green zero percent before the first customer cohort

- Sredni's exact zero-percent commit deployed successfully before any customer
  cohort was enabled. The candidate manifest stayed dark with `404`; the
  approved legacy route returned `206` for a valid Range and `416` for an
  invalid Range; the public catalog remained exactly four audiobooks.
- Browser proof is a separate gate from HTTP proof. Before playback intent the
  reader had no audio source and `readyState=0`. One click loaded the exact
  approved legacy route, reached `readyState=4`, stayed unpaused, and advanced
  to `25.047581` seconds with no console errors.
- Only after all of those signals passed was the deterministic rollout
  percentage changed from `0` to `5` in an isolated branch. The legacy active
  descriptor, candidate descriptor, salt, receipts, approval flags, narration,
  storage objects, and public audiobook count remained unchanged.
- The next release boundary is not elapsed time. Both a deterministic
  package-v2 cohort and a deterministic legacy cohort must pass production
  manifest, Range, stale/invalid route, and one-click browser checks before
  considering `25%`.

## 2026-07-30 — Validate deterministic cohorts before widening a package canary

- A rollout percentage is not evidence by itself. At Sredni's production
  `5%` checkpoint, a known candidate identity and a known legacy identity were
  exercised separately.
- The candidate identity received the exact package manifest, Range-streamed
  segment and timestamps. Invalid Range, wrong package version and a legacy
  identity attempting the candidate segment all failed closed. The legacy
  identity retained its approved monolithic Range stream.
- Five 1,024-byte Range probes per lane all returned `206`; observed first-byte
  times remained between `0.796964` and `1.112835` seconds, inside the current
  `1.5`-second p75 target for this bounded sample.
- The real browser landed in the legacy cohort and independently proved no
  pre-intent source, one-click playback, time advancement, and zero console
  errors. Deterministic candidate delivery was proven at the HTTP boundary.
- Only after all cohort checks passed was the pointer advanced to `25%` in a
  separate branch. Narration, storage, receipts, approval truth, rollout salt,
  and the four-title public count remained unchanged.

## 2026-07-30 — Full promotion must clear the candidate state, not leave 100 percent routing

- Sredni's production `25%` checkpoint repeated the deterministic candidate and
  legacy manifest/Range/fail-closed tests and the real browser legacy one-click
  proof before promotion.
- The full-promotion operation does not leave a `100%` percentage canary. It
  makes the package-v2 descriptor active, clears the candidate descriptor and
  rollout salt, resets percentage to `0`, and retains the approved legacy
  descriptor for explicit rollback.
- After deployment, every identity must receive the same exact package-v2
  manifest and segment. The customer browser must show the package segment URL
  on the first click with advancing playback and zero console errors. A
  monolithic legacy source at that point is a release-blocking failure.
- No narration, storage object, receipt, approval flag, or public audiobook
  count changes during this delivery promotion.

## 2026-07-30 — Full package promotion requires the browser to select the package route

- Two deterministic identities and the public request all resolved the exact
  active Sredni Vashtar package after full promotion.
- Before playback intent, the real browser transferred no audio. One click
  selected the package segment, reached `readyState=4`, and advanced playback
  with no media or console errors.
- The legacy descriptor remains retained for rollback but is no longer
  selected. The public audiobook count remains four.
- A Ghost Story package-v2 migration may now begin, serialized behind this
  completed production checkpoint.

## 2026-07-30 — Preserve the approved legacy stream while staging a multi-segment package

- A Ghost Story's exact approved narration, manuscript and existing release
  evidence can be migrated without TTS or release-gate mutation.
- Full-download verification must cover every payload and the final canonical
  manifest in both production and genuinely separate DR accounts before any
  pointer is staged.
- Zero-percent staging retains the legacy descriptor as active and binds the
  two-segment package only as a candidate. The public audiobook count remains
  four.
- The next boundary is a production-green zero-percent deploy. Do not enable
  five percent until legacy Range and one-click browser playback still pass
  and the candidate manifest remains dark.

## 2026-07-30 — A zero-percent migration must prove both darkness and legacy continuity

- A Ghost Story's exact merge commit passed both main workflows and deployed
  through Railway's Wait-for-CI integration with the configured backend root
  and config file.
- The candidate manifest, candidate segment and wrong package version stayed
  dark. The approved legacy stream retained exact Range and invalid-Range
  behavior, and the home catalog remained exactly four approved audiobooks.
- Browser proof began from a fresh reader navigation. Before user intent the
  audio element had no source, declared `preload="none"`, stayed at
  `readyState=0`, and the page asset inventory contained no audiobook asset.
- One click selected only the legacy route, reached `readyState=4`, advanced
  playback, and produced no media or console error. The audio was paused after
  evidence capture.
- Zero percent cannot prove package segment delivery or auto-advance. The next
  five-percent checkpoint must separately exercise deterministic candidate
  and legacy identities, both segments and timestamp sidecars, and a real
  candidate-browser transition before any wider rollout.

## 2026-07-30 — Prepare the first cohort with exact deterministic identities

- A Ghost Story moved from zero to five percent only after its exact
  zero-percent production deployment, HTTP matrix and one-click legacy
  browser checkpoint were green and committed.
- The guarded rollout operation changed only the percentage and regenerated
  matching checksums in the two controlled-publication mirrors. It did not
  change the active legacy descriptor, package candidate, rollout salt,
  receipts, narration, approval truth or public count.
- Cookie identity `a-ghost-story-canary-identity-000059` maps to bucket `3`
  and therefore selects the package candidate at five percent. Identity
  `a-ghost-story-canary-identity-000000` maps to bucket `47` and remains the
  legacy control.
- No-cookie requests are unsuitable for deterministic proof because the
  backend creates a random sticky identity.
- The canary is not production-green until both deterministic cohorts pass
  their exact manifest, Range, timestamp and negative-route matrices and the
  customer browser proves package playback without hidden preloading or
  errors.

## 2026-07-30 — Deterministic package transport plus a natural legacy browser can advance a reversible canary

- A Ghost Story's five-percent production matrix passed `63/63` checks. It
  covered the exact candidate manifest, both segment Range streams, both
  timestamp sidecars, invalid ranges, stale/unknown/cross-title rejection,
  legacy continuity and the exact four-title public catalog.
- The real browser naturally remained in the legacy control cohort. It still
  proved zero pre-intent audio, one-click playback, time advancement and zero
  media or console errors.
- Do not inspect or manipulate the secure sticky cookie to manufacture a
  desired browser cohort. Record the natural result and rely on deterministic
  HTTP identities for package transport proof.
- This is the same controlled boundary accepted for Sredni Vashtar: a
  reversible `25%` canary may be prepared, but full promotion is not yet
  green.
- If a candidate browser is not naturally observed before promotion, the
  post-promotion checkpoint must prove the exact package route and a real
  segment-one to segment-two transition. Any failure rolls back to the
  retained legacy descriptor.

## 2026-07-30 — A full promotion is prepared first and earned only after package-browser proof

- A Ghost Story's twenty-five-percent checkpoint repeated the full `63/63`
  candidate/control matrix after the exact deployment and preserved healthy
  natural-browser legacy playback.
- The promotion operation does not leave a one-hundred-percent canary. It
  makes the package descriptor active, clears the candidate and rollout salt,
  resets percentage to zero, and retains the approved legacy descriptor for
  rollback.
- Pointer preparation is not completion. After deployment, every identity must
  receive the same package manifest and the real browser must select
  `c001-s001` on one click.
- Because this package has two segments, customer proof must include a real
  `c001-s001` to `c001-s002` transition with advancing playback and zero media
  or console errors.
- Any post-promotion routing, playback, timestamp or transition failure must
  roll back to legacy rather than being documented as an acceptable canary
  variation.

## 2026-07-30 — Natural cross-segment playback closes the delivery migration

- A Ghost Story's exact promotion merge passed both main workflows and
  deployed through Railway with the required backend root and config.
- Both former rollout identities and the public request resolved the same
  active package manifest. The production matrix passed `78/78` checks across
  both segment Range streams, exact timestamp sidecars, invalid ranges,
  stale/unknown/cross-title rejection, and the exact four-title public audio
  catalog.
- The real browser began with an unbound audio element, `preload="none"` and
  `readyState=0`. One visible click played exact segment `c001-s001`.
- Segment one was allowed to end naturally. The production player switched to
  `c001-s002`, stayed unpaused at `readyState=4`, advanced playback, and
  reported no media or console error. No programmatic seek, synthetic ended
  event, cookie change, or browser-storage change was used.
- The delivery migration is production-green without changing narration,
  audiobook approval, storage objects, the public count of four, or
  `paid_tts.lock`. The legacy descriptor remains retained for explicit
  rollback.

## 2026-07-30 — Original graphical art removes Jekyll's cover and territorial blockers

- The earlier Macauley composition remained a useful private editorial
  candidate but retained a longer-term-jurisdiction caveat and rendered
  internal production wording on the back. It was not promoted.
- A new deterministic 1600 × 2400 front/back pair uses only programmatic
  graphical primitives plus the exact controlled-catalog title and author.
  It contains no third-party image asset, generated-image-model output,
  placeholder art, or reader-facing engineering copy.
- The front master SHA-256 is
  `eefa51647e7dbe342ab55c7ba1df1f7a596794ed0edfd0d628f793b7f69a7dd8`;
  the back master SHA-256 is
  `9ea5c9f6144169469fc5ed1c5f95ecc6f596bec13061e250d3273152f2ae9344`.
  Both remain legible in the bounded 320 × 480 derivatives.
- Production keeps public admin cover mutation disabled. A localhost-only
  operator used Railway-injected Mongo and Cloudinary configuration to upload
  the exact candidates, then a separate localhost-only promotion transaction
  re-downloaded and checksum-verified each immutable Cloudinary object before
  atomically updating both controlled-publication mirrors.
- Front and back are `CANONICAL_READY`; combined cover status is `COMPLETE`.
  Reader and audiobook truth were byte-snapshotted by the transaction and
  remained unchanged. Jekyll audio is still hidden.
- The next safe boundary is commit, merge, deploy and production cover proof.
  Only then may the already-selected Charon full-title lane acquire the paid
  lock and generate one source-bound candidate.

## 2026-07-30 — Bind Dracula narration input without rewriting the reader edition

- Dracula's canonical and packaged roots were not different manuscripts. The
  canonical root stored reader HTML using only `p` and `br`, while the backend
  root stored the exact corresponding plain text.
- Adding `bookSlug: dracula` to all 27 canonical chapter records repaired the
  metadata contract without changing any chapter `content` or stored
  `content_hash`.
- The canonical checksum manifest changed 28 tracked file rows: 27 chapter
  rows for the metadata-only additions and one stale `source_evidence.json`
  byte-count row. The source-evidence file and its SHA-256 did not change.
- The English input builder now accepts only plain text or the supported
  `p`/`br` reader subset, normalizes that subset deterministically, and fails
  closed on any other HTML tag.
- Cross-root preparation must match the exact normalized source SHA-256,
  character length, chapter count, and ordered chapter list. Dracula now
  matches at 27 chapters, 848683 characters, and SHA-256
  `3e7f5f40c82df29bca74745eab7afab200ee57318b813b118dc9b5b9c664aeb9`.
- Preserve the current source-evidence hash set and the distinct historical
  approval snapshot as separate provenance facts. Never overwrite one to make
  it look like the other.
- This repair makes a private source input deterministic. It does not generate
  audio, authorize a provider call, approve a release, or expose Listen.

## 2026-07-30 — Public catalog must not let a same-slug Mongo row shadow controlled covers

- The Jekyll cover pair was correct in the controlled publication, reader, and
  curated Home paths, but `/api/books` and `/api/books/jekyll-and-hyde`
  accepted a live-looking Mongo record first. Blank or stale cover values could
  therefore override the exact promoted cover pair on public catalog routes.
- Public list and detail records now start from the validated controlled
  artifact. Only the existing explicit Home/editorial curation allowlist may
  be restored from Mongo; cover, reader, rights, and audio fields may not.
- Starting from the artifact instead of overlaying it onto the database row is
  important: canonical absence is meaningful for hidden audio and cannot
  inherit stale approval-looking database fields.
- Public catalog and Home cache keys rotate through `controlled-covers-v1`.
  Reader and audiobook manifest caching remains on `audio-contract-v13`.
- Focused catalog, cover, publication, and audio-safety tests passed `65/65`.
  The standalone B2/audio-routing suite passed `29/29`. No media, storage,
  provider, audiobook approval, reader approval, or paid-lock state changed.

## 2026-07-30 — Approved controlled truth may authorize cover intake over stale Mongo metadata

- The Tell-Tale Heart had a valid reader-live controlled publication with
  approved rights evidence, while an older same-slug Mongo row lacked the
  full rights-field projection. Cover intake stopped before Cloudinary rather
  than falling through to the authoritative controlled artifact.
- An eligible draft or fully rights-approved Mongo row still remains a valid
  intake source. When a published Mongo row is incomplete, the resolver may
  use the exact approved controlled artifact; when neither source is eligible,
  the operation still fails before upload.
- The exact Redon-derived front and back files passed full-resolution and
  320 px review, then uploaded to content-addressed Cloudinary identities.
  Canonical promotion re-downloaded both immutable objects and verified SHA-256
  values `474742edf3427ac414565c05b170cb83e855b223951be3ed22cc597ddf6f673d`
  and `540a24ebdfef56fefe99f23aba4166c3ada20dd421132480eaf3546b07b8934d`.
- Both controlled-publication mirrors and checksum manifests remain in exact
  parity. Reader state stayed live; audiobook approval, media, endpoint truth,
  and `paid_tts.lock` stayed unchanged and audio remains hidden.
- Preserve dated missing-cover inventories as historical snapshots. Record a
  new reconciliation artifact and remove the title only from current runtime
  fallback evidence.

## 2026-07-30 — New-title package construction must not depend on public audio

- Requiring an already-approved public legacy audiobook before package-v2
  construction creates a circular release dependency for a newly QA-passed
  title. Keep the legacy migration profile intact and add a separate,
  narrower private-new-title profile instead of weakening it.
- Bind the new-title profile to the exact Google full-generation manifest,
  full audio-derived ASR/sync report, six-sample listening report, controlled
  reader/source/rights/cover records, every controlled chapter, and an
  explicit package-build-only authorization descriptor.
- Derive chapter and paragraph timing from the raw transcript token sequence
  mapped to audio-derived timestamp groups. One timestamp group may contain
  several tokens, but fail closed if a canonical paragraph boundary falls
  inside that group. This permits chapter-aligned segments only at measured
  canonical paragraph boundaries without estimated sync or a public
  word-level claim.
- Preserve every provider MP3 unchanged as provenance, assemble one PCM/WAV
  master for future encodes, and produce only 96-kbps mono delivery segments
  no longer than twelve minutes.
- Package construction is pre-storage evidence, not publication. Keep
  production-primary upload, independent DR verification, controlled
  activation, deployment, endpoint, and browser proof as explicit downstream
  blockers. No provider, cloud, public asset, release gate, or paid-lock state
  changes during the build.

## 2026-07-30 — Jekyll's full candidate converged to one hash-bound repair

- The 92-chunk Charon full candidate is not a broad regeneration problem.
  Five deterministic listening samples scored 9.4-9.5 with confidence 0.95
  and no fatal flags; only `chunk_0036` failed at 8.4 with confidence 0.90.
- The active English release policy is
  `platform_audiobook_acceptance_v4_89`. The existing 8.4 score still fails;
  changing a label or threshold in a report is not a repair.
- Keep the established `en-GB-Chirp3-HD-Charon` narrator and exact plain text,
  but test rate 1.00 for the intense Lanyon/Jekyll dialogue instead of the
  rejected 0.94. This is materially distinct without introducing a one-chunk
  narrator change or SSML/source drift.
- A replacement full manifest must bind the exact source, input manifest,
  rejected full manifest, failed listening report, chunk text, old audio hash,
  and new synthesis fingerprint. It must preserve 91 audio files byte-for-byte
  and prove that exactly one ordered audio hash changed.
- Full audio-derived ASR and measured-sync QA must run again because the
  replacement changes timing. Five listening judgments may be reused only
  when their source and audio hashes match the independent prior report;
  `chunk_0036` always requires one new judgment under the paid lock.
- The provider-free preflight passed with an estimated TTS cost of USD 0.03846.
  No synthesis, upload, publication, release mutation, or paid-lock write ran,
  and Jekyll remains audio-hidden.

## 2026-07-30 — A first-package canary needs an explicit no-audio identity

- A package-versus-legacy rollout cannot safely represent a newly approved
  title because the title has no approved legacy audio. Model the active
  fallback as the canonical SHA-256 of slug, source hash, manuscript hash, and
  `NO_PUBLIC_AUDIO`; any other missing-package descriptor fails closed.
- Keep the 5% checkpoint transport-only. The exact candidate cohort may call
  the package manifest and segment routes, while the 95% hidden cohort receives
  404. Catalog, Home, legacy audio routes, and reader Listen controls remain
  disabled for every customer until a separate production-proof promotion.
- Bind the canary to exact QA-candidate evidence, Tier A rights, both covers,
  ASR/source at least 9.7/0.98, listening dimensions at least 9.2 with
  confidence at least 0.90 and no fatal flags, production plus independent DR
  receipts, a hidden-before browser proof, and an explicit owner environment
  approval.
- Do not Redis-cache a cohort manifest. Use a sticky HttpOnly cookie,
  `private, no-store`, and `Vary: Cookie`; segment requests never mint a new
  identity.
- Generic rollout advancement is unsafe for a new title because it lacks the
  mandatory post-deploy manifest, 206 Range, timestamps, and browser playback
  evidence. Permit only rollback to 0 or explicit revocation until a dedicated
  proof-bound promotion command exists.

## 2026-07-30 — New-title canary quality must bind language and policy

- A single hard-coded listening cutoff is not safe across languages. Bind the
  QA-candidate release descriptor to the exact controlled language and the
  exact policy used by the hash-bound six-sample report.
- English QA candidates use
  `platform_audiobook_acceptance_v4_89`: every listening dimension and overall
  score must be at least 8.9, confidence at least 0.90, and every fatal flag
  false.
- Bengali QA candidates retain
  `bengali_audiobook_acceptance_v2_92`: every listening dimension and overall
  score must be at least 9.2, confidence at least 0.90, and every fatal flag
  false.
- Unknown languages, cross-language descriptors, stale policy names, missing
  policy bindings, and sub-threshold evidence fail before controlled
  publication mutation. ASR 9.7, coverage 0.98, exact ordered content,
  measured sync, rights, covers, primary/DR receipts, endpoint and browser
  proof remain unchanged.
## 2026-07-30 — The Gift of the Magi cover-truth repair

- A technically valid 1600×2400 cover can still be customer-invalid when it
  exposes release-operations language or renders truncated back-cover copy.
  Dimension and URL checks are necessary, but not sufficient.
- The fastest safe repair was an original deterministic composition using only
  programmatic watch, chain, comb, ribbon, frame, and star-field primitives,
  with exact title, author, and short description loaded from both controlled
  publication mirrors.
- Run accurate OCR against both master files after visual review. For this pair
  macOS Vision recovered the complete normalized front and back copy exactly,
  proving that the sentence is neither clipped nor overlapped.
- Keep upload and canonicalization separate: upload immutable content-addressed
  Cloudinary candidates, download and verify each full SHA-256, then use the
  controlled promotion transaction. Cover approval does not approve audio; Gift
  remains reader-live and audio-hidden.

## 2026-07-30 — Jekyll objective QA isolates a real chunk 9 narration omission

- The completed `medium.en` full-title report is valid objective evidence but
  not a release pass: ASR/source scored `9.8831`, coverage `0.9873`, and
  precision `0.9894`, while ordered content integrity failed.
- Before spending on a full alternate-model pass, adjudicate the weakest units
  plus exact-pass controls. Exact-revision `whisper-large-v3-turbo` and
  `whisper-large-v3-mlx` both failed the five-unit strict contract, so neither
  justified a 92-unit inference run.
- `chunk_0009` is a narration defect, not a `medium.en` limitation. Three
  recognizers omit the same 16 source tokens and measured timestamps cross
  directly from `or` to `this` at `31.92s`, leaving no hidden speech interval.
- `chunk_0045` is substantially a `medium.en` limitation: full large-v3
  improved it from `9.4698 / 0.9184` to `9.8940 / 0.9929`, but duplicate and
  unexpected tokens still prevent strict content integrity.
- Strong controls matter. Full large-v3 exactly passed controls 8 and 64 but
  regressed control 71 with duplicated content and a zero-duration word
  timestamp, independently blocking model-wide substitution.
- Stop before listening, upload, publication, or release mutation. The cheapest
  safe next action is a no-provider-call, sentence-boundary-safe
  `chunk_0009` repair preflight that preserves all other audio byte-for-byte and
  binds fresh objective QA before any provider call.

## 2026-07-30 — Jekyll chunk 9 can be repaired without discarding chunk 36

- Always build a second repair against the newest immutable parent candidate.
  Jekyll's current parent already contains the completed `chunk_0036`
  replacement; planning from the older root manifest would silently lose that
  work.
- A source chunk can start and end mid-sentence while still containing a safe
  internal splice. For `chunk_0009`, replace only the defective clause between
  the measured word anchors at `30.10s` and `31.92s`; keep all other 91 files
  byte-identical.
- Generate surrounding prose for prosody, but retain only the exact aligned
  repair clause. The 192-character context contains a left clause anchor, the
  complete missing text, a sentence stop, and a right sentence anchor. Blind
  time-only cutting and estimated alignment remain forbidden.
- The bounded plan costs an estimated `$0.005760`, preserves the local Charon
  voice/rate/pitch, and has no provider or release authority. Its future paid
  holder is scoped to one private `chunk_0009` context-window call.
- After a repair, changed audio invalidates inherited evidence. Require fresh
  objective and listening judgments for `chunk_0009` and the already-repaired
  `chunk_0036`, then full-title strict objective/sync proof before package-v2
  construction.

## Homepage Primary Shelf Taxonomy and Ginni Crop - 2026-08-02

- The authoritative 32-title Sprint 1 set must map one-to-one to the five homepage editorial shelves; do not repeat titles to increase visual density.
- Ginni's canonical 1122x1402 front and back assets contain no white top/bottom padding. The visible bands came from applying `object-fit: cover` to the wrapper while the nested image retained global `object-fit: contain`.
- Shelf counts should describe all uniquely mapped reader titles, while cover compositions may show a smaller truth-gated selection of canonical graphical covers.
- Sparse shelves should use spotlight or duo composition; they must not borrow duplicate titles from another primary shelf.

## Gitanjali controlled cover promotion - 2026-08-05

- The production cover-status queue is Sprint 1 scoped and can omit an approved controlled publication; query the exact candidate IDs when release evidence is title-specific.
- Keep immutable upload and canonical promotion separate. Both Gitanjali candidates were content-addressed, downloaded again, and matched the approved SHA-256 values before promotion.
- Canonical promotion requires identical primary and backend controlled-publication mirrors. Add the missing primary mirror before running the transaction rather than bypassing the mirror gate.
- Cover publication must preserve reader/audio separation. Gitanjali remains reader-live with 104 ready chapters while audiobook fields stay disabled and no public audiobook route is authorized.

## Cost governor baseline and controller repair - 2026-08-07

- Cost work must begin from actual billing data. The prior Railway period cost $98.89, of which $87.40 was memory; the current period projects $2.50 after earlier runtime reductions.
- A scale request can create a skipped desired deployment while the old successful manifest stays active. Verify active instances and replica metadata; never count the requested topology as a saving.
- Redis contains only ten cache/RUM keys and no authoritative namespace, but service deletion still requires a deployed no-Redis canary and a rollback window.
- Complete push-range checks prevent a multi-commit push from hiding backend or frontend changes. `HEAD^..HEAD` is not an adequate deployment scope gate.
- Scheduled monitoring should verify lightweight liveness. Catalog and reader-manifest checks belong in manual deep monitoring and post-deploy canaries, not a 30-minute loop.

## Publication manifest conveyor pilot - 2026-08-08

- Reader, audio, and commerce readiness are independent lanes. `NOT_REQUESTED` audio or commerce must never block a validated reader release.
- A single checksum-bound manifest should own release truth. Static allowlists remain compatibility inputs only and must not be a second approval authority for migrated titles.
- Chapter boundaries belong in each import manifest when a source has nested Roman numerals or other ambiguous headings. Sherlock's exact story-heading regex produced the canonical 12-story index; generic heuristics produced false chapters.
- The migration conveyor must regenerate the legacy checksum bundle whenever it writes chapters or metadata, otherwise compatibility validators can reject otherwise identical content.
- Readiness is not publication approval. The Sherlock pilot remains `READY_FOR_APPROVAL`, `exposed=false`, with no audiobook requested.

## Agentic AI reader-only publication - 2026-08-08

- First-party original works need an owner attestation, copyright owner, commercial-use permission, rights basis, approval tier, and verification timestamp; public-domain dates and external source URLs are not applicable evidence and must not be fabricated.
- Imported technical manuscripts can contain safe HTML mixed with top-level plain text. Normalize those text runs into semantic paragraphs or code blocks before hashing; otherwise reader pagination can serialize later markup as visible text.
- Validate the backend under the Railway launch topology (`backend/start_prod.sh` uses `uvicorn server:app`). A repository-root `backend.server:app` launch can exercise a different optional-import fallback and produce misleading escaped output.
- Agentic AI With Python passed a 14-chapter index, sanitizer audit, focused tests, production build, and desktop/mobile browser QA. Publish it through the reader lane only; audio remains `NOT_REQUESTED` and hidden.

## Pather Panchali private audition closeout - 2026-08-08

- A strong opening and ending do not compensate for failed dialogue and punctuation-heavy passages. The four-passage Sarvam `bulbul:v3` Simran audition closed at `8.0` with `0.85` confidence and a fatal list-reading-rhythm flag.
- Keep the existing reader-only edition live and audio hidden. A DNS-blocked source reingestion must not replace or downgrade the approved reader artifact.
- Do not widen this audition into full-title TTS. The next audio attempt must use a materially different provider or an approved human/licensed path and must pass every 8.9/0.90 listening and objective gate.

## Local audiobook WAV scratch cleanup - 2026-08-08

- `output/**/_work/*.wav` files from legacy polish runs were decoded intermediates: 2,538 files / 27,621,225,718 bytes, with zero tracked references.
- A safe local cleanup must hash every target, bind the manifest to `HEAD` and `origin/main`, validate path, size, and modification time before deletion, and leave intent plus tombstone evidence.
- Preserve provider `_work/*.mp3` chunks, final MP3s, source audiobooks, timestamps, VTT, chapter, and metadata sidecars. Their counts and bytes remained unchanged.
- This cleanup is storage hygiene only; it does not alter release readiness or public audio state.
## Parameterized Colab audiobook conveyor - 2026-08-09

- Title parameters, canonical controlled-publication identity, voice, model, territory, and owner intent belong in one auditable configuration block; generation cells must not contain title-specific paths or manuscript uploads.
- Adaptive narration decisions may tune speed and punctuation-aware silence within bounded ranges, but they must preserve canonical token order and produce a deterministic attempt fingerprint so failed settings are never silently repeated.
- Representative ASR is a cost and quality circuit breaker. Full synthesis may start only after representative source fidelity passes, and one bounded slower repair is the maximum automatic retry for the same title/voice lineage.
- Emotional expression cannot be self-certified from ASR. Full-title listening remains a human evidence gate at 8.9 per dimension, 0.90 confidence, and zero fatal flags before package construction or public release.
- Colab artifacts are private release inputs, not public assets. Production storage receipts, checksums, endpoint proof, browser playback, and controlled-publication mutation remain separate guarded stages.

## 2026-08-09 - Colab local output with optional private B2 handoff

- Google Drive is no longer required for the Colab audiobook conveyor. Synthesis and QA default to ephemeral `/content/earnalism-audiobooks` storage.
- Optional B2 transport accepts only short-lived pre-signed upload URLs from Colab Secrets; permanent B2 credentials remain outside the notebook.
- The handoff uploads the final MP3 and evidence ZIP only, records local SHA-256 receipts, and never mutates public release fields.
- The safe Colab integration now obtains title-scoped PUT URLs from the protected admin presign route using an admin bearer token; B2 access keys remain Railway-only.

## Mobile home and CTA accuracy - 2026-08-10

- A catalog destination must use browsing language. “Browse Library” is accurate for `/library`; “Start Reading” is reserved for a route that actually opens a reader.
- Pricing language must mirror the product model. Earnalism sells minute-based reading passes, not memberships, subscriptions, seven-day access, or an unimplemented coupon discount.
- One high-intent action per outcome is clearer than duplicate reader links. Dracula now has one primary “Read Chapter 1 Free” action plus a separate pass-discovery action.
- At 390x844, a one-viewport hero, immediate Bengali/English/approved-audio quick paths, zero horizontal overflow, and 44px minimum controls materially improve orientation without changing catalog or audiobook release truth.
- Journey automation must check the current route-specific CTA promise and query parameters. Stale Dracula-first and seven-day-pass assertions can conceal destination drift.

## Mobile CTA V2 production verification - 2026-08-10

- Static source assertions are insufficient for API-fed CTA labels. Production must verify the rendered accessible name after live curation data is applied; an approved-audiobook destination now always renders and announces “Approved Audiobooks.”
- A 44px touch audit must include form controls and short footer links, not only primary buttons and cards. Newsletter inputs and footer navigation now enforce the same minimum target contract.
- When CI stalls before a deploy command, preserve the merged-main gate result and use the repository-equivalent Vercel pull, prebuilt production build, and production deploy sequence; still require custom-domain browser and API canaries before calling the release live.

## Reader UX 9.8 V2 - 2026-08-11

- Fixed reader chrome needs a viewport-bound paper surface at every breakpoint. A large `min-height` can put apparently valid paginated content behind bottom controls even when the page itself has no horizontal overflow.
- Production Gutenberg-style prose may already arrive as one HTML paragraph per source-width line. Repair contiguous top-level fragments conservatively at render time so controlled content hashes, punctuation, word order, and release truth remain unchanged.
- Paragraph pagination on short viewports must split at whitespace without inserting spaces around punctuation. Sentence-token joins changed `8:35` and `M.,`; word-bound chunking preserves fidelity.
- A drop cap is appropriate only on the first content page when the first paragraph starts with a letter. Applying it to every page or to parenthetical front matter produces decorative noise instead of editorial hierarchy.
- Outer-versus-inner window dimensions are not a reliable security signal in split-screen, embedded, or in-app browsers. Keep visibility and explicit copy/print protections, but never blur legitimate reading layouts based on viewport deltas.

## Deterministic catalog exclusion - 2026-08-11

- Removing a title from one catalog list is insufficient when approved manifests, audiobook allowlists, Home curation, bundled snapshots, and installed-app caches can independently restore it.
- A dropped-title tombstone must be a final deny rule with higher precedence than historical publication and audio approval evidence in every runtime layout.
- Listening surfaces should fail closed until canonical API truth arrives; a versioned cache namespace prevents stale installed clients from replaying a previously approved audiobook card.
- Historical publication packets and media are audit evidence, not active release truth. Retain them privately while blocking reader, audio, and admin republication paths.
- Metering must settle the preceding interval from server-stored activity before accepting the next client state; otherwise a pause request can erase time already consumed.
- Native audio cannot attach bearer headers, so protected playback needs a short HttpOnly credential rebound server-side to the active login, exact content, lease hash, and expiry; credentials must never enter media URLs.
- Multi-device authentication and single-device consumption are separate constraints. Keep login sessions available while enforcing one unique account consumption lock and an explicit audited transfer.
- Every lock-releasing path must settle the final server-timed interval transactionally. Heartbeat-only settlement leaves a repeatable sub-heartbeat evasion path through end, transfer, revoke, or stale-session replacement.
- Canonical block segmentation must preserve meaningful text between recognized HTML blocks. Dropping unmatched fragments creates deterministic pages with deterministic content loss, which is still a release failure.
- Access-confirmation copy must describe authorization state, not imply audiobook release state. “Protected listening access verified” is accurate after a lease is issued; “audiobook ready” can overclaim public availability.
- A ledger is not fully canonical if only new metering events have `signed_seconds`. Every compatibility writer, including admin adjustments and migrated wallet rows, must emit the same event shape; health must compare each stored wallet balance with the ledger-derived balance while preserving old rows through `credit - debit` fallback.
- A local MongoDB replica set with synthetic accounts is sufficient to prove transaction, lease, transfer, exhaustion, and 100-request idempotency invariants without copying production data or provisioning paid staging infrastructure. It does not replace remote private-media, CDN-expiry, provider-payment, or physical-device validation.
- A valid audio checksum and high automated polish score do not make an audiobook a master. Preview derivation must remain blocked when canonical source binding, derivative/voice rights, full-book human and accessibility listening QA, alignment QA, or explicit owner release approval is absent.

## PR #269 checksum-bound Dracula master gate - 2026-08-12

- A provider voice name does not prove commercial output entitlement. The retained Dracula bundle records `edge-tts` and `en-IN-NeerjaNeural`, but no Azure customer subscription, paid-tier transaction, request ID, or immutable provider output record binds rights to the exact audio checksum.
- Master approval must be executable, not narrative. Preview generation and registration now require the same packet checksum, exact master SHA-256, canonical source binding, derivative and voice-rights evidence, full-book human and accessibility listening QA, objective alignment, and explicit staging-scoped owner approval.
- A hold packet is useful release evidence but is not an approval packet. Missing human review or owner approval remains missing even when the audio file is intact and automated QA looks strong.

## Checksum-bound accessibility exception - 2026-08-13

- A physical-device accessibility exception must preserve `NOT_TESTED`; owner acceptance cannot be relabeled as a test pass.
- Bind the exception to the exact audiobook attempt fingerprint, audio SHA-256, listening confidence, owner identity, timestamp, and a deterministic exception checksum so it cannot drift to another candidate.
- Limit the exception to VoiceOver and TalkBack physical-device checks. Keyboard controls, chapter navigation, pause/resume recovery, rights, objective/audio QA, listening, storage, endpoint, browser, Git, and deployment gates remain fail-closed.

## Two conversation approvals with automatic continuation - 2026-08-13

- Bind reader approval to the sanitized manuscript and rendered preview; bind narration approval to six or seven exact sample/source checksums, model, voice, quality scores, confidence, fatal flags, and public-release intent.
- Repeated subjective prompts after those checksum-bound decisions add delay. Continue automatically through the remaining machine-verifiable gates.
- Automatic continuation is not automatic success: rights, structure, full-title fidelity, technical audio, storage, CI, browser, production, and post-deployment evidence remain fail-closed.
- Preserve the distinction between `READY_FOR_GO_LIVE` and `LIVE`; post-deployment API, range, playback, cache-control, and stale-URL checks establish live truth.

## Dracula source-document index labels - 2026-08-14

- A chapter number is structural context, not a useful index name when the rest of the title uses journals, letters, or correspondence labels.
- Preserve the source-document convention across the complete index and fill missing labels from the chapter’s actual opening document; do not invent plot-summary spoilers.
- Keep canonical and backend artifacts byte-parallel, regenerate their checksum manifests, and rerun the catalog-wide deterministic index audit after any metadata repair.

## Dracula server-owned audiobook release precedence - 2026-08-14

- A valid conveyor release can be active in the canonical database while stale controlled-artifact audio-disabled fields still hide public audio.
- Controlled artifacts remain authoritative for reader, rights, cover, and content truth; a schema-matched conveyor with `audio_release_approved: true` may overlay only the server-owned audio-release fields.
- Rotate the public and reader cache namespace when changing release precedence, then require fresh API, range, cache, and browser postchecks before declaring the audiobook live.
- An approved conveyor cannot affect public truth if the Mongo selector excludes the row first. A title-scoped selector exception must require the exact conveyor schema and `audio_release_approved: true`; legacy publication-workflow drift must not justify broadening every controlled-title query.

## Gitanjali checksum-bound hf_alpha candidate - 2026-08-14

- Keep the clean narration as the archival speech master and bind the customer candidate separately when approved ambience is mixed beneath an unchanged speech bed.
- Run full-title ASR on the exact ambience-backed bytes, not only on the clean master. The Gitanjali public candidate passed at `0.985862` similarity, `0.999381` coverage, exact first/last spans, ordered integrity, and zero failed sections.
- Low-latency playback does not require downloading a multi-gigabyte file. A compact `84,510,093`-byte MP3 plus the existing same-origin byte-range proxy and metadata-only preload keeps initial transfer bounded while preserving seek and resume behavior.
- A representative listening approval authorizes automatic continuation only for the exact model, voice, and sample set. The final full-title fingerprint, manuscript checksum, audio checksum, objective evidence, storage receipt, browser proof, and production postchecks remain separate mandatory bindings.

## Mobile-first premium home storytelling - 2026-08-15

- A desktop cinematic composite is not a mobile hero merely because `object-fit: cover` can fill the viewport. The crop can remove the emotional focal points while a defensive overlay turns the remaining image into an indistinct dark field.
- Mobile needs its own composition: portrait-safe negative space for live text, intentional visual anchors below and beside the copy, and a restrained directional overlay that protects contrast without erasing the artwork.
- Release-gate truth belongs in availability logic and evidence, not in customer-facing aspiration. Public headings should describe the reader's desired experience while links and data filters continue to prevent unavailable media from appearing.
- Premium literary typography comes from a controlled display face, optical spacing, short balanced measures, and confident scale; decorative menu language or tiny text would reduce trust and accessibility.
- Exact-copy regression contracts must move with an approved customer-facing rewrite; otherwise a healthy release can fail on intentionally removed legacy language.
- Keep unsupported-audio guards semantic and strict. Removing an ambiguous phrase such as “listen now” from general brand copy is safer than weakening a crawler-visible availability assertion.

## Compact mobile carousel controls - 2026-08-15

- A separate metadata plaque below a mobile cover stage duplicates vertical structure and weakens first-viewport density, even when each piece is individually polished.
- A single translucent rail can preserve title identity, the open action, autoplay control, previous and next navigation, count, progress, keyboard behavior, and swipe behavior while returning more than 80px to the composition.
- Compact must not mean miniature: keep every interactive control at least 44px, truncate metadata before shrinking controls, and verify the 320px narrow-phone breakpoint independently.

## Luxury mobile headline typography - 2026-08-15

- A premium serif becomes loud when scale, weight, and color emphasis all compete at once; reduce at least two before changing the message.
- Preserve one clear typographic gesture. A light masthead with a single italic keyword feels more editorial than applying the same gold weight to an entire phrase.
- Font fallback is part of brand quality. Pair the display face with a compatible high-contrast serif before the generic Georgia fallback so intermittent font loading does not collapse the intended voice.

## Mobile hero photographic story layers - 2026-08-15

- A supplied photograph can enrich an established hero without replacing it when the recognizable objects are isolated through position, opacity, and a soft mask rather than a hard rectangular crop.
- Decorative secondary art should remain lower priority than the primary hero image, carry empty alternative text, and stay beneath live copy and controls.
- Compress first-viewport story layers aggressively. The owner-supplied 482x564 PNG retained its useful detail as a 466x564 WebP under 20KB.

## English 25-title controlled batch preflight - 2026-08-15

- Resolve title identity before repairing artifacts. The requested long Jekyll title maps to the existing production `jekyll-and-hyde` 11-chapter reader; the incomplete long-slug duplicate must remain excluded rather than creating a second edition.
- Historical audio URLs are not reusable release evidence. Twenty canonical packs carried stale mapped-audio claims, so every title was normalized to reader-only/audio-hidden and rebound to a checksum manifest that excludes itself.
- Structured rights metadata can be deterministically recovered from the existing internal source-rights notes without changing reader content. All 25 resulting rights decisions pass for the unchanged `IN` territory.
- Missing production covers can be repaired without external art licensing or heavy assets. Eighteen original vector-based front/back pairs passed local visual smoke and stay below 26KB per WebP against the 180KB feature budget.
- A reusable Colab notebook must fail closed at rest: blank title and voice, Drive persistence on, GO LIVE off, no object key, no public intent, and a hard stop before full synthesis until the checksum-bound six-sample gate is approved.

## Durable Colab checkpoint enforcement - 2026-08-15

- A persistence toggle is not durable evidence unless the notebook actually mounts Google Drive and writes the immutable attempt directory beneath `MyDrive`.
- Derive the final run directory only after the source-bound attempt fingerprint exists. This prevents unrelated retries from sharing an unfingerprinted folder and makes every sample, unit, ASR chunk, and checkpoint resumable against one identity.
- Bind launches to an optional exact repository commit and record the resolved commit in the durable output. A moving branch name alone is insufficient provenance for a long-running synthesis job.

## Shortest-first English reader repair - 2026-08-16

- Hard-wrapped plain text must be reflowed from authoritative blank-line blocks before reader publication. Whitespace-normalized equality is a strong guard that restores semantic paragraphs without changing words or order.
- Every controlled reader intended for Railway needs a byte-identical backend mirror and a checksum manifest that excludes itself. A valid root packet alone is not deployable truth.
- Translated public-domain editions must bind translator identity and death year into the rights engine. Author-only evidence is incomplete even when the source repository labels its U.S. copy public domain.
- Contradictory duplicate approvals and stale audio URLs never combine into release evidence. Retain the canonical audio-hidden decision, invalidate unmeasured synchronization, and leave remote media untouched until a separately authorized cleanup workflow exists.
- Forbidden-furniture checks alone do not detect hard-wrapped reader corruption. Paragraph-count and words-per-block shape metrics exposed The Happy Prince and An Occurrence at Owl Creek Bridge as hundreds of print-line fragments despite otherwise valid boundaries.
- Publisher edition banners need explicit fail-closed patterns. The private preview renderer now rejects `THE MILLENNIUM FULCRUM EDITION` before a human gate can approve it as reader content.
- Reflow repairs must bind the immutable raw-source hash, prove normalized narrative equality after allowlisted furniture removal, rebuild root and backend packets byte-for-byte, and invalidate estimated synchronization before any preview is rendered.

## Live pilot audio truth reconciliation - 2026-08-16

- A successful database-owned audiobook release can leave a controlled reader pack stale: the public API and proxy may serve approved exact bytes while the nested reader manifest still says audio is disabled.
- Reconcile that split without re-uploading media: bind the production object to the exact attempt fingerprint, manuscript hash, audio SHA-256, size, duration, human approvals, objective QA, residual accessibility decision, API 200, Range 206, and observed browser playback.
- Keep the raw private storage URL inside controlled server artifacts; public projections and reader manifests must expose only the same-origin release-gated API route.
- A publication manifest must represent approved audio as an independent lane. Reader approval cannot imply audio approval, and approved audio requires explicit release evidence, passing audio QA, a checksum, a fingerprint, and a mapped MP3 asset.

## Live pilot audio truth reconciliation - 2026-08-16

- A successful database-owned audiobook release can leave a controlled reader pack stale: the public API and proxy may serve approved exact bytes while the nested reader manifest still says audio is disabled.
- Reconcile that split without re-uploading media: bind the production object to the exact attempt fingerprint, manuscript hash, audio SHA-256, size, duration, human approvals, objective QA, residual accessibility decision, API 200, Range 206, and observed browser playback.
- Keep the raw private storage URL only in the database-owned conveyor; controlled file packs, public projections, and reader manifests must expose only the same-origin release-gated API route.
- A publication manifest must represent approved audio as an independent lane. Reader approval cannot imply audio approval, and server-owned approved audio requires explicit release evidence, passing audio QA, a checksum, a fingerprint, an exact same-origin endpoint, and a verified production receipt.

## Post-preview source parity repair - 2026-08-16

- A checksum-bound preview proves what was shown, not that the underlying manuscript matches the authoritative edition. Full source parity remains mandatory before synthesis.
- The Open Boat retained one syntactically malformed sentence that omitted eleven canonical words even though boundary, paragraph, checksum, and preview gates passed.
- Repair only the exact source-proven phrase, bind the official download checksum, regenerate root/backend controlled checksums, invalidate the previous preview fingerprint, and keep audio hidden until a fresh owner gate.

## Long-form print-line reflow repair - 2026-08-16

- A complete long-form narrative can still be reader-invalid when every physical source line was promoted to a paragraph; source parity and reader structure are separate gates.
- For The Great Gatsby, bind the exact official download first, split only on the nine canonical chapter headings, join wrapped lines only within source-delimited paragraphs, and prove normalized narrative equality chapter-by-chapter.
- A semantic reflow changes every chapter checksum and therefore invalidates stale estimated sync and historical reader approval even though no narrative token changes.
- Retaining a legacy cover URL is not cover approval: without repository-local checksum and rights/provenance evidence, keep the exact-title cover gate blocked and the repaired reader private.

## Great Gatsby deterministic reader repair - 2026-08-16

- Centered Roman chapter headings in the official Gutenberg plain-text edition provide deterministic nine-chapter boundaries; blank-line blocks restore semantic paragraphs while whitespace-normalized equality guards every word, punctuation mark, and ordering decision.
- A historical remote cover URL is not exact-slug graphical-cover proof. Keep the reader private and do not render an approval preview until the cover passes the active cover policy.
- India release evidence for Fitzgerald must cite Copyright Act 1957 Section 22 and the 1940 death year, not rely solely on United States public-domain reasoning.

## Enchanted April deterministic reader repair - 2026-08-16

- The official 2025 plaintext preserves exactly 22 chapter headings; exact source-byte hashing and whitespace-normalized chapter comparison make semantic reflow deterministic. Chapters 19 and 22 also restore two exact phrases omitted by the prior package, with no editorial rewriting or reordering.
- India release evidence for Elizabeth von Arnim must cite Copyright Act 1957 Section 22 and her 1941 death year; the work entered India's public domain on 1 January 2002.
- Exact-title deterministic vector covers may pass the graphical-cover gate only when dimensions, bytes, checksums, and no-external-art provenance all match the repository audit.

## Picture of Dorian Gray canonical reader repair - 2026-08-16

- PG 174 is the revised Preface plus Chapters I-XX edition. The duplicate `the-` slug was an exact ordered subset: it omitted the Preface and two 12-word passages accidentally absorbed into chapter titles, and contributed no unique narrative.
- Duplicate retirement is recoverable when every retired file is checksum-bound to the pre-repair Git commit and a tombstone records the exact recovery path.
- Oscar Wilde died in 1900; India Section 22 places this work in India's public domain from 1 January 1961. Cover provenance remains an independent fail-closed gate.

## Release-truth reconciliation - 2026-08-21

- A reader package marked `reader_approval_required` must be absent from every historical live allowlist and SEO surface; stale promotion records cannot override a current checksum-bound approval blocker.

## A Ghost Story P0 cover correction - 2026-08-30

- Semantic inspection and the authoritative Cloudinary mapping both confirmed that the active A Ghost Story front/back pair belongs to Bharat at the Crossroads; treat it as `WRONG_TITLE_ART`, not as a neutral placeholder.
- Text-free art plus deterministic typography can be prepared privately and checksum-bound without changing release truth. Private artwork review, candidate upload, and canonical assignment remain separate owner-gated actions.
- The assignment-review package validated 47 focused backend tests, eight frontend cover-contract tests, the production build, static SEO, and cover audit. `regression:ci` is not green until its browser journey receives a fully completed loopback UAT service; do not misstate the partial runner attempts as a pass.

## A Ghost Story controlled promotion - 2026-08-30

- The existing checksum-bound promotion mechanism fails closed when controlled-publication file trees differ. Restore byte-identical mirror parity before promotion; do not bypass the mechanism or write MongoDB directly.
- Explicit owner assignment approval bound to both image SHA-256 values allowed only the plan-defined cover fields and the mechanism-owned audit timestamp to change. Reader, audio, publication, rights, source, and Reading Pass truth stayed unchanged.

## Reader fixture identity containment - 2026-09-05

- A visual-review fixture must never provide fallback chapter identity on a production reader route. If the canonical page endpoint fails or its chapter identity does not agree with the manifest, the route must fail closed instead of rendering fixture metadata or text.
- A reader card marked live while Reading Pass v2 is disabled is a separate availability defect. Contain the identity violation first, then restore or truthfully withdraw reader availability through a distinct evidence-backed change.
- A release workflow's production-surface hash is an authority, not a cosmetic constant. Derive and contract-test it against the checked-in reviewed source so a real source change cannot make post-capture evidence fail solely through a stale baseline.

## P1 rollback baseline reconciliation - 2026-09-05

- `READING_PASS_V2_ENABLED=false` disables the v2 canonical-page and entitlement path; it does not revoke a title's independently approved `PUBLIC_READER` release state.
- Rollback evidence must preserve correct public Book Detail, reader-route, and manifest identity while proving page 4+ remains protected, audio remains exactly zero seconds, and no cross-title fallback can render.

## P1 neutral provider rollback rehearsal - 2026-09-05

- A neutral D0 → D1 redeploy → D2 provider rollback can prove exact code/image restoration and flag-false safety without enabling Reading Pass v2 or changing release, content, rights, payment, Mongo, or Redis state.
- HTTP 200 for a public reader route does not itself prove reader availability: production currently hydrates `Reader unavailable` because canonical v2 page 1 is feature-disabled. Keep that P1 availability defect distinct from the preserved PUBLIC_READER metadata and the successful protected-content/audio rollback boundaries.

## 2026-09-16 — Reader session and navigation repair

Lease renewal changes must not clear or refetch the current page. Separate content loading, valid server access, and session balance. A 200 renewal can still be Paused, Exhausted, or Stale; only a current Running grant authorizes protected content. Serialize renewal and settlement, preserve retry idempotency, bound network requests, and stop active renewals when no valid page is displayed. Production models must not inherit visual-fixture images, dates, genre, rights, or reading estimates. See `internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/READER_REPAIR_20260916_review.md`. Customer paid-time testing and live release remain unverified.

## 2026-09-16 — Reader auth recovery follow-up

PR #400 is deployed at `3a539e96572754f5d05d2ade05c2d3cce17b9075` / `main.98bb273e.js`; Frankenstein free-page navigation, preferences/focus, Library exit, and fixture-metadata removal passed the live check. The subsequent anonymous state has no confirmed live cause. Source review separately confirmed that no-redirect bootstrap also disabled refresh and that raw token equality rejected valid rotation. Track authentication identity separately from token rotation, share one bounded refresh, and reject stale responses after logout or a newer login. Terminal 401 and genuine 403 must remain denied; a refresh transport failure is not proof that the refresh cookie is invalid. The local follow-up passed 29 focused tests, 408 full frontend tests, the build, 2,502 SEO assertions, and 46 workflow checks, but is not released. Secure sign-in remains pending; zero of the authorized 120 paid seconds have been used. See `internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/READER_AUTH_FOLLOWUP_20260916_review.md`.

## 2026-09-16 — Reader balance and personalized manifest follow-up

A public edition manifest is not an authenticated wallet authority. Use strict identity-bound profile/session values; reject malformed or stale values and preserve newer session evidence against delayed profile responses. Shared balance updates must not trigger page refetches. Personalized manifests must not share an edition-only ETag across guest, account changes or wallet updates: the candidate disables storage and 304 reuse with Authorization/Cookie variation. Focused frontend checks passed 56 tests; actual backend cache/CORS checks passed 14 tests. Fresh CI and separate frontend/backend deployment proof remain required. No customer financial data is recorded here.

## 2026-09-16 — Preserve repeated headers in release evidence

PR #401 is merged and its Railway deployment is provider-confirmed, but the initial cache canary passed only 11/13 checks. Both manifest probes were 200/private/no-store/no-ETag. Converting HTTP headers to a dict and selecting the first case-insensitive match can erase required Vary tokens. Preserve repeated raw fields and combine case-insensitive values before evaluating the unchanged gate. Origin/edge Vary loss remains unproven until the corrected canary runs; parser repair does not itself prove deployed cache compliance. See `internal/earnalism_intelligence/ux_governor/ux_phase_review_packets/READER_CACHE_CANARY_FOLLOWUP_20260916_review.md`.

## 2026-09-17 — Immutable canonical Reader publication safeguard

- Candidate construction, active-version promotion, and rollback must remain separate operations. A count or stored checksum label is insufficient: verify every retained page's ordered identity, content hash, and the manifest derived from those pages before a pointer can change.
- Bind promotion to both the active version and its generation, persist an operation result in the same transaction, and recover an uncertain commit only by retrying the identical operation ID. A new operation must never guess whether the old commit applied.
- Reader leases and saved text positions must identify the retained publication version they use. Legacy unversioned sessions fail closed for protected pages; old bound sessions can read their retained version after a newer version becomes active.
- This source validation did not prepare, promote, or roll back Agentic AI With Python or any production title. Reader-only and no-TTS truth remain unchanged; exact-head review, deployment, and title-scoped Stage 3 checks are still required.

## 2026-09-17 — Reader publication operation replay correction

- A globally unique operation ID must be bound to a versioned, complete intent: canonical title, operation kind, target immutable version, and the promotion preconditions. Returning a globally matched durable result without validating that identity can report Book A's success for Book B without mutating Book B.
- Model coverage is not transaction evidence. The release gate now executes isolated-Mongo replica-set coverage with independent sessions, deterministic overlap, a disposable namespace, and real indexes; an injected fault inside a real transaction is recorded as an injected application fault, not as a MongoDB incident.
- Legacy activation-operation records may be recovered only where their own stored result and digest establish the full identity. Ambiguous or contradictory records fail closed and do not alter an active publication pointer.

## 2026-09-23 — India pilot full-free Reader candidate

- A three-page preview is not a complete launch when checkout is disabled. The proprietor chose full, free, no-debit reading only for the three accepted India editions; this does not alter rights acceptance, held titles, audio, commerce, or other territories.
- Reuse authenticated canonical-page leases with an explicit free entitlement. Check the signed India proxy assertion and immutable accepted Reader-delivery decision on admission and renewal; bind the session to the current publication pointer; never turn a zero wallet balance into an access denial or a debit for this entitlement.
- Local focused backend, frontend, proxy and build checks are supporting evidence only. Exact-head hosted regression, protected merge, deployed-version proof and real production Reader smoke remain required before declaring customer readiness.

## 2026-09-23 — Post-launch Reader and presentation completion candidate

- The active V2 Reader uses immutable server-defined canonical page indices; only the legacy Reader has viewport-derived pagination. Typography and viewport changes must not renumber V2 pages or move saved progress.
- The pilot/free versus future metered choice now has a single server-owned controlled-launch mode. The metered path remains closed without enabled commerce and separate accepted Pass uses; the frontend derives current free access from the manifest.
- The homepage's second social rail duplicated the shared footer social navigation. Keep one configured footer set with visible names and secure external-link attributes; layout capacity for nine covers must never create extra publication authority.

## 2026-09-24 — Bengali rights clearance Sprint 1, Bankim Cohort 1

- Bound six title-level India/source records to their canonical chapter hashes and exact identified Wikisource revisions. The author’s ordinary lifetime-published works have India Section 22 term evidence; this does not itself clear each reused transcription or edition layer.
- The identified Bengali Wikisource transcription layer is recorded as CC BY-SA 4.0 with attribution/change/share-alike conditions; the underlying public-domain literary works, scans, editorial additions, and Earnalism-created covers remain distinct rights layers. No attribution implementation or source-text verification is claimed for the six titles.
- Legacy package approval/public flags were stale relative to the current three-title pilot allowlist. Root and existing backend mirrors were reconciled to explicit hold metadata with checksums; canonical Bengali chapter content and controlled launch configuration were unchanged.
- The onboarding validator now separates evidence readiness from actual Reader release: a complete package may be `READY_FOR_COMMERCIAL_RELEASE` while still unlisted, held, and denied until the separate hash-bound release decision, package approval, and allowlist controls pass.
- Five titles still lack complete exact-edition comparison; Indira has only a seven-of-eight chapter similarity diagnostic and a source-fetch rate limit, not text verification. Cover external-component provenance and title-specific edition/editorial questions also remain. Yugalanguriya was not reopened; Cohort 2 was not started.

### 2026-09-24 — Indira chapter-six source discrepancy follow-up

- The revision-bound 1873 Wikisource transcript and the visually inspected facsimile (printed page 33, PDF page 35) both contain two paragraphs after Earnalism's former chapter-six ending. The exact source continuation has been restored to the canonical and controlled chapter text; derived content/provenance hashes, word counts and package checksums were rebound. The original raw source remains unchanged. This closes only chapter 6; the other seven chapter comparisons remain incomplete, so Indira is still `HOLD_SOURCE` and unpublished.
- The onboarding validator previously equated a CC BY-SA attribution flag with all license obligations. It now separately fails closed unless title-level evidence confirms attribution, source/license links, a changes notice, ShareAlike treatment, and no incompatible additional restrictions. These are all currently unevidenced for Cohort 1; test success means the holds are enforced, not that any title is cleared.

### 2026-09-24 — Indira chapter-eight source comparison

- Pinned Wikisource revision 1910620 for the 1873 edition's printed pages 38–45 matches Earnalism's full canonical chapter-eight Bengali text after removing the source title/chapter heading, page furniture and presentation whitespace. No literary reading was changed. Chapter 8 is now resolved; only chapters 1–5 and 7 remain to compare. Indira remains held and unpublished; do not infer whole-book `TEXT_VERIFIED` from this chapter result.

## 2026-09-24 — V2 Reader page-turn continuity candidate

- The V2 route mounted a full-page `Opening page` state whenever the selected canonical page request was pending. That unmounted the Reader shell, reset focus/scroll on each re-entry, and made the perceived normal-turn delay equal to the page request latency. Manifest and stable session state were already loaded once; progress persistence was already asynchronous, so neither was the measured root cause.
- A deterministic lifecycle test with a 400 ms delayed page-4 endpoint confirms the old page remains readable and the same Reader article remains mounted throughout; only an inline status appears after 400 ms. The same harness confirms page 5 is fetched once into the authorization-bound adjacent cache and selected with zero fake-clock elapsed time. These are controlled test timings, not production-network measurements.
- The cache key binds book, manifest version, page/hash and preview-or-session identity; entries are LRU bounded and the active window is N−2…N+2. Protected prefetch uses the existing Reading Pass page endpoint and is skipped without a running session; cached possession does not authorize rendering. Production latency, payload bytes and India authenticated browser timings remain unmeasured in this workspace and must not be inferred from the mock.
- Focused Reader/cache suite: 56 passed. Production build and static SEO verification pass. The full local frontend suite has one unrelated baseline failure: `chapterIndex.test.js` expects 96 manifests while the clean base tree contains 95; current-main GO LIVE regression workflow is green, and this Reader change does not touch that test or publication data.

### 2026-09-24 — Canterville India evidence preparation

- Bound the complete canonical narrative byte-for-byte after whitespace folding and removal of only the seven source Roman-numeral chapter labels; case, punctuation, spelling, and word order matched the repository's identified Project Gutenberg source text exactly.
- Corrected the old source note's unsupported worldwide/free-reuse wording. India clearance is based on Copyright Act 1957 section 22 and Wilde's evidenced 1900 death; the source is the 1906 John W. Luce edition as represented in PG eBook 14522, with Wallace Goldsmith illustrations excluded. The PG license/trademark material is not carried into the Earnalism Reader and no PG branding is used.
- Verified both first-party vector cover files against the recorded audit hashes. Root/backend publication packages remain unexposed and outside the three-title pilot allowlist; this title waits for the separately authorized commercial cutover.

### 2026-09-25 — India commercial entitlement cutover candidate

- Applied the owner's uniform six-title India release direction in a local candidate: pages 1–3 remain the free preview, page 4+ requires valid server-authorized Reading Pass entitlement, and old pilot-full-free evidence is retained only as historical provenance.
- Public checkout and audio remain disabled. The live Razorpay config endpoint returned `available=false`, `configured=false`, `mode=disabled`, so no purchase can be accepted; this does not grant protected full-text access.
- Reconciled homepage fallback and static SEO snapshots/validators to the six-title catalogue. Structured Book data now correctly says the full edition is not accessible for free, and static book routes offer only the 3-page preview.
- Focused backend access/publication suites passed 93 tests; full frontend passed 472 tests; production build and all 34 static snapshots passed. Broad local backend tests cannot be counted as a release pass: integration groups require a local API/Mongo service and produced connection errors; hosted required CI remains authoritative.
- No production deployment has occurred in this worktree. Do not declare customer or commercial go-live until exact-head CI and all enabled-commerce disclosures/provider actions are complete.

### 2026-09-25 — PR 433 exact-head CI reconciliation

- The first commercial-cutover candidate failed three checks for bounded consistency defects: a historical UI baseline was being reused after an authorized copy change, two auth-page sentence delimiters did not match the locked product-copy contract, and a rights-package gate/test confused nine retained accepted registry records with six current live titles while three backend package mirrors were stale. The active per-title hashes and six-title allowlist are the release authority; historical registry entries remain preserved.
- Focused repairs keep the historical baseline intact, add a separately bound owner-authorized copy-transition baseline, align only duplicate backend hashes/checksum inputs to existing root evidence, and clarify the auth sentence. Rights-package tests pass 4/4; home-baseline tests pass 7/7. Fresh PR exact-head CI is still required.
- The production payment-config endpoint returned `available=false`, `configured=false`, and `mode=disabled`; paid checkout remains off and page-4+ access remains denied without server entitlement. This is an external payment-activation blocker, not a rights or preview-release failure. No merge, deployment, payment activation, audio, or production mutation has occurred.

- The three title repairs were evidence rebindings, not new copyright clearances: canonical text, source/edition, cover provenance, territory, uses, and legal basis stayed unchanged. A White Heron's checksum self-reference and Gift of the Magi's root-only runtime checksum row were removed; active runtime decisions were re-hashed, while superseded candidate and registry bindings were retained as history. Focused backend validation passed 75 tests; the auth-copy suite and production frontend build passed.

- Exact-head CI then exposed a runtime source-selection defect: root historical decisions shadowed missing backend active decisions, denying signed India catalogue requests with 451. The backend is now the active decision source; A Ghost Story received a backend-specific non-circular checksum binding, while Tell-Tale Heart and Radharani received byte-identical runtime mirrors. The release-proxy/CORS, commercial, rights, and evidence-package suites passed 81 tests.

- The next exact-head regression correctly passed the signed CORS contract but revealed that its parity test still read root historical evidence as a live decision. The test now selects the backend package whenever it exists, exactly matching the server's active lookup. Controlled-launch parity, CORS, commercial-launch, and rights-decision suites passed 79 tests. A local full harness reached its browser-smoke stage only to find the checkout lacks root `node_modules/playwright`; this is not a source or release-gate result because CI provisions root dependencies separately.

- The subsequent exact-head regression passed the runtime gates but surfaced broad regression checks still describing the former three-title full-free pilot and enabled checkout. UX, crawler SEO, and reader-content checks now assert the six-title, three-page preview and page-4 Reading Pass contract with checkout and audio disabled. Those three modules passed 74 tests. Direct local full-regression failures without the isolated UAT stack are service-reachability failures, not release evidence; the CI workflow creates the required MongoDB and Redis stack before its authoritative run.

- The seamless-brand review then completed its browser tooling and exposed one final stale static-SEO assertion for the prior three-title pilot. Its contract check now requires the exact sorted six-title India allowlist. The focused seamless-brand batch passed all 21 checks locally; this did not alter customer-facing code or release inputs.

- A subsequent seamless browser journey had the current six-title allowlist but intercepted `/api/books` with only the older three-title fixture, so its equality wait timed out. Added only synthetic catalog metadata for the three additional released titles; no literary text, external source data, production catalog, or rights evidence was added. The journey script parses cleanly and retains the page-4 entitlement/audiobook-hidden assertions.

- The next seamless run completed its full cross-browser capture, but its final evidence generator still selected the superseded free-India Home sections baseline. The separately authorized India-commercial cutover baseline is now the active selector and validator fixture; the former baseline is retained unchanged as history. Focused final-evidence and historical-baseline suites pass (22 and 7 cases respectively). This is a verification-authority repair only: no rights-relevant title input, access behavior, checkout, audio, provider configuration, deployment, or production data changed.

- PR 433 merged after all exact-head checks passed and its Vercel frontend deployment completed. The main production raw-HTML canary then failed because it still required the retired full-free Book CTA and `isAccessibleForFree: true`; the deployed six book pages correctly expose the current three-page preview and `false` structured-data value. A local live-site rerun passes after rebinding the canary and adding a negative test for the retired metadata. This does not prove a fully green post-merge release: the focused remediation still requires its own exact-head CI, merge, deployment, and canary.

- The focused canary remediation passed exact-head CI and merged. Its main workflow correctly skipped a new frontend deployment because no `frontend/` files changed; the prior PR 433 Vercel frontend deployment remains the customer-facing bundle. Direct production route, raw-HTML static-SEO, and frontend regression canaries all pass against the public endpoints. The payment configuration remains `available=false`, `configured=false`, `mode=disabled`; this is an external paid-commercial activation blocker, so customer readiness and commercial go-live remain undeclared.

- Commercial activation audit confirmed that the secure production store already has the Razorpay live-mode prerequisites, while public checkout is still deliberately disabled by both launch controls. The browser-return verification path now requires a fetched Razorpay record with an exact order, amount, currency, and `captured` status before it can invoke the existing atomic, idempotent wallet credit; signed webhooks enforce the same match. Focused backend payment/concurrency checks (11), frontend commercial-contract checks (15), production frontend build, and all 34 static SEO snapshots passed. Remaining work is owner-only: approve the proposed offers and provide the actual India customer-remedy and merchant/grievance disclosure facts before any public-commerce flag can change.

- Any intentional frontend production-source change must rebind both checked-in exact-source authorities in the seamless-brand workflow. PR 436’s first exact-head review correctly rejected the previous fingerprint; the regenerated authority passes the 46-case workflow contract check and does not alter public commerce availability.


### 2026-09-29 — Lane 2 first genuinely new activation batch

- Reconciled the 15 requested candidates against `data/controlled_launch.json`: the authoritative live set remains six titles, and none of these candidates is live or excluded. Package-local `LIVE_APPROVED` values and historical decisions are not launch authority.
- Rebuilt three candidate checksum inventories from exact checked-in package files and generated three schema-valid blocked manifests; refreshed the existing Sherlock Holmes manifest to `READY_FOR_APPROVAL`, unexposed. Alice, Pride and Prejudice, and Frankenstein were inspected read-only because the active rights-binding automation owns them. The remaining nine priority candidates contain audio-enabled package metadata; their builders require audio hashes, so they were left untouched under the text-only Lane 2 boundary. Sherlock Holmes is technically ready but cannot activate without accepted title-specific authorization, cover provenance, and runtime release validation.
- No title is activation-ready. Required rights decisions, edition-bound authorization, and independent cover provenance are absent. Bengali source evidence also needs an exact revision and complete attribution/license/share-alike/change-notice obligations. Frankenstein requires source/edition reconciliation.
- Local catalog authority agrees with the six-title set. The production catalog/reader probe remains held by `RELEASE_PROXY_SCOPE_INVALID` / HTTP 451. Do not change the allowlist or infer publication readiness from package metadata. No evidence was fabricated; audio, payments, entitlements, and production data remain untouched.
- Review record: `internal/earnalism_intelligence/lane2_first_activation_batch_20260929.md`.

- 2026-09-29T06:51:05Z — Sherlock Holmes follow-up: calibrated the public same-origin release probe against known-live `a-ghost-story` (HTTP 200); Sherlock returns HTTP 451 and local runtime validation reports `ACCEPTED_DECISION_MISSING`. The old source hash did not match the current official PG #1661 text, and chapter 2 and 5 omitted source spans; both were restored and all twelve normalized chapter bodies now match. Rebound source/content/provenance and package checksums. Replaced the unsupported India-rights assertion with `review_required`; no registry decision or publication authorization was fabricated. Generated and visually inspected first-party covers with no external art. See `sherlock_holmes_publication_decision_packet_20260929.md`.

- 2026-09-29T08:21:18Z — Sherlock owner/legal decision: bound the supplied approval to PG #1661, source `922e2a12ccb43a4c9544c260b2166c6ad2097aeb5957faeee113f173bb857cd0`, content `d6cb7d46af3d95b071c3783bf3b093f8c8397144ae717bbfbe87b8fc336fdc5c`, India, and text-reader-only uses. The accepted rights record references exact package components and a registered decision hash; the publication manifest is approved while audio remains NOT_REQUESTED. Added only Sherlock to the paired controlled-launch authorities after local runtime actions passed. Production activation is not claimed until exact merged backend deployment and 200/200 control/candidate checks.
## 2026-09-30 — Option B beige exact-head visual review

- The seamless-brand workflow production-surface authority fingerprints checked-in frontend source. The old value exactly matched merged `origin/main`; homepage CSS changes legitimately require deriving and rebinding both authorities to the new source hash. Keep the source-hash equality contract mandatory and rerun fresh exact-head CI; this does not imply production deployment or owner visual approval.

## 2026-09-30T08:10:54Z — Lane 2 autonomous branch convergence

- Merged current main after PR472 into the published Lane 2 history. Preserve the active PR469 Library recovery baseline and newer shell tests; retain both append-only learning histories. The Sherlock package, rights decision, checksum bindings, and exact 12-chapter manuscript remain unchanged.
- Reproduced the merged production source fingerprint `118b5ed10d64b59915789dcac64cc574765e6bcb01a46b0c84d7f1f56afb21c2` from 332 inputs and rebound both workflow authorities. Local validation passed 171 backend tests, 30 frontend tests, 23 evidence-input checks, 46 review-workflow checks, and 767 static SEO assertions. Restore the known generated sitemap after a local build, as required by the existing review workflow.
- Completion remains pending fresh exact-head CI, protected merge, actual successful production deployment, and non-destructive Reader/catalogue/audio/blocked-title verification. Hosted implementation workers do not own production publication.

## 2026-09-30T08:58:54Z — Lane 2 deployment trigger repair

- PR470 merged after all five exact-head gates passed. Railway skipped the merge because an inherited owner-evidence workflow contained an invalid bracket path pattern for the literal `[...proxy].js` filename. Escape the brackets while preserving the trigger and every evidence job; do not disable CI waiting or redeploy the older revision. Production Reader proof remains pending an India-based authenticated context.

## 2026-09-30 — Reader approval and complete catalogue scope

The owner approves the Reader by default when fresh rendered evidence matches the supplied mock. This approval replaces the design handoff only; it does not clear title rights, source editions, covers, protected Reader delivery, or audio. Current CI captures exposed missing literary and notebook details, now implemented with device-local, edition/account-isolated persistence. The repository tests continue to verify access and session settlement. Catalogue reconciliation must use accepted backend runtime rights records; three root package decisions are intentionally historical and must not shadow them.

## 2026-09-30 — Complete catalogue processing through the autonomy pipeline

Processed all 231 inventory/package identities and 1,012 prepared chapters into 162 private manifests with retained file hashes, chapter content hashes, accepted runtime-decision checks, a draft intake manifest and explicit per-title dispositions. Seven titles retain accepted India text scope; 224 require factual evidence, including 69 without a cleared source package. Original content, source, approval and rights bytes are unchanged. The legacy worker review condition excluded successful non-Codex workers; include either successful worker branch. The bounded catalogue task runs without paid generation, customer mutations, publication, new credentials or relaxed scope controls, and its reviewer independently recomputes the evidence.

## 2026-09-30 — Fresh Reader responsive review

Exact-head captures revealed that an older max-width rule hid the notebook at 1024px while retaining a third grid column. Keep the tablet notebook pane through 1279px and place the desktop chapter heading below its toolbar in a full grid row. The 231-title catalogue job and independent review passed on the prior candidate; rerun normal checks and fresh visual captures on the correction before using conditional design approval.

## 2026-09-30 — Catalogue compliance runner repair

Run 36743576217 failed because pytest was absent, after Codex had already stopped on the missing canonical checkout path. Install the checked-in backend requirements before execution, provision the single canonical branch/path from a clean exact-main snapshot, and reject stale or dirty snapshots. Focused backend tests require a synthetic loopback UAT import environment. Frontend tests must run once in CI mode. The existing full regression gate requires Chromium, MongoDB replica-set and Redis prerequisites; prepare privileged browser dependencies before Codex drops sudo and always clean up isolated services. Publish no-progress findings only after successful validation, and report execution failure separately. Keep candidate work on the canonical branch and avoid shell command substitution in commit-SHA status text. Local validation passed 100 backend, 11 catalogue/bridge and 11 frontend tests, plus bootstrap success/dirty/stale cases and shell/YAML syntax. Hosted CI and the corrected main campaign remain pending; no title was newly released.

## 2026-09-30T18:04:51.641651+00:00 — Open issue source preservation and regression repair

Historical positive audio tests must not reopen held titles or put playback URLs back into public manifests. Intercept the current package resolver for synthetic transport checks; retain real current-release rejection and version/range/canary coverage. The full routing file went from 8 failures / 25 passes to 34 passes. Revised manuscript source is already exact (14 chapters), as are seven Commerce artwork crops; both original archive inventories verify. Preserve later approved Option B, current offer semantics and Auth/Account safeguards. Current source inclusion does not prove live accepted-decision publication, authenticated production readback or physical-device UAT. Local relevant backend tests passed 89 and frontend tests 27; require fresh CI before merging. The hosted catalogue worker still had no validated outcome after its step budget. Retain the canonical branch and require automated merge to match its reviewed candidate SHA.


## Catalogue worker identity recovery — 2026-09-30

The pinned Codex action documents that drop-sudo removes the runner account's Docker service access. The earlier campaign nevertheless started Docker after that action, so successful model execution would still be unable to run its isolated validation. Use the supported dedicated unprivileged account instead: verify non-root identity, no sudo/Docker authority, clean exact-head Git reads and shared checkout writes, while the controller retains Docker. Remove persisted checkout credentials and authenticate candidate pushes through the controller-only transient GH_TOKEN helper. Real UID tests must pass hosted required CI; local setuid/group transition is unavailable and is not reported as a pass. Recompute and check the exact source baseline each iteration, preserve existing accepted records/revocations, and reject worker HEAD/branch drift. Approved main advanced through PR #476 to 7348f064f4a9275127512b5f1bf76f365701b745 and was fast-forwarded intact. No source/title/release/product mutation or new evidence acceptance is implied by this orchestration repair.

## 2026-09-30T19:50:44.025492+00:00 — Preserve approved bounds and inspect actual completion

PR #481 is retained in full intent: cancellation of superseded runs, 75-minute job, 18-minute worker, 20 deterministic candidates and at most five modified titles. Its first main run 36766302362 confirms two execution defects: the generated untracked batch makes the canonical checkout dirty and stops the worker; drop-sudo then prevents controller Docker validation (exit 126). Keep the exact validated baseline and batch outside Git and restore only generated snapshots before implementation. The controller validates the fresh main revision; the worker uses read-only Git identity checks because its sandbox protects .git. No failed or blocked worker result establishes evidence exhaustion. Approved main c98a84513d408d2aac6ebfcc795c6146ca68cf61 and all product/source bytes are preserved.

## 2026-09-30T20:28:08.545737+00:00 — Green action is not completed implementation

Run 36770076565 passed all controller checks and full isolated regression, but every worker command failed at startup with EACCES and no candidate was inspected. The action exited successfully and generated a misleading no-progress comment; that comment is corrected in #477. Make the canonical Codex CWD physical and retain only a GitHub workspace alias. Require a completed, exact-source/batch-bound execution receipt with nonempty assessed candidate slugs; reject missing/blocked/started/stale/mismatched receipts before deriving any no-progress or publication result. Receipt guards and their tests cannot be modified by the worker. The controller full regression now finishes normally in about three minutes, so stale conflicting PR #484 was closed without deleting its branch or commits. The symlink explanation remains a hypothesis until actual Codex command startup succeeds. The separate production raw-HTML fallback on approved historical unavailable-title routes is reproduced; preserve PR #476 routing and add truthful unavailable snapshots in a later focused release repair.

## 2026-09-30T20:41:08.735068+00:00 — Preserve approved recovery routes and repair pre-hydration truth

PR #476 deliberately keeps historical Dracula and Selfish Giant Book/Reader/Listener URLs on a safe no-content unavailable page with recovery links and noindex/nofollow. Reverting those URLs to 404 would remove approved continuity. The old raw-HTML canary retained the prior Dracula 404 expectation, and production still serves generic Home/released-book copy before hydration. Add six explicit RELEASE_HELD snapshots and earlier exact/trailing rewrites, retaining all app fallbacks and the unknown-title 404 policy. Require exact unavailable identity/canonical, noindex/nofollow, unavailable access copy, recovery-only links, and no preview/released schema/media/control exposure in both build and production checks. Sixteen independent canary/generator/tampering tests and 27 existing frontend route/unavailable/release tests pass. Current rights, commerce, entitlement, accepted records, source/manuscript and audio authority remain unchanged. Normal source-bound production deployment and canaries remain pending.


## 2026-09-30 — Executed catalogue assessment and report preservation

PR #485 passed actual hosted UID/bootstrap and receipt tests plus complete regression. Run 36773761003 executed the 20-title worker assessment and passed source/batch-bound completed receipt validation; the physical canonical checkout fixes command startup. The worker proposed checksum-only repairs for five still-held packages (the-art-of-money-getting, bn-031, bn-035, bn-036, bn-041). The controller correctly blocked private generated JSON outputs at the unchanged changed-file scope gate, so focused/full validation and publication did not run. These proposals are not accepted releases and no completed-catalogue claim follows.

Retain known canonical and alternate worker generated JSON directories, plus the exact title-package proposal diff, outside Git as an uploaded artifact before restoring only known historical report snapshots. Reject symlinks, non-report files and tracked alternate source without moving it. Keep package changes in the checkout and preserve the existing scope, immutable accepted decision, rights, territory, audio and full regression gates. Use the controller-provisioned setup-python interpreter for model tests; login PATH selected system Python without dependencies. Three real-Git report-preservation fixtures pass. Rebind both existing exact-source workflow authorities after the intentional Vercel rewrite change; this is source provenance, not visual approval. Seven accepted live and 224 held remain the release truth.


## 2026-09-30 — Fresh full-regression snapshot assertion reconciliation

PR #486 hosted permission/archive fixtures and the mandatory snapshot fixtures passed. Full regression run 36776970714 found one latent released-Dracula SEO assertion because that snapshot now exists as the approved unavailable page; 122 other regression tests passed and four were skipped. Retain the positive released-book SEO/schema/canonical checks using accepted A Ghost Story and add unavailable/noindex/no-content assertions for all six historical routes. Do not re-release Dracula, remove its safe page, or disable the regression module. A fresh CRA build is the generator's real production input; reusing an already populated local snapshot root is not fresh build evidence. Require all checks again on the corrected exact head.


## 2026-09-30 — Deployed historical-page repair and worker report ownership

PR #486 merged at cae4d7c8105d14e831e62152403003a8cdad5016 after exact-head protected regression, container, coordination, Auth/Account and editorial checks. The three-browser review and independently downloaded envelope subsequently passed for candidate da340e6f53a6c2e614fb3de0f4f16800c68ead45 (same tree 61e27f91311343ee0a8f0e82f694fb0dcaab00ff). Main regression, actual Vercel deployment (earnalism-oujgqhwpx-sales-8498s-projects.vercel.app, apex alias) and all production route/static-SEO/module canaries passed. Approved product JSX, artwork, manuscript, launch and accepted-decision bytes are unchanged.

Actual campaign 36780560381 executed model commands and 109 applicable tests but correctly failed its incomplete STARTED receipt: default report generation could not overwrite controller-restored files, and three Enchanted April checks depended on /private/tmp/pg16389.txt. Use the explicit private _worker report directory, already covered by the archive guard; do not grant broader permissions or rewrite the approved historical reports. The repository retains the exact official source archive with the required d2d5a31f295361fb742f44729d3de6082cd7bff742a0484cd178731d66ef8370 hash. Use that input for Enchanted April tooling and require all three existing source/cover/private/audio/determinism assertions in normal regression and campaign validation. Those three tests and nine receipt/archive tests pass locally. The new actual-UID read-only-report/worker-owned-output/controller-recovery fixture must pass hosted CI; local UID transition is unavailable. No test is disabled, no new legal/approval fact is invented and no publication follows from dry-run repair plans.


## 2026-09-30 — Prioritize available checksum repairs in a bounded assessment

The last actual worker inspected five external approval/QA holds and changed no package; the earlier completed 20-candidate assessment had already identified five checksum-only proposals. The existing broad deterministic category sorted fewer-blocker approval holds ahead of mechanically repairable exact retained-hash mismatches. Rank exact checksum mismatches first without changing any blocker, accepted record, source or approval field. The five-title limit controls modifications, not an instruction to stop assessing at five held titles. Four tests execute the real selector and retain the 20/5 bounds, live exclusions, stable order and missing-package holds. Require fresh normal CI on the final PR487 head; no no-progress or release conclusion is claimed from this candidate.

## Catalogue controller evidence and bridge PR handoff — 2026-09-30

Campaign 36785743093 genuinely examined 20 selected candidates and passed its completed receipt, release/scope checks, focused tests and full regression. Five title checksum repairs reduce proposed blockers 919 to 912 without changing source/approval bytes, 224 holds, seven accepted titles or audio authority. Independent artifact digest and exact replacement-byte checks passed. The preserved commit b016ca0b2edfaa25fb5c52b656043a5b21bde431 then hit the repository policy that forbids Actions PR creation. PR #488 was opened through the authorized GitHub connection, retaining normal exact-head checks.

A controller smoke reporter also changed its tracked output timestamp after the early scope check. Keep this truthful generated report as exact-byte evidence outside the implementation diff; compare the final source identity against the validated pre-test diff and untracked bytes. Reject any change to result/authentication facts, any unexpected tracked/untracked source change, or a report symlink. Six new fixtures pass locally; fresh hosted validation remains mandatory. Only the specific Actions PR-policy rejection becomes a durable bridge handoff; other errors remain failures. A handoff is not a merge, title release or completed campaign. No repository administration, new credential, paid TTS, approved product/manuscript/artwork or accepted-record change.

Next exact command: `gh pr checks 488 --repo ronik18/earnalism-digital-library --watch --fail-fast`.

The bridge handoff fixture executes the actual controller shell. Export actual PR_HEAD_SHA in the creation step; writing GITHUB_ENV alone exposes it only in later steps. Nine controller evidence fixtures now pass, including only the specific repository PR-policy rejection becoming a pending handoff, unrelated PR errors failing, and normal creation retaining its required-check path. No test invents a merge or executes real PR/network mutations. Fresh amended-head CI remains required.

## Verified second bounded catalogue pass — 2026-09-30

Campaign 36789262625 succeeded on source main 4905cf7f8fb1c22d28e37e193a436650f01c79ba. The actual receipt records 20 examined titles; worker/controller focused and full regression, exact final source guard, known smoke-report retention and policy-bound bridge handoff all passed. Five additional held titles have exact existing-byte checksum repairs: book-0deb35c750, book-2b9853ec52, book-2ddbed8293, book-2e468c4990, the-student. Candidate a027b349da465f83e574eb99ef270493c119d76c contains only six checksum manifests; proposal blockers 912 to 907, with 224 held, seven accepted and no new rights decision/publication/audio. All three private/controller/handoff artifact digests and the controller/proposal diff identity were independently verified. This is a validated pending candidate, not a merged result or evidence exhaustion. Fresh normal exact-head checks and protected merge remain required. Approved UI, manuscript, source/approval bytes, accepted records and launch controls are unchanged.

## Verified third bounded catalogue pass — 2026-09-30

Campaign 36791115145 succeeded with 20 examined candidates and complete receipt/release/scope/focused/full-regression/final-source/evidence-retention gates. Exact existing-byte checksum repairs for carmilla, eyesore-chokher-bali, hound-of-the-baskervilles, hungry-stones, woman-in-white reduce proposal blockers 907 to 902. Candidate 3a9286e6b6ce2e3e363219f1dc28f49144ebf7a2 changes only ten checksum manifests; 224 held, seven accepted, no new decision/publication/audio, and all approved product/source/approval/registry/launch bytes are unchanged. All three artifact digests and exact controller/proposal diff identity were verified independently. Fresh normal candidate checks and protected merge remain required. Three other chapter files (Scientific Management chapter-004, The Suicide Club chapter-001, Ward No. 6 chapter-001) are absent from the committed tree and no path history was found; their exact recorded hashes are retained in the decision record. Do not bless missing chapters by changing checksums, stripping inventory entries or inserting placeholders.

## Verified fourth bounded catalogue pass

Campaign 36792862881 passed all actual receipt/release/scope/focused/full/final-source and retained-proof gates. Four replacement hashes for Pather Panchali match exact unchanged approval/public-book bytes in root/runtime packages; proposal blockers 902 to 900, with seven accepted/224 held and no new rights/publication/audio. All artifact digests and exact controller/proposal identity were independently verified. Candidate dc959fa8151b027b960599b5dc7e5d3238c7f27c contains only two checksum manifests. Remaining checksum discrepancies correspond to three absent chapter files, not refreshable metadata. Fresh normal candidate CI and protected merge remain required. Approved UI/manuscript/artwork and source/approval/registry/launch bytes are unchanged. The local shell Git fetch was cancelled by network approval; the authorized GitHub connection supplied exact commit metadata instead, and reconstructed commit/tree identities were hash-verified before any local ref move.

## 2026-10-01 — Complete next actual assessment and preserve original prose

PRs #488–#491 passed their normal exact-head checks and expected-SHA protected merges. Nineteen stale retained metadata blockers across sixteen titles were repaired; source, chapter, approval, accepted-registry, approved UI/artwork/manuscript and launch bytes were preserved. PR #491 merged at 45490009cf45fc1ce6853752f80e903636169916; normal merged-main regression 36794894307 passed.

Campaign 36794894294 completed its exact-source/batch-bound 20-candidate receipt, focused/full regression and final source identity guard. Both independently downloaded artifact digests match. Its proposal is empty and all title decisions/releases remain unchanged: seven accepted, 224 held, 900 aggregate blockers. This is a bounded no-progress result, not a claim that every possible external source has been exhausted.

A separate exact-source inspection identifies a false positive: Enchanted April chapter-003's original prose contains “proper category:”, also present in the retained official source. Restrict Category namespace detection to line, wiki-link and URL boundaries, with eight processor tests that preserve original content and accepted-decision holds while retaining real metadata, encoding, unsafe-HTML and checksum rejection. All original source/package bytes remain unchanged. Reproduce the complete private snapshot (899 candidate blockers) and require both normal full regression and independent catalogue worker/reviewer checks. Do not mark READY_FOR_APPROVAL historical metadata as new QA.

The legacy the-picture-of-dorian-gray checksum/source/approval removal is part of approved canonical reader repair 4b41439bb2397f6e6ecebd6d35ca990213a59840. Preserve it and the separate current picture-of-dorian-gray package; no historical bundle is restored merely to clear an inventory hold. Three absent chapter files require exact cleared recovery, with their recorded hashes retained. Keep #347 completed, #380 release/authenticated acceptance open, #477 the 224 explicit per-slug holds, and #385 owner-deferred NOT_RUN / UNVERIFIED.

Next generated prompt: require the corrected checker and reproduced private snapshot's normal exact-head and independent catalogue checks; protected merge; verify fresh main; update all four issues. Resume only with exact cleared evidence and truthful applicable production acceptance.

## 2026-10-01 — Verified correction, complete snapshot and four-issue reconciliation

PR #492 exact head cc8d1ca5b198e53bc97dc745351d06027bb3b25e passed normal regression 36796257882, independent full-catalogue worker/reviewer 36796257939 and coordination 36796257778, then merged with expected-head protection at 5e800608e6a5c02a4a58bb12680f0af38321f152. Fresh main regression 36796711277 and catalogue worker/reviewer 36796711291 pass. Both catalogue ZIP digests were independently verified; all 165 snapshot files and exact-head result envelopes match, with no worker source changes or publication authority. The original prose remains byte-identical. Mandatory normal preflight ran 26 tests including all eight processor tests, followed by 47 frontend and 124 regression passes with four existing configured skips.

The canonical private per-slug snapshot is now reproducible: 231 assessed, 162 prepared, 1,012 chapters, seven pre-existing accepted titles, 224 explicit holds, 69 absent cleared packages and 899 aggregate blockers (919 before repairs). Nineteen stale hash blockers for sixteen titles and one prose false positive are repaired. Existing accepted records/revocations, all approved source/manuscript/artwork/product versions, historical Dorian repair and all remaining title-specific evidence holds are preserved. Public route/SEO/browser proof is not authenticated production readback, accepted scope is not a new title release, and the selected 20-title no-progress result is not global evidence exhaustion.

Issue #347 is closed completed. #380's UI and revised manuscript inclusion is verified; Agentic exact cover/component/text-use decision and applicable authenticated trusted-India acceptance remain open. #477 keeps its complete 224 per-slug holds. #385 remains owner-deferred post-CUSTOMER_READY UAT, NOT_RUN / UNVERIFIED and narrowly nonblocking. Resume on new exact evidence through existing rights/admin review; do not repeat unchanged held batches or fabricate missing facts.

Next generated prompt: Resume from the clean, current canonical branch and the verified per-slug catalogue state. Prioritize Agentic AI With Python: verify exact current revision and genuine cover/component ownership or licence evidence, then use the existing rights-review/registry process for an accepted hash-bound India text-only decision. Promote only passing drafts through the existing admin path and verify applicable authenticated trusted-India Reader acceptance and production readback. Recover Scientific Management chapter-004, Suicide Club chapter-001 and Ward No. 6 chapter-001 only from exact cleared evidence matching the retained hashes; preserve approved canonical Dorian repair and all other source/manuscript/UI versions. Reassess other held titles only when their listed missing evidence is substantiated; do not repeat the unchanged 20-title run or invent QA, legal, cover or production observations. Physical Android/iOS UAT remains owner-deferred NOT_RUN until an owner-provided tester after CUSTOMER_READY. Audio stays disabled; no paid provider call, customer wallet/data, launch flag or deployment-configuration change.

## 2026-10-01 — Substantiated Agentic owner facts and exact remaining component conditions

Ronik Basak directly reaffirmed Agentic manuscript authorship and confirmed creation of both existing covers. Retained author evidence already authorizes commercial Reader publication; do not treat authorship, public-domain dates, an author-death year, cover creation dates or registration as missing first-party prerequisites. All 14 chapter hashes/root-runtime bytes and all 428 archive checksum entries verify. Both exact versioned CDN cover bytes are now retained with SHA-256 bindings, alongside approved local asset hashes.

The visible Python logo treatment appears stylized/3D. Official PSF book-use terms permit unchanged nominative use, require a book trademark notice and address variant approval. No current-variant approval or notice in the delivered chapters was found. Record this specific condition without claiming infringement or converting an owner-creation statement into PSF permission. The exact-schema India text-reader proposal remains HOLD outside the runtime registry; no grant, approved asset replacement, title release, paid Pass or audio activation occurred.

Production secure Google sign-in reached account verification; fresh production still showed Sign In. A requested/selected sign-in method is not authenticated readback, and a cloud request cannot fabricate trusted India context. Keep account/credential/OAuth details out of the repository. Existing catalogue snapshot and counts remain unchanged: seven accepted, 224 held, 899 blockers. Android/iOS UAT stays owner-deferred NOT_RUN / UNVERIFIED.

Next generated prompt: Use the confirmed Ronik Basak manuscript authorship and creation of both covers; do not reopen those missing-fact questions. Resolve only the evidenced Python logo variant and required notice conditions, preserve approved assets/text, and rebind the reviewed exact India text-reader record through the existing registry process when conditions are satisfied. Complete secure account verification, then inspect applicable production Reader/admin active publication and exact revised hashes from a trusted India context. Use the existing draft/admin path only after all gates pass. Keep audio disabled, physical-device UAT owner-deferred, all seven existing accepted titles and all other holds intact; do not change wallets, customer data, launch flags or deployment configuration.

## 2026-10-01 — Owner-authorized Agentic component correction and exact text release

Ronik Basak authorizes the necessary cover/notice edits and release. The two owner-created originals are preserved; sibling release assets remove the stylized Python logo and use a neutral connected-node illustration. The back cover and public description carry the trademark/non-affiliation notice. Actual assistant visual checks substantiate these conditions without claiming PSF variant permission or an independent human review. All 14 revised chapter files, source/approval evidence and chapter index bytes remain unchanged.

The exact India commercial text decision binds six runtime metadata components, cover provenance/release approval, all 14 chapter files and four delivered cover assets. The existing registry gains one canonical record while preserving all ten prior bindings, history and revocations; backend/root/client allowlists add only Agentic. Audio, exports, storage signing and generation remain ungranted. Hash inventories are built before the decision to avoid a self-reference cycle.

The complete private catalogue now assesses eight source-approved titles and 223 held titles, with 897 aggregate blockers. Other 230 title assessments remain unchanged. Advance the assessment to the actual receipt time; never backdate a new accepted record to satisfy a stale checker timestamp. Default check and new worker outputs use the retained canonical assessment time. Source approval remains separate from deployment, authenticated Reader readback, trusted country and canonical page activation. Production still shows Sign In; CUSTOMER_READY is not declared. Physical Android/iOS UAT remains owner-deferred NOT_RUN / UNVERIFIED.

Next generated prompt: Require normal exact-head regression and independent catalogue checks for the owner-authorized Agentic release, merge with expected-head protection, and deploy only merged main. Verify the four corrected cover assets and the public title readback, then complete authenticated trusted-India Reader and existing Reading Pass acceptance. If canonical segments require preparation, use the existing admin dry-run/parity and separately guarded activation workflow; do not overwrite an approved active version. Preserve all 14 revised chapter files, the original covers, all seven earlier accepted releases and all other evidence holds. Audio stays disabled; physical-device UAT remains owner-deferred NOT_RUN / UNVERIFIED. Do not mutate wallets, customers, unrelated publication pointers or global payment policy. Record actual production observations without claiming CUSTOMER_READY from offline rights checks.

## 2026-10-01 — Release dependency checks kept mandatory

The first Agentic candidate passed exact catalogue and most regression checks; full hosted checks caught the missing tracked sitemap entry, PR cover tests probing the previous production origin, and stale explicit source-hash authority. Regenerate sitemap/robots through existing offline tooling. Test first-party assets against the actual loopback candidate before deployment, keeping external hosts, production checks and image content-type validation unchanged. Rebind both workflow hash authorities to the exact authorized cover/allowlist/SEO surface without editing Library/layout baselines or skipping browser reviews. The same rights record and all 14 manuscript files remain unchanged; rerun normal exact-head checks before merge.


## 2026-10-01 — Near-ready editions first, without new paid production

The owner prioritizes small, substantiated releases and judicious spend. Sixteen existing India text editions reuse verified source and original artwork; all 66 chapter files pass complete sanitized-text and canonical-page parity (539 offline pages). Only four ready drafts need fresh delegated QA flags; the canonical repaired 21-chapter Dorian edition gains its already-existing audit-bound cover pair. Horseman gains an identical backend mirror. No approved source, chapter or art bytes are replaced, and all eight prior release packages / eleven registry bindings and history remain unchanged. The fresh full-catalogue snapshot records 24 source-approved, 207 held and 860 blockers; production activation and authenticated India observation remain separate. No image/audio/provider call was made.

Agentic merged PR #496 and frontend deployed, but an overseas canary expected backend JSON through an India-only guard that returned an empty 451; Railway correctly skipped that head. Return a specific territory-denial JSON without forwarding overseas requests. Recognize only exact reviewed protected-route denials from known non-IN context and mark India backend checks NOT_RUN_FROM_NON_IN. Keep strict original backend status/code and all held/removed-route checks. Never report this as observed India delivery or bypass suite gates. A fresh production build passes 94 static snapshots / 2017 assertions. Preserve frozen chapter-index history and explicitly document the existing Horseman mirror addition, rather than regenerating the baseline from candidate files.

Most Dangerous Game requires visible CC BY-SA credits and recipient-use compliance; source footer metadata alone is not the delivered credit. Current cover provenance gaps and conflicting root/runtime editions remain genuine title-specific holds. Do not repeatedly run the unchanged no-progress campaign, spend on new imagery or stamp unsupported legal/QA facts.

Next generated prompt: Validate the exact 16-title near-ready batch with normal regression, independent catalogue and browser checks. Merge only the current protected head; deploy merged main through the existing Vercel/Railway checks. Verify delivered title and cover hashes and applicable authenticated trusted-India Reader and active canonical version. Use existing admin dry-run/parity and guarded bootstrap/promotion only when genuinely authenticated and qualified; preserve every approved active pointer. Continue only other cheap exact-evidence candidates; Most Dangerous Game needs its visible licence/downstream-use conditions, current Cloudinary cover gaps and conflicting mirrors remain held. No paid image/audio generation, inferred legal grants, overwritten approved sources/art or customer/wallet changes.


## 2026-10-01 — Keep historical drafts separate from current accepted editions

Normal hosted checks caught two remaining eight-title test authorities: reader-content batch membership and browser static-contract membership. Update only the explicit reviewed set and verify exact current Jekyll/Dorian decisions. Preserve canonical Dorian historical content draft and promotion report, and test the newly accepted repaired public edition separately. Both local corrected tests pass (6 reader-content cases and 21 browser-tooling cases). No rights, source, art, product UI or publication files change in this correction; normal checks remain required on the new head.

Next generated prompt: Complete protected PR #497 exact-head checks, merge and deploy merged main. Preserve all 16 exact accepted decisions and old source/art/history. Verify the production canary without claiming India or authenticated delivery from the overseas denial; perform qualified active canonical readback through the existing admin workflow where actually authenticated.

## 2026-10-01 — Traverse the existing Library shelf in release checks

The 24-title fixture passes the actual release and Reader-only facet helpers, while the existing LibraryBrowseShelf initially renders ten editions. The journey must use its Show more controls and verify 10 → 20 → 24 exact results, focus on the first new cover, exhausted controls and reflow. Preserve the product shelf and exact release assertion. Local syntax, five baseline-authority checks and seven Library facet tests pass. All 2807 prior source/chapter/art files and 231 prior released package files remain byte-identical. Full browser evidence is still required on the corrected head; no authenticated production observation is implied.

Next generated prompt: Complete protected PR #497 exact-head browser, regression and independent catalogue checks; merge the passing head and deploy merged main normally. Verify applicable actual production delivery and active canonical Reader versions while retaining the explicit India/authentication limitations.


## 2026-10-01 — Stable browser sessions and bounded approved Reader initialization

A legacy IP-bound session rejects a legitimate network change. Use a private random HttpOnly/Secure cookie plus signed grant, and migrate only a retained active refresh proof with its original user agent. Preserve absolute/idle bounds, blocking, single-login and revocations; a concurrent migration loser returns retryable 503. Node fetch cookies must be forwarded independently. Authenticated and auth-endpoint responses remain private/no-store.

Source approval does not create canonical Reader pages. The owner authorizes a deployment-scoped initializer for the exact 24 accepted decisions, using existing immutable preparation and audited transactional bootstrap with an explicit system actor. All active/retained/revoked/operator-prepared versions are preserved, and missing uniqueness prerequisites hold safely. Offline exact authority and complete projection pass for 24 titles / 1,015 pages; this is not production readback. Local 41 session/bootstrap/promotion/password tests and 12 proxy tests pass. Initialization runs only in production; isolated UAT/preview/development seed flows remain unchanged. All 2,807 prior source/art files and 231 prior release-package files remain byte-identical.

Exact preceding-head full browser/independent evidence, regression and catalogue checks passed. Editorial exceeded 25 minutes downloading unused 554.6 MB Torch. Restrict visual-job dependencies to actual Pillow/reportlab imports while retaining mandatory evidence validation; audio/production requirements remain untouched. No paid image/audio/provider calls. Production deployment, initialization outcomes and authenticated trusted-India observations remain pending.

Next generated prompt: Complete PR #497 exact-head regression, independent catalogue and mandatory browser/owner checks; merge with expected-head protection and deploy only merged main. Observe the actual Railway revision and bounded approved Reader initialization results, preserving all existing pointers, revocations and retained candidates. Verify delivered edition/cover hashes and authenticated trusted-India Reader/Reading Pass readback only where actually available. Keep unresolved production observations explicit, preserve source/art/history and all other holds, and continue only inexpensive evidence-complete candidates without paid image/audio generation or customer/wallet changes.


## 2026-10-01 — Stop automatic paid proposal work from stalling checked releases

PR #497 merged at 160b8175ac80e505e4888be7306677f022f86923 with 24 source-approved text editions / 207 held / 860 blockers. Main regression, catalogue, frontend deployment and production canary passed. The automatic catalogue implementation consumed 112,690 reported tokens and hit provider quota, so Railway correctly skipped the backend. Its partial Most Dangerous Game edits are unvalidated and unpublished; never adopt them as legal approval. No quota increase or paid rerun is authorized by this correction.

Make proposal work manual-only and default-off with an explicit budget boolean, then require an open campaign issue in a separate read-only policy job. A step exiting zero on a closed issue does not stop later job steps. Retain worker permission, evidence/receipt, batch, source, normal regression and deployment gates. The new cost fixtures execute both actual OPEN/CLOSED policy-shell outcomes; 26 local cost/receipt/controller tests pass.

The bounded production Reader initializer can safely install only missing exact uniqueness constraints. Never drop an index, delete duplicates or choose a winner; conflicts hold. Actual loopback-Mongo tests now require missing-index initialization and duplicate-history preservation in hosted regression. Local 42 session/bootstrap/promotion/password tests pass. All source/art/decisions/approved UI and prior 2,807+231 byte comparisons are unchanged. Backend initialization and authenticated trusted-India delivery remain unobserved until normal deployment.

Next generated prompt: Complete the protected quota-recovery PR with normal exact-head regression, including actual loopback-Mongo missing-index and duplicate-history preservation tests. Merge only the passing revision and deploy merged main through the unchanged check-suite, Vercel and Railway gates. Do not rerun the quota-exhausted paid proposal job; it requires a separate explicit budget opt-in. Observe the actual backend revision and approved Reader initialization results; preserve every retained version/revocation and report holds truthfully. Verify authenticated trusted-India Reader delivery where an actual session is available. Preserve all 24 accepted text decisions, book source/art/history, all other holds and disabled audio; no customer/wallet changes.


## 2026-10-01 — Checked production backend and canonical initialization observed

PR #497 released 16 additional source-approved editions (24 configured total). PR #498 passed real 115-case canonical/session integration and preserved the source/UI. Railway deployment 50ba50c5-0f7f-4bdb-aacd-8e1c9c2afefd succeeded at 56e1bedbd11ab696497ddedd03bef6bed2a0f56a; its independently downloaded, hash-verified native canary confirms Railway provenance and five GET/HEAD checks PASS. The earlier frontend source deployment and production canary passed; unchanged frontend source is reused. Paid proposals are default-off and were not retried after quota failure.

Actual startup reports 17 initialized versions / 714 canonical pages and seven preserved active versions, with zero holds. Fifteen initialized titles are from the new batch; Jekyll already has an active version. Two previously approved editions also gained missing pages. Independently reproduced production-renderer hashes/counts match all 17 actual activations and preserve the full source text. The earlier raw-source projection is retained: sanitizing HTML can change a version hash without changing content/page counts. Never replace source or production hashes merely to match a raw representation expectation. All 2,807 prior source/art and 231 prior accepted-package comparisons still pass.

The secure production browser still shows Sign In. Authenticated/trusted-India delivery, seven retained active-version content checks and delivered Agentic cover-byte hashes are NOT_VERIFIED; CUSTOMER_READY is not declared. Physical Android/iOS remains owner-deferred, and all 207 genuine catalogue holds remain. No customer/wallet changes, audio activation, new paid image/audio generation or accepted partial quota-failed worker output.

Next generated prompt: Complete authenticated trusted-India Reader and Reading Pass readback for the 24 configured editions, prioritizing the seven preserved active versions and exact Agentic delivery/cover hashes. Use the existing secure sign-in handoff; never forge auth/country or overwrite retained approved versions. Keep all 207 genuine catalogue holds and deferred physical-device UAT explicit. Continue only inexpensive evidence-complete candidates; paid proposal workflow stays default-off and requires separate budget opt-in.


## 2026-10-01 — Missing Reader benchmark entry point restored

The successful coordination run 36844619269 only emitted a plan; its Reader benchmark path was missing. The restored entry point refuses production/remote/credentialed MongoDB, requires the existing explicit loopback replica-set fixture and prepared Python environment, and runs actual HTTP auth/refresh/lease/page handlers. Timings are isolated ASGI/database response timings; no browser paint, production latency, trusted India or customer readiness is inferred. Twelve local guard/bridge/cost cases passed. Real native Mongo execution is pending the mandatory hosted regression stack because the local replica set is unavailable. The queue is WAITING_CI rather than repeating a stale dispatch.

The owner selected Google through secure authentication. Google reported a device-approval notification; attachment to its popup timed out. A fresh target-domain tab still shows Sign In. Authentication and trusted-India context are NOT_VERIFIED, so all 24 Reader/Reading Pass readbacks remain explicitly NOT_RUN. No credentials were extracted, country/entitlement controls bypassed, production records changed, paid generation started or paid proposals rerun. Existing 17 initialization / 714-page / seven-preserved-version proof is historical unchanged evidence. All 207 genuine catalogue holds and deferred physical-device UAT remain.

Next generated prompt: Review the exact-head isolated Reader benchmark artifact and merge only its passing repair. Complete the pending Google device approval through the secure sign-in flow and verify authenticated trusted-India Reader/Reading Pass delivery for all 24 configured editions, including seven retained versions and delivered Agentic hashes. Preserve all approved source, art, versions and 207 genuine holds; run no paid generation or proposal reruns.


## 2026-10-01 — Benchmark respects the approved five-session policy

The first hosted repair revision 054f3ca4d55f48b9c12546f5c335aa775e54e4ca passed all 115 existing native cases, then failed the new benchmark because it incorrectly expected a second login to revoke the signup session. Approved Reading Pass V2 permits five active logins. Preserve runtime behavior and test the actual bound: a retained session remains valid within the limit, and the sixth real login revokes the oldest. The corrected native run is still pending; the failed run is retained as evidence.

The public production Reading Pass page rendered all four existing offers, with Sign In still visible. This is public presentation evidence only: authenticated entitlement, checkout, metering, trusted India and all 24 protected title readbacks remain unverified. No purchase, production mutation or paid rerun occurred.

Next generated prompt: Review the exact-head isolated Reader benchmark artifact and merge only its passing repair. Complete the pending Google device approval through the secure sign-in flow and verify authenticated trusted-India Reader/Reading Pass delivery for all 24 configured editions, including seven retained versions and delivered Agentic hashes. Preserve all approved source, art, versions and 207 genuine holds; run no paid generation or proposal reruns.


## 2026-10-01 — Preserve publication identity while validating the real admission audit fence

Hosted revision e8ce0e5c133bc2efe426407ce6daca143ef589ae again passed 115 existing native cases. The new benchmark completed the real signup/bounded-login/refresh/lease flow, 20 protected-page content/hash checks, invalid-access denials and logout before failing its overly broad pointer equality assertion. Real admission correctly adds an authority fence and last-start timestamp to serialize against revocation. Validate the exact +1 fence and admission timestamp bounds, then require every other pointer field, segment and manifest to remain unchanged. Do not remove the production fence or replace a content version. Native acceptance remains pending the corrected run.

Next generated prompt: Review the exact-head isolated Reader benchmark artifact and merge only its passing repair. Complete the pending Google device approval through the secure sign-in flow and verify authenticated trusted-India Reader/Reading Pass delivery for all 24 configured editions, including seven retained versions and delivered Agentic hashes. Preserve all approved source, art, versions and 207 genuine holds; run no paid generation or proposal reruns.


## 2026-10-01 — Native Reader benchmark accepted; production prerequisite remains explicit

Normal hosted regression run 36852504273 / job 110337212016 passed on source head 7bc1aa2ba6fbc8131da25382d0da0fad14020dc6 and tested merge revision 3c7702b7ad23288c085acff3dba43326eccb6839. Both trees equal cb1e8e0d20fd48bf0ae6a3b365c4b4dd84649772. The independently downloaded 8,128-byte artifact matches GitHub digest 8a6dfe645ab001efcd60e29d7020da1931728b00d77e0fd0554e729658f73d76; the unchanged native report hashes to a14ea12db0e64419f8cdf9de7cb176810817b9d9785a4018ba1bc17495b3206f. It completes actual isolated signup, five-session bound, login, refresh, admission, 20 protected-page content/hash checks, six denials and logout. Fixture segments, active version, activation generation and manifest are preserved; the required authority fence increments once and no wallet seconds are debited. Informational median 5.825 ms, p95 6.155 ms and maximum 6.564 ms exclude network and browser paint. Existing 115 native cases, 47 frontend tests and 124 full regression tests pass with four existing full-regression skips.

The repaired coordinator task now advances to VERIFYING_PRODUCTION with an exact prerequisite blocker, never DONE or CUSTOMER_READY. The production target remains on Sign In. All 24 authenticated trusted-India Reader/Reading Pass observations are NOT_RUN, not failed title tests. Public offers render; authenticated entitlements, metering, seven retained-version parity and Agentic delivered cover hashes remain unverified. Preserve prior 17-version / 714-page initialization evidence, all 207 catalogue holds and owner-deferred physical UAT. No paid generation/proposal rerun, credential extraction, country/entitlement bypass or production customer/version mutation.

Next generated prompt: Finish secure production sign-in and authenticated trusted-India Reader/Reading Pass readback for all 24 configured editions, including seven retained versions and delivered Agentic cover hashes. Use the preserved exact-source evidence; do not rerun paid generation or proposals, overwrite approved versions, or bypass country or entitlement controls. Record actual per-title results and keep every remaining hold explicit.

## Blog / canonical header / English Reader rendering

- Independent centering of prose inside an expanding canvas caused the visible second inset; align heading and prose against one bounded reading measure.
- Shared cover `height:100%` stretched artwork to manuscript height; constrain editorial covers to their actual aspect ratio.
- Delegating immersive headers to the canonical public Header prevents navigation drift; preserve lease settlement before exits.
- Existing static article snapshots alone cannot serve newly authored Journal slugs. Published-only runtime metadata routes must preserve missing/draft 404 and distinct outage states.

## Bengali text preparation — 2026-10-02

Author lifetime facts, transcription licensing, exact source edition and publication authorization are separate gates. Owner-designed covers still require explicit asset bindings. Source site licensing is not an accepted edition decision. Preserve legacy import hashes while binding actual current chapter hashes. A text-preparation manifest must not inherit stale audio approval; ordinary publication validation remains strict. Current canonical launch authority has 24 titles and paid commerce, so held-cohort audit must enforce package-local non-exposure rather than a historical three-title/global-commerce-off assumption.

## Catalogue clearance 2026-10-02

122 packages repaired; four local exact-edition text decisions, no live activation. Later editorial rights and ambiguous publication dates remain held. Repeatable static SEO generation must strip only its own generated fallback. CC-licensed delivered text must retain downstream license permissions.

### Catalogue clearance final checkpoint
103 local text decisions remain unexposed; covers deferred. Primary-source whole-work verification, immutable license notices, conservative India publication bounds and known-live runtime controls prevent false readiness. Damaged Eyesore glyphs and conflicting Kafka permissions remain held.

### Vercel prebuilt packaging
Source deployments succeeding do not prove prebuilt file selection. Validate includeFiles, generated filePathMap and external symlink targets against the actual CLI manifest; preserve generated-output exclusions with a narrow required-asset exception.

## Book GO-LIVE 477 continuation — 2026-10-02

Recover the existing checkout/candidates when bridge task actions are unavailable. Clear the sole existing PR before integration. Preserve exact source/licence facts and encode existing covers deterministically; compare original→derivative hashes rather than infer attribution from visual similarity. Parallel preparation remains separate from serialized activation. Local rights evaluation is not production or entitlement UAT.

## Book GO-LIVE 477 route support hold — 2026-10-02

Static generation is not production route reachability. Two reviewers identified the Bengali edition lacks explicit route mappings while generic slug routes target404. Preserve its exact preparation but remove launch exposure when deployment configuration is outside owner scope; advance the independently routable edition through the existing PR.

## Book GO-LIVE 477 runtime/app integration — 2026-10-02

Accepted exact rights and configured publication remain separate. Inventory must derive territory from the current accepted decision when admin dispositions omit it, retain digest/component/revocation gates, and mark off-allowlist titles unexposed. Static released pages need matching API-gated app routes after hydration; detail helpers must preserve exact approved cover aliases rather than replace them with legacy artwork.

## Book GO-LIVE477 routing correction/currentchapterfixture — 2026-10-02

Do not infer confirmed404 or campaign exhaustion from missing explicit rewrites: Vercel checks filesystem first and the build generates directory indexes per safe publication. Preserve exact current28-unit Dracula edition and immutable frozen27narrative baseline via explicit hash-bound overlay; never delete accepted original Preface to satisfy stale test. Real production path and canonical-version observations remain separate gates.

- 2026-10-02 #477: public release projection must bind exact approved publication manifests, not historical package draft labels. Required validated license attribution is public; private evidence keys remain forbidden. Six isolated final assertions repaired; exact protected CI and deployed readback pending.

- 2026-10-02 #477: after full regression passes, browser journey fixtures must match exact approved26/Bengali scope while preserving independent held/audio cases. Evidence executive snapshot counts must derive from hash-bound actual report/manifest, never historical fixed142. Two source reviews and39tests pass; production unobserved.

- 2026-10-02 #477: metadataReader200 is not canonicalReader readiness. Each exactnewapprovedtitle requires existing audited absent-pointer initialization plan or observed existingvalidversion. Extend exactplanbindings, test actualhandlers/allhistoryholds, strengthen observedversion canary; neverrewriteexistingpointer orinferproductionfrom isolated276/9page computations. Next3deliveryderivatives now two-reviewed/inactive.

## 2026-10-04 — Reader opening
- Canonical manifest and first-page readiness can drive a personalized CSS book opening without a second fetch or minimum duration. Retain protected denial and ordinary page-turn paths.
- Measure first-page response separately from prefetch; prefetch overwrites otherwise corrupt startup timing. Local DOM handoff 15–29ms; gzip bundle delta2300 bytes.
- Review/evidence: `reader_opening_review_20261004.md`. PR516 occupies release slot; no production observation or deployment inferred.

## 2026-10-04 — Reader measured pagination
Canonical server chunks are authorization boundaries, not responsive visual pages. Preserve those gates while adding measured fragments. Hidden measurement DOM needs explicit font loading; invalidate cache after font load. A short-screen decorative drop cap can exceed the reading surface. Whole-book numbering and oversized structure adapters remain release holds; local tests are not proof of native zoom. See reader_pagination_review_20261004.md.

## Reader pagination correction — 2026-10-04

- Prose-only fixtures missed tables/code/blockquote spacing in the supplied Agentic AI With Python chapter. Complete-row table splitting and compressed short-screen spacing preserve text and font size.
- Read fragment text, source offsets and geometry atomically during browser traversal; separate calls can straddle a React render and produce false integrity failures.
- Yield long DOM pagination calculations in bounded slices; cancel superseded work before it clears or commits a newer shared measurement container. Use the canonical opening presentation only for genuine initial calculation.
- Passing full-chapter local fixtures is not proof that the public authorized-chunk API supplies a single whole-chapter visual-page map. Preserve the release hold until that contract and native zoom acceptance are complete.
