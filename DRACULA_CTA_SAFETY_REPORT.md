# Dracula CTA Safety Report

## Decision

Dracula is the only live controlled reading title. Every other book must render Coming Soon, Notify Me, or pipeline-only interest CTAs until publication gates pass.

## Gate Helpers

`frontend/src/lib/publicationSafety.js` exposes:

- `isControlledLiveReadingBook(book)`
- `canShowStartReading(book)`
- `canShowPreview(book)`
- `canShowAudioCTA(book)`
- `isPipelineOnlyBook(book)`

## Expected Behavior

| Item | Reader CTA | Preview CTA | Audio CTA | Fallback CTA |
| --- | --- | --- | --- | --- |
| Dracula approved core reader | Allowed | Allowed | Hidden until audio QA passes | Reading pass |
| Kshudhita Pashan pipeline | Blocked | Blocked | Blocked | Notify Me / Voice Sample Soon |
| Other unapproved books | Blocked | Blocked | Blocked | Coming Soon / Notify Me |
| Tier B/Tier C unsafe items | Blocked | Blocked | Blocked | Quarantine or no public CTA |

## Validation Coverage

- Static UX regression checks Dracula-first homepage copy.
- Static UX regression checks Library live shelf says Dracula only.
- Static UX regression checks unapproved pipeline blocks do not contain Start Reading, Read Preview, Listen Now, or Full Audiobook.
- Static UX regression checks old pricing names are absent from user-facing rendered sources.
- Launch readiness audit accepts current Dracula-first reading pass CTAs without broad catalog assumptions.

## Safety Confirmation

- No new book was published.
- No audiobook was enabled.
- No payment provider was called.
- No production data was mutated.
- No provider API was called.
