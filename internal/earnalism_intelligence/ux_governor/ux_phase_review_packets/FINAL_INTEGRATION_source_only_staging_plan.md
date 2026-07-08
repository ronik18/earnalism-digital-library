# FINAL_INTEGRATION Source-Only Staging Plan

Generated: 2026-07-08T14:05:00Z

## Objective

Create a clean source-only staging set for the approved UX release candidate. This plan does not commit, deploy, upgrade Vercel CLI, unlock paid TTS, approve paid Listen campaigns, mutate release gates, or claim production validation.

## Staging Decision Summary

| Bucket | Decision |
| --- | --- |
| Frontend source | COMMIT_SOURCE |
| Frontend tests | COMMIT_TEST |
| UX governor packets/state | COMMIT_GOVERNANCE / COMMIT_REVIEW_PACKET |
| Decision ledgers and sprint learnings | COMMIT_GOVERNANCE |
| `frontend/public/sitemap.xml` | REVIEW_BEFORE_COMMIT; default restore/exclude |
| `frontend/build/` | DO_NOT_STAGE; gitignored build output |
| `/tmp/earnalism-ux-review/**` | DO_NOT_STAGE; local screenshots/contact sheets only |
| `ux_visual_regression_report.json` | EXCLUDE_TMP unless owner requests raw smoke artifact |
| Root report JSON/log files | REVIEW_BEFORE_COMMIT or DO_NOT_STAGE |
| Audiobook operational reports/daemon files | DO_NOT_STAGE for this UX source-only PR unless explicitly approved |

## COMMIT_SOURCE

Stage these app/runtime source changes:

- `frontend/public/service-worker.js`
- `frontend/scripts/visual-luxury-smoke.mjs`
- `frontend/src/components/AudioPlayer.css`
- `frontend/src/components/AudioPlayer.jsx`
- `frontend/src/components/BookCard.jsx`
- `frontend/src/components/Footer.jsx`
- `frontend/src/components/Header.jsx`
- `frontend/src/components/ShelfTwoSlideshow.jsx`
- `frontend/src/components/BrandHeaderLogo.jsx`
- `frontend/src/config/socialLinks.js`
- `frontend/src/hooks/useSEO.js`
- `frontend/src/index.css`
- `frontend/src/lib/audioReleaseSafety.js`
- `frontend/src/lib/bookDetailPresentation.js`
- `frontend/src/lib/controlledLaunch.js`
- `frontend/src/lib/libraryCatalog.js`
- `frontend/src/lib/libraryFallbackBooks.js`
- `frontend/src/lib/readerSettings.js`
- `frontend/src/pages/About.jsx`
- `frontend/src/pages/BookDetail.jsx`
- `frontend/src/pages/Contact.jsx`
- `frontend/src/pages/Journal.jsx`
- `frontend/src/pages/Library.jsx`
- `frontend/src/pages/Pricing.jsx`
- `frontend/src/pages/Reader.jsx`

## COMMIT_SOURCE Intentional Deletion

- `frontend/src/components/AudioPlayer 2.jsx`

Reason: duplicate legacy audio player risk removed so it cannot be reconnected with static audio behavior.

## COMMIT_TEST

Stage these tests:

- `frontend/src/components/AudioPlayer.releaseTruth.test.js`
- `frontend/src/components/BrandHeaderLogo.test.js`
- `frontend/src/lib/audioReleaseSafety.test.js`
- `frontend/src/lib/bookDetailPresentation.test.js`
- `frontend/src/lib/libraryCatalog.test.js`
- `frontend/src/lib/marketingLandingTruth.test.js`
- `frontend/src/lib/readerSettings.test.js`
- `frontend/src/pages/Reader.releaseTruth.test.js`

## COMMIT_GOVERNANCE / COMMIT_REVIEW_PACKET

Stage these governance sources and packets:

- `internal/earnalism_intelligence/decision_ledger.jsonl`
- `internal/earnalism_intelligence/sprint_learnings.md`
- `internal/earnalism_intelligence/ux_governor/**`

The `ux_governor` directory contains the phase policies, owner approval state, decision ledger, and review packets for HOME through FINAL_INTEGRATION.

## REVIEW_BEFORE_COMMIT

Do not include these in the default source-only `git add` command:

- `frontend/public/sitemap.xml`: build-generated SEO artifact. Current diff changes `lastmod` dates and route ordering. Commit only after explicit SEO-owner review.
- `graphical_cover_generation_report.json`: cover-audit timestamp churn only. Default restore before commit.
- `repo_cleanup_report.md`: broad hygiene report; useful evidence but noisy for a focused source PR.
- `sprint_go_live_dashboard.md`: broad sprint dashboard; useful evidence but noisy for a focused source PR.
- `parallel_prelaunch_sprint_dashboard.json`
- `parallel_prelaunch_sprint_dashboard.md`
- `parallel_prelaunch_validation_summary.json`
- `parallel_prelaunch_unblock_plan.json`
- `ux_governor_readiness_report.json`
- `frontend_visual_smoke_blocker.json`
- `home_visual_smoke_static_route_404_diagnosis.json`

## DO_NOT_STAGE / DELETE_TEMP

Default exclude from the source-only PR:

- `frontend/build/`
- `ux_visual_regression_report.json`
- `book_cover_art_briefs.json`
- `audio_deployment.log`
- `audio_generation.log`
- `english_audio_sync.log`
- `prelaunch_bengali_audiobook_daemon.log`
- `prelaunch_bengali_audiobook_daemon_heartbeat.json`
- `prelaunch_bengali_audiobook_daemon_state.json`
- `prelaunch_bengali_audiobook_next_actions.json`

## DO_NOT_STAGE Unless Owner Explicitly Adds Audiobook Evidence

These are audiobook/rights/forensics artifacts, not source-only UX release source:

- `audiobook_pipeline_status_audit.json`
- `audiobook_pipeline_status_audit.md`
- `bengali_canary_asr_forensics_summary.json`
- `bn_066_audiobook_clean_text_report.json`
- `bn_066_content_integrity_report.json`
- `bn_066_cover_readiness_report.json`
- `bn_066_prelaunch_rights_source_audit.json`
- `bn_066_representative_audition_ready_report.json`
- `book-d19e96859f_canary_source_provenance_report.json`
- `book-f5d593e1f4_canary_source_provenance_report.json`
- `muchiram_gurer_representative_timeout_repair_report.json`
- `paid_tts_lock_diagnosis.json`
- `pather_panchali_audiobook_go_no_go_report.json`
- `pather_panchali_cover_repair_plan.json`
- `pather_panchali_full_work_completeness_report.json`
- `pather_panchali_source_scope_review_report.json`
- `internal/audiobook_lab/scripts/prelaunch_bengali_audiobook_daemon.py`

## REVIEW_BEFORE_COMMIT For Locks

- `internal/earnalism_intelligence/locks/backend_deploy.lock`
- `internal/earnalism_intelligence/locks/paid_tts.lock`
- `internal/earnalism_intelligence/locks/production_metadata.lock`
- `internal/earnalism_intelligence/locks/ux_owner_approval.lock`

`paid_tts.lock` is active and legitimate, but lock files are operational governance state. Stage only if the owner wants lock state preserved in the PR.

## Sitemap Decision

Decision: `REVIEW_BEFORE_COMMIT`.

Rationale:

- Build regenerated `frontend/public/sitemap.xml`.
- Diff includes date churn from `2026-07-04` to `2026-07-08`.
- Diff also reorders `book/dracula` and `book/book-2b9853ec52`.
- This may be valid generated SEO output, but it is not required for source-only UX staging and should not be staged blindly.

Default action before source-only commit:

```bash
git restore -- frontend/public/sitemap.xml
```

Only stage it after explicit SEO-owner review.

## Exact Source-Only `git add` Command

```bash
git add -- \
  frontend/public/service-worker.js \
  frontend/scripts/visual-luxury-smoke.mjs \
  "frontend/src/components/AudioPlayer 2.jsx" \
  frontend/src/components/AudioPlayer.css \
  frontend/src/components/AudioPlayer.jsx \
  frontend/src/components/AudioPlayer.releaseTruth.test.js \
  frontend/src/components/BookCard.jsx \
  frontend/src/components/BrandHeaderLogo.jsx \
  frontend/src/components/BrandHeaderLogo.test.js \
  frontend/src/components/Footer.jsx \
  frontend/src/components/Header.jsx \
  frontend/src/components/ShelfTwoSlideshow.jsx \
  frontend/src/config/socialLinks.js \
  frontend/src/hooks/useSEO.js \
  frontend/src/index.css \
  frontend/src/lib/audioReleaseSafety.js \
  frontend/src/lib/audioReleaseSafety.test.js \
  frontend/src/lib/bookDetailPresentation.js \
  frontend/src/lib/bookDetailPresentation.test.js \
  frontend/src/lib/controlledLaunch.js \
  frontend/src/lib/libraryCatalog.js \
  frontend/src/lib/libraryCatalog.test.js \
  frontend/src/lib/libraryFallbackBooks.js \
  frontend/src/lib/marketingLandingTruth.test.js \
  frontend/src/lib/readerSettings.js \
  frontend/src/lib/readerSettings.test.js \
  frontend/src/pages/About.jsx \
  frontend/src/pages/BookDetail.jsx \
  frontend/src/pages/Contact.jsx \
  frontend/src/pages/Journal.jsx \
  frontend/src/pages/Library.jsx \
  frontend/src/pages/Pricing.jsx \
  frontend/src/pages/Reader.jsx \
  frontend/src/pages/Reader.releaseTruth.test.js \
  internal/earnalism_intelligence/decision_ledger.jsonl \
  internal/earnalism_intelligence/sprint_learnings.md \
  internal/earnalism_intelligence/ux_governor
```

## Exact Restore/Remove Commands For Generated Artifacts

Run only immediately before commit after confirming no owner needs these artifacts staged:

```bash
git restore -- frontend/public/sitemap.xml graphical_cover_generation_report.json
rm -f \
  book_cover_art_briefs.json \
  frontend_visual_smoke_blocker.json \
  home_visual_smoke_static_route_404_diagnosis.json \
  ux_visual_regression_report.json
```

Keep operational audiobook reports/logs untracked unless owner explicitly asks to include them:

```bash
rm -f \
  prelaunch_bengali_audiobook_daemon.log \
  prelaunch_bengali_audiobook_daemon_heartbeat.json \
  prelaunch_bengali_audiobook_daemon_state.json \
  prelaunch_bengali_audiobook_next_actions.json
```

## Final Pre-Commit Validation Commands

```bash
npm ci --prefix frontend --legacy-peer-deps --no-audit --no-fund
npm test --prefix frontend -- --watchAll=false
REACT_APP_BACKEND_URL=/api npm run build --prefix frontend
node frontend/scripts/audit-book-covers.mjs
python3 internal/earnalism_intelligence/ux_governor/run_ux_governor_check.py
git diff --check
```

Strict full-route visual smoke Stage A passed 189/189 with no blockers. Rerun it before commit only if source changes after this staging review.

## Final Source Truth Checks

```bash
grep -RInE 'sales@reoenterprise\.in|mailto:sales@reoenterprise\.in' frontend/src frontend/public internal/earnalism_intelligence/ux_governor/ux_phase_review_packets 2>/dev/null || true
grep -RInE 'speechSynthesis|SpeechSynthesisUtterance|word-level|word level|word sync|AudioObject|static /audio|/audio/|paid Listen|Listen now' frontend/src frontend/public 2>/dev/null | head -n 300 || true
```

Expected result:

- No bad public `.in` email matches.
- Release-risk hits should be test-only, internal-only, or approval-gated.
