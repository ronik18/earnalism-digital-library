# Post-Deploy Reading-Only Canary Report

Status: `TEMPLATE_PENDING_PRODUCTION_DEPLOY`

Date: 2026-06-26

## Scope

This template records post-deploy production canaries for The Earnalism Dracula reading-only launch.

It does not approve public audiobook release, production audiobook status, Kshudhita publication, future-title publication, public Listen Now CTA, AudioObject metadata, or public audio URLs.

## Deployment Metadata

| Field | Value |
| --- | --- |
| Production base URL | PENDING |
| Deployment URL | PENDING |
| Deployed commit SHA | PENDING |
| Deployment timestamp | PENDING |
| Operator | PENDING |
| Owner reviewer | Ronik Basak |
| Canary started at | PENDING |
| Canary completed at | PENDING |
| Overall canary decision | HOLD_POST_DEPLOY_CANARY_REQUIRED |

## Route Canary Checklist

| Check | Expected Result | Actual Result | Decision |
| --- | --- | --- | --- |
| `/` | Loads Dracula-first reading-only home | PENDING | HOLD |
| `/book/dracula` | Loads Dracula book page | PENDING | HOLD |
| `/reader/dracula` | Loads Dracula reader and Chapter 1 preview path | PENDING | HOLD |
| `/pricing` | Shows reading-time wallet/pass model only | PENDING | HOLD |
| `/login` | Loads sign-in path | PENDING | HOLD |
| `/signup` | Loads account creation path | PENDING | HOLD |
| `/account` or wallet route | Redirects to sign-in or loads account safely if publicly reachable | PENDING | HOLD |
| `/sitemap.xml` | Includes approved public routes only | PENDING | HOLD |
| `/robots.txt` | Keeps admin/API/private routes blocked and allows approved reader route as configured | PENDING | HOLD |
| social preview metadata | Dracula reading-only metadata, no audiobook-live claim | PENDING | HOLD |
| legacy tombstone routes | Return `404` or `410`; no generic storefront shell | PENDING | HOLD |
| Razorpay public payment status endpoint, if available | Safe public status/config only; no secrets or mutation | PENDING | HOLD |

## Product Canary Checklist

| Check | Expected Result | Actual Result | Decision |
| --- | --- | --- | --- |
| Dracula Chapter 1 free preview | Publicly reachable | PENDING | HOLD |
| Locked/paid continuation behavior | Later chapters require sign-in and reading time | PENDING | HOLD |
| Wallet reading-time copy | Explains reading time, no ownership/subscription overclaim | PENDING | HOLD |
| Razorpay payment entry point | Shows reading-time purchase path without exposing secrets | PENDING | HOLD |
| No public audio files | No `.mp3`, `.wav`, `.m4a`, `.ogg`, or `.aac` under public/build routes | PENDING | HOLD |
| No Listen Now CTA | No public Listen Now control or CTA | PENDING | HOLD |
| No AudioObject metadata | No public AudioObject structured data | PENDING | HOLD |
| No public audiobook claim | No claim that audiobooks are live, ready, or available | PENDING | HOLD |
| No Kshudhita public CTA | Kshudhita remains pipeline-only / notify-only | PENDING | HOLD |
| No unapproved book payment CTA | Future titles have no Start Reading, payment, or reader access CTA | PENDING | HOLD |

## Automated Canary Command

Run:

```bash
PRODUCTION_BASE_URL=https://theearnalism.com npm run launch:post-deploy-canary
```

Expected behavior:

- Uses public `GET`/`HEAD` requests only.
- Requires no secrets.
- Does not execute live payment.
- Does not mutate production data.
- Does not call internal audiobook paths.
- Writes local reports under `output/launch/`.

## Public Audio Status

- Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Audiobook production: `PRODUCTION_BLOCKED`.
- Full Dracula Chapter 1 audiobook: internal only.
- Listen Now CTA: not allowed.
- AudioObject metadata: not allowed.

## Final Decision

Final launch completion decision: `LIVE_VERIFIED`

Production reading-only canary passed against the production base URL below. This does not approve public audiobook release, audiobook production, Kshudhita publication, future-title publication, public Listen Now CTA, AudioObject metadata, or public audio URLs.

## Final Production Canary Result

- production_base_url: https://theearnalism.com
- canary_command: `PRODUCTION_BASE_URL="https://theearnalism.com" npm run launch:post-deploy-canary`
- result: PASS
- reading_launch_status: LIVE_VERIFIED
- public_audio_status: PUBLIC_AUDIO_RELEASE_BLOCKED
- audiobook_production_status: PRODUCTION_BLOCKED
