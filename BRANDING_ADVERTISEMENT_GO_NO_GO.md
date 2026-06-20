# Branding And Advertisement Go/No-Go

## Environment

- Frontend URL: `https://theearnalism.com`
- API URL: `https://api.theearnalism.com/api`
- Branch: `codex/static-seo-snapshots-dracula`

## Recommendation

`KEEP_DRACULA_LIVE_BUT_HOLD_ADS`

## Current Evidence

| Area | Status |
| --- | --- |
| Backend catalog truth | PASS in latest local canary; must pass again after deploy. |
| Real-user hydrated UX | PASS from PR #39 artifacts; must be rerun after this PR deploy if ads are considered. |
| Static Dracula book SEO | PASS locally after static snapshots. |
| Social preview tags | PASS locally after static snapshots. |
| Dracula audio | Disabled as required. |
| Non-Dracula books | Pipeline-only; no live reader, preview, or audio CTA allowed. |

## Decision

- Dracula stays live: `yes`
- Rollback needed before deploy: `no`
- Start ads: `no`

Paid ads, broad branding, and public acquisition campaigns remain on hold until the deployed build passes:

- `npm run launch:backend-catalog-truth-canary`
- `npm run launch:seo-audit`
- `npm run launch:social-preview-audit:prod`
- `npm run release:post-production-canary`
- `npm run release:ux-go-no-go`

Never mark `GO_FOR_BRANDING_AND_ADVERTISEMENT` while backend catalog truth fails, raw production SEO/social-preview fails, Playwright fails, or unapproved titles expose live CTAs.

No publication, ad, email, social, payment, provider, or production data mutation was performed by this PR.
