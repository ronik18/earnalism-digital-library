# Phase 14 Dracula Validation Report

Scope: harden PR #30 so Dracula can only receive a controlled-publication approval artifact when source, rights, hash, QA, route, payment, workflow, and approval-builder gates all pass.

Baseline commit before this hardening diff: `735ff9712e8951ac2f84611e5efdb77d2ecaa1eb`.

No public content was published. No final controlled-publication activation was run. No production data was mutated. No deployment, email, social, LLM, TTS, STT, OCR, image, paid provider, or external publishing call was performed.

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
| Detected chapter segments | `54` |
| Meaningful chapter count | `27` |
| Rights tier | `A` |
| Verification status | `approved` |
| QA status | `QA_PASSED` |
| Publishing workflow | `READY_FOR_PUBLICATION_DRAFT_CANDIDATE` |
| Workflow blockers | `0` |
| Route canary | `PASS` |
| Payment smoke | `PASS_TEST_MODE` |
| Controlled precheck | `PASS` |
| Public publish actions | `0` |

## Hardening Checks

| Check | Result |
| --- | --- |
| Blocked no-source path | `HOLD_FOR_FIXES`; approval artifact removed/blocked |
| Approval builder with blocked workflow | Refuses approval and removes stale artifact |
| Approval builder with matching ready workflow | `PASS_EVALUATE_ONLY` and `PASS_APPROVAL_ARTIFACT_WRITTEN` |
| Hash consistency | source evidence, ingestion evidence, and `source_hashes.json` match |
| Meaningful chapter QA | Empty/TOC-like segments excluded; threshold requires at least 25 meaningful chapters |
| Approval artifact paths | Repo-relative paths only; no local absolute evidence paths |
| Approval scope | Core Dracula reading candidate only; full study guide, full visual edition, full audiobook, ads, email, and social publishing are excluded |
| Workflow status normalization | Lowercase and uppercase `approved` status inputs both evaluate correctly |

## Commands Run

| Command | Result |
| --- | --- |
| `unset EARNALISM_ALLOW_SOURCE_FETCH; python3 scripts/prepare_dracula_candidate.py --source-url https://www.gutenberg.org/ebooks/345 --dry-run && python3 scripts/approved_to_publish_builder.py --candidate output/publication_candidates/dracula/source_evidence.json --evaluate-only` | PASS fail-closed; builder status `BLOCKED` |
| `EARNALISM_ALLOW_SOURCE_FETCH=true python3 scripts/prepare_dracula_candidate.py --source-url https://www.gutenberg.org/ebooks/345 --dry-run` | PASS, recommendation `GO_FOR_CONTROLLED_PUBLICATION_FOR_DRACULA_ONLY` |
| `python3 scripts/approved_to_publish_builder.py --candidate output/publication_candidates/dracula/source_evidence.json --evaluate-only` | PASS_EVALUATE_ONLY |
| `EARNALISM_ALLOW_APPROVAL_ARTIFACT_WRITE=true python3 scripts/approved_to_publish_builder.py --candidate output/publication_candidates/dracula/source_evidence.json --write-approval-artifact` | PASS_APPROVAL_ARTIFACT_WRITTEN |
| `python3 scripts/check-hidden-unicode.py backend/publishing_workflow.py backend/tests/test_dracula_candidate_scripts.py backend/tests/test_publishing_workflow.py scripts/approved_to_publish_builder.py scripts/prepare_dracula_candidate.py APPROVED_TO_PUBLISH.md DRACULA_GATE_RESULTS.md DRACULA_SOURCE_RIGHTS_REPORT.md PHASE14_VALIDATION_REPORT.md` | PASS |
| `python3 -m py_compile backend/publishing_workflow.py scripts/prepare_dracula_candidate.py scripts/approved_to_publish_builder.py scripts/post_deploy_route_canary.py scripts/launch_readiness_audit.py scripts/controlled_publication_precheck.py backend/tests/test_dracula_candidate_scripts.py backend/tests/test_publishing_workflow.py` | PASS |
| `PYTHONPATH=. pytest backend/tests/test_dracula_candidate_scripts.py backend/tests/test_launch_readiness_audit.py backend/tests/test_rights_engine.py backend/tests/test_demand_scoring.py backend/tests/test_source_ingestion.py backend/tests/test_edition_generator.py backend/tests/test_visual_design_engine.py backend/tests/test_audiobook_voice_pipeline.py backend/tests/test_publishing_workflow.py backend/tests/test_daily_growth_loop.py backend/tests/test_automation_observability.py backend/tests/test_first_batch_dry_run.py` | PASS, 270 passed |
| `npm run regression:ci` | PASS, 12 suites passed / 2 skipped |
| `npm run catalog:audit` | PASS, 251 items audited |
| `npm run demand:score` | PASS |
| `npm run publish:workflow` | PASS dry-run |
| `npm run audio:voice` | PASS dry-run |
| `npm run first-batch:dry-run` | PASS, guarded dry-run with blocks |
| `npm run growth:daily` | PASS, dry-run tasks only |
| `npm run observability:audit` | PASS command; sample guardrails blocked unsafe actions as expected |
| `npm run launch:post-deploy-route-canary` | PASS |
| `npm run launch:production-parity` | PASS |
| `npm run launch:seo-audit` | Expected global-launch status `BLOCKED_FOR_BOOK_SEO` |
| `npm run launch:payment-smoke` | PASS_TEST_MODE |
| `npm run launch:audio-audit` | PASS_WITH_WARNINGS |
| `npm run launch:readiness` | Expected broader launch status `HOLD_FOR_FIXES` |
| `npm run controlled-publication:precheck` | PASS for Dracula approval artifact |
| `npm run regression -- modules/13-public-content-governance.test.js` | PASS, 18 passed |
| `npm --prefix frontend run build` | PASS |

## Line Integrity

Local line-count verification after this hardening:

| File | Line Count |
| --- | ---: |
| `backend/publishing_workflow.py` | 400 |
| `backend/tests/test_dracula_candidate_scripts.py` | 295 |
| `backend/tests/test_publishing_workflow.py` | 298 |
| `scripts/approved_to_publish_builder.py` | 429 |
| `scripts/prepare_dracula_candidate.py` | 1205 |
| `APPROVED_TO_PUBLISH.md` | 39 |
| `DRACULA_GATE_RESULTS.md` | 24 |
| `DRACULA_SOURCE_RIGHTS_REPORT.md` | 57 |
| `PHASE14_VALIDATION_REPORT.md` | 100 |

`PHASE14_RAW_VERIFICATION.md` documents the raw-download verification command pattern to rerun after this commit is pushed.

## Final Status

Dracula controlled-candidate score: `9.9/10`.

Recommendation: `GO_FOR_CONTROLLED_PUBLICATION_FOR_DRACULA_ONLY`.

This is not a final activation. Public publishing remains disabled until a separate explicit final controlled-publication activation step is requested and reviewed.
