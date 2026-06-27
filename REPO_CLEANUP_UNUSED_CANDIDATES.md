# Repo Cleanup Unused Candidates

Inventory generated from 1961 tracked files and 1807 indexed text files.

## SAFE_TO_QUARANTINE_HIGH_CONFIDENCE

Criteria used: no detected references, no package-script references, duplicate-style filename, and a counterpart without the duplicate suffix.

| Path | Counterpart | References | Package script reference | Action |
| --- | --- | ---: | --- | --- |
| regression/config/expected-indexes 2.json | regression/config/expected-indexes.json | 0 | no | quarantined |
| regression/config/modules 2.json | regression/config/modules.json | 0 | no | quarantined |
| regression/config/performance.rules 2.json | regression/config/performance.rules.json | 0 | no | quarantined |
| regression/config/seo.rules 2.json | regression/config/seo.rules.json | 0 | no | quarantined |
| regression/fixtures/books.manifest 2.json | regression/fixtures/books.manifest.json | 0 | no | quarantined |
| regression/modules/06-seo.test 2.js | regression/modules/06-seo.test.js | 0 | no | quarantined |
| regression/modules/08-mongodb-performance.test 2.js | regression/modules/08-mongodb-performance.test.js | 0 | no | quarantined |
| regression/modules/11-security-access-control.test 2.js | regression/modules/11-security-access-control.test.js | 0 | no | quarantined |
| regression/modules/12-migration-data-consistency.test 2.js | regression/modules/12-migration-data-consistency.test.js | 0 | no | quarantined |
| regression/reporters/moduleScoreReporter 2.js | regression/reporters/moduleScoreReporter.js | 0 | no | quarantined |
| regression/scripts/assert-go-live-pass 2.js | regression/scripts/assert-go-live-pass.js | 0 | no | quarantined |
| regression/scripts/post-deploy-canary 2.js | regression/scripts/post-deploy-canary.js | 0 | no | quarantined |
| regression/scripts/update-visual-baselines 2.js | regression/scripts/update-visual-baselines.js | 0 | no | quarantined |
| requirements 2.txt | requirements.txt | 0 | no | quarantined |
| scripts/audit_bengali_library 2.py | scripts/audit_bengali_library.py | 0 | no | quarantined |
| scripts/audit_data/bengali_live_source_evidence 2.json | scripts/audit_data/bengali_live_source_evidence.json | 0 | no | quarantined |
| scripts/extract_gutenberg_collection_stories 2.py | scripts/extract_gutenberg_collection_stories.py | 0 | no | quarantined |
| scripts/k6_10x_spike 2.js | scripts/k6_10x_spike.js | 0 | no | quarantined |
| scripts/live_library_green_audit 2.py | scripts/live_library_green_audit.py | 0 | no | quarantined |
| scripts/record_earnalism_tour 2.py | scripts/record_earnalism_tour.py | 0 | no | quarantined |
| scripts/render_bengali_covers 2.mjs | scripts/render_bengali_covers.mjs | 0 | no | quarantined |
| scripts/repair_and_prepare_bengali_wikisource 2.py | scripts/repair_and_prepare_bengali_wikisource.py | 0 | no | quarantined |
| scripts/run_audiobook_backfill 2.command | scripts/run_audiobook_backfill.command | 0 | no | quarantined |
| voices 2.json | voices.json | 0 | no | quarantined |
| voices 3.json | voices.json | 0 | no | quarantined |

## KEEP_EVIDENCE_OR_HISTORY

1483 files are retained because they are launch reports, legal/payment/audio evidence, internal manifests, owner QA artifacts, or history-heavy operational documents.

- ACCESSIBILITY_CLAIMS_POLICY.md
- ACCESSIBILITY_NON_VISUAL_JOURNEY_REPORT.md
- ACCESSIBLE_AUDIOBOOK_USER_JOURNEY.md
- AGENTS.md
- APPROVED_TO_PUBLISH.md
- APPROVED_TO_PUBLISH.template.md
- AUDIOBOOK_ACCESSIBILITY_10_10_RELEASE_CRITERIA.md
- AUDIOBOOK_ACCESSIBILITY_GATE_REPORT.md
- AUDIOBOOK_ASSET_QUARANTINE_REPORT.md
- AUDIOBOOK_CHAPTER_PIPELINE_REPORT.md
- AUDIOBOOK_CHUNK_GENERATION_PLAN.md
- AUDIOBOOK_COMPLIANCE_SCORECARD.md
- AUDIOBOOK_COST_CONTROL_REPORT.md
- AUDIOBOOK_DISCLOSURE_AND_CLAIMS_POLICY.md
- AUDIOBOOK_GENERATION_SYNC_PIPELINE_REPORT.md
- AUDIOBOOK_HIGHLIGHT_SYNC_QA_RUBRIC.md
- AUDIOBOOK_INTERNAL_SAMPLE_REVIEW_PACKET.md
- AUDIOBOOK_LEGAL_ACCESSIBILITY_COMPLIANCE_GATE.md
- AUDIOBOOK_MODEL_BAKEOFF_PLAN.md
- AUDIOBOOK_NARRATION_EDITORIAL_POLICY.md
- AUDIOBOOK_NARRATION_MODEL_DECISION_REPORT.md
- AUDIOBOOK_NARRATION_QA_RUBRIC.md
- AUDIOBOOK_NARRATION_SANITIZATION_REPORT.md
- AUDIOBOOK_PARALLEL_TRACK_STATUS.md
- AUDIOBOOK_PROVIDER_ADAPTER_POLICY.md
- AUDIOBOOK_READINESS_REPORT.md
- AUDIOBOOK_REGENERATION_GOVERNANCE_REPORT.md
- AUDIOBOOK_RELEASE_GATE_REPORT.md
- AUDIOBOOK_VOICE_PIPELINE.md
- AUDIOBOOK_VOICE_PROFILE_POLICY.md
- AUDIO_INTEGRATION_GUIDE.md
- AUTOSCALING_OPERATIONS_READINESS_REPORT.md
- AUTOSCALING_READINESS_REPORT.md
- BACKEND_CATALOG_TRUTH_AUDIT.md
- BACKEND_CATALOG_TRUTH_CANARY_FAILURE_ANALYSIS.md
- BACKEND_CATALOG_TRUTH_DEPLOYMENT_CHECKLIST.md
- BACKEND_CATALOG_TRUTH_MATRIX.csv
- BACKEND_SEO_TRUTH_REPORT.md
- BENGALI_AUDIOBOOK_HUMAN_QA_QUEUE.md
- BENGALI_AUDIOBOOK_HUMAN_REVIEW_SCORECARD.md
- BENGALI_AUDIOBOOK_RELEASE_PATHWAY.md
- BENGALI_AUDIOBOOK_STORE_CANDIDATE_INVENTORY.md
- BENGALI_AUDIOBOOK_STORE_IMPROVEMENT_PLAN.md
- BENGALI_AUDIOBOOK_STORE_ORCHESTRATOR_STAGE.md
- BENGALI_AUDIOBOOK_STORE_QUALITY_SCORECARD.md
- BENGALI_AUDIOBOOK_STORE_RELEASE_GATE_REPORT.md
- BENGALI_AUDIOBOOK_TOP_5_REMASTER_PLAN.md
- BENGALI_AUDIOBOOK_TOP_CANDIDATE_TRIAGE_REPORT.md
- BENGALI_GOTHIC_INTEREST_DASHBOARD.md
- BOOK_CARD_TRUTH_GATE_REPORT.md
- BOOK_ONBOARDING_ORCHESTRATION_REPORT.md
- BOOK_SEO_PRERENDER_PLAN.md
- BRANDING_ADVERTISEMENT_GO_NO_GO.md
- BRAND_SITE_TOUR_HUMAN_REVIEW_FORM.md
- BRAND_SITE_TOUR_VIDEO_INDEX.md
- BRAND_SITE_TOUR_VIDEO_SCORECARD.md
- CAROUSEL_AND_SHELVES_TRUTH_AUDIT.md
- CAROUSEL_SHELVES_VIDEO_REVIEW.md
- CATALOG_GOVERNANCE.md
- CATALOG_TRUTH_AUDIT_RUNBOOK.md
- ... 1423 more retained evidence/history files listed in REPO_CLEANUP_USAGE_INVENTORY.json

## KEEP_GENERATED_BUT_DOCUMENT

80 generated/static artifacts are retained because audits, snapshots, or launch evidence can depend on them.

- frontend/public/index.html
- frontend/public/robots.txt
- frontend/public/sitemap.xml
- output/call_of_the_wild/go_live_qa_report.md
- output/codex_prompts/next_english_book_onboarding_prompt.md
- output/launch/analytics_event_schema.json
- output/launch/audio_asset_audit.json
- output/launch/launch_readiness.json
- output/launch/payment_smoke.json
- output/launch/post_deploy_route_canary.json
- output/launch/post_deploy_route_canary.txt
- output/launch/production_removed_routes.json
- output/launch/production_removed_routes_curl.txt
- output/onboarding/frankenstein/AUDIOBOOK_CHAPTER_PIPELINE_REPORT.md
- output/onboarding/frankenstein/BOOK_ONBOARDING_ORCHESTRATION_REPORT.md
- output/onboarding/frankenstein/ELEVENLABS_DRACULA_HIGHLIGHT_SYNC_QA_REPORT.md
- output/onboarding/frankenstein/ELEVENLABS_DRACULA_INTERNAL_SAMPLE_REPORT.md
- output/onboarding/frankenstein/ELEVENLABS_DRACULA_SAMPLE_QA_SCORECARD.md
- output/onboarding/frankenstein/ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md
- output/onboarding/frankenstein/ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md
- output/onboarding/frankenstein/ENGLISH_AUDIOBOOK_QA_PACKET.md
- output/onboarding/frankenstein/ENGLISH_AUDIOBOOK_RELEASE_GATE_REPORT.md
- output/onboarding/frankenstein/ENGLISH_BOOK_PUBLICATION_GATE_REPORT.md
- output/onboarding/frankenstein/ENGLISH_BOOK_RIGHTS_EVIDENCE_SCORECARD.md
- output/onboarding/frankenstein/ENGLISH_BOOK_SEO_PREVIEW_REPORT.md
- output/onboarding/frankenstein/ENGLISH_BOOK_VISUAL_SCORECARD.md
- output/onboarding/frankenstein/KOKORO_AF_HEART_EVIDENCE_COLLECTION_CHECKLIST.md
- output/onboarding/frankenstein/KOKORO_AF_HEART_OWNER_LEGAL_REVIEW_FORM.md
- output/onboarding/frankenstein/KOKORO_SELECTED_VOICE_INTERNAL_EVAL_PACKET.md
- output/onboarding/frankenstein/KOKORO_SELECTED_VOICE_RIGHTS_SCORECARD.md
- output/onboarding/frankenstein/TTS_INTERNAL_EVAL_CANDIDATE_SCORECARD.md
- output/onboarding/frankenstein/TTS_MODEL_LICENSE_EVIDENCE_MATRIX.md
- output/onboarding/frankenstein/TTS_MODEL_PRODUCTION_ELIGIBILITY_REPORT.md
- output/onboarding/frankenstein/TTS_PROVIDER_COMMERCIAL_RIGHTS_SCORECARD.md
- output/onboarding/frankenstein/TTS_PROVIDER_INTERNAL_EVAL_REVIEW.md
- output/onboarding/frankenstein/TTS_VOICE_RIGHTS_INTERNAL_EVAL_APPROVAL_PACKET.md
- output/onboarding/frankenstein/audiobook_sync/qa_packet.json
- output/onboarding/frankenstein/audiobook_sync/release_gate_report.json
- output/onboarding/frankenstein/audiobook_sync/sync_manifest.json
- output/onboarding/frankenstein/english_book_onboarding_report.json
- output/onboarding/frankenstein/next_codex_prompt.md
- output/onboarding/frankenstein/tts_model_license_review.json
- output/onboarding/frankenstein/tts_provider_internal_eval_review.json
- output/publication_candidates/dracula/approved_to_publish_builder.json
- output/publication_candidates/dracula/dracula_gate_results.json
- output/publication_candidates/dracula/rights_evidence.json
- output/publication_candidates/dracula/source_evidence.json
- output/publication_candidates/dracula/source_hashes.json
- output/publication_candidates/kshudhita-pashan/audio_preview_plan.json
- output/publication_candidates/kshudhita-pashan/rights_evidence.json
- ... 30 more generated artifacts listed in REPO_CLEANUP_USAGE_INVENTORY.json

## REVIEW_REQUIRED

69 files require owner/developer review before any move. They were not quarantined.

| Path | Category | Reason |
| --- | --- | --- |
| assets/clavier-music-inspiring-cinematic-ambient-255033.mp3 | unknown | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| audio_generation.log | unknown | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/.dockerignore | backend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_api_public_catalog_projection.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_auth_password_safety.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_controlled_publication_publish.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_dracula_production_availability.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_elevenlabs_api_generation_pipeline.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_elevenlabs_internal_sample_import.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_elevenlabs_manual_generation_workflow.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_elevenlabs_narration_text_validation.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_elevenlabs_tts_client.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_english_book_onboarding_orchestrator.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_redis_cache_policy.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_tts_model_license_review.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| backend/tests/test_tts_provider_internal_eval_review.py | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/.dockerignore | unknown | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/craco.config.js | unknown | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/jsconfig.json | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/postcss.config.js | unknown | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/public/assets/shelves/history-politics.jpg | public asset | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/public/assets/shelves/literature.jpg | public asset | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/public/assets/shelves/self-growth.jpg | public asset | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/public/assets/shelves/technology.jpg | public asset | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/components/AppToaster.jsx | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/components/BookCoverImage.jsx | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/components/BrandMark.jsx | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/components/GoogleAuthBoundary.jsx | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/components/JsonLd.jsx | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/components/LiveCoverShowcase.jsx | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/components/ShareButtons.jsx | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/lib/api.test.js | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/lib/funnelOffers.js | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/lib/images.test.js | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/pages/NotFound.jsx | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/src/pages/SecureReaderHarness.jsx | frontend source | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| frontend/tailwind.config.js | unknown | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| monitor_audio_progress.sh | unknown | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| playwright.config.js | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/fixtures/visual-baselines/.gitkeep | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/modules/01-book-integrity.test.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/modules/02-rendering-visual.test.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/modules/04-legal-compliance.test.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/modules/05-url-navigation.test.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/modules/07-redis-cache.test.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/modules/08-mongodb-performance.test.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/modules/09-infra-readiness.test.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/modules/10-e2e-uat.test.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/modules/11-security-access-control.test.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/modules/12-migration-data-consistency.test.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/scripts/assert-go-live-pass.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/utils/db.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/utils/envGuard.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/utils/hashing.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/utils/http.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/utils/playwright.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/utils/redis.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| regression/utils/sitemap.js | test/regression | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| scripts/audit_bengali_library.py | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| scripts/extract_gutenberg_collection_stories.py | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| scripts/generate_and_upload_bengali_covers.py | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| scripts/generate_and_upload_business_covers.py | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| scripts/lib/elevenlabs_tts_client.py | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| scripts/live_library_green_audit.py | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| scripts/record_earnalism_tour.py | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| scripts/render_bengali_covers.mjs | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| scripts/repair_and_prepare_bengali_wikisource.py | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| scripts/repair_bengali_source_cases.py | script/tooling | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
| tools/docx_review.py | unknown | zero detected static references, but not enough confidence to move because it may be config, test entrypoint, public asset, support tool, or manual operator artifact |
