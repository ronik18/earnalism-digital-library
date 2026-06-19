# Pricing UX Hardening Report

## Scope

This PR hardens the visible reading-time pricing UX for the controlled Dracula launch. It does not change pack prices, payment backend mechanics, Razorpay calls, wallet crediting, or live payment behavior.

## Pack Name Changes

| Pack | Before | After |
| --- | --- | --- |
| 30 minutes | Afternoon Pause | The First Chapter |
| 1 hour | An Evening In | The Quiet Hour |
| 3 hours | Long Weekend | The Deep Reading Pass |
| 10 hours | The Reader's Reserve | The Reader’s Reserve |

## Updated Pack Notes

| Pack | New note |
| --- | --- |
| The First Chapter | Continue after the free preview, one careful sitting at a time. |
| The Quiet Hour | Best first choice — enough time to settle into Dracula. |
| The Deep Reading Pass | A longer weekend return to the castle and the count. |
| The Reader’s Reserve | Ten quiet hours kept for Dracula and the classics coming next. |

## Value Rationale

- The pack names now feel like literary access choices, not commodity minute bundles.
- The 1-hour pack is framed as the safest first paid step after Dracula Chapter 1.
- The 10-hour pack is framed as a value reserve for Dracula plus upcoming classics without implying a subscription.
- Reading time is explained as wallet-style access: no subscription, no autorenewal, and no pressure to finish in a billing cycle.
- Trust copy near checkout clarifies Razorpay security, wallet crediting after payment confirmation, and support/refund contact.

## Conversion Hypothesis

Dracula-first language should reduce decision friction by giving each pack a narrative role:

- Free Chapter 1 builds confidence before payment.
- The Quiet Hour gives first-time readers a low-pressure recommended next step.
- The Reader’s Reserve gives high-intent readers a clear value anchor without changing the price.
- Clear “reading time, not subscription” copy should reduce hesitation from users wary of recurring billing.

## Analytics Added

- `pricing_pack_view`
- `pricing_pack_cta_click`
- `reading_time_explainer_view`
- `dracula_continue_from_pricing_click`

These remain regular local/frontend funnel events and do not call payment providers.

## Payment Safety

- No pack prices were changed.
- No Razorpay checkout behavior was changed.
- No live payment was run.
- Existing dry-run/static payment smoke remains the required safety gate.
