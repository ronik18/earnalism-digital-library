# Revenue Funnel Readiness Report

Launch status: LIVE_VERIFIED  
Production base URL: https://theearnalism.com  
Launch scope: Dracula reading-only revenue launch  
Revenue path: reading-time wallet/pass via Razorpay  
Public audio status: PUBLIC_AUDIO_RELEASE_BLOCKED  
Audiobook production status: PRODUCTION_BLOCKED

## Decision

Revenue funnel readiness: GO_MONITOR_24_48_HOURS

The funnel is ready for production monitoring because the core path is public, payment evidence is complete, post-deploy canary passes, and public-audio blockers remain intact. The next work is measurement and optimization, not launch gating.

## Funnel Status

| Step | Surface | Status | Evidence |
| --- | --- | --- | --- |
| Homepage view | `/` | READY | `homepage_view` instrumentation and post-deploy canary. |
| First-time tour shown/completed/skipped | FirstVisitSiteTour | READY | Mounted in Layout, first-time localStorage gate, `?tour=1` force path, PII-safe events. |
| Read Chapter 1 Free click | Home hero | READY | `hero_read_chapter_free_click`. |
| Dracula page view | `/book/dracula` | READY | Dracula-specific page and `dracula_book_page_view`. |
| Start Dracula click | Book/home/library/cards | READY | `start_dracula_click`. |
| Reader opened | `/reader/dracula` | READY | `reader_opened`, `reading_started`, `dracula_reader_start`. |
| Free preview | Reader Chapter 1 | READY | Chapter 1 free preview path remains public. |
| Locked/paid continuation | Reader | READY | `reader_locked_state`, `reader_low_balance_state`, upsell copy. |
| Pricing page view | `/pricing` | READY | `pricing_page_view` and post-deploy canary. |
| Pack selected | Pricing/account | READY | `reading_pack_selected`. |
| Razorpay checkout started | Pricing | READY | `checkout_started`; no live Razorpay call in validation. |
| Payment success | Pricing | OWNER_VERIFIED | Final live payment evidence says GO with redacted fields only. |
| Wallet credited | Backend/account | OWNER_VERIFIED | Final evidence marks wallet credit YES and duplicate replay VERIFIED. |
| Continue reading | Pricing/account/library | READY | `return_resume_reading_click`. |
| Return/resume reading | Account/library | READY | Account continue action instrumented. |

## Revenue Feature Status

| Feature | Status | Notes |
| --- | --- | --- |
| Dracula public reading | LIVE_VERIFIED | Only approved public reading release. |
| Chapter 1 free preview | READY | Supports low-friction first session. |
| Reading-time wallet/pass | GO_READY | Final payment evidence complete. |
| Razorpay live checkout evidence | GO | Owner verified low-value live checkout, wallet credit, webhook, idempotency, refund/support, rollback. |
| Failed/cancelled payment handling | READY_TO_MONITOR | Static/test-mode checks pass; monitor production failures. |
| Support/refund path | READY | Owner evidence marks support/refund readiness READY. |
| Kshudhita/future titles | BLOCKED_PIPELINE_ONLY | Notify/pipeline only; no public payment CTA. |
| Public audiobook | BLOCKED | No Listen Now, no AudioObject, no public audio URL. |

## Funnel Risks To Monitor

- Tour completion vs skip rate may identify whether the first-time orientation is helpful or too heavy.
- Reader-to-pricing drop-off may show whether locked-state copy needs a lighter nudge.
- Checkout-start to payment-success drop-off should be reviewed against Razorpay dashboard evidence.
- Payment-success to wallet-credit must remain effectively 1:1.
- Resume after payment is the most important revenue quality signal after wallet credit.

## Next Optimization Actions

1. Review 0-2 hour, 6 hour, 24 hour, and 48 hour funnel rows in `POST_LAUNCH_FUNNEL_BASELINE_REPORT.md`.
2. If reader-to-pricing is weak, polish the locked continuation copy before changing price.
3. If pricing-to-checkout is weak, simplify pack hierarchy and preserve current payment behavior.
4. If checkout fails spike, use Razorpay dashboard/support evidence outside the repo and record redacted notes only.
5. Keep public audiobook release blocked while using audiobook status only as private review/trust language.
