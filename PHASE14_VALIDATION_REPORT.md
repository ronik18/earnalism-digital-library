# Phase 14 Dracula Validation Report

Scope: harden PR #30 so Dracula can become a true Tier A controlled-publication candidate only when deterministic source, rights, hash, QA, route, payment, and approval-artifact gates pass.

Hardening commit checked: `a1eaa2101c747d7a627920b5ab7525f77d52d01d`.

No public content was published. No final controlled-publication activation was run. No production data was mutated. No LLM, TTS, STT, OCR, image, email, social, paid provider, or deployment command was run.

## Dracula Evidence

| Evidence | Status |
| --- | --- |
| Source URL | `https://www.gutenberg.org/ebooks/345` |
| Source text URL | `https://www.gutenberg.org/cache/epub/345/pg345.txt` |
| Source fetch mode | `EARNALISM_ALLOW_SOURCE_FETCH=true` explicit opt-in |
| Source license | `Project Gutenberg License` |
| Source hash | `9516dd7e092027e700b179c8f6d35499da43f4bb495c33184b655610aa2d17fe` |
| Content hash | `059ee06703b309c017b770587c6106afc0542a3cc9d52eb5daaf27fa633e2252` |
| Provenance hash | `512a127ee44fcd1ed61cf2c6d3352ab74147e7ab60e0855609c1a0842dbdb711` |
| Raw source characters | `881060` |
| Cleaned source characters | `840534` |
| Chapter count | `54` |
| Rights tier | `A` |
| Verification status | `approved` |
| QA status | `QA_PASSED` |
| Route canary | `PASS` |
| Payment smoke | `PASS_TEST_MODE` |
| Controlled precheck | `PASS` |
| Public publish actions | `0` |

## Commands Run

| Command | Result |
| --- | --- |
| `python3 scripts/check-hidden-unicode.py changed-files-list` | PASS for changed Dracula/report files |
| `python3 -m py_compile scripts/prepare_dracula_candidate.py scripts/approved_to_publish_builder.py scripts/post_deploy_route_canary.py scripts/launch_readiness_audit.py scripts/controlled_publication_precheck.py backend/tests/test_dracula_candidate_scripts.py` | PASS |
| `PYTHONPATH=. pytest backend/tests/test_dracula_candidate_scripts.py backend/tests/test_launch_readiness_audit.py backend/tests/test_rights_engine.py backend/tests/test_demand_scoring.py backend/tests/test_source_ingestion.py backend/tests/test_edition_generator.py backend/tests/test_visual_design_engine.py backend/tests/test_audiobook_voice_pipeline.py backend/tests/test_publishing_workflow.py backend/tests/test_daily_growth_loop.py backend/tests/test_automation_observability.py backend/tests/test_first_batch_dry_run.py` | PASS, 264 passed |
| `npm run regression:ci` | PASS, 12 suites passed / 2 skipped |
| `npm run catalog:audit` | PASS, 251 items audited |
| `npm run demand:score` | PASS |
| `npm run publish:workflow` | PASS dry-run |
| `npm run audio:voice` | PASS dry-run, audio not published |
| `npm run first-batch:dry-run` | PASS command, guarded dry-run with blocks |
| `npm run growth:daily` | PASS command, dry-run tasks only |
| `npm run observability:audit` | PASS command, sample guardrails BLOCKED unsafe actions as expected |
| `npm run launch:post-deploy-route-canary` | PASS |
| `npm run launch:production-parity` | PASS |
| `npm run launch:seo-audit` | Expected `BLOCKED_FOR_BOOK_SEO` for global launch |
| `npm run launch:payment-smoke` | PASS_TEST_MODE |
| `npm run launch:audio-audit` | PASS_WITH_WARNINGS |
| `npm run launch:readiness` | Expected `HOLD_FOR_FIXES` for global launch |
| `npm run controlled-publication:precheck` | PASS for Dracula approval artifact |
| `npm run regression -- modules/13-public-content-governance.test.js` | PASS, 18 passed |
| `npm --prefix frontend run build` | PASS |

## Raw Download Verification

`PHASE14_RAW_VERIFICATION.md` records raw GitHub `wc -l` checks for the changed scripts/tests on branch `codex/dracula-controlled-publication-candidate`.

## Dracula-Specific Paths

| Path | Result |
| --- | --- |
| Blocked path without source fetch | HOLD_FOR_FIXES, no approval artifact |
| Explicit fetch/evaluate-only path | PASS_EVALUATE_ONLY, no approval artifact write |
| Explicit approval artifact path with `EARNALISM_ALLOW_APPROVAL_ARTIFACT_WRITE=true` | PASS_APPROVAL_ARTIFACT_WRITTEN |

## Final Status

Dracula controlled-candidate score: `9.9/10`.

Recommendation: `GO_FOR_CONTROLLED_PUBLICATION_FOR_DRACULA_ONLY`.

This is not a final activation. Public publishing remains disabled until a separate explicit final controlled-publication activation step is requested and reviewed.
