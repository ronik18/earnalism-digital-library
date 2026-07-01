# Signed User Journey Regression Report

Status: `TWO_TIER_JOURNEY_QA_READY`

## Tier 1: CI-Safe Smoke Journey

- Command: `npm run ux:journey-smoke`
- CI integration: `npm run regression:ci` runs this smoke before the standard regression bundle.
- Runs headless by default.
- Does not ask for owner credentials.
- Uses `EARNALISM_JOURNEY_TEST_STORAGE_STATE` if a safe seeded test-user Playwright storage state is available.
- Without a seeded state, account and admin routes are treated as auth-boundary checks.
- Does not execute live Razorpay payment.
- Produces JSON and lightweight screenshots only.
- Output path: `output/ux-journey-regression/<timestamp>/`

Covered automatically:

- homepage load
- forced first-time site tour
- Dracula CTA route outcomes
- `/library`
- `/book/dracula`
- `/reader/dracula`
- `/pricing` without checkout execution
- `/account` wallet/auth boundary
- `/journal`
- `/contact` and official social link scan
- `/admin` and `/admin/launch-monitor` access boundary
- public audio, Listen Now, AudioObject, Kshudhita public CTA, broad catalog, ownership, and accessibility overclaim scans

## Tier 2: Owner-Operated Full Video Journey

- Command: `npm run ux:journey-record:prod`
- Headed browser mode.
- Owner signs in manually.
- Recording starts only after owner confirmation.
- Video and trace artifacts remain gitignored.
- Recommended before/after major releases, launch-monitor changes, payment/wallet UX changes, reader changes, and post-deploy verification. It is not required before every tiny docs-only production deploy unless a high-risk user-flow surface changed.

## Latest Smoke Result

- latest_smoke_status: PASS
- latest_smoke_output: output/ux-journey-regression/2026-07-01T10-41-34-897Z
- latest_test_auth_state_status: NOT_CONFIGURED
- latest_failure_count: 0

## Latest Manual Recording Result

- latest_manual_recording_status: OWNER_RUN_REQUIRED
- latest_manual_recording_output: not committed

## Release Acceptance Criteria

- CI-safe smoke must pass for user-flow PRs.
- Manual full-video journey is required for major releases and recommended for post-deploy verification.
- Public audio must remain `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Audiobook production must remain `PRODUCTION_BLOCKED`.
- No live Razorpay payment may be executed by either recorder.
- No secrets, passwords, cookies, payment IDs, customer data, or card/UPI/bank data may be committed.
