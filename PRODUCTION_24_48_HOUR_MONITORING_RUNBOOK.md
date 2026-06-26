# Production 24-48 Hour Monitoring Runbook

Launch: Dracula reading-only production launch  
Production base URL: https://theearnalism.com  
Launch status: LIVE_VERIFIED  
Public audio status: PUBLIC_AUDIO_RELEASE_BLOCKED  
Audiobook production status: PRODUCTION_BLOCKED

## Scope

This runbook covers the first 24-48 hours after the Dracula reading-only launch. It monitors public reading, pricing, wallet, support, and rollback readiness. It does not approve public audiobook release, Listen Now CTA, AudioObject metadata, Kshudhita publication, new books, or payment behavior changes.

## Owner Monitoring Schedule

| Window | Owner action | Evidence to record |
| --- | --- | --- |
| First 2 hours | Run public canary every 30 minutes and inspect payment/wallet logs after any checkout. | Canary result, support inbox status, failed checkout count. |
| 6 hours | Review conversion funnel checkpoints and wallet credit confirmations. | Funnel notes, wallet credit evidence, webhook/idempotency notes. |
| 24 hours | Confirm reader continuation, pricing, account/wallet, and support/refund readiness. | 24-hour metrics row and any incident links. |
| 48 hours | Decide whether to keep steady, roll back, or open a follow-up polish PR. | 48-hour summary and owner decision. |

## First 2 Hours Checks

- Run `PRODUCTION_BASE_URL="https://theearnalism.com" npm run launch:post-deploy-canary`.
- Open `/`, `/book/dracula`, `/reader/dracula`, `/pricing`, `/login`, `/signup`, `/library`, `/robots.txt`, and `/sitemap.xml`.
- Confirm Chapter 1 remains free.
- Confirm locked/paid continuation behavior remains clear after Chapter 1.
- Confirm no public audio, public audio URL, Listen Now CTA, AudioObject metadata, or audio route appears.
- Confirm Kshudhita and future titles show only pipeline/Notify Me style surfaces.
- Confirm first-time site tour can be forced with `?tour=1`, dismissed, and does not say "Audio is not available yet."
- Confirm homepage, Dracula page, pricing, and reader open without visible layout or performance regressions on a mobile viewport.

## 6 Hour Checks

- Review first-party funnel events if `REACT_APP_ENABLE_LAUNCH_ANALYTICS=true` is configured.
- Confirm homepage view, first-time tour shown, tour completed/skipped, hero CTA, book view, reader opened, pricing view, checkout start, payment success/failure, wallet credited, and return/resume events are visible without PII in `/admin/launch-monitor`.
- Check support inbox for payment, access, refund, and reader continuation issues.
- Review failed checkout count and wallet-credit delays.
- Review Search Console or equivalent crawler dashboard for sitemap fetch, indexing issues, and unexpected excluded routes.
- Review Vercel/Railway logs for 4xx/5xx spikes and backend `/healthz` failures.

## 24 Hour Checks

- Confirm no spike in failed checkouts, duplicate credits, stuck wallet credits, or account-login issues.
- Confirm reader continuation after payment works for owner-observed flows.
- Confirm support/refund handling is ready and response ownership is clear.
- Re-run audio leak scan locally before any follow-up deploy:
  `find frontend/public frontend/build -type f \( -iname "*.mp3" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.ogg" -o -iname "*.aac" \)`.
- Review Core Web Vitals or Vercel analytics if enough production traffic exists.
- Review top funnel drop-offs and decide whether copy, tour, pricing, or reader-lock messaging needs a follow-up polish PR.

## 48 Hour Checks

- Review conversion drop-offs and decide whether the next action is copy polish, pricing explanation polish, onboarding polish, or payment UX polish.
- Confirm all launch truth remains intact:
  Dracula reading-only live, public audiobook blocked, production audiobook blocked, no Kshudhita public CTA, no unapproved book payment CTA.
- Confirm autoscaling and operations dashboards have no unresolved alerts: Vercel deployment health, Railway CPU/memory/restarts, MongoDB connections, Redis memory/evictions, and Razorpay webhook delivery.
- Record owner decision: continue steady state, open optimization PR, or rollback/hotfix.

## Payment Monitoring

- Track checkout started, payment success, payment failed/cancelled, wallet credited, and continue reading after payment.
- Do not record customer email, phone, card, UPI, bank details, raw Razorpay payment IDs, raw order IDs, secrets, invoices, or screenshots in repo docs.
- Use redacted references only for owner evidence.

## Wallet-Credit Monitoring

- Confirm wallet credit arrives after payment success.
- Confirm duplicate replay/idempotency remains verified.
- Escalate if wallet credit is delayed beyond the owner-defined support window.

## Failed Checkout Monitoring

- Track payment failed/cancelled counts.
- Confirm failure messaging stays clear and does not expose payment internals.
- Escalate if multiple failures occur for the same pack or browser.

## Reader Continuation Monitoring

- Confirm locked-state messaging routes readers to sign-in or pricing.
- Confirm account/library resume paths stay visible.
- Confirm low-balance and wallet-empty states do not imply subscription, ownership, or audiobook access.

## SEO And Crawler Monitoring

- Confirm `/sitemap.xml` stays reachable and contains `/book/dracula`.
- Confirm sitemap excludes `/reader/*`, Kshudhita, public audio URLs, and legacy ecommerce routes.
- Confirm `/reader/dracula` remains noindex/canonicalized to `/book/dracula`.
- Confirm public snippets do not imply public audiobook access.
- Track Search Console indexing and crawl errors as owner-dashboard evidence only.

## Performance Monitoring

- Review `/admin/launch-monitor` Core Web Vitals, Vercel analytics, or browser RUM metrics if available.
- Watch homepage, book page, reader, and pricing route response/load time.
- Watch mobile user complaints around first load, reader opening, and Razorpay checkout startup.
- If a route feels slow, check image transfer size, bundle size, backend health, and API latency before changing product copy.

## Backend Logs

- Inspect Railway logs for `/healthz`, `/api/books`, `/api/reader`, `/api/payments/config`, `/api/payments/topup`, `/api/payments/verify`, and `/api/payments/webhook` errors.
- Confirm webhook failures, if any, are explained and do not create wallet-credit mismatches.
- Confirm no API logs expose secrets, customer data, raw payment IDs, card data, UPI data, bank data, invoices, or billing data in repo artifacts.

## Support And Refund Monitoring

- Keep support/refund owner reachable.
- Confirm refund/support copy remains available on pricing/contact surfaces.
- Use redacted references only in any evidence report.

## Rollback Triggers

Rollback or hotfix if any of these occur:

- Public audio, Listen Now, AudioObject, or public audio URL appears.
- Kshudhita or another unapproved title shows public reading/audio/payment CTA.
- Wallet credit fails after successful payment and cannot be resolved quickly.
- Duplicate credit/idempotency issue is observed.
- Pricing copy misrepresents reading time, subscription, ownership, or audiobook availability.
- Production canary fails on core routes.

## Public-Audio Leak Check

Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`. Audiobook production remains `PRODUCTION_BLOCKED`. The internal Dracula Chapter 1 audiobook is not part of public launch.

## Uptime And Canary Schedule

- First 2 hours: every 30 minutes.
- 6-24 hours: every 3-6 hours or after any production change.
- 24-48 hours: at least twice per day and immediately after support/payment incidents.
- Continue daily canary checks for the first week if any payment, wallet, or crawler anomaly appears.
