# Post-Launch Funnel Baseline Report

Launch status: LIVE_VERIFIED  
Production base URL: https://theearnalism.com  
Public audio status: PUBLIC_AUDIO_RELEASE_BLOCKED  
Audiobook production status: PRODUCTION_BLOCKED  
Tracking status: OPT_IN_READY

## Events Implemented

| Area | Events |
| --- | --- |
| Homepage | `homepage_view`, `hero_read_chapter_free_click` |
| First-time tour | `first_time_site_tour_shown`, `first_time_site_tour_completed`, `first_time_site_tour_skipped` |
| Book detail/library/card | `dracula_book_page_view`, `start_dracula_click`, `pricing_page_view` |
| Reader | `reader_opened`, `reader_locked_state`, `reader_low_balance_state` |
| Pricing/checkout | `pricing_page_view`, `reading_pack_selected`, `checkout_started`, `payment_success_return`, `payment_failed_or_cancelled`, `wallet_credited_visible` |
| Return/resume | `continue_reading_click`, `return_resume_reading_click` |
| Core Web Vitals | `core_web_vital` |

## Events Still Manual

- Human review of support/refund conversations.
- Owner reconciliation of live Razorpay dashboard references.
- Owner review of wallet-credit evidence using redacted references.
- Production conversion summary until opt-in analytics delivery is enabled and reviewed in `/admin/launch-monitor`.
- Search Console indexing and query data.
- Vercel/Railway/MongoDB/Redis dashboard checks.
- Production Core Web Vitals until field data is available.

## Privacy Notes

- Event delivery is first-party and opt-in.
- Metadata sanitizer blocks PII-like fields and unsafe values before sink, debug, or network delivery.
- No customer email, phone, card, UPI, bank details, raw payment IDs, raw order IDs, webhook secrets, API keys, invoices, screenshots, or billing data are recorded in this repo.
- No third-party pixels were added.

## Monitoring Instructions

1. Run production canary on the agreed schedule:
   `PRODUCTION_BASE_URL="https://theearnalism.com" npm run launch:post-deploy-canary`
2. If analytics is enabled, review safe event counts in `/admin/launch-monitor`.
3. Cross-check payment success against wallet-credit evidence using redacted owner references only.
4. Keep public audio and audiobook production blocked during all follow-up analysis.

## 24-48 Hour Metrics Table

| Window | Homepage views | Tour shown | Tour complete | Tour skipped | Hero CTA clicks | Book views | Reader opened | Pricing views | Checkout starts | Payment success | Payment failed/cancelled | Wallet credited | Resume clicks | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0-2h |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2-6h |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 6-24h |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 24-48h |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

## Conversion Funnel Template

| Step | Count | Rate from previous | Alert threshold |
| --- | ---: | ---: | --- |
| Homepage view |  |  | Canary failure or unexpected traffic drop |
| Tour shown |  |  | Tour not shown for first-time/forced users |
| Hero CTA click |  |  | Sharp CTA drop after copy or layout change |
| Book page view |  |  | Broken book route or copy mismatch |
| Reader opened |  |  | Reader load errors or lock confusion |
| Pricing view |  |  | Pricing route or wallet-copy confusion |
| Checkout started |  |  | Razorpay load/config issue |
| Payment success |  |  | Payment failure spike |
| Wallet credited |  |  | Credit delay or idempotency issue |
| Continue reading after payment |  |  | Resume/library/account confusion |

## Decision Thresholds

- Hotfix if public audio, Listen Now, AudioObject, public audio URL, Kshudhita public CTA, or unapproved book payment CTA appears.
- Hotfix if payment success does not reliably lead to wallet credit.
- Investigate if checkout failures exceed owner tolerance in the first 24 hours.
- Investigate if reader opened to pricing transition is unexpectedly low.
- Keep audiobook work on the internal QA track until highlighted-text sync, accessibility QA, and release gates pass.

## Baseline Readiness Summary

| Area | Baseline status | Notes |
| --- | --- | --- |
| Funnel tracking | OPT_IN_DASHBOARD_READY | First-party logger and owner dashboard exist; network delivery is disabled by default. |
| Revenue funnel | READY_TO_MONITOR | Core public path from homepage to wallet/resume is mapped. |
| Payment evidence | GO | Owner evidence is complete and redacted. |
| SEO baseline | READY_TO_MONITOR | Sitemap/static SEO/social previews pass local checks. |
| Performance baseline | READY_TO_MONITOR | Build passes; image/bundle quick wins remain. |
| Operations baseline | OWNER_DASHBOARD_VERIFICATION_REQUIRED | Code/runbooks are ready; dashboard health must be observed. |

## Owner Notes Template

| Time | Observation | Owner action | Follow-up needed |
| --- | --- | --- | --- |
| 0-2h |  |  |  |
| 6h |  |  |  |
| 24h |  |  |  |
| 48h |  |  |  |
