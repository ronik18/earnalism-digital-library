# Final Live Payment Switch Runbook

Status: `READING_ONLY_LIVE_PAYMENT_SWITCH_CONDITIONAL`

Date: 2026-06-26

## Scope

This runbook covers the final owner-controlled switch for Dracula reading-only revenue. It does not approve any audiobook release, public audio route, Listen Now CTA, AudioObject metadata, broad catalog launch, or production audiobook status.

## Product Truth

- Launch product: Dracula reading only.
- Free access: Dracula Chapter 1 preview.
- Paid access: reading-time wallet/pass model.
- Audiobook status: `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Production audio status: `PRODUCTION_BLOCKED`.
- Kshudhita and other books: pipeline-only, no public payment CTA.

## Before Live Switch

- Confirm owner approves the live payment window.
- Confirm live Razorpay account verification is complete.
- Confirm live key ID is configured only in the production environment.
- Confirm live key secret is configured only in the production environment.
- Confirm live webhook secret is configured only in the production environment.
- Confirm no key, secret, webhook secret, payment identifier, customer identifier, card data, UPI data, bank data, or invoice is committed.
- Confirm server-owned pack prices still match the approved reading-time packs.
- Confirm support/refund owner is online.
- Confirm rollback owner is online.
- Confirm `npm run launch:payment-smoke:test-mode` passes before touching live mode.
- Confirm public audio checks pass before touching live mode.

## Owner Low-Value Live Drill

The owner has reported completing one low-value live checkout drill through Razorpay. This runbook records that as launch evidence only. It does not store payment IDs, customer data, bank data, card data, UPI data, account screenshots, invoices, or secrets.

The drill is not enough for final GO until the remaining evidence is recorded:

- Wallet credit confirmed.
- Webhook delivery confirmed.
- Duplicate replay prevention confirmed.
- Refund/support readiness confirmed.
- Rollback readiness confirmed.

## Live Switch Procedure

1. Put the site in the owner-approved live payment observation window.
2. Confirm `RAZORPAY_MODE=live` only in the intended production environment.
3. Confirm the production environment has live key ID, live key secret, and live webhook secret.
4. Run a low-value owner checkout.
5. Confirm the account/wallet view shows the exact reading-time credit once.
6. Confirm backend top-up intent status is credited once.
7. Confirm webhook audit row exists and does not double-credit the wallet.
8. Replay or reconcile only through documented internal/admin procedures.
9. Record only redacted evidence in repository docs.
10. Keep public audio blocked.

## Rollback Procedure

- Switch Razorpay back to test mode or remove live payment environment variables if checkout behavior is wrong.
- Hide pricing CTAs only if checkout health is compromised.
- Keep Dracula reading route available only if reader integrity remains healthy.
- Keep audiobook release blocked.
- Re-run payment smoke, controlled publication precheck, catalog audit, audio audit, audiobook release gate, and reading-only regression checks.
- Record incident notes without secrets or personal payment data.

## Final Recommendation

Recommendation: `CONDITIONAL_GO_AFTER_PAYMENT_EVIDENCE`

The owner live drill is useful evidence, but final GO remains blocked until wallet credit, webhook, duplicate replay, refund/support, and rollback evidence are complete.
