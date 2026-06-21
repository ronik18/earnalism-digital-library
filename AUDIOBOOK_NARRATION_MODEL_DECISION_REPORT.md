# Audiobook Narration Model Decision Report

Status: `PUBLIC_AUDIO_RELEASE_BLOCKED`

This report defines the current decision framework for Bengali and English audiobook model evaluation. It does not merge Draft PR #44 or Draft PR #45, does not approve any model for public release, and does not expose audio publicly.

## Reviewed Candidate Categories

| Category | Current Use | Public Release Status |
| --- | --- | --- |
| Bengali open-source/local TTS models | Research and internal planning only. | `BLOCKED` |
| English open-source/local TTS models | Research and internal planning only. | `BLOCKED` |
| Provider TTS hooks | Metadata-only governance and planning. | `BLOCKED` |
| Manual human narration | Allowed only after source, contract, rights, QA, and owner approval. | `BLOCKED` until evidenced |
| AI-assisted enhancement | Allowed only if disclosed truthfully and licensed. | `BLOCKED` until evidenced |

## Accepted Model Criteria

A model/provider can become a production candidate only when all of these are true:

- Commercial-use license is reviewed and stored.
- Derivative audiobook rights for the exact source/edition/region are approved.
- Voice/narrator rights are approved.
- No real-person voice cloning risk remains unresolved.
- Bengali or English human-review scorecard is complete.
- Final human-review score is at least `9.5/10`.
- Text fidelity passes.
- Accessibility listening review passes.
- Owner approval and rollback plan pass.
- Public audio URLs, Listen Now CTAs, and AudioObject metadata remain absent until explicit publication approval.

## Rejected Model Conditions

Reject or keep in Draft if any of these apply:

- Source text evidence is missing.
- Model license is missing, unclear, noncommercial, or incompatible with derivative audiobook use.
- Output omits text, adds text, repeats text, hallucinates passages, or changes chapter order.
- Bengali literary tone or English gothic tone sounds flat, comic, robotic, over-dramatic, or tiring.
- Samples are generated only from placeholder text.
- Human listening score is below `9.5/10`.
- Owner approval is missing.
- Public release would require exposing audio before the release gate passes.

## Minimum Release Threshold

Minimum threshold: `9.5/10` final human-review score plus all hard gates marked `PASS`.

The threshold is intentionally high because audiobook output affects rights, accessibility, literary trust, and listener fatigue. A model can be useful for internal research at lower scores, but it cannot become a public Earnalism audiobook candidate.

## Hard Fail Conditions

- `PUBLIC_AUDIO_RELEASE_BLOCKED` is bypassed.
- Draft PR #44 or Draft PR #45 evidence is treated as public approval.
- Public audio is enabled while human-review scorecards are HOLD.
- Public audio appears under `frontend/public` or `frontend/build`.
- Any public copy claims human narration when the narration is AI-generated or AI-assisted.
- Any public copy claims "no AI touch" when AI generation or enhancement was used.
- Any public copy claims blind-user testing, WCAG compliance, or fully accessible audiobook platform status without evidence.

## Bengali Decision Status

Decision: `HOLD`

PR #44 remains Draft because:

- Approved full Bengali source text evidence is not complete on main.
- Bengali human-review scorecard is blank and HOLD.
- Model/license commercial-use evidence is not approved.
- Derivative audiobook rights are not approved.
- Bengali human listening QA at or above `9.5/10` is not present.
- Owner approval and rollback approval are missing.
- Public Kshudhita Pashan audio remains blocked.

## English Decision Status

Decision: `HOLD`

PR #45 remains Draft because:

- Generated internal samples are not owner-approved as production candidates.
- English human-review scorecard is blank and HOLD.
- Model/license commercial-use evidence is not approved.
- Derivative audiobook rights are not approved.
- English human listening QA at or above `9.5/10` is not present.
- Owner approval and rollback approval are missing.
- Dracula audio remains disabled publicly.

## Evidence Required Before PR #44 Can Become Merge-Ready

- Approved full Kshudhita Pashan source text evidence.
- Source URL, source name, source license, source hash, content hash, and provenance hash.
- Model/provider license review.
- Derivative audiobook rights approval.
- Bengali samples generated only from approved source text.
- Completed Bengali human-review scorecard with final score at or above `9.5/10`.
- Text fidelity pass.
- Accessibility listening pass.
- Owner approval.
- Rollback plan.
- Confirmation that no public audio URL exists.

## Evidence Required Before PR #45 Can Become Merge-Ready

- Owner-approved internal local generation evidence.
- Model/provider license review.
- Derivative audiobook rights approval.
- English samples generated only from approved source text.
- Completed English human-review scorecard with final score at or above `9.5/10`.
- Text fidelity pass.
- Accessibility listening pass.
- Owner approval.
- Rollback plan.
- Confirmation that Dracula audio remains disabled until explicit approval.

## Public Release Status

Public release status: `PUBLIC_AUDIO_RELEASE_BLOCKED`

No audiobook may become public from PR #44 or PR #45 until `npm run audiobook:release-gate` remains blocked for public release and separately reaches internal review readiness with complete human-review evidence, rights evidence, accessibility evidence, owner approval, and rollback evidence.
