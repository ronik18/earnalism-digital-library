# Audiobook Compliance Scorecard

Status: `PUBLIC_AUDIO_RELEASE_BLOCKED`

Recommendation: `HOLD_PUBLIC_AUDIO`

This scorecard summarizes the current audiobook legal, rights, accessibility, support, and public-claims state. It is internal evidence tracking only and does not approve public audio.

## Current Score

Overall audiobook compliance readiness: `0.0/10`

The score remains low by design because public audiobook release is blocked until complete rights, licensing, accessibility, support, owner/legal, and rollback evidence exists.

## Score Areas

| Area | Score | Reason |
| --- | ---: | --- |
| Source and derivative rights | 0.0/10 | Derivative audiobook rights are not approved. |
| Model and voice rights | 0.0/10 | Model license, commercial-use evidence, narrator/voice rights, and cloning review are missing. |
| Storage and public serving | 0.0/10 | Storage/CDN/public-serving rights are not approved. |
| Narration QA | 0.0/10 | Bengali and English human listening scorecards are templates and not completed. |
| Accessibility QA | 0.0/10 | Transcript, sync, player, keyboard, screen-reader, and mobile assistive-tech evidence is incomplete. |
| Public claims safety | 8.5/10 | Public surface is currently blocked from audio claims, but claims review is still missing. |
| Support/refund readiness | 0.0/10 | Paid audiobook support, refund, and takedown readiness are not approved. |
| Rollback readiness | 0.0/10 | Rollback approval is missing. |

## Required Status Before GO

Every row must be `PASS` before public release:

| Requirement | Current status |
| --- | --- |
| Dracula audio remains disabled | PASS |
| Kshudhita Pashan remains pipeline-only | PASS |
| No public audio files under `frontend/public` or `frontend/build` | PASS |
| No AudioObject or public audiobook metadata | PASS |
| No Listen Now CTA | PASS |
| Approved audiobook source text | HOLD |
| Derivative audiobook rights | HOLD |
| Model commercial-use rights | HOLD |
| Voice/narrator rights | HOLD |
| Real-person voice cloning risk resolved | HOLD |
| Storage/CDN/public-serving rights | HOLD |
| Attribution reviewed and satisfied | HOLD |
| Public claims evidence reviewed | HOLD |
| Bengali human listening review >= 9.5 | HOLD |
| English human listening review >= 9.5 | HOLD |
| Accessibility listening review | HOLD |
| Refund/support readiness | HOLD |
| Owner/legal approval | HOLD |
| Rollback approval | HOLD |
| PR #44/#45 treated only as Draft evidence | PASS |

## Compliance Gate Status

Expected command status today:

```bash
npm run audiobook:release-gate
```

Expected result:

- `PUBLIC_AUDIO_RELEASE_BLOCKED`
- no public audio publish allowed
- no audio files under public/build directories
- blockers remain for rights, licensing, QA, accessibility, support/refund, owner/legal approval, and rollback

## Public Claims Decision

Current approved public claims:

- Dracula is the only live approved core reading release.
- Dracula audio is not available yet.
- No public audiobook is live today.

Current blocked public claims:

- audiobooks are live
- Listen Now
- WCAG compliant
- blind-user tested
- screen-reader certified
- fully accessible audiobook platform
- human narrated without human-recording evidence
- no AI touch if AI generation or enhancement is used

## Safe To Merge

`CONDITIONAL`

Safe to merge only as a governance hardening change if validation passes and public audio remains blocked. Not safe for public audiobook launch.

