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

`backend/catalog_truth.py` mirrors the controlled launch truth for public APIs:

- `is_live_approved_book(book)`
- `is_pipeline_candidate(book)`
- `can_expose_reader(book)`
- `can_expose_preview(book)`
- `can_expose_audio(book)`
- `public_book_projection(book)`

## Expected Behavior

| Item | Reader CTA | Preview CTA | Audio CTA | Fallback CTA |
| --- | --- | --- | --- | --- |
| Dracula approved core reader | Allowed | Allowed | Hidden until audio QA passes | Reading pass |
| Kshudhita Pashan pipeline | Blocked | Blocked | Blocked | Notify Me / Reading Circle |
| Other unapproved books | Blocked | Blocked | Blocked | Coming Soon / Notify Me |
| Tier B/Tier C unsafe items | Blocked | Blocked | Blocked | Quarantine or no public CTA |

## Validation Coverage

- Home source now uses the exact hero eyebrow `The Earnalism Digital Library`.
- Home source now exposes the exact headline label `Begin with Dracula.`
- Home source no longer contains the broad catalog copy `A quieter bookstore for readers who linger`, `Preview every book before you pay`, or `Discover thoughtful books across`.
- Library source explicitly states `Live Controlled Release: Dracula only` and `Coming Through the Rights-Safe Pipeline: future titles only`.
- Static UX regression checks Dracula-first homepage copy.
- Static UX regression checks Library live shelf says Dracula only.
- Static UX regression checks unapproved pipeline blocks do not contain Start Reading, Read Preview, Listen Now, or Full Audiobook.
- Static UX regression checks old pricing names are absent from user-facing rendered sources.
- Launch readiness audit accepts current Dracula-first reading pass CTAs without broad catalog assumptions.
- Backend catalog truth audit reports Dracula as the only live approved book and audio disabled.

## Safety Confirmation

- No new book was published.
- No audiobook was enabled.
- No payment provider was called.
- No production data was mutated.
- No provider API was called.
- Public backend audiobook routes return 404 while audio remains disabled.
