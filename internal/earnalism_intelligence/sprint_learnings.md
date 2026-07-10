# Sprint Learnings

- Bengali reused local audio repeatedly failed manuscript match; do not rerun stale audio blindly.
- Bengali reader-only publication is a valid customer-facing outcome when content, rights, covers, and reader pass.
- OpenAI Bengali TTS has not met premium literary listening expectations; Sarvam remains promising but unproven for full release.
- Objective gates remain strict even with tiered listening and paragraph/stanza sync policy.
- Customer-facing book covers must never fall back to plain typography panels. Use approved graphical covers first and lightweight graphical runtime fallback only when source art is missing.
- Deterministic HTML text is safer than generated image text for covers because it avoids misspellings, supports Bengali/English typography, and prevents heavy raster churn.
- Homepage performance in the CRA shell is still constrained by client-render LCP; hero asset/font/background optimizations improved local Lighthouse from 66 to 90 but did not restore the requested >=94 guardrail.

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

## 2026-07-07 Bengali Post-Go-Live Canary Gate

- The first Bengali audiobook remains live after post-go-live checks: detail API, reader manifest, audiobook endpoint, audio sidecars, reader desktop/mobile audio control visibility, and unapproved Bengali audio hiding all pass.
- The detail page still shows stale `Audiobook held for QA` copy for `book-2b9853ec52`; this is not unsafe audio exposure, but it should be fixed before expanding Bengali audiobook releases.
- Canary execution must not start while factory/browser hook source remains untracked. Promote it through the clean source-only integration branch first.
- `paid_tts.lock` and `production_metadata.lock` remain active. A canary cannot run until these locks are explicitly cleared or reassigned.
- Only `muchiram-gurer-jibanchorit` currently passes audiobook-clean frontmatter preflight among the requested canary slugs. `book-d19e96859f` and `book-2ddbed8293` require clean-text/frontmatter repair before representative auditions or paid TTS.
- No paid canary operations ran in this pass.

## 2026-07-07 Main Branch Cleanliness Finalization

- Use `/private/tmp/earnalism-source-only-clean-integration` on branch `codex/source-only-clean-integration` as the route back to a clean main branch.
- Do not stage `frontend/package-lock.json` unless `frontend/package.json` changed intentionally. In this pass, package.json is unchanged and package-lock drift was excluded.
- Do not stage `frontend/public/sitemap.xml` unless the sitemap itself is the reviewed source change. Build validation regenerates it, so restore it from `origin/main` after validation.
- The clean branch passed Python factory checks, backend route tests, `npm ci`, audio safety, frontend build, cover audit, visual smoke, and `git diff --check`.
- Main branch cleanup should proceed through a source-only PR. Do not deploy or merge automatically.

## 2026-07-07T17:06:05Z Launch Lot + Marketing Strategy

- Inventory scanned 229 available books from controlled-publication/content/manifest sources.
- First launch should be reader-first with a staged audiobook lot: only `book-2b9853ec52` and existing approved `a-ghost-story` are audio-marketable today.
- Bengali canary candidates remain high-value but must not be marketed as audio until canary-aware Sarvam guard, representative evidence, full TTS, measured sync, upload, metadata, endpoint, and browser gates pass.
- English short classics are strong low-cost audio candidates, but require fresh naturalness and objective gates before listen CTAs or audio teasers.
- Long classics belong in SEO/flagship reader shelves first; do not force them into the founding audiobook lot.
## 2026-07-07 UX Governor Installation

- Installed a persistent UX governor under `internal/earnalism_intelligence/ux_governor/` so future Home, Library, Book Detail, Reader, Audiobook Player, cover, settings, marketing, and conversion sprints start from repo policy instead of ad hoc prompts.
- Green UX claims now require the 10/10 scorecard plus release-gate truth, audio safety, cover audit, build, visual smoke, accessibility/performance evidence, and generated-artifact hygiene.
- This task was governance-only: no runtime UI, production metadata, audiobook, deploy, merge, or public audio exposure was changed.
## 2026-07-07 Home/Library/Reader 10 UX Sprint

- Home and Library source already contained the approved premium UX direction: non-Dracula hero, curated action cards, Bengali visibility, filters, status badges, graphical covers, and gated Listen CTAs.
- Reader source still had browser speech-synthesis and inferred static audio URL fallback paths. These were removed because approved audiobook UX must require explicit manifest/assets and must not present browser/system speech as a real audiobook.
- Validation is blocked in the original dirty workspace because `npm ci`/install attempts stalled and left `frontend/node_modules` incomplete (`react-scripts` missing). Restore dependencies from a clean worktree or known-good npm/Node pairing before claiming green.
## 2026-07-07 Launch Activation Learning

- Season 1 marketing must separate `LIVE NOW`, `COMING TO THE LISTENING ROOM`, `READER-FIRST CLASSICS`, and `SEO / LONG-FORM FLAGSHIP` so public copy never implies audio availability where gates have not passed.
- `book-2b9853ec52` is safe for Bengali listen copy with section-following narration language backed by go-live evidence.
- `a-ghost-story` has approved local controlled-publication audio assets that resolve, but guessed public API manifest/audiobook paths returned 404 during activation planning; use reader-route marketing and do a final browser/manifest route check before paid listen ads.
- Non-live Tier 1 candidates get Read, Coming Soon, or Follow copy only. No Listen CTA until endpoint/browser gates pass.
## 2026-07-08 Launch Gate 0 Learning

- Dependency repair succeeded only after renaming the stale `frontend/node_modules` tree in place; direct `rm -rf` and cross-volume move both stalled. Future cleanup should avoid blocking validation on slow deletion and should ignore `frontend/node_modules.stale-*`.
- Canonical frontend hardening needed promotion: production API now defaults to same-origin `/api`, direct `api.theearnalism.com` preconnects were removed, and the legacy audio player fails closed unless explicit approved asset URLs are passed.
- `book-2b9853ec52` is production-route verified for Listen. A Ghost Story remains approved by local controlled-publication assets, but guessed production API book/manifest/audiobook routes return 404; paid Listen stays HOLD until exact route/player evidence passes.
- Launch Gate 0 is LIMITED GO: organic reader/brand and verified Bengali Listen campaigns may proceed; full 10/10 UX and A Ghost Story paid Listen remain gated by Lighthouse/accessibility and production manifest/player evidence.

## 2026-07-07 Bengali Canary ASR/Source Repair

- `book-d19e96859f` and `book-f5d593e1f4` must remain audio-hidden. Their full Sarvam canary audio is not releaseable because final groups narrate standalone source/publication year `১২৯৮?`.
- The verifier also had a false positive: raw `পৃ` substring matching rejected valid Bengali literary words such as `পৃথিবী` and `পৃথগন্ন`. Page detection must be boundary-safe, e.g. `পৃ.` or `পৃ ৬৫`, not any word beginning with `পৃ`.
- Cheapest safe repair is group-only: regenerate group `4` for `book-d19e96859f` and group `7` for `book-f5d593e1f4`; reuse all other group audio by hash.
- Weak Bengali ASR remains diagnostic, not publish-blocking by itself, only after clean TTS-by-construction, full listening QA, measured paragraph/stanza sync, upload/checksum, metadata, endpoint, and browser gates pass.
- Do not replace these titles before attempting group-only repair; replacement candidates are only needed if repaired provenance/listening/sync fails.

## 2026-07-08 Launch Convergence Learning

- Frontend dependency recovery succeeded with `npm ci --prefix frontend --legacy-peer-deps --no-audit --no-fund`; `react-scripts` and Craco validation are restored.
- UX truth validation is green locally: audio safety `4/4`, API same-origin tests `4/4`, production build PASS, cover audit `0` typographic-only covers, visual smoke `72/72`, and `git diff --check` PASS.
- The Bengali canary repair lane remains cost/lock-blocked, not source-blocked. `paid_tts.lock` is active with no allowed next holders, so Sarvam group repair and `muchiram-gurer-jibanchorit` representative retry must wait.
- Current public launch truth is unchanged: only `book-2b9853ec52` and `a-ghost-story` are audio-marketable; canary titles remain Coming Soon / production candidates with no Listen CTA.

## 2026-07-08 Bengali Pre-Launch Two-Title Gate

- `anandamathh` resolves deterministically to canonical slug `bn-066` / `আনন্দমঠ`; keep the user-request spelling only as provenance, not as the canonical slug.
- `bn-066` passes rights/source/content/cover/audiobook-clean extraction for Stage 1, but it is not audio-live. Representative Sarvam audition is blocked by active `paid_tts.lock`, and full audiobook generation must not run before representative evidence passes.
- `Pather Panchali` resolves to `pather-panchali`, but local data remains ambiguous because there is also a partial manifest entry and local source artifacts do not prove full-work audiobook scope. It also lacks approved front/back cover URLs for the pre-launch gate.
- Both titles must remain no-Listen public candidates. Marketing may say reader-ready or priority listening candidate after gates only; no audio teaser, narrator, duration, endpoint, or Listen CTA until browser gates pass.

## 2026-07-09 Bengali Paid Audition Stage 1

- Owner authorized a 5 USD representative-audition sprint, but the shell did not expose `MAX_TTS_BUDGET_USD=5` and the repo-required Bengali paid env gates were missing.
- No provider calls ran; spend is `0.00 USD`. Treat this as a blocked paid-execution preflight, not a failed audition.
- `bn-066` remains the first candidate after env gates and cleaned sample construction. Its opening reader chapter includes source/page boilerplate that must be stripped before TTS.
- `muchiram-gurer-jibanchorit` needs compact split samples before any retry. `book-d19e96859f` and `book-f5d593e1f4` remain targeted group-only repair diagnostics, not public audio.
- `pather-panchali` is a rights/source/cover repair track before paid audio. `a-ghost-story` remains outside this Bengali-priority sprint and must stay reader-first/audio-hidden.

## 2026-07-09 Bengali Paid Audition Stage 1B

- Command-scoped paid gates and `SARVAM_API_KEY` were present for the `bn-066` representative audition, but the run blocked before synthesis because no supported `ratan` voice was selected.
- The run used the owner-requested `--voice-filter sarvam:ratan` and `--max-voices-per-provider 1`; the bakeoff parser accepts `ratan` or `sarvam/ratan`, while the Bengali 9.2 policy ranks `pooja` before `ratan`, so a one-voice limit can exclude `ratan` before filtering.
- No audio was generated, no ASR/listening QA could run, and observed spend remains `0.00 USD`.
- Do not silently switch to `pooja` or widen the voice set. The next run needs explicit owner approval for either corrected `ratan` selection or a `pooja` audition.

## 2026-07-10 Bengali Paid Audition Stage 1C

- Owner authorized a supported-voice retry for `bn-066`, including fallback to `pooja` if `ratan` is unavailable, but the live shell did not expose `MAX_TTS_BUDGET_USD=5` or any required Bengali representative paid env gates.
- `SARVAM_API_KEY` is present, but provider credentials alone are not enough to open the paid lane. The run stopped before lock acquisition and before any Sarvam provider call.
- Actual spend remains `0.00 USD`; no sample, ASR, listening QA, sync, upload, metadata, endpoint, browser gate, or public audio approval exists for `bn-066`.
- Current voice evidence still comes from Stage 1B: `pooja` was listed and `ratan` was not. The next retry should use `pooja` unless a fresh gated capability probe lists `ratan`.

## 2026-07-10 Bengali Paid Audition Stage 1D

- Inline paid gates and `SARVAM_API_KEY` were present for `bn-066`; `paid_tts.lock` was acquired for `audiobook_enablement_sprint_1` and restored to active/no-holder after the run.
- The bakeoff selected Sarvam `pooja`, generated the cleaned `narrative_opening` passage, and estimated cost at `0.0119 USD`.
- The script stopped before synthesis because schema-3 listening QA was unavailable: `EARNALISM_ENABLE_OPENAI_LISTENING_QA` was not true.
- No audio was generated and actual spend remains `0.00 USD`. The next retry must enable listening QA in the same bounded env before any representative sample can be synthesized and judged.

## 2026-07-10 Bengali Paid Audition Stage 1E

- Inline paid TTS gates, `SARVAM_API_KEY`, `OPENAI_API_KEY`, `EARNALISM_ENABLE_OPENAI_LISTENING_QA=true`, and `EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio` were present for `bn-066`.
- The listening-QA hook reads the configured model env, but no repo-enforced bounded OpenAI/listening-QA USD cap was found.
- The run stopped before `paid_tts.lock` acquisition and before any Sarvam or OpenAI provider call because listening QA must remain inside the same `5 USD` cap.
- Actual spend remains `0.00 USD`; `bn-066` remains audio-hidden and not ready for full-book TTS. The next retry needs a bounded listening-QA spend gate before provider execution.

## 2026-07-10 Bengali Paid Audition Stage 1F

- Added a fail-closed OpenAI listening-QA budget gate: `EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD` is required before OpenAI listening QA can call the provider.
- `bn-066` ran one Sarvam `pooja` / `literary_warm_pacing` representative audition under `MAX_TTS_BUDGET_USD=5` and listening-QA cap `1`.
- The generated 45 second sample passed schema-3 QA under `bengali_audiobook_acceptance_v2_92`: overall `9.3`, confidence `0.95`, no fatal flags, and no frontmatter.
- Estimated total spend is `0.0619 USD`; actual provider billing was not reported. `bn-066` is ready for full-book TTS owner approval, but public Listen/upload/release gates remain blocked until full objective gates pass.

- 2026-07-10T10:54:33Z: Stage 2 generated private full-book `bn-066` Sarvam/pooja audio under the 5 USD cap (`1.2226 USD` estimated, actual billing not reported). Keep release gates closed until bounded ASR/source alignment and full-book listening QA pass.

- 2026-07-10T17:18:06Z: Stage 3 added an ASR budget gate and attempted bounded full-book ASR for `bn-066`, but OpenAI transcription stalled around `group_0079`/152. Keep release gates closed and add resumable per-chunk ASR checkpointing before retry.

- 2026-07-10T17:34:29Z: Stage 3B reclassified the `bn-066` ASR state as `ASR_CHECKPOINT_REPAIR_REQUIRED`, added per-chunk ASR checkpoints, request timeout, bounded retry controls, and remaining-chunk budget estimation. No provider calls ran; keep release gates closed until an owner-approved bounded checkpoint resume completes ASR/source alignment and listening QA.

- 2026-07-10T19:16:02Z: Stage 3C completed `152/152` checkpointed `bn-066` ASR chunks with zero timeout, failure, or retry and crossed the prior `group_0079` stall. The mixed-script transcript scored `0.8403/10` against the required `9.7`, with first/last ASR mismatches; bounded listening QA did not run. The static construction audit independently found 100% TTS-input coverage and a `1.0` canonical-to-clean match, but remained blocked because fresh generation records `group_repair.status=NOT_REQUESTED` while the verifier accepts `PASS` or `NOT_NEEDED`. Preserve all checkpoints and private audio; repair this manifest semantics mismatch before another bounded resume.

- 2026-07-10T20:02:48Z: Stage 3D proved `group_repair.status=NOT_REQUESTED` was a fresh-generation verifier semantics bug, not a failed repair: all 152 hashes, 100% prepared-text coverage, canonical match `1.0`, and first/last construction boundaries pass. The release gate remains blocked because `whisper-1` auto-detected Bengali per chunk into a Devanagari-dominant mixed-script transcript (`0.2801` Bengali ratio) and scored only `0.8403/10`. Recalibrate ASR language/model on a tiny bounded sample before normalization repair or any full retry; do not regenerate TTS without evidence of a true audio mismatch.
