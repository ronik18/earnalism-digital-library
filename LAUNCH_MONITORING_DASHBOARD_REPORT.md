# Launch Monitoring Dashboard Report

Status: OWNER_ADMIN_ONLY_DASHBOARD_READY

## Dashboard Route

- Frontend route: `/admin/launch-monitor`
- Backend endpoint: `GET /api/admin/launch-monitor/summary`
- Access control: existing admin auth gate
- Public access: blocked by admin login requirement

## Implemented Signals

Funnel events:

- homepage_view
- first_time_site_tour_shown
- first_time_site_tour_completed
- first_time_site_tour_skipped
- hero_read_chapter_free_click
- dracula_book_page_view
- start_dracula_click
- reader_opened
- reader_locked_state
- reader_low_balance_state
- pricing_page_view
- reading_pack_selected
- checkout_started
- payment_success_return
- payment_failed_or_cancelled
- wallet_credited_visible
- continue_reading_click
- return_resume_reading_click

Payment and wallet metrics:

- payment intents created
- payment success count
- payment failed count
- wallet credit count
- webhook received count
- duplicate webhook replay blocked count

Operations metrics:

- post-deploy canary status from recorded evidence
- public audio leak check
- support queue status counts
- refund queue status counts
- backend error status placeholder when no persisted error collection exists

Core Web Vitals:

- LCP
- CLS
- INP
- FID
- FCP
- TTFB

Core Web Vitals are captured only when the first-party performance flag is enabled.

## Backend Behavior

`POST /api/analytics/event`:

- accepts approved event names only
- rejects unknown event names
- rejects PII-like fields and values
- rejects payment-secret-like fields and values
- stores only minimal safe metadata
- uses the existing rate-limit middleware with an analytics-specific bucket
- never returns or stores API keys

`GET /api/admin/launch-monitor/summary`:

- requires admin auth
- returns aggregate counts only
- returns no payment/customer row-level details
- returns no raw payment ids, order ids, signatures, customer emails, or phone numbers

## Owner Manual Checks Still Needed

- Compare successful payment count with Razorpay dashboard.
- Confirm wallet credit count against owner-visible account balances.
- Review support/refund queue manually.
- Confirm Railway backend logs for unexpected error spikes.
- Confirm Vercel frontend dashboard for traffic and deployment health.
- Run `PRODUCTION_BASE_URL="https://theearnalism.com" npm run launch:post-deploy-canary` after every production change.

## Public Truth

- Dracula reading-only launch: LIVE_VERIFIED
- Public audiobook: PUBLIC_AUDIO_RELEASE_BLOCKED
- Audiobook production: PRODUCTION_BLOCKED
- Full Dracula Chapter 1 audio: internal only
- Listen Now CTA: not allowed
- AudioObject metadata: not allowed
- Kshudhita public CTA: not allowed
- Payment behavior: unchanged

## Remaining Blockers

The dashboard is safe to merge for owner monitoring. Launch completion still depends on owner monitoring during the first 24 to 48 hours and continued successful canaries after production changes.
