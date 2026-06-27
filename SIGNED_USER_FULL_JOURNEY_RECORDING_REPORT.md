# Signed User Full Journey Recording Report

Status: `OWNER_RUN_READY`

This pass adds an owner-operated Playwright recorder for the live Earnalism signed-user journey. It is designed to capture UX evidence without recording login entry, payment secrets, customer data, or public-audio surfaces.

## Commands

- CI-safe smoke: `npm run ux:journey-smoke`
- Production: `npm run ux:journey-record:prod`
- Local: `npm run ux:journey-record:local`
- Custom base URL: `EARNALISM_BASE_URL=https://theearnalism.com npm run ux:journey-record`
- Latest regression summary: `npm run ux:journey-regression-report`

## Two-Tier Regression Integration

Tier 1 is a CI-safe smoke journey. It runs headless without manual sign-in, never uses owner credentials, never executes live Razorpay payment, and produces lightweight JSON/screenshots under `output/ux-journey-regression/<timestamp>/`.

Tier 2 is the owner-operated full video journey. It uses a headed browser, pauses for owner sign-in, and records video only after owner confirmation.

## Manual Sign-In Boundary

The recorder opens a headed browser at the configured base URL and pauses with:

`Please sign in manually in the opened browser. Press Enter here after sign-in is complete. Recording starts only after this confirmation.`

The owner signs in directly in the browser. The script does not ask for a password, does not print credentials, and does not write cookies, tokens, or storage state to disk. After Enter, it starts a new video-enabled browser context using the signed-in state in memory only.

## Journey Coverage

- `/` signed-in homepage and hero
- `/?tour=1` forced first-time site tour
- Homepage CTA outcomes for Read Chapter 1 Free, Start Dracula, Get 7-Day Reading Pass, and optional library exploration
- `/library` including Dracula release and pipeline-only CTAs
- `/book/dracula`
- `/reader/dracula`
- `/pricing` without live payment execution
- `/account`
- `/journal`
- `/about`
- `/contact` and social links
- `/admin` and `/admin/launch-monitor` access-boundary behavior when included
- Logout attempt and final signed-out verification state

## Artifacts

Each owner run writes to:

`output/ux-journey-recordings/<timestamp>/`

Expected artifacts:

- `signed-user-full-journey.webm`
- `screenshots/`
- `trace.zip`
- `journey_events.json`
- `route_timings.json`
- `console_errors.json`
- `network_failures.json`
- `enhancement_notes.json`
- `SIGNED_USER_JOURNEY_AUDIT_REPORT.md`
- `SIGNED_USER_JOURNEY_SCORECARD.md`
- `SIGNED_USER_JOURNEY_ENHANCEMENT_BACKLOG.md`

Large video and trace outputs are gitignored. Reports and manifests may be copied into a future PR only after confirming they contain no private data.

## Safety Position

- Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Audiobook production remains `PRODUCTION_BLOCKED`.
- The recorder never executes live Razorpay payment.
- The recorder never publishes Kshudhita or future titles.
- The recorder does not add third-party pixels.
- Admin recordings should be reviewed by the owner before any artifact is shared.
