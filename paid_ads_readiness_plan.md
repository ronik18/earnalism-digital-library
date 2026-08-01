# Paid Ads Readiness Plan

Generated: 2026-07-07

## Launch Rule

Do not launch paid ads until at least 4-6 audiobooks are live, unless running a very small validation test. Paid tests may promote only live audiobooks or reader-first shelves. No paid ad may claim unapproved audio availability.

## Eligible Paid Test Surfaces

- `book-2b9853ec52` Listen test: eligible now.
- `a-ghost-story` Listen test: eligible only after final production browser/manifest route confirmation for paid traffic.
- Bengali reader-first shelf: eligible as a reader campaign, no audio promise.
- English short classics shelf: eligible as reader-first discovery, no audio promise except approved titles.

## Meta Ads Concepts

1. Bengali nostalgia: “Return to Bengali classics in a calmer reading room.”
2. Approved Bengali audio: “দুই বিঘা জমি, now with quality-gated narration.”
3. English short classic: “A Ghost Story by Mark Twain, ready for one sitting.”
4. Reader-first classics: “Read public-domain classics without noisy interfaces.”

## YouTube Shorts Concepts

1. 15s approved audio teaser for দুই বিঘা জমি.
2. 15s approved audio teaser for A Ghost Story after route check.
3. Quality-gate explainer: why Earnalism does not publish every generated narration.
4. Cover montage for reader-first classics.

## Google Search Keyword Groups

- Bengali classics online.
- দুই বিঘা জমি audiobook.
- Tagore Bengali stories.
- Mark Twain A Ghost Story audiobook.
- Short classic audiobooks.
- Public domain classics online.

## Budget Test Plan

- Phase 0: no spend; verify events and landing shelves.
- Phase 1: $5-$10/day for 3 days on one live audiobook and one reader-first shelf.
- Phase 2: continue only if click-to-reader-start or listen-start is measurable and no release-truth errors appear.

## Stop-Loss Criteria

- Any unapproved audio CTA appears.
- Any stale/404 audio route appears in paid path.
- Listen-start event fires for a non-approved title.
- CPC exceeds target without reader_start or listen_start events.
- Negative trust feedback indicates audio claims are unclear.

## Retargeting Idea

Retarget readers who viewed a book detail page but did not start reading. Do not retarget “listen” unless the title has approved audio and `listen_start` is valid.
