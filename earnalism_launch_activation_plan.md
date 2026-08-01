# Earnalism Launch Activation Plan

Generated: 2026-07-07

## Activation Rule

Season 1 marketing may create demand, trust, and waitlist momentum, but it must not outrun production truth. The public launch separates live audiobooks, coming-soon audiobook candidates, reader-first classics, and long-form SEO anchors.

No paid ads, paid audio generation, publishing, or production metadata mutation is part of this plan.

## Live Now

- `book-2b9853ec52` / `দুই বিঘা জমি`: production-verified Bengali audiobook. Use Listen CTA and section-following narration language.
- `a-ghost-story` / `A Ghost Story`: approved asset-backed English audiobook by local controlled-publication evidence. Use reader-route marketing and final route/browser confirmation before paid listen ads, because guessed public API audiobook/manifest paths returned 404.

## Coming To The Listening Room

These Tier 1 titles are marketable as selected production candidates only:

- `muchiram-gurer-jibanchorit`
- `book-d19e96859f`
- `book-f5d593e1f4`
- `book-ac5a71075e`
- `the-gift-of-the-magi`
- `the-tell-tale-heart`
- `the-open-window`
- `sredni-vashtar`
- `dsires-baby`

Allowed copy: coming soon, in production, selected for Earnalism's Founding Audiobook Lot, audio appears only after quality gates pass.

Prohibited copy: listen now, full audiobook live, available in audio, word-level sync, or AI-generated audiobook.

## Reader-First Classics

Reader-only titles should be framed as complete premium reader editions. Use Read CTA, cover-led posts, quote cards, and reading challenges. Do not use missing-audio language.

## Launch Sequence

1. Publish Season 1 positioning and internal release-truth matrix.
2. Use the 14-day asset pack for organic social posts.
3. Clip audio teasers only from verified live audio assets.
4. Route coming-soon titles to Read or Notify/Follow copy, never Listen.
5. Start paid ads only after 4-6 audiobooks are live, except a tiny validation test focused on live audiobook or reader-first shelf traffic.

## Production Safety

- No unapproved audio CTA.
- No stale audio URL.
- No A Ghost Story audio CTA from a default probe; use only approved asset-backed copy.
- Bengali paragraph/stanza sync must be described as section-following narration.
- Bengali reader-only titles remain audio-hidden.
- Third-party tracking remains off unless explicitly enabled by env/config.

## Next Exact Command

```bash
python3 -m json.tool public_launch_lot_release_truth_matrix.json >/dev/null && python3 -m json.tool launch_title_public_naming_map.json >/dev/null && git diff --check
```
