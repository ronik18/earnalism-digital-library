# Payment Receipt Email Implementation Plan

Status: `PLANNING_ONLY_NO_EMAIL_SENDING_ADDED`

Current repository evidence does not show an approved Earnalism-owned payment receipt email flow. This plan compares safe options without enabling email sending in this task.

## Option A: Razorpay Automated Receipt

Use Razorpay dashboard receipt settings if available and appropriate.

Pros:

- Fastest MVP if already supported in owner dashboard.
- Keeps payment receipt tied to provider-confirmed payment state.
- No new email provider integration in Earnalism code.

Risks / checks:

- Dashboard-only; must be verified by owner.
- Field wording and branding may be limited.
- Tax/GST invoice claims must not be made unless dashboard/accounting setup proves them.

Recommended MVP status: `PREFERRED_FIRST_CHECK`

## Option B: Razorpay Invoice API

Generate formal Razorpay invoices through their API if business/tax requirements demand it.

Pros:

- More structured invoice workflow.
- May support tax/accounting needs better than a simple receipt.

Risks / checks:

- Requires explicit legal/accounting review.
- Requires API implementation, idempotency, error handling, and dashboard verification.
- Must avoid committing any invoice/customer/payment identifiers.

Recommended MVP status: `OWNER_ACCOUNTING_REVIEW_REQUIRED`

## Option C: Earnalism-Owned Transactional Email Receipt

Send an Earnalism-branded receipt email after wallet credit is confirmed.

Pros:

- Full control over premium brand tone.
- Can link account/wallet support guidance.
- Can avoid tax-invoice language until compliant.

Risks / checks:

- Requires approved transactional email provider and env configuration.
- Must never email before payment and wallet credit are confirmed.
- Must avoid exposing full payment IDs or customer data in logs.
- Requires bounce/failure monitoring and support process.

Recommended MVP status: `SECOND_PHASE_AFTER_RAZORPAY_RECEIPT_CHECK`

## Safest MVP Recommendation

1. Owner verifies Razorpay automated receipt setting for live Checkout orders.
2. Keep Earnalism account/wallet history as in-app transaction visibility, not a tax invoice.
3. Add an Earnalism-owned receipt email only after selecting an approved email provider and writing tests for redaction, idempotency, and failure handling.

No email sending is implemented by this plan.
