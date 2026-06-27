# Payment Receipt And Invoice Audit

Status: `OWNER_DASHBOARD_VERIFICATION_REQUIRED`

This audit reviews the repository evidence for Earnalism payment receipts and invoices. It does not call live Razorpay and does not inspect private Razorpay dashboard settings.

## Current Payment Flow Type

Evidence from code:

- `frontend/src/pages/Pricing.jsx` loads Razorpay Checkout script from `https://checkout.razorpay.com/v1/checkout.js`.
- `frontend/src/pages/Pricing.jsx` calls `/api/payments/topup` to create a top-up intent and Razorpay order.
- `backend/server.py` exposes `/api/payments/topup`, `/api/payments/verify`, and `/api/payments/webhook`.
- `backend/server.py` creates a Razorpay order with `client.order.create(...)`.
- `backend/server.py` sets a short Razorpay `receipt` value in order creation: `earn-<redacted-intent-prefix>`.
- Wallet credit is idempotent through `_credit_wallet_for_intent(...)`, with both verify and webhook paths guarded against duplicate credit.
- `frontend/src/pages/Account.jsx` displays wallet balance and recent ledger activity.

Conclusion: current primary flow is `Razorpay Orders + Checkout + server verify/webhook + Earnalism wallet ledger`.

## Receipt Sender

| Sender | Current evidence | Status |
| --- | --- | --- |
| Razorpay automated receipt | Dashboard setting cannot be verified from repo code. Razorpay order includes a `receipt` field, but that is not proof customer receipt email is enabled. | `OWNER_DASHBOARD_VERIFICATION_REQUIRED` |
| Earnalism owned email receipt | No approved transactional receipt email provider/path was found in the payment flow. MSG91 appears related to OTP/mobile auth, not payment receipts. | `NOT_IMPLEMENTED_IN_REPO` |
| Razorpay Invoice API | No repository evidence of Razorpay Invoice API usage. | `NOT_USED_IN_REPO` |

## Invoice / Tax Status

- GST/tax invoice generation is not proven by repository code.
- No code path was found that creates Razorpay invoices.
- No code path was found that generates Earnalism tax invoices.
- Any tax/GST invoice claim must remain blocked until owner/legal/accounting implementation evidence exists.

Current status: `GST_TAX_INVOICE_NOT_VERIFIED`

## Account / Wallet Visibility

Evidence:

- `frontend/src/pages/Account.jsx` renders wallet balance.
- `frontend/src/pages/Account.jsx` renders recent activity rows.
- Backend wallet ledger records top-up credits with `reason=f"Razorpay top-up ..."` and stores top-up intent references internally.

Conclusion: account/wallet history provides transaction visibility, but it is not a formal tax invoice and should not be represented as one.

## Email Delivery Verification

Status: `NOT_VERIFIED`

Repo evidence does not prove that a customer receives a payment receipt email automatically after successful payment. This remains a dashboard/owner verification item unless Earnalism implements its own transactional email receipt flow.

## Remaining Owner Dashboard Checks

1. Confirm whether Razorpay dashboard automated customer receipts are enabled for live Checkout orders.
2. Confirm the sender, subject line, and customer-visible fields in any Razorpay receipt email.
3. Confirm whether GST/tax invoice settings are configured in Razorpay or another accounting system.
4. Confirm whether the low-value live drill customer received any email automatically.
5. Confirm whether receipt references remain redacted in repo evidence.

## Public/Legal Copy Rule

Until verified, public copy and support docs must say only that payment success and wallet credit are owner-verified. They must not claim automatic email receipts, GST invoices, or tax invoices.
