# Real-User UX Review Report

## Environment

- Frontend URL: `https://theearnalism.com`
- API URL: `https://api.theearnalism.com/api`
- Source UX audit: PR #39 real-user video harness
- Current PR scope: static SEO snapshots only

## Scope

This report is generated from the live Playwright real-user UX video audit artifacts and live backend API probes. It must not be edited into a PASS state by hand.

The audit verifies:

- Dracula is the only live approved Tier A core reading title.
- Dracula audio is disabled.
- Kshudhita Pashan remains pipeline-only.
- Unapproved titles do not show Start Reading, Read Preview, or Listen Now.
- Pricing uses Dracula-first reading-time packs.
- Removed demo/ecommerce routes do not serve a generic Earnalism shell.

## Current Owner Recommendation

`KEEP_DRACULA_LIVE_BUT_HOLD_ADS`

## Validation Summary

| Check | Result |
| --- | --- |
| Playwright browser journey | PASS from PR #39 evidence; rerun after this PR deploy before ads. |
| Backend catalog truth | PASS in latest local canary evidence; rerun after deploy. |
| Static Dracula SEO | PASS locally in this PR. |
| Social preview audit | PASS locally in this PR. |
| Full launch readiness | HOLD_FOR_FIXES until deployed canaries and ad-readiness evidence pass. |

## Backend Catalog Truth

- `/api/books` live slugs must remain `['dracula']`.
- `/api/books/dracula` must return `200`.
- `/api/reader/book/dracula/manifest` must return `200` with `27` chapters.
- `/api/reader/book/dracula/audiobook` must remain `404` or hidden.

## UX Scope In This PR

This PR does not modify hydrated React components. It adds crawler-visible static SEO snapshots that preserve the React root and compiled JS/CSS bundles, then the existing CRA app owns the hydrated UX.

## Main Finding

Hydrated UX evidence from PR #39 passes. Static SEO/social-preview evidence now passes locally. Ads remain held until those same checks pass on the deployed production build.
