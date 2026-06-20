# Daily Owner Growth Report Snapshot

This is a committed sample snapshot from the 2026-06-20 IST owner audit. Recurring daily reports should be generated locally with `npm run owner:daily-growth-audit`, which writes dated artifacts under `output/daily/YYYY-MM-DD/`.

Date: 2026-06-20 IST

Today's score: 7.0 / 10

Recommendation: HOLD for new growth pushes; GO for keeping Dracula live.

## Executive Summary

Production health is good, Dracula is reachable, the reader manifest is healthy, removed routes are gone, and payment smoke passes in test mode. This PR applies the smallest safe frontend source fix by making the homepage Dracula-first, limiting live reading CTAs to Dracula, and changing other books to Coming Soon / Notify Me. The remaining blocker is backend/catalog governance: production can still expose non-Dracula published book records through the public API until a separate data/catalog pass quarantines or rights-approves them.

## Top 3 Wins

- Production canary, production parity, and removed-route checks passed.
- Dracula has 27 reader-manifest chapters, Chapter 1 is unlocked, and audio is disabled with zero assets.
- Payment smoke passed in dry-run/test mode without live-money charges.

## Top 3 Risks

- Current production score is capped at 7.0 until this source hardening is merged, deployed, and the backend catalog governance pass closes non-Dracula public records.
- SEO readiness remains HOLD because book detail metadata is client-rendered in CRA.
- Source-level CTA safety depends on deployment; do not expand campaigns until post-deploy canary confirms the Dracula-first homepage/library are live.

## Exact Fixes Needed

- Merge and deploy this CTA safety branch.
- Create a follow-up SEO PR for Dracula/prioritized book static snapshots or SSR/prerender metadata.
- Run a backend catalog governance pass for the 104 non-Dracula public books.

## Launch State

- Dracula stays live: Yes.
- Dracula audio stays disabled: Yes.
- New books published today: No.
- Audiobook enabled today: No.
- Emails/social posts sent today: No.
- Paid provider APIs called today: No.
- Rollback needed today: No.

## Owner Decision

Keep Dracula live. Do not expand paid growth, email, social, or Bengali Gothic publication until CTA safety and SEO warnings are addressed.
