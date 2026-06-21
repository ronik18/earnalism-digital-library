# PR 42-46 Final Handling Report

Generated: 2026-06-22

## Executive Summary

PR #42 was already merged and was verified only. PR #43 was rebased on current main, deduped against the stronger audiobook accessibility release gate, validated, force-pushed to its PR branch, and merged to main. PR #46 was rebased after #43, validated as a manual/local-only social brand kit, force-pushed to its PR branch, and merged to main. PR #44 and PR #45 remain open Draft PRs and were not merged.

Safe-to-continue decision: `YES`

This decision depends on the evidence below: public audio remains blocked, no audio-like files exist under `frontend/public` or `frontend/build`, Dracula remains the only live approved core reading title, Kshudhita Pashan remains pipeline-only, and all required validation commands passed. The only expected warning state was `npm run social:links:validate`, which returned `OPERATOR_REQUIRED` because real social profile URLs are intentionally not configured yet.

## PR #42 Verification

- PR: #42 `Create premium Earnalism site-tour video package`
- Branch: `codex/premium-site-tour-video-package`
- PR head: `97be5b020169636bd34c36aa0beef45994e9b54e`
- GitHub state: `closed`
- GitHub merged: `true`
- Local handling: verified only; not reopened.

Verification evidence:

- Current `main` contains the site-tour package command `brand:site-tour`.
- Current `main` contains site-tour/brand artifacts including `BRAND_SITE_TOUR_VIDEO_SCORECARD.json`, `BRAND_SITE_TOUR_VIDEO_INDEX.md`, and `BRANDING_ADVERTISEMENT_GO_NO_GO.md`.

Commands run:

| Command | Result |
| --- | --- |
| `npm run brand:site-tour || true` | Passed. Output regenerated local brand-site-tour package with recommendation `HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW`. Generated timestamp-only report churn was restored before branch work continued. |
| `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js` | Passed. 2 suites passed, 60 tests passed. |
| `npm --prefix frontend run build` | Passed. Frontend compiled successfully and static SEO snapshots were generated. |

## PR #43 Merge Result

- PR: #43 `Add separately approved regenerated audiobook narration workflow`
- Branch: `codex/audiobook-regeneration-governance`
- Original PR head before handling: `224d98ce9ce84d647243613412b0323d99b1d303`
- Final PR branch head: `2847cb09cf02ac3a398fba1d71d121d826eeebf0`
- Merge commit on main: `e58fe1ad6e6bf1349ce0e38cd63328a41fe1e0f3`
- GitHub state after handling: `closed`
- GitHub merged after handling: `true`

Conflict handling:

- Conflict in `package.json`: preserved current main's stronger canonical release gate:
  - `audiobook:release-gate = python3 scripts/audiobook_accessibility_release_gate.py`
- Added #43 workflow-specific scripts under `audiobook:regen:*` without replacing the canonical public audio gate.
- Conflict in `regression/modules/14-ux-conversion-static.test.js`: preserved current main regression coverage and added #43 regeneration workflow assertions under separate variables.
- Report conflicts were not present for #43 after the final rebase, but the branch evidence was refreshed.

Dedupe and safety hardening:

- Kept the existing stronger current-main blockers from:
  - `scripts/audiobook_accessibility_release_gate.py`
  - `scripts/controlled_publication_precheck.py`
  - `AUDIOBOOK_ASSET_QUARANTINE_REPORT.md`
  - `AUDIOBOOK_ACCESSIBILITY_GATE_REPORT.md`
  - `FIRST_BATCH_RIGHTS_EVIDENCE_SCORECARD.md`
- Removed URL-shaped test sentinels from #43's regeneration release gate and tests, replacing `https://cdn.example.com/kshudhita.mp3` with `INTERNAL_AUDIO_SENTINEL`.
- Confirmed #43 keeps:
  - `PUBLIC_AUDIO_RELEASE_BLOCKED`
  - `FULL_AUDIOBOOK_BLOCKED`
  - `OWNER_APPROVAL_REQUIRED`
- Confirmed no public audio URL, Listen Now CTA, public audio enablement, or Kshudhita publication was introduced.

Files changed by #43:

- `AUDIOBOOK_DISCLOSURE_AND_CLAIMS_POLICY.md`
- `AUDIOBOOK_PROVIDER_ADAPTER_POLICY.md`
- `AUDIOBOOK_REGENERATION_GOVERNANCE_REPORT.md`
- `AUDIOBOOK_RELEASE_GATE_REPORT.md`
- `AUDIOBOOK_VOICE_PROFILE_POLICY.md`
- `FINAL_GO_NO_GO_DECISION.md`
- `KSHUDHITA_PASHAN_REGENERATED_AUDIO_APPROVAL_FORM.md`
- `KSHUDHITA_PASHAN_REGENERATED_AUDIO_QA_CHECKLIST.md`
- `KSHUDHITA_PASHAN_REGENERATED_NARRATION_STYLE_GUIDE.md`
- `backend/audiobook_generation/__init__.py`
- `backend/audiobook_generation/provider_adapter.py`
- `backend/tests/test_audiobook_regeneration_workflow.py`
- `backend/tests/test_audiobook_release_gate.py`
- `data/audiobook_governance/kshudhita-pashan.regeneration_request.json`
- `data/audiobook_governance/schema.json`
- `data/audiobook_regeneration/kshudhita-pashan/segment_manifest.schema.json`
- `data/audiobook_voice_profiles/bengali-gothic-literary-female.sample.json`
- `package.json`
- `regression/modules/14-ux-conversion-static.test.js`
- `scripts/audiobook_regeneration_workflow.py`
- `scripts/audiobook_release_gate.py`

Validation run for #43:

| Command | Result |
| --- | --- |
| `python3 scripts/check-hidden-unicode.py $(git diff --name-only origin/main...HEAD)` | Passed for 21 files. |
| `git diff --check` | Passed. |
| `python3 -m py_compile scripts/audiobook_regeneration_workflow.py scripts/audiobook_release_gate.py backend/audiobook_generation/provider_adapter.py backend/tests/test_audiobook_regeneration_workflow.py backend/tests/test_audiobook_release_gate.py` | Passed. |
| `PYTHONPATH=. pytest backend/tests/test_audiobook_regeneration_workflow.py backend/tests/test_audiobook_release_gate.py` | Passed. 26 tests passed. |
| `npm run controlled-publication:precheck` | Passed. Controlled publication precheck PASS. |
| `npm run catalog:audit` | Passed. 46 items audited. |
| `npm run launch:audio-audit` | Passed. Launch readiness audio audit PASS. |
| `npm run audiobook:release-gate` | Passed. `PUBLIC_AUDIO_RELEASE_BLOCKED`; command status `PASS_EXPECTED_BLOCKED`; 23 blockers. |
| `npm run launch:seo-audit` | Passed. SEO audit PASS. |
| `npm run launch:social-preview-audit` | Passed. Social preview audit PASS. |
| `npm run regression -- modules/11-seo.test.js modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js` | Passed. 3 suites passed, 69 tests passed. |
| `npm --prefix frontend run build` | Passed. Frontend compiled successfully and static SEO snapshots were generated. |
| `find frontend/public frontend/build ... audio-like files` | Passed. No audio-like files were printed. |

## PR #46 Merge Result

- PR: #46 `Create premium Earnalism social media brand kit`
- Branch: `codex/premium-social-brand-kit`
- Original PR head before handling: `8593a5846e1f393fa00bbfc5bc5279778977e338`
- Final PR branch head: `c3ae39c62944e459029110ca85d02d3fc1631ca9`
- Merge commit on main: `fd8eb55637159b8bf95a35c09f2529c0199d7358`
- GitHub state after handling: `closed`
- GitHub merged after handling: `true`

Conflict handling:

- Conflicts in `BRANDING_ADVERTISEMENT_GO_NO_GO.md` and `FINAL_GO_NO_GO_DECISION.md` were resolved by combining the useful social brand kit evidence with the stronger current hold decisions.
- The final reports preserve:
  - `HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW`
  - `KEEP_DRACULA_LIVE`
  - no public audio
  - no social posting
  - no paid ads
  - no production data mutation
  - Kshudhita Pashan pipeline-only
- `package.json` auto-merged and preserved:
  - `release:post-production-canary`
  - `ux:real-user-video-audit`
  - `release:ux-go-no-go`
  - `launch:social-preview-audit`
  - `launch:social-preview-audit:prod`
  - canonical `audiobook:release-gate`
  - new `social:brand-kit`
  - new `social:links:validate`

Manual/local-only social kit audit:

- No `social:post` or `social:publish` script was added.
- No platform API call, access token, client secret, or provider credential was added.
- No paid ads, social upload, social post, tracking pixel, or automated profile creation was added.
- Real profile URLs remain operator-required; footer/social links remain configured only through validated http/https environment URLs.
- The social kit score remains capped at `8.5/10` until owner upload verification and real social links exist.

Files changed by #46:

- `.gitignore`
- `BRANDING_ADVERTISEMENT_GO_NO_GO.md`
- `FINAL_GO_NO_GO_DECISION.md`
- `SOCIAL_ASSET_INDEX.md`
- `SOCIAL_LINK_COLLECTION_RUNBOOK.md`
- `SOCIAL_PINNED_POSTS.md`
- `SOCIAL_PROFILE_COPYBOOK.md`
- `SOCIAL_PROFILE_OWNER_UPLOAD_CHECKLIST.md`
- `SOCIAL_PROFILE_REVAMP_REPORT.md`
- `SOCIAL_PROFILE_REVAMP_SCORECARD.json`
- `SOCIAL_PROFILE_REVAMP_SCORECARD.md`
- `SOCIAL_VISUAL_ASSET_GUIDE.md`
- `assets/social_brand/source/*.svg`
- `backend/tests/test_social_brand_kit.py`
- `data/social_brand/*.json`
- `output/social-brand-kit/latest/*`
- `package.json`
- `scripts/generate_social_brand_assets.py`
- `scripts/validate_social_links.py`

Validation run for #46:

| Command | Result |
| --- | --- |
| `python3 scripts/check-hidden-unicode.py $(git diff --name-only origin/main...HEAD)` | Passed for 68 files. |
| `git diff --check` | Passed. |
| `python3 -m py_compile scripts/generate_social_brand_assets.py scripts/validate_social_links.py backend/tests/test_social_brand_kit.py` | Passed. |
| `PYTHONPATH=. pytest backend/tests/test_social_brand_kit.py` | Passed. 12 tests passed. |
| `npm run social:brand-kit` | Passed. Generated 22 social brand asset records. Scorecard: `8.5/10`, `NOT_READY_FOR_PAID_SOCIAL_ADS`. |
| `npm run social:links:validate || true` | Expected warning state. Returned `OPERATOR_REQUIRED` because 0 real profile URLs are configured; 7 missing, 0 invalid. |
| `npm run controlled-publication:precheck` | Passed. Controlled publication precheck PASS. |
| `npm run launch:seo-audit` | Passed. SEO audit PASS. |
| `npm run launch:social-preview-audit` | Passed. Social preview audit PASS. |
| `npm run regression -- modules/11-seo.test.js modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js` | Passed. 3 suites passed, 69 tests passed. |
| `npm run regression:ci` | Passed. 13 suites passed, 2 suites skipped, 98 tests passed, 4 tests skipped. |
| `npm --prefix frontend run build` | Passed. Frontend compiled successfully and static SEO snapshots were generated. |

## PR #44 Draft Hold Decision

- PR: #44 `Benchmark open-source Bengali audiobook narration models`
- Branch: `codex/bengali-audiobook-model-bakeoff`
- Head: `a2d34c757d7c98d54452619d9c619a8c5680e039`
- GitHub state: `open`
- GitHub draft: `true`
- Merge decision: `DO_NOT_MERGE`

Reason:

PR #44 remains Draft because approved full Kshudhita Pashan source text, source/license evidence, generated internal samples from approved source, Bengali human listening QA, accessibility validation, derivative/model-license review, and owner approval are incomplete. It must not be used for public launch claims, public audio URLs, Listen Now CTAs, or score upgrades.

## PR #45 Draft Hold Decision

- PR: #45 `Benchmark open-source English audiobook narration models`
- Branch: `codex/english-audiobook-model-bakeoff`
- Head: `70f4b0e1883d999e091cb0efcd2eb6ce0eb64d75`
- GitHub state: `open`
- GitHub draft: `true`
- Merge decision: `DO_NOT_MERGE`

Reason:

PR #45 remains Draft because owner-approved internal local generation, generated samples, manual license review, English human listening QA, accessibility validation, and owner approval are incomplete. Dracula audio remains disabled publicly, and the branch must not expose public audio URLs or claim production candidate status.

## Public Audio Leakage Scan

Command:

```bash
find frontend/public frontend/build -type f \( -iname '*.mp3' -o -iname '*.wav' -o -iname '*.m4a' -o -iname '*.ogg' -o -iname '*.aac' -o -path '*/audio/*_timestamps.json' -o -path '*/audio/*_highlight.vtt' -o -path '*/audio/*_chapters.json' -o -path '*/audio/*_meta.json' \) -print 2>/dev/null | sort
```

Result: no files printed.

Conclusion: no audio-like files were detected under `frontend/public` or `frontend/build` after #43 and #46 were merged.

## Public Claims Audit

Confirmed after handling:

- Dracula remains the only live approved core reading title.
- Kshudhita Pashan remains pipeline-only.
- Audiobooks remain non-public.
- `PUBLIC_AUDIO_RELEASE_BLOCKED` remains the active release-gate state.
- No Listen Now CTA was added.
- No public audio URL was added.
- No social posting or paid ad automation was added.
- Social profiles are not claimed live; the social kit remains owner-upload/operator-required.

## Legal and Compliance Impact

Positive impact:

- #43 adds governance artifacts and tests that keep regenerated audiobook work separate from public release.
- #46 adds social brand copy/asset governance that avoids false claims, fake live profiles, paid ad launch claims, and unsupported catalog/audio/accessibility claims.

Residual legal/compliance blockers:

- Kshudhita Pashan audio remains blocked pending source/license and human review.
- Draft PR #44 and #45 evidence must not be treated as public truth.
- Social profile materials require owner review before upload or paid ads.

## Accessibility Impact

Positive impact:

- #43 keeps audiobook accessibility release blocked until owner approval, QA, rights, source text, and public release gates are satisfied.
- #46 produces SVG assets with `role="img"` and `aria-label` metadata for manual review.

Remaining accessibility blockers:

- No public audiobook accessibility claim is supported yet.
- No blind-user testing, WCAG compliance, or fully accessible audiobook platform claim is allowed from these PRs.
- Social assets still require manual owner review for contrast, readability, and platform rendering before public use.

## Rollback Instructions

To revert #46 only:

```bash
git revert -m 1 fd8eb55637159b8bf95a35c09f2529c0199d7358
git push origin main
```

To revert #43 only:

```bash
git revert -m 1 e58fe1ad6e6bf1349ce0e38cd63328a41fe1e0f3
git push origin main
```

If both need to be reverted, revert #46 first, then #43, because #46 was merged after #43.

## Final State

- #42: verified merged.
- #43: rebased, validated, merged.
- #46: rebased, validated, merged.
- #44: still Draft, not merged.
- #45: still Draft, not merged.
- Main branch after final merge: `fd8eb55637159b8bf95a35c09f2529c0199d7358`.
- Public audio leakage scan: passed.
- Safe-to-continue decision: `YES`.
