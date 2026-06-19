# Pricing UX Hardening Report

## Scope

This PR hardens the visible reading-time pricing UX for the controlled Dracula launch. It does not change pack IDs, pack prices, paise amounts, payment backend mechanics, Razorpay behavior, wallet crediting, or publication behavior.

## Final Pack Names

The pricing UX uses the curly apostrophe form consistently for `The Reader’s Reserve` across backend labels and user-facing frontend copy.

| Pack ID | Minutes | Price | Final label |
| --- | ---: | ---: | --- |
| `30m` | 30 | ₹49 | The First Chapter |
| `1h` | 60 | ₹89 | The Quiet Hour |
| `3h` | 180 | ₹239 | The Deep Reading Pass |
| `10h` | 600 | ₹499 | The Reader’s Reserve |

## Before / After Names

| Pack | Before | After |
| --- | --- | --- |
| 30 minutes | Afternoon Pause | The First Chapter |
| 1 hour | An Evening In | The Quiet Hour |
| 3 hours | Long Weekend | The Deep Reading Pass |
| 10 hours | The Reader's Reserve | The Reader’s Reserve |

## Final User-Facing Copy

| Surface | Final copy |
| --- | --- |
| Pricing headline | Choose your reading time. Return whenever the book calls. |
| Dracula subcopy | Start with Chapter 1 free. When you are ready to continue Dracula, add reading time. Your time is used only while you read. |
| Why reading time | Earnalism is a digital reading room. You buy quiet reading time, not a noisy subscription. There is no autorenewal and no pressure to finish before a billing cycle. |
| Payment trust | Secure payment by Razorpay. No subscription or autorenewal. Reading time is credited to your wallet after confirmation. For support or refund questions, contact sales@reoenterprise.org. |
| Micro-story intro | continue with The First Chapter — ₹49 |
| Micro-story unlock | unlock The First Chapter for ₹49 |

## Pack Notes

| Pack | Note |
| --- | --- |
| The First Chapter | Continue after the free preview, one careful sitting at a time. |
| The Quiet Hour | Best first choice — enough time to settle into Dracula. |
| The Deep Reading Pass | A longer weekend return to the castle and the count. |
| The Reader’s Reserve | Ten quiet hours kept for Dracula and the classics coming next. |

## Badge Strategy

- The Quiet Hour is marked `Best first choice`.
- The Reader’s Reserve is marked `Best value`.

## Event Semantics

The pricing page records render-based signals with render-based names:

- `pricing_pack_rendered`: emitted after the pack catalogue is fetched and rendered into frontend state.
- `reading_time_explainer_rendered`: emitted once when the explainer section is rendered on the pricing page.
- `pricing_pack_cta_click`: emitted only when a user clicks a pack CTA.
- `dracula_continue_from_pricing_click`: emitted only when the Dracula continuation CTA is clicked.

The previous names `pricing_pack_view` and `reading_time_explainer_view` were intentionally replaced because they implied viewport-based visibility tracking.

## Rendered Smoke Summary

See `PRICING_RENDERED_SMOKE_REPORT.md`.

The smoke artifact confirms:

- all four packs render;
- prices remain ₹49, ₹89, ₹239, and ₹499;
- recommended and best-value badges render;
- Dracula continuation copy and CTA render;
- the reading-time explainer renders;
- Razorpay trust copy renders;
- old visible pack names do not remain in backend/frontend rendered source;
- no payment provider was called;
- no live payment was run.

## Conversion Hypothesis

Dracula-first language should reduce decision friction by giving each pack a narrative role:

- free Chapter 1 builds confidence before payment;
- The Quiet Hour gives first-time readers a low-pressure recommended next step;
- The Reader’s Reserve gives high-intent readers a clear value anchor without changing the price;
- clear reading-time-not-subscription copy should reduce hesitation from users wary of recurring billing.

## Validation Results

| Command | Result |
| --- | --- |
| `python3 scripts/check-hidden-unicode.py backend/server.py frontend/src/pages/Pricing.jsx frontend/src/lib/funnelAnalytics.js frontend/src/index.css frontend/src/components/Funnel/ReaderUpsellPrompt.jsx frontend/src/pages/MicroStoryLanding.jsx frontend/src/pages/Reader.jsx regression/modules/14-ux-conversion-static.test.js scripts/launch_readiness_audit.py PRICING_UX_HARDENING_REPORT.md PRICING_RENDERED_SMOKE_REPORT.md` | PASS |
| `python3 -m py_compile backend/server.py scripts/launch_readiness_audit.py` | PASS |
| `npm run regression -- modules/14-ux-conversion-static.test.js` | PASS, 12 tests |
| `npm run launch:payment-smoke` | PASS_TEST_MODE |
| `npm run controlled-publication:precheck` | PASS |
| `npm --prefix frontend run build` | PASS |

Local hidden Unicode and line-ending scan passed. If GitHub continues to show a warning, it should be investigated against the raw file display because the repository safety scanner passed for the full requested file list.

## Safety Confirmation

- No price changes.
- No pack ID changes.
- No `amount_paise` changes.
- No wallet-crediting changes.
- No live payment run.
- No Razorpay behavior change.
- No publication behavior change.
- No paid provider call.
