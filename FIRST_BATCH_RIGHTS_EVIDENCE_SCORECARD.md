# First Batch Rights Evidence Scorecard

Generated for the current branch as a dry-run governance artifact. This file does not publish books, enable audio, expose private hashes publicly, deploy, or mutate production data.

## Executive Summary

- Dracula is the only approved public core reading release today.
- Dracula approval is narrow: core reading only. It does not approve a full study guide, full visual edition, full audiobook, ads, emails, or social campaigns.
- Kshudhita Pashan remains pipeline-only. Its source evidence is useful, but public reading/audio remains blocked until permalink, license compliance, owner approval, and controlled-publication review pass.
- Every first-batch product remains HOLD because source/license/commercial-use/hash/provenance/QA/owner-approval evidence is incomplete.
- Audiobook derivative rights are not approved for any item in this scorecard.
- Public audio remains blocked. Previously direct-reachable static audio assets have been moved to `internal/audio_quarantine/frontend-public-audio/`, and `frontend/public` plus `frontend/build` must remain audio-free before any controlled publication action.

## Reviewed Sources

- `AGENTS.md`
- `PRODUCT_TRUTH_LEDGER.md`
- `CATALOG_GOVERNANCE.md`
- `CONTROLLED_PUBLICATION_PRECHECK.md`
- `APPROVED_TO_PUBLISH.md`
- `FIRST_BATCH_REAL_SOURCE_MATRIX.csv`
- `FIRST_BATCH_REAL_SOURCE_MATRIX.md`
- `FIRST_BATCH_REAL_SOURCE_BACKFILL_INPUT.template.json`
- `FIRST_BATCH_SOURCE_RIGHTS_BACKFILL_PLAN.md`
- `DRACULA_SOURCE_RIGHTS_REPORT.md`
- `DRACULA_CONTROLLED_ARTIFACT_PACK_REPORT.md`
- `DRACULA_SEO_PRERENDER_IMPLEMENTATION_REPORT.md`
- `AUDIOBOOK_ACCESSIBILITY_10_10_RELEASE_CRITERIA.md`
- `ACCESSIBLE_AUDIOBOOK_USER_JOURNEY.md`
- `AUDIOBOOK_ACCESSIBILITY_GATE_REPORT.md`
- `AUDIOBOOK_ASSET_QUARANTINE_REPORT.md`
- `scripts/controlled_publication_precheck.py`
- `scripts/audit-public-content.mjs`
- `scripts/source_ingestion.py`
- `scripts/audiobook_accessibility_release_gate.py`
- `regression/modules/11-seo.test.js`
- `regression/modules/13-public-content-governance.test.js`
- `regression/modules/14-ux-conversion-static.test.js`

## Decision Legend

- `GO_DRACULA_CORE_READING_ONLY`: approved only for the existing Dracula core reading surface.
- `HOLD_PIPELINE_ONLY`: internal pipeline or draft work may continue; no public reader, preview, audio, or public metadata claim.
- `HOLD_SOURCE_RIGHTS_QA_REQUIRED`: source, rights, hashes, QA, and owner approval are missing or incomplete.

## Rights Evidence Matrix

| Title | Author | Language | Current Status | Public Visibility | Source URL | Source Name | Source License | License URL | Commercial Use Status | Source Hash | Content Hash | Provenance Hash | Attribution Requirement | Derivative/Audiobook Rights Status | Public Metadata Allowed | Public CTA Allowed | Owner Approval Status | GO/HOLD Decision | Blocking Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dracula | Bram Stoker | English | live approved core reading | public book page and reader preview allowed | https://www.gutenberg.org/ebooks/345 | Project Gutenberg eBook #345 | Project Gutenberg License | https://www.gutenberg.org/policy/license.html | conditional_allowed_subject_to_project_gutenberg_license_and_trademark_terms | 9516dd7e092027e700b179c8f6d35499da43f4bb495c33184b655610aa2d17fe | 059ee06703b309c017b770587c6106afc0542a3cc9d52eb5daaf27fa633e2252 | 512a127ee44fcd1ed61cf2c6d3352ab74147e7ab60e0855609c1a0842dbdb711 | simple_public_source_note_allowed; license/source evidence internal | not approved; separate approval required; AUDIO_NOT_REQUIRED for core reading | yes | yes | approved | GO_DRACULA_CORE_READING_ONLY | None for core reading. Audio, full study guide, full visual edition, ads, email, and social remain outside approval. |
| Kshudhita Pashan | Rabindranath Tagore | Bengali | pipeline-only | not public/live | https://bn.wikisource.org/wiki/%E0%A6%97%E0%A6%B2%E0%A7%8D%E0%A6%AA-%E0%A6%A6%E0%A6%B6%E0%A6%95/%E0%A6%95%E0%A7%8D%E0%A6%B7%E0%A7%81%E0%A6%A7%E0%A6%BF%E0%A6%A4_%E0%A6%AA%E0%A6%BE%E0%A6%B7%E0%A6%BE%E0%A6%A3 | Bengali Wikisource | Creative Commons Attribution-Share Alike 4.0 | https://creativecommons.org/licenses/by-sa/4.0/deed.bn | conditional_allowed_subject_to_cc_by_sa_attribution_sharealike_and_permalink_review | 33c52e97617493f9278d97f01d26d9a72685bf7e648b097c8e81582e59c7e9fa | e17c53487382eb060ff724dd1d35d9fc965cd90d6856b9b462b0e0091ee9ecf0 | 6b567144f5e8176b27ac3cd80ad804d2c0d8438008d7b293c87f6263fe04339c | CC BY-SA attribution and share-alike required | not approved; separate approval required | no | no | OWNER_APPROVAL_REQUIRED | HOLD_PIPELINE_ONLY | Source oldid/permalink capture, attribution/share-alike compliance, controlled-publication precheck, and owner approval are still required. |
| Anandamath Visual Study Companion | Bankim Chandra Chattopadhyay | Bengali | pipeline | not public/live | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_COMMERCIAL_USE | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_DERIVATIVE_RIGHTS | no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED | Real source metadata, commercial-use evidence, hashes, derivative/audio rights evidence, QA, and owner approval are not present. |
| Devdas Study Edition | Sarat Chandra Chattopadhyay | Bengali | pipeline | not public/live | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_COMMERCIAL_USE | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_DERIVATIVE_RIGHTS | no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED | Real source metadata, commercial-use evidence, hashes, derivative/audio rights evidence, QA, and owner approval are not present. |
| Abol Tabol Illustrated Reader | Sukumar Ray | Bengali | pipeline | not public/live | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_COMMERCIAL_USE | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_DERIVATIVE_RIGHTS | no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED | Real source metadata, commercial-use evidence, hashes, derivative/audio rights evidence, QA, and owner approval are not present. |
| Sultana's Dream Feminist Sci-Fi Edition | Rokeya Sakhawat Hossain | English | pipeline | not public/live | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_COMMERCIAL_USE | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_DERIVATIVE_RIGHTS | no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED | Real source metadata, commercial-use evidence, hashes, derivative/audio rights evidence, QA, and owner approval are not present. |
| Sherlock Holmes Logic Workbook | Arthur Conan Doyle | English | pipeline | not public/live | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_COMMERCIAL_USE | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_DERIVATIVE_RIGHTS | no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED | Real source metadata, commercial-use evidence, hashes, derivative/audio rights evidence, QA, and owner approval are not present. |
| Dracula Gothic Fiction Visual Guide | Bram Stoker | English | pipeline | not public/live | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_COMMERCIAL_USE | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_DERIVATIVE_RIGHTS | no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED | The live Dracula core reading candidate is separately approved; this visual-guide product remains blocked until its own source, derivative, QA, and owner-approval evidence exists. |
| Frankenstein Science & Ethics Guide | Mary Shelley | English | pipeline | not public/live | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_COMMERCIAL_USE | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_DERIVATIVE_RIGHTS | no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED | Real source metadata, commercial-use evidence, hashes, derivative/audio rights evidence, QA, and owner approval are not present. |
| Tagore Short Stories for Young Readers | Rabindranath Tagore | Bengali/English | pipeline | not public/live | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_COMMERCIAL_USE | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_DERIVATIVE_RIGHTS | no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED | Real source metadata, commercial-use evidence, hashes, derivative/audio rights evidence, QA, and owner approval are not present. |
| Calculus Made Easy Visual Guide | Silvanus P. Thompson | English | pipeline | not public/live | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_COMMERCIAL_USE | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_DERIVATIVE_RIGHTS | no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED | Real source metadata, commercial-use evidence, hashes, derivative/audio rights evidence, QA, and owner approval are not present. |
| Chander Pahar Adventure Companion | Bibhutibhushan Bandyopadhyay | Bengali | pipeline | not public/live | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_COMMERCIAL_USE | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | SOURCE_METADATA_REQUIRED | UNKNOWN_DERIVATIVE_RIGHTS | no | no | OWNER_APPROVAL_REQUIRED | HOLD_SOURCE_RIGHTS_QA_REQUIRED | Real source metadata, commercial-use evidence, hashes, derivative/audio rights evidence, QA, and owner approval are not present. |

## Public Metadata Policy

- Public book metadata may be emitted only for Dracula core reading today.
- Public JSON-LD must not expose `source_hash`, `content_hash`, `provenance_hash`, internal source evidence, or private rights metadata.
- First-batch and Kshudhita pipeline items may appear only as pipeline/Notify Me surfaces with no Start Reading, Read Preview, Listen Now, audio, or checkout-like CTA.
- Sitemap entries must not include unapproved reader or book routes.
- Audio-like files must not exist under `frontend/public` or `frontend/build`. Unlinked is not enough because static files are direct-reachable by URL.
- Public attribution may stay simple and truthful, but private provenance hashes, internal evidence URLs, and raw source-evidence internals stay out of public JSON-LD and public pages.

## Audiobook Derivative Rights Policy

- No item in this scorecard has public audiobook rights approval.
- Dracula audio remains disabled and outside the core reading approval.
- Kshudhita audio remains pipeline-only and requires separate rights, source, pronunciation, listening QA, and owner approval.
- First-batch derivative/audiobook rights are `UNKNOWN_DERIVATIVE_RIGHTS` until manually reviewed.
- `PUBLIC_AUDIO_RELEASE_BLOCKED` remains the correct release-gate status.
- Any future audiobook or sample-listening release requires derivative/audiobook rights, model commercial-use permission, model license evidence, voice rights, no voice-cloning risk, transcript/sync evidence, Bengali/English human listening QA, owner approval, and rollback approval.

## Gate Hardening Added

- Controlled-publication precheck now requires license URL, commercial-use status, attribution requirement, derivative/audiobook status, public metadata policy, public CTA policy, owner approval status, and GO/HOLD decision.
- Controlled-publication precheck now blocks if audio-like files exist under `frontend/public` or `frontend/build`.
- Controlled-publication activation validates the same fields before any Dracula-only activation can proceed.
- First-batch matrices and backfill templates now carry those fields as required evidence.
- Regression coverage blocks unapproved public CTAs, public audio claims, private hash exposure, stale PR-only claims, first-batch/Kshudhita public publication claims, public AudioObject metadata, and direct-reachable static audio assets.

## Remaining Blockers

- Capture immutable source URLs/permalinks and license URLs per work.
- Compute source/content/provenance hashes from the exact source text used for ingestion.
- Complete deterministic rights verification and QA per product.
- Complete derivative/audiobook rights review separately from text rights.
- Add owner approval per product and rerun controlled-publication precheck.
- Keep public publishing disabled until each item passes its own evidence gate.
- Keep quarantined audio assets out of public static directories until a separate public-audio release gate passes.

## Files Changed In This Hardening Pass

- `FIRST_BATCH_RIGHTS_EVIDENCE_SCORECARD.md`
- `scripts/controlled_publication_precheck.py`
- `backend/tests/test_controlled_publication_precheck.py`
- `regression/modules/11-seo.test.js`
- `regression/modules/14-ux-conversion-static.test.js`
- `scripts/audiobook_accessibility_release_gate.py`
- `backend/tests/test_audiobook_accessibility_release_gate.py`
- `AUDIOBOOK_ACCESSIBILITY_GATE_REPORT.md`
- `AUDIOBOOK_READINESS_REPORT.md`
- `AUDIOBOOK_ASSET_QUARANTINE_REPORT.md`
- `output/launch/audio_asset_audit.json`
- `internal/audio_quarantine/frontend-public-audio/`

## Validation Notes

Validation must be rerun after every source-rights evidence update:

- `python3 scripts/check-hidden-unicode.py FIRST_BATCH_RIGHTS_EVIDENCE_SCORECARD.md`
- `python3 scripts/check-hidden-unicode.py <changed files>`
- `git diff --check`
- `npm run controlled-publication:precheck`
- `npm run catalog:audit`
- `npm run launch:audio-audit`
- `npm run audiobook:release-gate`
- `npm run launch:seo-audit`
- `npm run launch:social-preview-audit`
- `npm run regression -- modules/11-seo.test.js modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js`
- `npm --prefix frontend run build`
- `PYTHONPATH=. pytest backend/tests/test_controlled_publication_precheck.py backend/tests/test_audiobook_accessibility_release_gate.py`

Latest validation result for this hardening pass:

- Hidden Unicode / line-ending scan on changed report, source, test, regression, and audit JSON files: PASS, 11 files.
- Hidden Unicode / line-ending scan on quarantined `.json` and `.vtt` sidecars: PASS, 20 files.
- `git diff --check`: PASS.
- Python compile for controlled-publication precheck, audiobook release gate, and focused tests: PASS.
- Focused Python tests: PASS, 17 passed.
- `npm run controlled-publication:precheck`: PASS.
- `npm run catalog:audit`: PASS, 46 items audited.
- `npm run launch:audio-audit`: PASS.
- `npm run audiobook:release-gate`: PASS_EXPECTED_BLOCKED, `PUBLIC_AUDIO_RELEASE_BLOCKED`, 23 blockers.
- `npm run launch:seo-audit`: PASS.
- `npm run launch:social-preview-audit`: PASS.
- Regression modules 11, 13, and 14: PASS, 65 passed.
- `npm --prefix frontend run build`: PASS.
- Final direct scan of `frontend/public` and `frontend/build` for audio-like files: PASS, no files found.

## Rollback

Revert this scorecard update and the gate/test hardening changes. Do not move quarantined audio assets back to `frontend/public` unless a separate approved public-audio release exists with derivative rights, model/voice evidence, listening QA, accessibility evidence, owner approval, and rollback approval. No production content or public publication state is mutated by these files.
