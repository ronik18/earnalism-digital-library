# Final PR 42/43/46 Merge Report

Generated: 2026-06-21

## Executive Summary

PR #42 was safely rebased, revalidated, merged into `main`, and pushed.
PR #43 was attempted next in the required order, but rebasing it onto the updated `main` produced a conflict in `regression/modules/14-ux-conversion-static.test.js`.
Because the task explicitly defines conflicts touching regression guardrails as a hard stop, the rebase was aborted and PR #43 was not merged.
PR #46 was not attempted because PR #43 blocked the ordered merge stack.

No deployment, public publication, audiobook enablement, social posting, paid ad activation, live Razorpay change, or production data mutation was performed.
PR #44 and PR #45 were untouched.

## PRs Attempted

| PR | Branch | Attempted | Result |
| --- | --- | --- | --- |
| #42 | `codex/premium-site-tour-video-package` | Yes | Merged |
| #43 | `codex/audiobook-regeneration-governance` | Yes | Blocked by guardrail conflict |
| #46 | `codex/premium-social-brand-kit` | No | Skipped because #43 blocked the required order |

## PRs Merged

| PR | Branch | Pre-merge branch HEAD | Merge commit |
| --- | --- | --- | --- |
| #42 | `codex/premium-site-tour-video-package` | `97be5b02` | `324fa770470654111baddab43313f27b89691994` |

## PRs Skipped Or Blocked

| PR | Branch | Branch HEAD at time of review | Status | Reason |
| --- | --- | --- | --- | --- |
| #43 | `codex/audiobook-regeneration-governance` | `224d98ce` | Not merged | Rebase conflict in regression guardrail file |
| #46 | `codex/premium-social-brand-kit` | `8593a584` | Not attempted | Required merge order stopped at #43 |

## Main Commit State

- Main before #42 merge: `0067ed53b1a8f77bd7f05f8b619b3905e5686ac7`
- Main after #42 merge: `324fa770470654111baddab43313f27b89691994`
- Current final main HEAD for this report: `324fa770470654111baddab43313f27b89691994`

## Preflight Guardrails

Confirmed present on `main` before merging:

- `MERGE_STACK_READINESS_REPORT.md`
- `PRODUCT_TRUTH_LEDGER.md`
- `LEGACY_SURFACE_TOMBSTONE_REPORT.md`
- Regression guardrails in `regression/modules/13-public-content-governance.test.js`
- Regression guardrails in `regression/modules/14-ux-conversion-static.test.js`

The product truth baseline remained:

- Dracula is the only approved core public reading release.
- Audiobooks are not public/live.
- Kshudhita Pashan remains pipeline-only.
- No public audio URLs.
- No `Listen Now` CTA.
- No generated audiobook publication.
- No social posting.
- No paid ads.
- No live Razorpay changes.
- No production data mutation.
- No deployment.

## Conflict Details

PR #43 was rebased after #42 was merged into `main`.
The rebase failed on the first PR #43 commit:

```text
CONFLICT (content): Merge conflict in regression/modules/14-ux-conversion-static.test.js
Could not apply f1e2f541... Add approved audiobook regeneration workflow
```

This file is an explicit regression guardrail file.
Per the hard-stop instructions, the conflict was not manually resolved and the rebase was aborted.

## Conflict Resolutions

No manual conflict resolution was performed.
The #43 rebase was aborted to preserve current `main` guardrails and require human review.

## Files Changed Per PR

### PR #42

Merged files included:

- `BRANDING_ADVERTISEMENT_GO_NO_GO.md`
- `BRAND_SITE_TOUR_HUMAN_REVIEW_FORM.md`
- `BRAND_SITE_TOUR_VIDEO_INDEX.json`
- `BRAND_SITE_TOUR_VIDEO_INDEX.md`
- `BRAND_SITE_TOUR_VIDEO_SCORECARD.json`
- `BRAND_SITE_TOUR_VIDEO_SCORECARD.md`
- `EARNALISM_SITE_TOUR_VOICEOVER_SCRIPT.md`
- `FINAL_GO_NO_GO_DECISION.md`
- `SITE_TOUR_FEATURE_HIGHLIGHT_REPORT.md`
- `output/release-canary/latest/summary.json`
- `output/release-canary/latest/summary.md`
- `package.json`
- `regression/modules/14-ux-conversion-static.test.js`
- `scripts/create_premium_site_tour.py`

### PR #43

Not merged. The attempted rebase touched a regression guardrail conflict.

### PR #46

Not attempted because the ordered merge stack stopped at PR #43.

## Validation Results

### PR #42 Pre-merge Validation

| Command | Result |
| --- | --- |
| `python3 scripts/check-hidden-unicode.py $(cat /tmp/pr42-files.txt)` | PASS for 14 files |
| `npm run controlled-publication:precheck` | PASS |
| `npm run launch:seo-audit` | PASS |
| `npm run launch:social-preview-audit` | PASS |
| `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js` | PASS, 47 tests |
| `npm --prefix frontend run build` | PASS |
| `npm run brand:site-tour` | PASS; recommendation remained `HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW` |

### Main Post-#42 Validation

| Command | Result |
| --- | --- |
| `npm run controlled-publication:precheck` | PASS |
| `npm run launch:seo-audit` | PASS |
| `npm run launch:social-preview-audit` | PASS |
| `npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js` | PASS, 47 tests |
| `npm --prefix frontend run build` | PASS |

### #43 Validation

Not run after the updated rebase because the branch hit a hard-stop conflict before validation.

### #46 Validation

Not run in this merge attempt because the ordered stack stopped at #43.

## Public-surface Changes

PR #42 adds a premium site-tour evidence package and related local reports/scripts.
It does not publish ads, enable social campaigns, publish books, enable audio, or mutate production data.
The go/no-go posture remains conservative:

- `HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW`
- Owner human review is still required before ad use.

## Legal / Compliance Impact

No new public book, audiobook, payment behavior, social post, or ad campaign was released.
PR #42 adds review and evidence artifacts only.
Current legal/compliance guardrails remain intact:

- Dracula-only controlled public reading truth.
- Kshudhita Pashan pipeline-only status.
- Audiobooks non-public.
- Legacy surface tombstones preserved.

## Audiobook Impact

No public audiobook was enabled.
No audio URL was exposed.
No TTS, STT, FFmpeg, paid provider, or cloud audio API call was performed.
PR #43 remains unmerged and requires human review because it conflicts with regression guardrails.

## Social / Ads Impact

No social post was sent.
No paid ad was started.
PR #42 keeps ads on hold pending human video review.
PR #46 was not attempted in this ordered merge run.

## Accessibility Impact

No new accessibility claim was made.
The product must still not claim WCAG compliance, blind-user testing, or a fully accessible audiobook platform without current-branch evidence and owner approval.

## Remaining Unproven Claims

- Product-wide 9.7+/10 or 10/10 launch readiness remains unproven.
- Paid ads readiness remains unproven pending human review.
- Social profile readiness remains unproven because PR #46 was not merged.
- Public audiobook readiness remains unproven and blocked.
- Kshudhita Pashan public reading/audio readiness remains unproven and blocked.

## Rollback Instructions

If PR #42 needs to be rolled back:

```bash
git switch main
git pull --rebase origin main
git revert -m 1 324fa770470654111baddab43313f27b89691994
npm run controlled-publication:precheck
npm run regression -- modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js
npm --prefix frontend run build
git push origin main
```

Do not revert unrelated guardrail commits.
Do not use destructive reset commands on shared branches.

## Final Safe-to-continue Decision

**CONDITIONAL**

It is safe to continue normal development from `main` with PR #42 merged.
It is not safe to continue merging #43 or #46 automatically in this ordered stack until a human reviews the #43 conflict in `regression/modules/14-ux-conversion-static.test.js`.
