# Payment Revenue 10x Confidence Report

Status: `HOLD_FOR_CONTROLLED_TEST_MODE_CHECKOUT`

Current confidence score: `9.1/10`

Date: 2026-06-22

## Executive Summary

Earnalism's reading-time revenue flow is structurally ready for controlled test-mode validation. The server owns pack IDs, prices, and wallet minutes. Razorpay verification is user-scoped and signature-gated. Webhook replay and manual reconciliation are protected by an atomic wallet-credit transition. Failed payments, bad signatures, user mismatch, and simulator misuse are blocked or recorded for audit.

This task did not run live Razorpay, did not call a payment provider, did not mutate production data, and did not change public prices or pack IDs.

No live Razorpay payment was run in this task.

Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.

No audiobook sale is live.

## Architecture

The reading-time flow is:

1. Frontend requests `/api/payments/packs`.
2. Backend returns the server-owned pack catalogue.
3. Authenticated users create a top-up intent through `/api/payments/topup` when Razorpay keys are configured.
4. Razorpay checkout returns order/payment/signature values.
5. `/api/payments/verify` verifies the HMAC signature and confirms the intent belongs to the signed-in user.
6. `/api/payments/webhook` independently verifies Razorpay's webhook signature and processes captured or failed payments.
7. `_credit_wallet_for_intent()` atomically transitions a top-up intent to `credited` and increments wallet seconds once.
8. Wallet ledger entries provide the user/admin audit trail.
9. Admin reconcile and refund-review routes reuse the same idempotency posture.

## Reading-Time Packs

| Pack ID | Visible name | Minutes | Amount paise | INR |
| --- | --- | ---: | ---: | ---: |
| `30m` | The First Chapter | 30 | 4900 | 49 |
| `1h` | The Quiet Hour | 60 | 8900 | 89 |
| `3h` | The Deep Reading Pass | 180 | 23900 | 239 |
| `10h` | The Reader's Reserve | 600 | 49900 | 499 |

No pack ID, amount, wallet-credit unit, Razorpay behavior, or live pricing behavior was changed by this task.

## Test-Mode Success Path

`npm run launch:payment-smoke:test-mode` is a dry-run/static smoke command. It reads the frontend/backend source and confirms the expected payment events, simulator endpoints, verify endpoint, webhook endpoint, signature checks, and post-payment account return path.

The simulator endpoints remain test-mode-only. They are blocked outside `RAZORPAY_MODE=test`.

## Webhook Idempotency

Webhook idempotency is enforced in two layers:

1. Duplicate Razorpay event IDs are short-circuited from `payment_webhook_events`.
2. Wallet crediting uses a single atomic Mongo update requiring top-up intent status to be not `credited`.

This prevents webhook replay and verify-plus-webhook races from double-crediting a wallet.

## Double-Credit Prevention

The wallet-credit helper:

- checks stale/expired intent status first,
- transitions the intent to `credited` atomically,
- increments `reading_seconds_balance` and `wallet_seconds` once,
- records a wallet ledger row,
- returns the refreshed intent for all callers.

Admin reconcile also goes through the same helper.

## Failed, Abandoned, Stale, And Expired Payments

Failed Razorpay events mark a `created` intent as `failed` without wallet credit.

Bad verify signatures mark the intent as failed with `failed_reason=bad_signature` and do not credit the wallet.

Top-up intents expire after 24 hours by default through `TOPUP_INTENT_TTL_SECONDS`. An expired intent is marked `expired` with `failed_reason=intent_expired` and cannot credit the wallet through verify, webhook, simulator, or admin reconcile.

Abandoned payments remain uncredited unless a valid signed capture arrives before expiry.

## User Mismatch Protection

`/api/payments/verify` looks up intents by both Razorpay order ID and signed-in user ID. The simulator webhook also checks intent ownership. Cross-user wallet credit is blocked.

## Missing Signature Handling

Webhook requests require `RAZORPAY_WEBHOOK_SECRET` and a matching `X-Razorpay-Signature`. Missing or invalid signatures are rejected; invalid attempts are stored as rejected audit records when persistence is available.

## Refund And Reconcile Operator Flow

Admin reconcile is idempotent and cannot double-credit an already credited intent.

Admin refund approval uses unique refund candidates and `$setOnInsert`; repeat approval of the same candidate returns zero applied seconds and does not add duplicate wallet time.

Remaining operator drill:

- run one controlled refund-review and refund-approve test in a non-production database,
- verify admin audit rows and user wallet transaction copy,
- confirm support copy matches the refund policy before broader launch.

## Wallet UX And Post-Payment Return

The frontend explains that reading time is credited after confirmation and is used only while the reader reads. Pricing and account copy avoid permanent ownership, subscription, and autorenewal claims.

No subscription or autorenewal is sold.

The post-payment path returns readers to the account/wallet view so credited reading time can be checked before continuing.

## Audit And Logging

Evidence present:

- top-up intents store pack, amount, user, mode, status, created time, expiry, and credited metadata,
- webhook events store event IDs, status, order/payment IDs, and a bounded raw payload preview,
- wallet ledger rows record top-up and refund credits,
- admin reconcile and refund flows preserve operator notes.

## Privacy And Data Minimization

The payment flow stores only operational metadata needed to reconcile payment and wallet state. It does not store card data. Razorpay checkout handles card/payment credentials.

Webhook raw payloads are bounded to 8000 characters for auditability and should remain internal/admin-only.

## Future Audiobook Monetization Readiness

Audiobook monetization is intentionally blocked. Public audio remains `PUBLIC_AUDIO_RELEASE_BLOCKED`.

Revenue copy must not sell audiobook access, audiobook passes, Listen Now access, permanent ownership, or accessible-audiobook claims until the audiobook release gate passes and owner/legal approval exists.

Future audiobook monetization should reuse this pattern only after:

- derivative audiobook rights pass,
- model/provider license evidence passes,
- Bengali/English human listening QA passes,
- accessible player evidence passes,
- refund/support policy for audio is approved,
- public audio storage/CDN serving is approved,
- owner approval allows publication.

## Blockers Before 10/10 Revenue Confidence

1. Run an operator-approved Razorpay test-mode checkout with a throwaway user in the production-like environment.
2. Confirm the actual hosted checkout window, payment success return, webhook delivery, and wallet credit using test keys only.
3. Confirm a failed/cancelled test payment produces the expected `payment_failed` event and no wallet credit.
4. Confirm refund-review and reconcile are exercised in a non-production database.
5. Confirm privacy/support language with the owner before scaling paid traffic.

## Changed Files

- `backend/server.py`
- `backend/tests/test_payment_revenue_confidence_static.py`
- `backend/tests/test_payments_razorpay.py`
- `scripts/launch_readiness_audit.py`
- `regression/modules/14-ux-conversion-static.test.js`
- `PAYMENT_REVENUE_10X_CONFIDENCE_REPORT.md`

## Rollback

Revert the commit that adds this report, the static payment confidence tests, and the top-up intent expiry guard. If rollback is needed after a deploy, keep public audio blocked and keep Razorpay in test mode until payment smoke is repeated.
