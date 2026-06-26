# Autoscaling Operations Readiness Report

Launch status: LIVE_VERIFIED  
Production base URL: https://theearnalism.com  
Frontend platform expectation: Vercel static frontend  
Backend platform expectation: Railway FastAPI service  
Public audio status: PUBLIC_AUDIO_RELEASE_BLOCKED  
Audiobook production status: PRODUCTION_BLOCKED

## Decision

Operations readiness: GO_WITH_OWNER_DASHBOARD_VERIFICATION_REQUIRED

The repo contains strong operational guardrails, health checks, payment idempotency tests, Redis-aware caching, and post-deploy canaries. Autoscaling itself is not claimed as fully verified from code alone; Railway/Vercel/MongoDB/Redis dashboard settings must be confirmed by the owner.

## Current Autoscaling Status

| Area | Status | Evidence |
| --- | --- | --- |
| Vercel frontend static serving | EXPECTED_READY | `frontend/vercel.json` builds static CRA output and main deploys through Git integration. |
| Railway backend service | CONFIGURED | `backend/railway.json` uses Nixpacks, `/healthz`, restart on failure, and configurable uvicorn workers. |
| Backend health endpoint | VERIFIED_IN_CODE | Railway healthcheck path is `/healthz`; production diagnostics and k6 scripts probe it. |
| MongoDB connection behavior | CONFIGURED_IN_CODE | Backend and diagnostics use `MONGODB_URL`/`MONGO_URL`; dashboard capacity requires owner verification. |
| Redis/cache | CONFIGURED_IN_CODE | Backend has Redis cache status and public/user cache paths; production Redis availability requires owner verification. |
| Judoscale/autoscaling | OWNER_DASHBOARD_VERIFICATION_REQUIRED | No repo file proves live autoscaling policy. |
| Payment webhook resiliency | TESTED_STATIC_AND_UNIT | Signed webhook, duplicate event handling, verify-plus-webhook race prevention covered by tests/docs. |
| Rate limits/abuse controls | CONFIGURED_IN_CODE | `docs/REGRESSION_AND_SCALE.md` documents public and mutation rate-limit policy. |
| Log monitoring | OWNER_DASHBOARD_VERIFICATION_REQUIRED | Owner should check Railway/Vercel/Razorpay dashboards and support inbox. |
| Rollback | READY_RUNBOOK | `PRODUCTION_READING_ONLY_DEPLOY_RUNBOOK.md` and monitoring runbook define rollback triggers. |

## Known Config And Environment Requirements

- Frontend production base: `https://theearnalism.com`.
- Backend API base: `https://api.theearnalism.com`.
- Railway backend must keep `MONGODB_URL` or `MONGO_URL` configured.
- Razorpay live env vars must be configured only in production secret storage.
- `RAZORPAY_KEY_SECRET` and `RAZORPAY_WEBHOOK_SECRET` must never be committed.
- Redis URL/config should be confirmed in Railway/admin cache status.
- ElevenLabs generation variables must not be enabled in production for the reading-only launch.
- Public audio must remain absent from `frontend/public` and `frontend/build`.

## What Is Verified By Repo Evidence

- Production canary checks public reading routes, sitemap, robots, legacy tombstones, no public audio, no Listen Now, no AudioObject, no Kshudhita public CTA, and no unapproved payment CTA.
- Controlled publication precheck keeps Dracula as the only approved public reading release.
- Audio release gate remains expected-blocked.
- Payment smoke test runs in test mode only.
- Full live payment evidence is redacted and marks payment readiness GO without storing secrets.
- Static tests guard public copy, tracking privacy, and payment/audiobook overclaims.

## Owner Dashboard Verification Required

- Vercel production deployment status, domain alias, and error logs.
- Railway service health, restart count, memory/CPU headroom, and replica/autoscaling policy.
- MongoDB Atlas connection count, slow query log, storage, and backup status.
- Redis cache connection and eviction/memory status.
- Razorpay webhook delivery, failures, retries, and live payment dashboard state.
- Any Judoscale/autoscaling threshold and max-replica policy.
- Alerting destination and owner on-call response path.

## Failure-Mode Checklist

- Canary route failure: inspect frontend deployment, DNS, Vercel logs, and latest main SHA.
- Backend `/healthz` failure: inspect Railway logs, env vars, MongoDB connectivity, Redis connectivity, and restart loop.
- Checkout start failure: inspect Razorpay script loading, `/payments/config`, `/payments/topup`, and browser console.
- Payment success without wallet credit: inspect verify path, webhook receipt, idempotency rows, and admin reconcile procedure.
- Duplicate credit: stop payment promotion, preserve evidence, and use rollback/support process.
- Public audio leak: hard stop, remove public asset/route, rerun audio audit and release gate.
- Kshudhita or unapproved CTA leak: rollback/hotfix controlled launch data and rerun public governance tests.

## Traffic Spike Checklist

1. Run `npm run launch:post-deploy-canary` against production.
2. Check Railway CPU, memory, response time, restart count, and replica status.
3. Check Vercel edge/function errors and cache hit behavior.
4. Check MongoDB connection and slow query dashboards.
5. Check Redis memory/eviction dashboard or admin cache status.
6. Check Razorpay checkout and webhook delivery metrics.
7. Keep payment mutation rate limits tighter than public GET traffic.

## Rollback Checklist

- Roll back the frontend deployment from Vercel if public copy, routing, or static assets are wrong.
- Roll back backend/Railway if payment, wallet, health, or catalog API behavior regresses.
- Keep Dracula reader available only if integrity and payment states remain safe.
- Do not roll forward by enabling audiobook/audio features.
- Record only redacted owner evidence in repo docs.

## Operations Score

Autoscaling/operations readiness score: 8.2/10

The code and runbooks are strong, but live autoscaling and dashboard observability remain OWNER_DASHBOARD_VERIFICATION_REQUIRED. This report does not claim autoscaling is fully verified.
