# Launch Now Reading-Only Decision

## Decision

Recommendation: `GO_READING_ONLY_LAUNCH_PREP`.

The Earnalism should begin revenue-oriented production launch with the Dracula reading product only. Do not wait for public audiobook release. The full Dracula Chapter 1 audiobook remains internal until highlighted-text player testing, sync QA, accessibility QA, and release gates pass.

This decision does not deploy, publish new books, switch live payment keys, expose audio, or approve production audio.

## Launch Scope

- Product scope: Dracula core reading product only.
- Public work: `Dracula` by Bram Stoker.
- Free entry point: Chapter 1 free preview.
- Paid path: reading-time wallet/pass model for continuing Dracula after the free preview.
- Publication approval: `GO_DRACULA_CORE_READING_ONLY`.
- Revenue objective: validate paid reading-time conversion without waiting for audiobook readiness.

## What Is Live

| Surface | Reading-only launch status | Notes |
| --- | --- | --- |
| Home | Ready for Dracula-first reading launch | Public copy says The Earnalism begins with Dracula. |
| Dracula book page | Ready | Chapter 1 free and reading-time continuation are the public path. |
| Reader preview | Ready | Dracula Chapter 1 is the free preview path. |
| Pricing | Ready for reading-time packs | Copy explains wallet time, not ownership or subscription. |
| Login/signup | Ready for continuation flow | Sign-in supports returning to reading-time purchase/account flow. |
| Account/wallet | Ready for wallet visibility | Wallet copy supports reading-time balance review. |
| Library/continue reading | Ready for Dracula-only public release | Unapproved books stay Coming Soon / Notify Me. |
| SEO/social previews | Ready for Dracula-first reading positioning | Must remain Dracula-first and reading-only. |
| Payment smoke | Ready in test mode | Razorpay live switch still requires owner checklist completion. |
| Controlled publication precheck | Ready | Current approval artifact is Dracula core reading only. |

## What Is Not Live

- Public audiobook release is not live.
- Public audio URLs are not live.
- Listen Now CTA is not live.
- AudioObject metadata is not live.
- Kshudhita Pashan is not public, readable, previewable, or listenable.
- Broad catalog access is not live.
- WCAG, blind-user-tested, or fully accessible audiobook claims are not live.
- Buy/own-forever book claims are not live.
- Full study guide, visual edition, paid ads, email sends, and social publishing are not approved by this decision.

## Revenue Path

1. Visitor lands on Home or Dracula book page.
2. Visitor reads Dracula Chapter 1 free.
3. Visitor chooses to continue with reading time.
4. Visitor signs in or signs up.
5. Visitor purchases a reading-time pack through the configured Razorpay flow.
6. Reading time is credited to the wallet after verified payment.
7. Visitor continues Dracula with wallet reading time.

The revenue path sells time to continue reading. It does not sell an audiobook, book ownership, permanent access, subscription, autorenewal, or a broad catalog.

## Payment And Wallet Readiness

- Payment model: Razorpay-backed reading-time top-up.
- Current confidence report: `PAYMENT_REVENUE_10X_CONFIDENCE_REPORT.md`.
- Current live launch posture: `HOLD_FINAL_GO_PENDING_PAYMENT_EVIDENCE`.
- Payment smoke evidence: `launch:payment-smoke:test-mode`.
- Wallet behavior: reading time is credited after confirmation and used only while reading.
- Live drill evidence: `LIVE_RAZORPAY_CHECKOUT_DRILL_REPORT.md`.
- Final payment evidence report: `LIVE_PAYMENT_FINAL_EVIDENCE_REPORT.md`.
- Live drill result: owner reported one low-value Razorpay live checkout with payment success `YES`.
- Remaining evidence before final deploy GO: wallet credit, webhook receipt, duplicate replay prevention, refund/support readiness, and rollback readiness.
- Live switch requirement: owner must complete the go/no-go checklist in `LIVE_PAYMENT_GO_NO_GO_CHECKLIST.md`.

Do not change live payment settings automatically in this launch prep.

## Audiobook Blocked Status

- Internal Dracula Chapter 1 audio exists.
- Imported chunks: `27`.
- Full chapter audio hash: `5cea977f3fcffca744f9fa71a8da249943462a9096580d6522b4d80c509bc2c0`.
- Owner listening QA score: `9.4/10`.
- Listening QA decision: `READY_FOR_INTERNAL_PLAYER_TEST`.
- Sync status: `HOLD_SYNC_QA_REQUIRED`.
- Public audio release: `PUBLIC_AUDIO_RELEASE_BLOCKED`.
- Production audio status: `PRODUCTION_BLOCKED`.
- Public audio allowed: `false`.
- Listen Now CTA allowed: `false`.
- AudioObject metadata allowed: `false`.

Audiobook revenue remains blocked until player QA, sync QA, accessibility QA, legal/release gates, and owner approval pass.

## Public Copy Confirmation

- Dracula only: confirmed.
- Chapter 1 free: confirmed.
- Reading-time/pass model clear: confirmed.
- No audiobook live claim: confirmed.
- No Kshudhita public claim: confirmed.
- No broad catalog claim: confirmed.
- No WCAG/blind-user-tested claim: confirmed.
- No buy/own-forever claim: confirmed.

## Final Owner Checklist

- [ ] Confirm production domain and API URLs are correct.
- [ ] Confirm Dracula book page loads and Chapter 1 preview opens.
- [ ] Confirm pricing packs display correct labels and INR amounts.
- [ ] Run Razorpay test-mode checkout with a throwaway user.
- [ ] Confirm wallet credit after successful test-mode payment.
- [ ] Confirm failed/cancelled test payment does not credit wallet.
- [ ] Confirm support/refund inbox and response owner.
- [ ] Confirm rollback owner is available during launch window.
- [ ] Confirm no public audio files exist under `frontend/public` or `frontend/build`.
- [ ] Confirm no public audiobook claim, Listen Now CTA, or AudioObject metadata exists.
- [ ] Keep audiobook public release blocked.

## Go/No-Go Recommendation

| Area | Decision |
| --- | --- |
| Dracula reading-only launch | `HOLD_FINAL_GO_PENDING_PAYMENT_EVIDENCE` |
| Revenue path | `GO_TEST_MODE_VALIDATED_READING_TIME_ONLY` |
| Public audiobook | `NO_GO_PUBLIC_AUDIO_RELEASE_BLOCKED` |
| Production audio | `NO_GO_PRODUCTION_BLOCKED` |
| Kshudhita Pashan | `NO_GO_PIPELINE_ONLY` |
| Broad catalog launch | `NO_GO_DRACULA_ONLY` |

Proceed with Dracula reading revenue launch only after wallet credit, webhook receipt, duplicate replay, refund/support, and rollback evidence are complete. Keep audiobook release blocked.
