# Revenue Launch Checklist

## Current Payment Evidence Status

- Live low-value owner checkout drill: `COMPLETED_OWNER_REPORTED`.
- Payment success: `YES`.
- Wallet credited: `YES_OWNER_VERIFIED`.
- Webhook received: `YES_OWNER_VERIFIED`.
- Duplicate credit prevention: `VERIFIED`.
- Refund/support readiness: `READY`.
- Rollback readiness: `READY`.
- Final live payment GO: `GO_READING_ONLY_PRODUCTION_DEPLOY_READY`.
- Evidence file: `LIVE_RAZORPAY_CHECKOUT_DRILL_REPORT.md`.
- Final evidence file: `LIVE_PAYMENT_FINAL_EVIDENCE_REPORT.md`.

## Remaining Launch Blockers

- No payment evidence blockers remain for Dracula reading-only production deploy readiness.
- Audiobook public release remains blocked.
- Production audio remains blocked.
- Deployment itself is not performed by this checklist.
- Reading-only production deploy status is `GO_READING_ONLY_PRODUCTION_DEPLOY_READY`.

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
- [x] Confirm support/refund owner is online during the first live checkout window.
- [x] Run a low-value live checkout only after owner approval.
- [x] Confirm wallet credit, ledger row, webhook audit row, and user-facing account copy.
- [x] Confirm duplicate replay prevention with no double wallet credit.
- [x] Record only redacted live checkout evidence.
- [ ] Keep audiobook sales disabled.

## Refund And Support Checklist

- [x] Confirm support email/contact route is monitored.
- [x] Confirm refund triage owner and response SLA.
- [x] Confirm refund review flow does not double-credit wallet time.
- [x] Confirm failed payment support script.
- [x] Confirm abandoned checkout support script.
- [x] Confirm privacy-safe payment audit notes.
- [x] Confirm no card or sensitive payment data is stored by The Earnalism.

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

- [x] Confirm launch message says Dracula reading only.
- [x] Confirm launch message says Chapter 1 is free.
- [x] Confirm launch message explains reading time.
- [x] Confirm launch message does not mention a public audiobook.
- [x] Confirm launch message does not make WCAG, blind-user-tested, full catalog, or buy/own-forever claims.
- [x] Confirm Bengali Gothic/Kshudhita remains pipeline-only.
- [x] Confirm rollback owner and observation window.
- [x] Confirm `LIVE_PAYMENT_FINAL_EVIDENCE_REPORT.md` is fully complete with only safe redacted references.

## Final Deploy Checklist

- Confirm production environment has live Razorpay variables configured outside the repository.
- Confirm no ElevenLabs generation variables are enabled in production.
- Confirm no public audio files exist under `frontend/public` or `frontend/build`.
- Confirm post-deploy canaries for Home, Dracula book page, reader preview, pricing, login/signup, account/wallet, payment return, and wallet balance.
- Confirm rollback owner is present during the deploy window.
- Re-run the launch validation bundle immediately before deploy.
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
- No automatic deploy from this checklist.
- No audiobook public release during Dracula reading-only launch.
