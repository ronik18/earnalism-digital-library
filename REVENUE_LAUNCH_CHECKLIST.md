# Revenue Launch Checklist

## Current Payment Evidence Status

- Live low-value owner checkout drill: `COMPLETED_OWNER_REPORTED`.
- Payment success: `YES`.
- Wallet credited: `NOT_VERIFIED`.
- Webhook received: `NOT_VERIFIED`.
- Duplicate credit prevention: `NOT_VERIFIED`.
- Refund/support readiness: `HOLD`.
- Rollback readiness: `HOLD`.
- Final live payment GO: `HOLD_FINAL_GO_PENDING_PAYMENT_EVIDENCE`.
- Evidence file: `LIVE_RAZORPAY_CHECKOUT_DRILL_REPORT.md`.
- Final evidence file: `LIVE_PAYMENT_FINAL_EVIDENCE_REPORT.md`.

## Remaining Launch Blockers

- Wallet credit evidence is not yet owner-verified in safe redacted form.
- Live webhook receipt is not yet owner-verified in safe redacted form.
- Duplicate replay prevention is not yet live-evidence verified.
- Refund/support readiness remains `HOLD`.
- Rollback readiness remains `HOLD`.
- Reading-only production deploy status remains `HOLD_FINAL_GO_PENDING_PAYMENT_EVIDENCE`.

## Razorpay Test-Mode Checks

- [ ] Confirm `RAZORPAY_MODE=test` in the launch test environment.
- [ ] Confirm test key ID is present only in the intended environment.
- [ ] Confirm no secret key is committed or printed.
- [ ] Run `npm run launch:payment-smoke:test-mode`.
- [ ] Complete one owner-approved test-mode checkout with a throwaway user.
- [ ] Confirm successful payment returns to account/wallet.
- [ ] Confirm reading time is credited exactly once.
- [ ] Confirm webhook delivery credits no duplicate wallet time.
- [ ] Confirm failed/cancelled test payment creates no wallet credit.
- [ ] Confirm expired payment intent cannot credit wallet.
- [ ] Confirm admin reconcile remains idempotent.

## Live Payment Switch Checklist

- [ ] Owner approves live switch timing.
- [ ] Owner confirms Razorpay live account is fully verified.
- [ ] Set live Razorpay key ID and secret only in the production environment.
- [ ] Set live webhook secret only in the production environment.
- [ ] Confirm webhook URL is registered in Razorpay live dashboard.
- [ ] Confirm prices match approved server-owned packs.
- [ ] Confirm support/refund owner is online during the first live checkout window.
- [x] Run a low-value live checkout only after owner approval.
- [ ] Confirm wallet credit, ledger row, webhook audit row, and user-facing account copy.
- [ ] Confirm duplicate replay prevention with no double wallet credit.
- [ ] Record only redacted live checkout evidence.
- [ ] Keep audiobook sales disabled.

## Refund And Support Checklist

- [ ] Confirm support email/contact route is monitored.
- [ ] Confirm refund triage owner and response SLA.
- [ ] Confirm refund review flow does not double-credit wallet time.
- [ ] Confirm failed payment support script.
- [ ] Confirm abandoned checkout support script.
- [ ] Confirm privacy-safe payment audit notes.
- [ ] Confirm no card or sensitive payment data is stored by The Earnalism.

## Monitoring Checklist

- [ ] Monitor payment success and failure events.
- [ ] Monitor wallet credit latency.
- [ ] Monitor duplicate webhook event handling.
- [ ] Monitor reader locked/unlocked states.
- [ ] Monitor 404/410 removed-route behavior.
- [ ] Monitor Dracula book page, reader preview, pricing, login, signup, and account routes.
- [ ] Monitor frontend/public and frontend/build for accidental audio files.
- [ ] Monitor public copy for audiobook, accessibility, broad catalog, and ownership overclaims.

## Founder Launch Checklist

- [ ] Confirm launch message says Dracula reading only.
- [ ] Confirm launch message says Chapter 1 is free.
- [ ] Confirm launch message explains reading time.
- [ ] Confirm launch message does not mention a public audiobook.
- [ ] Confirm launch message does not make WCAG, blind-user-tested, full catalog, or buy/own-forever claims.
- [ ] Confirm Bengali Gothic/Kshudhita remains pipeline-only.
- [ ] Confirm rollback owner and observation window.
- [ ] Confirm `LIVE_PAYMENT_FINAL_EVIDENCE_REPORT.md` is fully complete with only safe redacted references.

## Remaining Owner Actions

- Verify the owner live checkout credited reading time exactly once.
- Verify the live webhook was received and signature-processed.
- Verify duplicate replay does not double-credit wallet time.
- Confirm refund/support owner and response window.
- Confirm rollback owner and switch-back procedure.
- Re-run the launch validation bundle before deploy.
- Keep audiobook public release blocked during reading-only launch.

## Rollback Checklist

- [ ] Disable live payment keys or switch back to test mode if payment behavior is wrong.
- [ ] Hide pricing CTA if checkout is unhealthy.
- [ ] Keep Dracula reading route available only if reader integrity remains healthy.
- [ ] Keep public audio blocked.
- [ ] Remove any accidental public audio file from `frontend/public` or `frontend/build`.
- [ ] Re-run controlled publication precheck and payment smoke after rollback.
- [ ] Record incident notes, user impact, and refund/support follow-up.

## Non-Negotiables

- No public audio.
- No Listen Now CTA.
- No AudioObject metadata.
- No Kshudhita public reader or audio access.
- No broad live catalog claim.
- No live payment switch without owner approval.
- No automatic deploy from this checklist.
