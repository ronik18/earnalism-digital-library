# Reading Launch Funnel Tracking Plan

Launch: Dracula reading-only production launch  
Production base URL: https://theearnalism.com  
Tracking approach: first-party, privacy-safe, opt-in

## Funnel Events

| Funnel step | Event |
| --- | --- |
| Homepage view | `homepage_view` |
| First-time tour shown | `first_time_site_tour_shown` |
| First-time tour completed | `first_time_site_tour_completed` |
| First-time tour skipped | `first_time_site_tour_skipped` |
| Hero Read Chapter 1 Free click | `hero_read_chapter_free_click` with CTA metadata |
| Dracula book page view | `dracula_book_page_view` |
| Start Dracula click | `start_dracula_click` |
| Reader opened | `reader_opened` |
| Pricing page view | `pricing_page_view` |
| Reading pack selected | `reading_pack_selected` |
| Razorpay checkout started | `checkout_started` |
| Payment success | `payment_success_return` |
| Payment failed/cancelled | `payment_failed_or_cancelled` |
| Wallet credited | `wallet_credited_visible` |
| Continue reading after payment | `continue_reading_click` |
| Reader low-balance/locked state | `reader_low_balance_state` and `reader_locked_state` |
| Return/resume reading | `return_resume_reading_click` |
| Core Web Vitals | `core_web_vital` |

## Privacy Requirements

- No PII.
- No customer email or phone.
- No payment secrets.
- No webhook secrets.
- No card, UPI, bank, billing, or invoice data.
- No raw unredacted Razorpay payment IDs, order IDs, customer IDs, or signatures.
- No third-party pixels unless separately approved.
- No broad browser fingerprinting.
- Use first-party, privacy-safe events only.
- Keep production performance low-cost and non-blocking.

## Implementation Notes

- Frontend events use `frontend/src/lib/funnelAnalytics.js`.
- Network delivery is disabled unless `REACT_APP_ENABLE_LAUNCH_ANALYTICS=true` or `window.__EARNALISM_ENABLE_FUNNEL_ANALYTICS__ === true`.
- Local review can use `window.__EARNALISM_ANALYTICS_SINK__` or `REACT_APP_ENABLE_LAUNCH_ANALYTICS_DEBUG=true`.
- Metadata is sanitized before sinks, console debug, or network delivery.
- The backend endpoint remains first-party: `/api/analytics/event`.
- The owner dashboard endpoint is admin-only: `/api/admin/launch-monitor/summary`.
- No production mutation is required to emit events; events are lightweight POSTs only when first-party analytics delivery is explicitly enabled.
- No third-party pixel was added by this pass.

## Allowed Metadata

Safe examples:

- event name
- timestamp through backend insertion time
- route path/search
- CTA ID
- source surface
- book slug
- chapter ID
- pack ID
- price INR
- minutes
- boolean credited state
- safe failure reason code

Blocked examples:

- email
- phone
- customer name
- raw Razorpay payment/order/customer IDs
- Razorpay signatures
- card, UPI, bank, invoice, or billing data
- API keys, bearer tokens, webhook secrets, or provider keys

## Owner Review

Before enabling production network delivery, owner should confirm:

- Analytics endpoint is expected to receive first-party events.
- Storage/retention policy is acceptable.
- Event review confirms no PII.
- Performance impact is acceptable.
- Public audio and audiobook production remain blocked.
- Owner dashboard aggregates only safe counts and never returns row-level payment/customer data.

## Revenue Review Questions

- Does the first-time tour improve the Chapter 1 free-click rate, or should it become shorter?
- Does the Dracula book page convert better than the homepage hero path?
- Does the reader locked state lead readers to pricing without confusion?
- Does payment success reliably lead to wallet credit and resume reading?
- Does the wallet/pass model read as time credit, not subscription, ownership, or audiobook access?

## Production Enablement Gate

Keep network delivery disabled until the owner confirms:

- First-party endpoint storage is acceptable.
- Event payload review shows only safe event names and coarse metadata.
- No customer email, phone, payment ID, order ID, UPI/card/bank details, invoice, billing data, API key, or webhook secret is recorded.
- No public audio, Listen Now CTA, AudioObject metadata, or audiobook-live claim is introduced.
