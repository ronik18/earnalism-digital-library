# ElevenLabs Dracula Full Chapter 1 QA Scorecard

Decision: `PENDING_FULL_CHAPTER_IMPORT_AND_QA`

This scorecard is for the future full Chapter 1 internal import only. It does not approve public audio, production, Listen Now CTA, AudioObject metadata, payment changes, or full-book generation.

## Guardrails

- public_audio_release: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- production_approved: false
- listen_now_cta_allowed: false
- audio_object_metadata_allowed: false
- full_book_generation_allowed: false
- imported_audio_scope: `internal/audiobook_lab_only`

## Full Chapter QA Areas

| QA Area | Status | Notes |
| --- | --- | --- |
| Chunk completeness | HOLD | Confirm all `c001` through `c027` files import. |
| Voice consistency | HOLD | Confirm Rachel remains consistent across chunks. |
| Literary tone | HOLD | Maintain restrained premium narration. |
| Gothic restraint | HOLD | No horror-trailer delivery. |
| Pacing | HOLD | Check chapter-level pacing across chunk joins. |
| Pauses | HOLD | Confirm diary dates, quotations, and paragraph transitions. |
| Pronunciation | HOLD | Review all names and places in `pronunciation_notes.md`. |
| Emotional expression | HOLD | Expressive but controlled. |
| Noise/artifacts | HOLD | No clicks, clipping, gaps, or chunk-boundary artifacts. |
| Fatigue risk | HOLD | Confirm comfortable long-form listening. |
| Text fidelity | HOLD | Compare imported audio against `full_chapter_text.txt`. |
| Sync readiness | HOLD | Sentence timings remain placeholder-only until sync QA. |
| Accessibility listening readiness | HOLD | Requires separate accessibility listening review. |
| Overall score | HOLD | Score after full chapter import and listening QA. |
| Decision | HOLD | No public or production approval. |

## Required Blocks

- No Listen Now CTA.
- No AudioObject metadata.
- No public audio URL.
- No public player.
- No production approval.
- No full-book generation.
