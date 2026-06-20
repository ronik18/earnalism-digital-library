# UX Fixes Required

Date: 2026-06-20

## Critical Fixes

None from the real-user browser UX journey.

## Non-Critical Polish

No blocking UX polish item was found in this PR's Playwright journey.

## Release/Advertising Hold

`npm run launch:seo-audit` still returns `BLOCKED_FOR_BOOK_SEO` because the CRA book detail page relies on client-side metadata after API load. This should be fixed with prerender/SSR/static snapshots for priority book pages before broad advertising.

## Decision Rule

- Any unapproved reading/listening CTA requires a fix before advertising.
- Any removed demo route returning a generic shell requires a fix before advertising.
- Any Dracula reader failure requires hold or rollback review.
- Any pricing old pack name or awkward pricing copy requires a fix before broader conversion campaigns.

## Current Status

`KEEP_DRACULA_LIVE_BUT_HOLD_ADS`
