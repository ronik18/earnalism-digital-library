# Merge Stack Readiness Report

Generated: `2026-06-21T10:03:36.851336+00:00`

Scope: open PRs #42, #43, #44, #45, and #46 for `ronik18/earnalism-digital-library`.

No merge, deploy, production publication, audiobook enablement, social post, live Razorpay call, or production data mutation was performed.

## Main Baseline

- `origin/main`: `2b2f71ca1685016ba4a76be7007cd0879a4ec479`

## Executive Recommendation

Recommended safest merge order:

1. **PR #43** audiobook regeneration governance. Establishes shared audiobook gate/policy baseline before model bakeoffs.
2. **PR #46** premium social brand kit. Low runtime risk; merge after #43 to avoid final go/no-go doc drift and package script overlap.
3. **PR #42** premium site-tour video package. Merge after #46 so branding/go-no-go docs can be reconciled once, and rerun UX/static regression.
4. **PR #44** Bengali audiobook model bakeoff, only after it leaves Draft and is rebased on the merged #43 baseline.
5. **PR #45** English audiobook model bakeoff, only after it leaves Draft and is rebased after #44 or explicitly reconciled with #44 shared license evidence and release-gate files.

Do not merge #44 or #45 while they are Draft. Do not merge #44/#45 before reconciling shared audiobook release-gate tests, package scripts, and license evidence files.

## PR Summary

| PR | Title | Draft | Branch | HEAD | Main merge | Risk | Expected hardening commit |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| #42 | Create premium Earnalism site-tour video package | false | `codex/premium-site-tour-video-package` | `75192d70` | CLEAN / GitHub `True` | 6.5 | `75192d70` present |
| #43 | Add separately approved regenerated audiobook narration workflow | false | `codex/audiobook-regeneration-governance` | `bf6ee229` | CLEAN / GitHub `True` | 7.0 | `bf6ee229` present |
| #44 | Benchmark open-source Bengali audiobook narration models | true | `codex/bengali-audiobook-model-bakeoff` | `a2d34c75` | CLEAN / GitHub `True` | 8.2 | `a2d34c75` present |
| #45 | Benchmark open-source English audiobook narration models | true | `codex/english-audiobook-model-bakeoff` | `70f4b0e1` | CLEAN / GitHub `True` | 8.1 | `70f4b0e1` present |
| #46 | Create premium Earnalism social media brand kit | false | `codex/premium-social-brand-kit` | `ec5e0525` | CLEAN / GitHub `True` | 5.2 | `ec5e0525` present |

## Branch Heads And Recent Logs

### PR #42: Create premium Earnalism site-tour video package

- Branch: `codex/premium-site-tour-video-package`
- HEAD: `75192d701da6af4a92525c8bd30eca2ceb6dd769`
- Changed files: `14`
- `git log --oneline -5`:
  - `75192d70 Burn overlays into premium site tour master`
  - `20924da0 Harden premium site tour scorecard evidence`
  - `484e3e50 Harden premium site tour evidence package`
  - `e3d210e4 Create premium Earnalism site-tour package`
  - `2b2f71ca Merge pull request #41 from ronik18/codex/premium-footer-social-links`

### PR #43: Add separately approved regenerated audiobook narration workflow

- Branch: `codex/audiobook-regeneration-governance`
- HEAD: `bf6ee22904a834a273c66e991984e8ecca8ade0e`
- Changed files: `21`
- `git log --oneline -5`:
  - `bf6ee229 Harden audiobook regeneration evidence gates`
  - `5a62a1f9 Harden audiobook regeneration release gates`
  - `6aea92fc Add approved audiobook regeneration workflow`
  - `2b2f71ca Merge pull request #41 from ronik18/codex/premium-footer-social-links`
  - `2dc2f06c Add premium social media links to footer`

### PR #44: Benchmark open-source Bengali audiobook narration models

- Branch: `codex/bengali-audiobook-model-bakeoff`
- HEAD: `a2d34c757d7c98d54452619d9c619a8c5680e039`
- Changed files: `43`
- `git log --oneline -5`:
  - `a2d34c75 Harden Bengali bakeoff review gates`
  - `082fbb77 Harden Bengali audiobook bakeoff gates`
  - `65dea3af Benchmark open-source Bengali audiobook narration models`
  - `2b2f71ca Merge pull request #41 from ronik18/codex/premium-footer-social-links`
  - `2dc2f06c Add premium social media links to footer`

### PR #45: Benchmark open-source English audiobook narration models

- Branch: `codex/english-audiobook-model-bakeoff`
- HEAD: `70f4b0e1883d999e091cb0efcd2eb6ce0eb64d75`
- Changed files: `50`
- `git log --oneline -5`:
  - `70f4b0e1 Harden English bakeoff review gates`
  - `212f6617 Harden English audiobook model bakeoff gates`
  - `77b9c264 Benchmark English audiobook narration models`
  - `2b2f71ca Merge pull request #41 from ronik18/codex/premium-footer-social-links`
  - `2dc2f06c Add premium social media links to footer`

### PR #46: Create premium Earnalism social media brand kit

- Branch: `codex/premium-social-brand-kit`
- HEAD: `ec5e0525d4a6a2b57bc586d7f89d4491d60fbd4f`
- Changed files: `68`
- `git log --oneline -5`:
  - `ec5e0525 Create premium Earnalism social brand kit`
  - `2b2f71ca Merge pull request #41 from ronik18/codex/premium-footer-social-links`
  - `2dc2f06c Add premium social media links to footer`
  - `90e82097 Merge pull request #40 from ronik18/codex/static-seo-snapshots-dracula`
  - `565d134d Add static SEO snapshots for Dracula launch`

## Mergeability And Conflicts

### Against Main

- PR #42: `CLEAN` against `origin/main` (conflicts: none).
- PR #43: `CLEAN` against `origin/main` (conflicts: none).
- PR #44: `CLEAN` against `origin/main` (conflicts: none).
- PR #45: `CLEAN` against `origin/main` (conflicts: none).
- PR #46: `CLEAN` against `origin/main` (conflicts: none).

### Pairwise PR Conflict Matrix

| Pair | Status | Conflict files | Overlapping files |
| --- | --- | --- | --- |
| #42 + #43 | CONFLICT | `regression/modules/14-ux-conversion-static.test.js` | `FINAL_GO_NO_GO_DECISION.md`, `package.json`, `regression/modules/14-ux-conversion-static.test.js` |
| #42 + #44 | CLEAN | None | `package.json` |
| #42 + #45 | CLEAN | None | `package.json` |
| #42 + #46 | CONFLICT | `BRANDING_ADVERTISEMENT_GO_NO_GO.md`, `FINAL_GO_NO_GO_DECISION.md` | `BRANDING_ADVERTISEMENT_GO_NO_GO.md`, `FINAL_GO_NO_GO_DECISION.md`, `package.json` |
| #43 + #44 | CONFLICT | `backend/tests/test_audiobook_regeneration_workflow.py`, `backend/tests/test_audiobook_release_gate.py`, `package.json`, `scripts/audiobook_release_gate.py` | `backend/tests/test_audiobook_regeneration_workflow.py`, `backend/tests/test_audiobook_release_gate.py`, `package.json`, `scripts/audiobook_release_gate.py` |
| #43 + #45 | CONFLICT | `AUDIOBOOK_DISCLOSURE_AND_CLAIMS_POLICY.md`, `AUDIOBOOK_PROVIDER_ADAPTER_POLICY.md`, `AUDIOBOOK_VOICE_PROFILE_POLICY.md`, `backend/audiobook_generation/__init__.py`, `backend/tests/test_audiobook_regeneration_workflow.py`, `backend/tests/test_audiobook_release_gate.py`, `scripts/audiobook_release_gate.py` | `AUDIOBOOK_DISCLOSURE_AND_CLAIMS_POLICY.md`, `AUDIOBOOK_PROVIDER_ADAPTER_POLICY.md`, `AUDIOBOOK_VOICE_PROFILE_POLICY.md`, `backend/audiobook_generation/__init__.py`, `backend/tests/test_audiobook_regeneration_workflow.py`, `backend/tests/test_audiobook_release_gate.py`, `package.json`, `scripts/audiobook_release_gate.py` |
| #43 + #46 | CLEAN | None | `FINAL_GO_NO_GO_DECISION.md`, `package.json` |
| #44 + #45 | CONFLICT | `backend/tests/test_audiobook_regeneration_workflow.py`, `backend/tests/test_audiobook_release_gate.py`, `data/audiobook_models/license_evidence/chatterbox.json`, `data/audiobook_models/license_evidence/dia.json`, `data/audiobook_models/license_evidence/f5-tts.json`, `data/audiobook_models/license_evidence/xtts-v2.json`, `scripts/audiobook_release_gate.py` | `backend/tests/test_audiobook_regeneration_workflow.py`, `backend/tests/test_audiobook_release_gate.py`, `data/audiobook_models/license_evidence/chatterbox.json`, `data/audiobook_models/license_evidence/dia.json`, `data/audiobook_models/license_evidence/f5-tts.json`, `data/audiobook_models/license_evidence/xtts-v2.json`, `package.json`, `scripts/audiobook_release_gate.py` |
| #44 + #46 | CLEAN | None | `package.json` |
| #45 + #46 | CLEAN | None | `package.json` |

## Overlapping Files

- `AUDIOBOOK_DISCLOSURE_AND_CLAIMS_POLICY.md`: #43, #45
- `AUDIOBOOK_PROVIDER_ADAPTER_POLICY.md`: #43, #45
- `AUDIOBOOK_VOICE_PROFILE_POLICY.md`: #43, #45
- `BRANDING_ADVERTISEMENT_GO_NO_GO.md`: #42, #46
- `FINAL_GO_NO_GO_DECISION.md`: #42, #43, #46
- `backend/audiobook_generation/__init__.py`: #43, #45
- `backend/tests/test_audiobook_regeneration_workflow.py`: #43, #44, #45
- `backend/tests/test_audiobook_release_gate.py`: #43, #44, #45
- `data/audiobook_models/license_evidence/chatterbox.json`: #44, #45
- `data/audiobook_models/license_evidence/dia.json`: #44, #45
- `data/audiobook_models/license_evidence/f5-tts.json`: #44, #45
- `data/audiobook_models/license_evidence/xtts-v2.json`: #44, #45
- `package.json`: #42, #43, #44, #45, #46
- `regression/modules/14-ux-conversion-static.test.js`: #42, #43
- `scripts/audiobook_release_gate.py`: #43, #44, #45

## Committed Reports And Regression Evidence

### PR #42
- `BRANDING_ADVERTISEMENT_GO_NO_GO.md`
- `BRAND_SITE_TOUR_HUMAN_REVIEW_FORM.md`
- `BRAND_SITE_TOUR_VIDEO_INDEX.json`
- `BRAND_SITE_TOUR_VIDEO_INDEX.md`
- `BRAND_SITE_TOUR_VIDEO_SCORECARD.json`
- `BRAND_SITE_TOUR_VIDEO_SCORECARD.md`
- `FINAL_GO_NO_GO_DECISION.md`
- `SITE_TOUR_FEATURE_HIGHLIGHT_REPORT.md`
- Regression evidence claimed in PR body / required for merge:
  - `npm run brand:site-tour`
  - `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js`
  - `npm --prefix frontend run build`

### PR #43
- `AUDIOBOOK_DISCLOSURE_AND_CLAIMS_POLICY.md`
- `AUDIOBOOK_PROVIDER_ADAPTER_POLICY.md`
- `AUDIOBOOK_REGENERATION_GOVERNANCE_REPORT.md`
- `AUDIOBOOK_RELEASE_GATE_REPORT.md`
- `AUDIOBOOK_VOICE_PROFILE_POLICY.md`
- `FINAL_GO_NO_GO_DECISION.md`
- `KSHUDHITA_PASHAN_REGENERATED_AUDIO_APPROVAL_FORM.md`
- `KSHUDHITA_PASHAN_REGENERATED_AUDIO_QA_CHECKLIST.md`
- `KSHUDHITA_PASHAN_REGENERATED_NARRATION_STYLE_GUIDE.md`
- Regression evidence claimed in PR body / required for merge:
  - `npm run audiobook:release-gate:expect-blocked`
  - `npm run audiobook:release-gate:expect-ready || true`
  - `npm run launch:audio-audit`
  - `PYTHONPATH=. pytest backend/tests/test_audiobook_regeneration_workflow.py backend/tests/test_audiobook_release_gate.py`

### PR #44
- `AUDIOBOOK_BENGALI_MODEL_BAKEOFF_SCORECARD.json`
- `AUDIOBOOK_BENGALI_MODEL_BAKEOFF_SCORECARD.md`
- `AUDIOBOOK_MODEL_BAKEOFF_AUDIO_QA_REPORT.md`
- `AUDIOBOOK_MODEL_BAKEOFF_HUMAN_REVIEW_FORM.md`
- `AUDIOBOOK_MODEL_SELECTION_REPORT.md`
- `BENGALI_AUDIOBOOK_CHUNK_COVERAGE_REPORT.md`
- `BENGALI_GOTHIC_VOICE_CONFIG_REPORT.md`
- `BENGALI_TEXT_NORMALIZATION_REPORT.md`
- Regression evidence claimed in PR body / required for merge:
  - `npm run audiobook:model-bakeoff:plan`
  - `npm run audiobook:model-bakeoff:dry-run`
  - `npm run audiobook:release-gate`
  - `PYTHONPATH=. pytest backend/tests/test_bengali_audiobook_model_bakeoff.py backend/tests/test_bengali_audiobook_chunker.py backend/tests/test_audiobook_model_adapters.py`

### PR #45
- `AUDIOBOOK_DISCLOSURE_AND_CLAIMS_POLICY.md`
- `AUDIOBOOK_ENGLISH_MODEL_BAKEOFF_AUDIO_QA_REPORT.md`
- `AUDIOBOOK_ENGLISH_MODEL_BAKEOFF_HUMAN_REVIEW_FORM.md`
- `AUDIOBOOK_ENGLISH_MODEL_RESEARCH_REPORT.md`
- `AUDIOBOOK_ENGLISH_MODEL_SELECTION_REPORT.md`
- `AUDIOBOOK_ENGLISH_SAMPLE_SCORECARD.json`
- `AUDIOBOOK_ENGLISH_SAMPLE_SCORECARD.md`
- `AUDIOBOOK_PROVIDER_ADAPTER_POLICY.md`
- `AUDIOBOOK_VOICE_PROFILE_POLICY.md`
- `ENGLISH_AUDIOBOOK_CHUNK_COVERAGE_REPORT.md`
- `ENGLISH_GOTHIC_VOICE_CONFIG_REPORT.md`
- `ENGLISH_TEXT_NORMALIZATION_REPORT.md`
- Regression evidence claimed in PR body / required for merge:
  - `npm run audiobook:english-model-bakeoff:plan`
  - `npm run audiobook:english-model-bakeoff:dry-run`
  - `npm run audiobook:release-gate`
  - `PYTHONPATH=. pytest backend/tests/test_english_audiobook_model_bakeoff.py backend/tests/test_english_audiobook_chunker.py backend/tests/test_english_audiobook_model_adapters.py`

### PR #46
- `BRANDING_ADVERTISEMENT_GO_NO_GO.md`
- `FINAL_GO_NO_GO_DECISION.md`
- `SOCIAL_ASSET_INDEX.md`
- `SOCIAL_LINK_COLLECTION_RUNBOOK.md`
- `SOCIAL_PROFILE_COPYBOOK.md`
- `SOCIAL_PROFILE_OWNER_UPLOAD_CHECKLIST.md`
- `SOCIAL_PROFILE_REVAMP_REPORT.md`
- `SOCIAL_PROFILE_REVAMP_SCORECARD.json`
- `SOCIAL_PROFILE_REVAMP_SCORECARD.md`
- `SOCIAL_VISUAL_ASSET_GUIDE.md`
- `data/social_brand/platform_profiles.json`
- `output/social-brand-kit/latest/SOCIAL_ASSET_INDEX.md`
- `output/social-brand-kit/latest/social_asset_index.json`
- Regression evidence claimed in PR body / required for merge:
  - `npm run social:brand-kit`
  - `npm run social:links:validate || true`
  - `PYTHONPATH=. pytest backend/tests/test_social_brand_kit.py backend/tests/test_backend_catalog_truth.py`
  - `npm --prefix frontend run build`

## Required Tests Before Merge

Baseline for every PR after rebase or conflict resolution:

- `python3 scripts/check-hidden-unicode.py changed-files-list`
- `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js`
- `npm run regression:ci`
- `npm --prefix frontend run build`
- `npm run launch:backend-catalog-truth-canary`
- `npm run launch:post-deploy-route-canary`
- `npm run launch:production-parity`
- `npm run launch:seo-audit`
- `npm run controlled-publication:precheck`

PR #42 specific tests:
- `npm run brand:site-tour`
- `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js`
- `npm --prefix frontend run build`

PR #43 specific tests:
- `npm run audiobook:release-gate:expect-blocked`
- `npm run audiobook:release-gate:expect-ready || true`
- `npm run launch:audio-audit`
- `PYTHONPATH=. pytest backend/tests/test_audiobook_regeneration_workflow.py backend/tests/test_audiobook_release_gate.py`

PR #44 specific tests:
- `npm run audiobook:model-bakeoff:plan`
- `npm run audiobook:model-bakeoff:dry-run`
- `npm run audiobook:release-gate`
- `PYTHONPATH=. pytest backend/tests/test_bengali_audiobook_model_bakeoff.py backend/tests/test_bengali_audiobook_chunker.py backend/tests/test_audiobook_model_adapters.py`

PR #45 specific tests:
- `npm run audiobook:english-model-bakeoff:plan`
- `npm run audiobook:english-model-bakeoff:dry-run`
- `npm run audiobook:release-gate`
- `PYTHONPATH=. pytest backend/tests/test_english_audiobook_model_bakeoff.py backend/tests/test_english_audiobook_chunker.py backend/tests/test_english_audiobook_model_adapters.py`

PR #46 specific tests:
- `npm run social:brand-kit`
- `npm run social:links:validate || true`
- `PYTHONPATH=. pytest backend/tests/test_social_brand_kit.py backend/tests/test_backend_catalog_truth.py`
- `npm --prefix frontend run build`

## Risk Scores

- PR #42: **6.5/10**. Touches package.json, regression static UX tests, go/no-go docs, and release-canary latest summaries; video score remains human-review gated.
- PR #43: **7.0/10**. Introduces shared audiobook release-gate scripts/tests and governance docs; merge order should precede model bakeoff PRs to establish the common gate.
- PR #44: **8.2/10**. Draft PR with broad audiobook adapter/test/license evidence changes; conflicts with PR #43 and #45 in shared release-gate and model evidence files.
- PR #45: **8.1/10**. Draft PR with Dracula internal audio planning files and shared audiobook docs/tests; conflicts with PR #43 and #44 in release-gate, policies, and license evidence.
- PR #46: **5.2/10**. Large asset/report addition but limited runtime surface; only package scripts, .gitignore, and go/no-go docs overlap with other PRs.

## Blocked Actions

Across the whole merge stack:

- Do not publish new books.
- Do not deploy as part of this audit.
- Do not enable audiobook or expose public audio URLs.
- Do not post to social platforms or call social APIs.
- Do not run live Razorpay or provider APIs.
- Do not mutate production data.

PR #42 blocked actions:
- No ads until owner video review
- No social posting
- No production publication

PR #43 blocked actions:
- Public audio release remains blocked
- No provider calls
- No audio URLs
- No publication mutation

PR #44 blocked actions:
- Draft until approved Bengali source, internal samples, human review, and license review exist
- No public audio
- No public audio URLs

PR #45 blocked actions:
- Draft until owner-approved local generation, license review, and human listening review exist
- Dracula audio remains disabled
- No public audio URLs

PR #46 blocked actions:
- No social posting
- No fake social links
- No ads until owner-uploaded profile screenshots and valid URLs exist

## Merge Stack Notes

- All five PRs are individually clean against current `origin/main` by local `git merge-tree` and GitHub mergeability metadata.
- Pairwise conflicts are real and should be resolved by rebasing after each prior merge, not by batch-merging the whole stack.
- PR #43 should be treated as the audiobook governance base. PR #44 and #45 both add model-specific extensions and conflict with #43 and each other.
- PR #42 and #46 both update branding/go-no-go docs and `package.json`; merge them sequentially and rerun static UX/social validations after each rebase.
- PR #44 and #45 are Draft and should stay Draft until their owner/human/license review gates are satisfied.

## Validation Performed For This Audit

- `git fetch origin main codex/premium-site-tour-video-package codex/audiobook-regeneration-governance codex/bengali-audiobook-model-bakeoff codex/english-audiobook-model-bakeoff codex/premium-social-brand-kit`
- `git rev-parse origin/<branch>` for all five PR branches
- `git log --oneline -5 origin/<branch>` for all five PR branches
- GitHub PR metadata fetch for #42-#46
- GitHub changed-file list fetch for #42-#46
- `git merge-tree --write-tree --messages origin/main origin/<branch>` for all five PR branches
- Pairwise `git merge-tree --write-tree --messages origin/<branch-a> origin/<branch-b>` for all PR combinations
- Existing branch-visible report/evidence file enumeration
