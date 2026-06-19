# Pricing Rendered Smoke Report

## Scope

This is a committed static/rendered-source smoke artifact for the Dracula-first pricing UX. It confirms the intended UI contract without calling Razorpay, running live payments, changing prices, changing wallet logic, or publishing content.

## Pack Rendering

| Check | Status |
| --- | --- |
| The First Chapter renders | PASS |
| The First Chapter renders at ₹49 | PASS |
| The Quiet Hour renders | PASS |
| The Quiet Hour renders at ₹89 | PASS |
| The Quiet Hour has Best first choice badge | PASS |
| The Deep Reading Pass renders | PASS |
| The Deep Reading Pass renders at ₹239 | PASS |
| The Reader’s Reserve renders | PASS |
| The Reader’s Reserve renders at ₹499 | PASS |
| The Reader’s Reserve has Best value badge | PASS |

## Dracula Continuation

| Check | Status |
| --- | --- |
| Continue Dracula CTA renders | PASS |
| Dracula Chapter 1 free copy renders | PASS |
| Why reading time section renders | PASS |
| Razorpay trust copy renders | PASS |

## Negative Checks

| Check | Status |
| --- | --- |
| Afternoon Pause absent from backend/frontend rendered source | PASS |
| An Evening In absent from backend/frontend rendered source | PASS |
| Long Weekend absent from backend/frontend rendered source | PASS |
| Straight-apostrophe The Reader's Reserve absent from backend/frontend rendered source | PASS |
| Awkward phrase `₹49 The First Chapter` absent | PASS |
| Awkward phrase `unlock the ₹49` absent | PASS |

## Payment Safety

| Check | Status |
| --- | --- |
| Payment provider was not called | PASS |
| Live payment was not run | PASS |
| Pack IDs unchanged | PASS |
| `amount_paise` values unchanged | PASS |
| Wallet crediting unchanged | PASS |
| Razorpay behavior unchanged | PASS |
