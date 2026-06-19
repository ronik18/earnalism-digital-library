# Phase 13B Validation Report

Commit SHA at report generation: `302237d8807d628dcbf16d15f10921bfae5929d4`
Final score: `7.0/10`
Recommendation: `HOLD_FOR_FIXES`

## Commands

| Check | Command | Result |
| --- | --- | --- |
| hidden_unicode_scan | python3 scripts/check-hidden-unicode.py scripts/launch_readiness_audit.py scripts/open_source_audiobook_onboarding.py backend/tests/test_launch_readiness_audit.py frontend/src/pages/Pricing.jsx package.json PHASE13B_VALIDATION_REPORT.md PHASE13_RAW_VERIFICATION.md FINAL_GO_NO_GO_DECISION.md | PASS |
| py_compile | python3 -m py_compile scripts/launch_readiness_audit.py scripts/open_source_audiobook_onboarding.py backend/tests/test_launch_readiness_audit.py | PASS |
| phase_guardrail_pytest | PYTHONPATH=. pytest backend/tests/test_launch_readiness_audit.py backend/tests/test_rights_engine.py backend/tests/test_demand_scoring.py backend/tests/test_source_ingestion.py backend/tests/test_edition_generator.py backend/tests/test_visual_design_engine.py backend/tests/test_audiobook_voice_pipeline.py backend/tests/test_publishing_workflow.py backend/tests/test_daily_growth_loop.py backend/tests/test_automation_observability.py backend/tests/test_first_batch_dry_run.py | PASS, 253 passed |
| regression_ci | npm run regression:ci | PASS, 11 passed / 2 skipped |
| catalog_audit | npm run catalog:audit | PASS, 251 items audited |
| rights_audit | python3 scripts/rights_audit.py --input regression/fixtures/catalog-audit/books.json --output-dir output/rights_audit | PASS, approved=0 quarantine=2 blocked=0 |
| demand_score | npm run demand:score | PASS, 10 items scored |
| publish_workflow | npm run publish:workflow | PASS, dry-run readiness=READY |
| audio_voice | npm run audio:voice | PASS, dry-run ready |
| first_batch | npm run first-batch:dry-run | PASS, DRY_RUN_COMPLETE_WITH_BLOCKS |
| growth_daily | npm run growth:daily | PASS, dry-run tasks=17 blocked=3 |
| observability | npm run observability:audit | PASS command; dry-run report status=BLOCKED as guardrail evidence |
| launch_payment_smoke | npm run launch:payment-smoke | PASS_WITH_WARNINGS |
| launch_production_parity | npm run launch:production-parity | BLOCKED |
| launch_seo | npm run launch:seo-audit | BLOCKED_FOR_BOOK_SEO |
| launch_performance | npm run launch:performance-audit | PASS |
| launch_audio | npm run launch:audio-audit | PASS_WITH_WARNINGS |
| launch_readiness | npm run launch:readiness | HOLD_FOR_FIXES |
| public_content_governance | npm run regression -- modules/13-public-content-governance.test.js | PASS, 15 passed |
| frontend_build | npm --prefix frontend run build | PASS |

## Evidence Artifacts

- `output/launch/production_removed_routes_curl.txt`
- `output/launch/production_removed_routes.json`
- `output/launch/analytics_event_schema.json`
- `output/launch/payment_smoke.json`
- `output/launch/audio_asset_audit.json`
- `FIRST_BATCH_REAL_SOURCE_MATRIX.md`
- `FIRST_BATCH_REAL_SOURCE_MATRIX.csv`

No production content was mutated. No deploy, public publishing, provider call, email, social post, LLM, TTS, STT, OCR, image generation, or paid API call was performed.
