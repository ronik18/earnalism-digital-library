# Earnalism Wallet Refund Pipeline

Admin location: `/admin` -> `users` -> select a reader -> `Billing discrepancy review`.

## What It Checks

The refund scanner reviews reader wallet consumption transactions and only flags high-confidence billing discrepancies:

- `stale_gap_overcharge`: one historical consume transaction charged more than one 30-second reader pulse. The scanner keeps one valid 30-second pulse and recommends refunding the excess.
- `duplicate_pulse`: two consume transactions from the same reading session landed within a few seconds. The scanner recommends refunding the duplicate pulse.

It also reports wallet-vs-ledger divergence, but does not automatically refund ambiguous divergence. Admins can still use the manual wallet adjustment box for cases that need human judgment.

## Approval Flow

1. Open the reader account in the admin `users` tab.
2. Click `Run refund review`.
3. Read each finding and keep only the candidates you agree with selected.
4. Click `Approve selected refund`.
5. Add an optional approval note.
6. The backend recomputes eligibility, prevents duplicate refunds with a deterministic candidate ID, credits the wallet, and writes a `refund_credit` ledger entry.

## Safety Rules

- No refund is applied during review.
- Every refund requires explicit admin approval.
- The same finding cannot be refunded twice.
- Refunds are recorded in both `wallet_refunds` and the wallet ledger.
- Reader-facing recent activity shows the credit as a normal wallet credit.

