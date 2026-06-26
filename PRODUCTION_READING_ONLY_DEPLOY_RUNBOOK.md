# Production Reading-Only Deploy Runbook

Status: `READY_FOR_OWNER_CONTROLLED_DEPLOY`

Date: 2026-06-26

## Scope

This runbook covers the final production deployment workflow for The Earnalism Dracula reading-only launch.

It does not approve public audiobook release, production audiobook status, Kshudhita publication, future-title publication, public Listen Now CTA, AudioObject metadata, public audio URLs, or payment behavior changes.

## Launch Boundary

- Public launch scope: Dracula reading-only production launch.
- Approved public book: `dracula`.
- Free public entry point: Dracula Chapter 1 preview.
- Paid public path: reading-time wallet/pass continuation for Dracula.
- Reading-only launch status: `GO_READING_ONLY_PRODUCTION_DEPLOY_READY`.
- Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Audiobook production: `PRODUCTION_BLOCKED`.
- Full Dracula Chapter 1 audiobook: internal only.
- Kshudhita Pashan and future titles: pipeline-only.

## Pre-Deploy Checklist

- [ ] Owner confirms deployment action is allowed.
- [ ] `origin/main` includes PR #68.
- [ ] Local `main` is clean and aligned with `origin/main`.
- [ ] No unrelated local changes are included.
- [ ] `LIVE_PAYMENT_FINAL_EVIDENCE_REPORT.md` says `GO_READING_ONLY_PRODUCTION_DEPLOY_READY`.
- [ ] `LIVE_PAYMENT_GO_NO_GO_CHECKLIST.md` owner sign-off is complete.
- [ ] `REVENUE_LAUNCH_CHECKLIST.md` final deploy checklist is reviewed.
- [ ] `AUDIOBOOK_PARALLEL_TRACK_STATUS.md` still says `PUBLIC_AUDIO_RELEASE_BLOCKED` and `PRODUCTION_BLOCKED`.
- [ ] `frontend/public` and `frontend/build` contain no audio-like files.
- [ ] No secrets, payment IDs, customer data, invoices, screenshots, billing data, API keys, Razorpay secrets, webhook secrets, or ElevenLabs keys are committed.

## Required Local Validation Before Deploy

Run:

```bash
python3 scripts/check-hidden-unicode.py PRODUCTION_READING_ONLY_DEPLOY_RUNBOOK.md POST_DEPLOY_READING_ONLY_CANARY_REPORT.md scripts/post_deploy_reading_canary.mjs package.json regression/modules/14-ux-conversion-static.test.js
git diff --check
npm run controlled-publication:precheck
npm run catalog:audit
npm run launch:audio-audit
npm run audiobook:release-gate
npm run launch:seo-audit
npm run launch:social-preview-audit
npm run launch:payment-smoke:test-mode
npm run regression -- modules/11-seo.test.js modules/13-public-content-governance.test.js modules/14-ux-conversion-static.test.js
npm --prefix frontend run build
find frontend/public frontend/build -type f \( -iname "*.mp3" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.ogg" -o -iname "*.aac" \)
```

Hard stop if any command fails.

## Deploy Command / Platform Steps

Deployment must be started only after explicit owner confirmation.

Recommended platform sequence:

1. Confirm the production deployment target is The Earnalism production project.
2. Confirm the commit being deployed is the latest `origin/main` containing PR #68 and this deploy runbook.
3. Trigger the platform's standard production deploy for the reviewed main commit.
4. Do not set or change any payment, Razorpay, webhook, or ElevenLabs environment variables from this repository.
5. No public audio storage, public audio routes, Listen Now CTA, or AudioObject metadata may be added.
6. Record the production deployment URL, commit SHA, deployment timestamp, and operator in `POST_DEPLOY_READING_ONLY_CANARY_REPORT.md`.

If using Vercel, use the owner-approved production deployment flow for the existing frontend project and run post-deploy canaries immediately after the deployment is live.

## Production Environment Checks

- [ ] Production domain resolves to the expected deployment.
- [ ] Production deployment SHA matches the reviewed main commit.
- [ ] Production API/base URLs point to the intended production services.
- [ ] No staging or preview URLs are linked from public navigation.
- [ ] No `ELEVENLABS_API_KEY` or ElevenLabs generation enablement variables are active in public frontend production.
- [ ] No public audio bucket, CDN route, or static audio path is configured.
- [ ] Internal audiobook files remain under `internal/audiobook_lab/` and are not publicly served.

## Razorpay Live Environment Checks

- [ ] Owner confirms Razorpay live account is the intended account.
- [ ] Live Razorpay key ID is configured only in the production environment.
- [ ] Live Razorpay key secret is configured only in the production environment.
- [ ] Live webhook secret is configured only in the production environment.
- [ ] Webhook URL is registered in the Razorpay live dashboard.
- [ ] No Razorpay key secret, webhook secret, payment ID, order ID, customer data, invoice, screenshot, card data, UPI detail, bank detail, or billing data is committed.
- [ ] Do not run a live checkout from this runbook unless the owner explicitly performs it outside the repository.

## Post-Deploy Canary Checks

Run after the production deployment is live:

```bash
PRODUCTION_BASE_URL=https://theearnalism.com npm run launch:post-deploy-canary
```

The canary performs public `GET`/`HEAD` checks only. It does not require secrets, execute live payment, mutate production data, or call private/internal routes.

For the owner launch monitoring dashboard deployment, also run the canary with the production backend origin so the unauthenticated admin API guard is verified:

```bash
PRODUCTION_BASE_URL=https://theearnalism.com PRODUCTION_API_BASE_URL=https://api.theearnalism.com npm run launch:post-deploy-canary
```

The admin API guard must confirm `GET /api/admin/launch-monitor/summary` returns `401` or `403` without admin credentials. A `404` means the dashboard backend is not deployed or the backend URL is wrong, and any `200` response is a hard stop.

Manual canaries must also be recorded in `POST_DEPLOY_READING_ONLY_CANARY_REPORT.md`:

- `/`
- `/admin/launch-monitor` in a fresh incognito/non-admin browser session redirects to or blocks behind `/admin/login`
- `/book/dracula`
- `/reader/dracula`
- `/pricing`
- `/login`
- `/signup`
- account/wallet route if publicly reachable
- `sitemap.xml`
- `robots.txt`
- social preview metadata
- legacy tombstone routes
- Razorpay payment status endpoint if available
- unauthenticated `GET /api/admin/launch-monitor/summary` returns `401` or `403`
- Dracula Chapter 1 free preview
- locked/paid continuation behavior
- wallet reading-time copy
- no public audio
- no Listen Now CTA
- no AudioObject metadata
- no Kshudhita public CTA
- no unapproved book payment CTA

Do not mark launch complete until post-deploy canaries pass against production.

## Rollback Steps

Rollback immediately if any critical canary fails:

1. Stop further public promotion.
2. Roll back the production deployment to the last known-good release.
3. Keep Dracula reading route live only if reader integrity and payment integrity remain healthy.
4. Disable or hide pricing CTAs only if checkout or wallet behavior is unhealthy.
5. Keep public audio blocked.
6. Keep Kshudhita and future titles pipeline-only.
7. Re-run the local validation bundle and post-deploy canary after rollback.
8. Record incident notes without secrets or personal/payment data.

## Owner Sign-Off Fields

| Field | Value |
| --- | --- |
| Owner deployment approval | PENDING |
| Owner approver | Ronik Basak |
| Deployment operator | PENDING |
| Deployment timestamp | PENDING |
| Production deployment URL | PENDING |
| Deployed commit SHA | PENDING |
| Post-deploy canary status | PENDING |
| Rollback owner | PENDING |
| Final launch completion decision | HOLD_POST_DEPLOY_CANARY_REQUIRED |

## Final Rule

Reading-only deploy readiness is `GO_READING_ONLY_PRODUCTION_DEPLOY_READY`, but launch completion remains `HOLD_POST_DEPLOY_CANARY_REQUIRED` until production canaries pass.
