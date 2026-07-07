# Earnalism GO LIVE Sprint Dashboard

Generated: 2026-07-06

## Workstream Branches

| Workstream | Branch / worktree | Current status | Merge readiness |
| --- | --- | --- | --- |
| Book Publishing Factory | `sprint/book-publishing-factory` branch ref created from `main`; no active worktree assigned yet | Not run in this checkout; keep separate from UX dirty branch before executing Railway/factory work | Not merge-ready; needs isolated worktree/checkout and fresh factory audit |
| Luxury Frontend UX Rebirth | `sprint/luxury-ux-rebirth` current checkout | Second redesign/safety pass implemented; formal UX Index is 9.53 provisional | Partial; worktree is noisy and needs selective staging/cleanup plus same-origin preview validation before PR |

## Latest Commands Run

| Area | Command | Result |
| --- | --- | --- |
| Branching | `git switch -c sprint/luxury-ux-rebirth` | PASS |
| Branching | `git branch sprint/book-publishing-factory main` | PASS |
| UX build | `npm --prefix frontend run build` | PASS; React build and static SEO snapshots generated |
| UX unit safety | `npm --prefix frontend test -- --runTestsByPath src/lib/audioReleaseSafety.test.js --watchAll=false` | PASS; 4/4 audiobook release-safety tests |
| UX static route probe | `python3 -m http.server 4175 --directory frontend/build` + curl routes | PASS for `/`, `/library/`, `/book/dracula/`, `/reader/dracula/` |
| UX browser smoke | Playwright via system Chrome against `http://127.0.0.1:4175` | PASS for homepage/library/Dracula detail shell; localhost production API calls blocked by CORS as expected |
| Accessibility | axe-core WCAG 2 A/AA on local homepage, library, Dracula detail, desktop/mobile | PASS; 0 violations after fixes |

## Current Product State

| Metric | Current value | Source / note |
| --- | ---: | --- |
| Published audiobook books | 1 | Memory/repo cleanup report: `a-ghost-story` verified previously; not rerun in this checkout |
| Reader-only live count | ~160 | Existing release reports; requires fresh factory audit in book workstream |
| Audiobook-live count | 1 | Existing release reports |
| UX score | 9.53 / 10 provisional | Formal `earnalism_luxury_ux_index.json`; below 9.7 because same-origin preview, Lighthouse, and repo cleanup remain |
| Release-gate truth | PASS for changed UI | New helper hides audiobook controls unless metadata/release/QA/audio asset are approved |

## Latest Status

### Book Publishing Factory

- No book-factory execution was started from the dirty UX branch.
- Next action is to create/switch to an isolated worktree or checkout for `sprint/book-publishing-factory`, then run state truth/audit only.
- Known prior state from cleanup report: `a-ghost-story` is live, Bengali audio/manuscript mismatch blockers are evidenced, and audio naturalness/listening QA remains mandatory.

### Luxury Frontend UX Rebirth

- Added release-gate-safe audiobook visibility helper.
- Book cards and detail pages now show explicit premium reader/audio states without exposing blocked audio.
- Reader no longer presents browser/system speech fallback as an audiobook path.
- Approved audiobook spotlight renders only after provider-backed reader manifest proof.
- Dracula detail page uses controlled fallback metadata if production API is unavailable locally/404, without exposing reader content or audio.
- Audio player CSS invalid color syntax was fixed.
- Accessibility contrast and site-tour ARIA issues were fixed.
- Formal weighted Luxury UX Index and sprint report were added.

## Blockers

| Blocker | Workstream | Status | Required next action |
| --- | --- | --- | --- |
| Dirty repo contains many unrelated generated/imported files | Both | Active | Selectively stage only source/docs; do not commit generated artifacts |
| Book-factory branch has no isolated worktree yet | Book factory | Active | Use a separate worktree or checkout before running factory commands |
| Local build cannot fully load production API-backed routes due CORS | UX | Expected local limitation | Validate API-backed book/reader routes on deployed same-origin environment |
| Reader route still depends on production reader API | UX | Active production dependency | Do not create shadow static reader content unless release policy approves it |
| UX score below 9.7 | UX | Active | Run deployed preview/Lighthouse validation, clean worktree, then complete retention/motion polish |

## Next Exact Commands

### Book Publishing Factory

```bash
git worktree add /private/tmp/earnalism-sprint-book-factory sprint/book-publishing-factory
cd /private/tmp/earnalism-sprint-book-factory
python3 internal/audiobook_lab/scripts/release_catalog_factory.py \
  --manifest book_import_manifest.json \
  --languages eng,ben \
  --status-only \
  --resume-from-latest \
  --fail-closed
```

If production credentials are required:

```bash
railway run --project a8533934-35c4-463e-9f43-577a9ac391ee \
  --service 5af42e7e-f518-4f6a-b602-d9950866501f \
  --environment 580b250c-80ee-48ad-bfbe-fa4e31a6b378 -- \
python3 internal/audiobook_lab/scripts/release_catalog_factory.py \
  --manifest book_import_manifest.json \
  --languages eng,ben \
  --status-only \
  --resume-from-latest \
  --fail-closed
```

### Luxury UX Rebirth

```bash
npm --prefix frontend run build
```

Then rerun browser evidence on the deployed same-origin preview once available.

## Merge Readiness

- Do not merge as-is.
- The UX source changes are promising and build/a11y pass, but the worktree contains unrelated generated/imported changes.
- The book-factory branch must not inherit this dirty frontend state.

## Bengali Publishing Governor - 2026-07-06

| Metric | Value |
| --- | ---: |
| Bengali titles discovered | 106 |
| Reader-live precheck | 31 |
| Reader-only/audio-hidden recommended | 19 |
| Audio-decommission/reader-live recommended | 12 |
| Full title blocked with evidence | 75 |
| Bengali audiobook newly live | 0 |
| Provider status | AUDIO_PROVIDER_QUALITY_LIMIT |
| Best current provider sample | Sarvam `ritu`, score `7.9`, confidence `0.85` |
| OpenAI listening-QA quota | PASS |

Dashboard: `internal/audiobook_lab/release_gate/bengali_go_live_20260706T000000Z/bengali_go_live_dashboard.json`

Next exact command: implement a reader-only/audio-decommission production hook before running a Bengali metadata/browser wave. Do not run the audiobook factory against known stale Bengali audio.

## Graphical Covers + Calm Typography - 2026-07-06

| Metric | Value |
| --- | ---: |
| Previous UX score | 9.73 |
| Updated evidence-based UX score | 9.66 |
| Visible/controlled covers audited | 164 |
| Typography-only covers found | 0 |
| Typography-only covers remaining in customer UI | 0 |
| Runtime graphical fallbacks assigned | 105 |
| Visual smoke | PASS |
| Audio release safety | PASS |
| Build | PASS |
| Lighthouse performance | 90 |
| Lighthouse accessibility | 100 |
| Lighthouse SEO | 100 |
| LCP | 3.6s |

Status: PARTIAL. Graphical cover and calmer typography changes are validated, but performance remains below the requested >=94 guardrail, so this is not a 9.7+ / GREEN claim.

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && \
REACT_APP_BACKEND_URL=/api npm --prefix frontend run build && \
VISUAL_SMOKE_BASE_URL=http://127.0.0.1:4173 node frontend/scripts/visual-luxury-smoke.mjs && \
npx --yes lighthouse http://127.0.0.1:4173/ --chrome-flags="--headless=new --no-sandbox" --quiet
```

## Achievement-Aware Cost Governor - 2026-07-07

| Goal | Status | Cost decision |
| --- | --- | --- |
| Homepage/library visual regression | ACHIEVED_CONFIRMED | Skip redesign and full screenshot matrix unless source changes. |
| Home conversion UX baseline | ACHIEVED_NEEDS_LIGHT_REVERIFY | Prior GREEN evidence is stale after cover/type source changes; current evidence score is 9.66/perf 90. |
| Graphical cover requirement | ACHIEVED_CONFIRMED | Audit reports 0 typography-only customer-facing covers; skip cover generation. |
| Bengali reader-only/audio-hidden | ACHIEVED_CONFIRMED | Latest integration dashboard reports 31/31 approved, 0 rights blockers, 31 hidden audiobook endpoints; skip duplicate production mutations. |
| Bengali audiobook provider lane | BLOCKED | Keep audio hidden; no Sarvam/OpenAI paid auditions without explicit approval and higher-priority wins locked. |
| Clean merge/deploy package | NOT_ACHIEVED | Prepare clean worktree and source-only staging list next. |

Latest cost governor path: `internal/earnalism_intelligence/achievement_ledger.json`.

Next exact command:

```bash
cd /Users/ronikbasak/Documents/GitHub/earnalism-digital-library && git fetch origin && git worktree add /tmp/earnalism-sprint-clean origin/main && cd /tmp/earnalism-sprint-clean && git switch -c cleanup/source-only-sprint-package
```

## Performance Rescue - 2026-07-07

- Activated achievement-aware cost governor and froze Bengali reader-only, Sarvam provider-limit, graphical cover, visual smoke, and audio-safety wins.
- Root cause: Lighthouse LCP was held by the mobile hero image, then by automatic first-visit tour text and early idle prefetch/settings work.
- Fix: responsive compressed Dracula hero variants, mobile procedural cover face, lazy/delayed first-visit tour, delayed route prefetch/settings fetch, optimized bundled brand mark.
- Lighthouse: performance `90` -> `96`, LCP `3.6 s` -> `2.7 s`, total byte weight `Total size was 417 KiB` -> `Total size was 239 KiB`.
- Cover audit remains PASS: 164 covers, 0 typography-only covers.
- Visual smoke remains PASS. Audio safety remains PASS. Accessibility and SEO remain 100.
- No paid operations, provider calls, Bengali mutations, deployments, or broad catalog waves were run.


## Sarvam Bengali Seed Rescue - 2026-07-06T19:27Z

- Status: `AUDIO_PROVIDER_QUALITY_LIMIT`
- Provider/model/voice: `sarvam` / `bulbul:v3` / `pooja`
- Styles tested: `dialogue_human_touch`, `literary_warm_pacing`, `punctuation_aware_emotional`
- Representative score: `7.9`
- Confidence: `0.85`
- Seed generalized: `false`
- Full pilot generated: `false`
- Bengali audio public exposure: `none`; audio remains hidden
- Report: `sarvam_corrective_audition_report.json`
- Run report: `internal/audiobook_lab/release_gate/bengali_tts_provider_bakeoff_20260706T192224Z/bengali_tts_provider_bakeoff_report.json`
- Next exact command: do not run another Sarvam audition now; keep Bengali reader-only/audio-hidden until a new provider or licensed human audio path has evidence.

## Bengali Audio Closure - 2026-07-07

- Automated Bengali audiobook status: `AUDIO_PROVIDER_QUALITY_LIMIT_CONFIRMED`
- Evidence: Sarvam `bulbul:v3` / `pooja` did not generalize from an isolated 9.6 sample to representative narration.
- Representative score: `7.9`
- Confidence: `0.85`
- Red flags: `list_reading_rhythm_detected`, `mechanical_cadence_detected`
- Full pilot generated: `false`
- Upload/metadata/browser gates: not run
- Bengali reader-only approved: `31`
- Audiobook endpoints hidden: `31`
- Audio controls hidden: `PASS`
- Production mutations in this closure pass: `0`
- Future reopening criteria: new provider/model evidence, human narration workflow, licensed audiobook import, manually approved exceptional representative sample set, or improved Sarvam capability evidence.
- Next exact command: continue PR #87 merge readiness by fixing CI regression contracts and preview validation; do not run Bengali provider work.

## Sprint Continuation / PR87 - 2026-07-07

- PR #87 remains blocked from merge.
- `backend + frontend + browser regression`: fail.
- `regression gate`: fail.
- Railway deploy, Vercel deploy, and production canary: skipped.
- Vercel status context: pass, but actual deployment was `Canceled by Ignored Build Step`.
- Do not run Bengali provider work while this merge/deploy blocker remains.
- Vercel CLI note: local CLI is outdated; upgrade with `npm i -g vercel@latest` or `pnpm add -g vercel@latest` before further Vercel preview/deploy work.
- Next exact command:

```bash
cd /private/tmp/earnalism-clean-source-only-merge-20260706T191326Z && \
rg -n "pipeline-card-kshudhita-pashan|pipeline-books|live_approved_slugs|visual-luxury-smoke" frontend/src scripts regression data
```

## Bengali Audiobook 9.2 Rescue - 2026-07-06T21:48:08Z

- Policy: `bengali_audiobook_acceptance_v2_92`.
- Representative audition: PASS.
- Provider/model/voice/style: Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`.
- Representative score/confidence: 9.3 / 0.95.
- Fatal red flags: none for the passing arm.
- Pilot candidate: `book-2b9853ec52`.
- Full pilot generated: false.
- Production publish: false; ASR/sync/upload/metadata/browser gates not run.
- Reader-only/audio-hidden Bengali state remains protected.
- Report: `bengali_representative_audition_report.json`.

## Bengali Audiobook Campaign Activation - 2026-07-06T21:54:41Z

- Campaign status: `BENGALI_AUDIOBOOK_CAMPAIGN_ACTIVE`.
- Campaign titles: `31`.
- Published Bengali audiobooks: `0`.
- Representative-passed titles: `1` (`book-2b9853ec52`).
- Ready for representative audition after pilot proof: `30`.
- Best current setting: Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`, representative score `9.3`, confidence `0.95`.
- Full pilot score: not run.
- ASR/sync/upload/metadata/browser: not run.
- Duplicate passage/settings cache entries: `192`.
- Paid/provider operations in this activation: `0`.
- Campaign dashboard: `bengali_audiobook_campaign_dashboard.json`.
- Campaign queue: `bengali_audiobook_31_campaign_queue.json`.
- Next exact command: run the guarded Railway campaign controller command from `bengali_audiobook_next_actions.md`; do not scale beyond one full pilot until every objective gate passes.

## Bengali Sarvam Full Pilot - 2026-07-07T04:13Z

- Pilot: `book-2b9853ec52` / `দুই বিঘা জমি`.
- Provider/model/voice/style: Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`.
- Representative audition: PASS, score `9.3`, confidence `0.95`, no fatal flags.
- Full pilot TTS: GENERATED, duration `330.061917s`, estimated cost `$0.0197`, no stale local audio reuse.
- ASR/manuscript gate: BLOCKED, score `7.0199 < 9.7`, first/last boundary checks failed, no word/segment timestamps returned.
- Sync tier: none accepted; `auto_estimated_sync=false`.
- Listening QA, upload/checksum, metadata approval, endpoint, and browser gates: NOT RUN because ASR/sync blocked first.
- Published: `false`; Bengali audio remains hidden.
- Evidence: `sarvam_bengali_pilot_goliveevidence.json`, `sarvam_full_pilot_asr_report.json`, `sarvam_full_pilot_sync_report.json`, `sarvam_full_pilot_listening_report.json`.
- Next exact command: do not rerun full TTS automatically; require explicit owner approval before any repaired second pilot after the frontmatter-stripping hook fix.

## Visual Brand System Hardening - 2026-07-07T04:54:30+00:00

- Cover inventory: 164 active/public covers audited; 0 typography-only covers found; 0 remaining in customer UI.
- Graphical coverage: 106 deterministic runtime graphical fallbacks; 164 effective front/back cover pairs.
- Typography: home/library/book-card/book-detail scales reduced for calmer premium hierarchy without shrinking below readable sizes.
- Validation: Lighthouse performance 96, LCP 2641.1ms, accessibility 100, SEO 100; visual smoke PASS with 72/72 checks; audio safety PASS 4/4.
- Preview: protected Vercel preview remains blocked by login shell without `VERCEL_AUTOMATION_BYPASS_SECRET` or a shareable preview link; local same-origin proxy remains canonical evidence for this pass.

## 2026-07-07T05:06:15.040184+00:00 Bengali Pilot ASR Forensics
- `book-2b9853ec52` full pilot remains hidden and unpublished.
- ASR score `7.0199`; no word/segment timestamps; upload/checksum, metadata, and browser gates were not run.
- Forensics diagnosis: current TTS input contains disallowed frontmatter/source metadata; `tts_by_construction_verified=false`.
- Reports: `book_2b9853ec52_bengali_asr_forensics_plan.json`, `book_2b9853ec52_tts_source_provenance_report.json`, `book_2b9853ec52_bengali_asr_provider_comparison.json`, `book_2b9853ec52_bengali_pilot_closeout.json`.

## Bengali Pilot Clean Repair - 2026-07-07T05:21:38.249911+00:00
- `book-2b9853ec52` remains unpublished/audio-hidden.
- Repair ready: regenerate contaminated group 0 only; reuse groups 1 and 2.
- Planned clean TTS provenance: coverage 100%, `tts_by_construction_verified=true`.
- Remaining blocker: explicit paid/provider approval and budget env vars before Sarvam group repair and downstream gates.

## Bengali Pilot Audio QA PASS - 2026-07-07T05:54:36Z

- Pilot: `book-2b9853ec52` / `দুই বিঘা জমি`.
- Provider/model/voice/style: Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`.
- TTS provenance: PASS, clean TTS input coverage `100.0%`, canonical-to-clean-TTS match `1.0`, `tts_by_construction_verified=true`.
- ASR provider status: weak/mixed-script and diagnostic only; `asr_transcript_match_score=1.1258`, `asr_release_status=SUPPORTING_DIAGNOSTIC_WEAK`.
- Source verification for release: PASS by clean TTS source provenance, `source_match_score=10.0`.
- Sync: PASS, `PARAGRAPH_OR_STANZA_SYNC_PREMIUM`, measured group audio durations, `auto_estimated_sync=false`.
- Listening QA: PASS, score `9.4`, confidence `0.95`, no fatal red flags.
- Upload/checksum, metadata approval, endpoint, browser: NOT RUN.
- Published: `false`; Bengali audio remains hidden until final gates pass.
- Next exact command: run the guarded single-pilot factory resume with TTS/ASR/paid workers disabled and upload/metadata/browser workers enabled.

## Bengali Pilot Final Gate Blocked - 2026-07-07T07:27:10Z

- Pilot: `book-2b9853ec52` / `দুই বিঘা জমি`.
- Upload/checksum: PASS for final repaired audio and measured paragraph/stanza sidecars.
- Metadata API: PASS after clearing partial audio metadata and reapplying Sarvam provenance.
- Metadata provenance: Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing` is preserved in local controlled-publication evidence; production admin response stores provider `sarvam` and voice `ratan`.
- Endpoint: BLOCKED, public audiobook route still returns `404`.
- Browser gate: NOT RUN because endpoint verification failed.
- Published: `false`; audio remains hidden from the public endpoint.
- Next exact action: deploy/restart or refresh the backend controlled-launch/audio route, then resume metadata/browser only with TTS/ASR/upload workers disabled.

## Bengali Pilot Endpoint Materialization - 2026-07-07T07:43:30Z

- Root cause: production admin metadata has Sarvam audio assets, but public routes are hidden by the packaged backend controlled-launch truth gate.
- Public route status: `/api/books/book-2b9853ec52` `404`, `/api/reader/book/book-2b9853ec52` `404`, `/api/reader/book/book-2b9853ec52/audiobook` `404`.
- Data mismatch: root `data/controlled_launch.json` includes the pilot in live/audio allowlists; `backend/data/controlled_launch.json` does not.
- Safe action: prepare a clean backend deploy package with the packaged allowlist/source fix; do not deploy the current dirty workspace.
- Resume after deploy: metadata/browser only, with TTS/ASR/sync/upload workers disabled.

## Homepage Figma Alignment - 2026-07-07T10:45:00Z

- Status: `GREEN_LOCAL_SOURCE_VALIDATED_DEPLOY_PENDING`.
- Live-vs-Figma gap fixed in source: homepage no longer uses Dracula as the main hero or static fallback headline.
- Source hero: hybrid editorial reading-room hero plus three curated action cards.
- Bengali Classics: visible in action-card row with reader-only/live copy and no audio promise.
- English Classics: Dracula remains one refined action tile.
- Approved Audiobooks: gated; no A Ghost Story audio CTA or default probe.
- UX index: `9.74`, local production-equivalent.
- Lighthouse: performance `98`, LCP `2491.1598ms`, accessibility `100`, SEO `100`.
- Cover audit: `164` visible/controlled covers, `0` typographic-only remaining.
- Visual smoke: PASS `72/72`.
- Audio release safety: PASS `4/4`.
- Deploy status: not deployed by Codex. Next action is a clean source-only branch/PR or targeted deploy after owner approval.
## 2026-07-07 Figma UX System Status

- Home source: aligned to hybrid editorial hero plus three curated action cards.
- Library source: aligned to premium catalog controls and reader-ready/audio-hidden truth.
- Reader source: aligned to calm reading room defaults, expanded settings, and paragraph/stanza sync wording.
- Cover status: PASS, 164 audited, 0 typographic-only public covers.
- Audio safety: PASS, no unapproved controls exposed by audioReleaseSafety tests.
- Visual smoke: PASS, 72 routes/viewports completed.
- Lighthouse local production-equivalent: performance 97, LCP 2554.18 ms, accessibility 100, SEO 100, CLS 0, TBT 0.
- Live deploy status: PARTIAL. Production still serves the old Dracula-first static shell and requires source promotion/deploy validation.

## Parallel Go-Live Acceleration - 2026-07-07T16:33:36+05:30

- Coordination artifacts: `parallel_go_live_sprint_dashboard.json`, `parallel_go_live_sprint_dashboard.md`, and lock files under `internal/earnalism_intelligence/locks/`.
- Bengali pilot endpoint: live API detail/manifest expose approved audio; audiobook endpoint returns `206`; a non-pilot Bengali sample remains audio-hidden.
- Bengali pilot browser gate: BLOCKED. Factory browser gate cannot see production reader audio controls or measure audio start latency; production frontend bundle lacks current reader-manifest audio-control support.
- PR87: GitHub checks PASS, Vercel PASS, protected preview validation PASS; owner may merge after review. PR87 alone is not expected to resolve the Bengali pilot browser gate because it does not include `Reader.jsx`/`audioReleaseSafety.js` manifest-audio support.
- Bengali reader-only rights lane: no production mutation. Requested dry-run script is absent, and existing intelligence reports 31 reader-only approved and 0 rights blockers.
- Canary prep: `bengali_next_3_canary_preflight.json` written for post-pilot planning only; no TTS or upload ran.
- Validation: endpoint branch Bengali materialization tests PASS 7/7; factory stop-guard/listening schema checks PASS; `npm ci --prefix frontend` PASS with existing warnings; frontend audio safety PASS 4/4; frontend build PASS; `git diff --check` PASS.

## Bengali Audiobook Pilot Live - 2026-07-07T11:48:33Z

- Pilot `book-2b9853ec52` / `দুই বিঘা জমি` is production-live as the first Bengali audiobook.
- Frontend source: `codex/bengali-approved-audio-locked-reader-panel` at `bbf5c17f06643c12c52a4aff4062b25da0f0cc6b`, deployed to production via Vercel `dpl_8d4m6uSb3NAkdiHB7TQaRAPevgFi`.
- Final gates: upload/checksum PASS, metadata PASS, endpoint PASS, browser gate PASS, no remaining blockers.
- Audio evidence: Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing`, listening `9.4` with confidence `0.95`, sync tier `PARAGRAPH_OR_STANZA_SYNC_PREMIUM`, `auto_estimated_sync=false`.
- Production verification: pilot reader manifest exposes approved audio and the audiobook endpoint returns audio; sample unapproved Bengali title `book-ac5a71075e` remains audio-hidden.
- Catalog final gate: `CATALOG GO LIVE READY`, published this run `1`, total audiobook-live count `2`, Bengali audiobook-live count `1`.
- Do not start the 3-title Bengali canary until owner approval; recommended candidates remain `muchiram-gurer-jibanchorit`, `book-d19e96859f`, and `book-2ddbed8293`.

## Bengali Post-Go-Live Stabilization - 2026-07-07T12:30:00Z

- Status: source stabilization branch in progress, no production mutation and no TTS/ASR/sync/upload reruns.
- Pilot live status: `book-2b9853ec52` remains live by prior endpoint/manifest/browser evidence.
- Detail copy fix: source now merges reader-manifest evidence into `BookDetail` and recognizes `manifest.audio.url`; approved copy is `Audiobook available`, with paragraph/stanza sync represented as section-following narration.
- Unapproved Bengali audio: remains hidden; incomplete audio evidence returns reader-safe copy and no controls.
- Source preservation: `release_catalog_factory.py` and `factory_hooks/browser_hook.py` in the clean integration branch match the original workspace hashes.
- PR readiness: PR #88 is open as a stacked PR on `codex/source-only-clean-integration`; production stale detail copy remains until the source-only base and stabilization PR are merged/deployed.
- Canary preflight: `muchiram-gurer-jibanchorit`, `book-d19e96859f`, and `book-f5d593e1f4` are prepared for a future owner-approved canary; `book-2ddbed8293` is blocked by missing public source/API visibility, and `book-4968248842` is skipped pending source/title provenance review.
