# Daily Blockers Snapshot

This is a committed sample snapshot from the 2026-06-20 IST owner audit. Recurring daily reports should be generated locally with `npm run owner:daily-growth-audit`, which writes dated artifacts under `output/daily/YYYY-MM-DD/`.

Date: 2026-06-20 IST

Today's overall score: 7.0 / 10

Recommendation: HOLD for growth expansion; GO for keeping Dracula live.

The score is capped at 7.0 until this source hardening is merged and deployed. This branch removes broad homepage catalog copy, makes the library state Dracula-only, and gates live reading CTAs to Dracula only. A separate backend/catalog governance pass is still required because production/public API records can include non-Dracula books.

## Top 3 Wins

- Production health, route canary, and production parity passed.
- Dracula reader manifest is healthy with 27 chapters and audio disabled.
- Payment smoke passed in test mode with idempotency/wallet checks detected.

## Top 3 Risks

- Public catalog contains 104 non-Dracula books from `/api/books`; most sampled rows expose no rights metadata.
- Current SEO audit is `BLOCKED_FOR_BOOK_SEO` because book detail metadata is client-rendered.
- Post-deploy verification must confirm the Dracula-first homepage/library source is live before growth expansion.

## Exact Fixes Needed

- Merge and deploy this small CTA safety branch.
- Add prerender/SSR/static-snapshot metadata for Dracula and priority public book pages.
- Follow up with a backend/catalog governance pass so non-approved books are draft/private or explicitly rights-approved.

## Rollback

No production rollback is needed today.

If the CTA safety branch causes unexpected frontend behavior, revert that branch. It is frontend-only and does not mutate backend data.

## New PR Recommended

Yes. This branch is the recommended small PR:

- Gate public reader CTAs to Dracula only.
- Add Dracula-specific CTA copy and analytics.
- Add daily reports documenting the HOLD reasons.
