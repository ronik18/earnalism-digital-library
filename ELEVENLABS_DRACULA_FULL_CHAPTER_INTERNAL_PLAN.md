# ElevenLabs Dracula Full Chapter 1 Internal Plan

Decision: `READY_FOR_FULL_CHAPTER_INTERNAL_ONLY`

This plan prepares a manual, chunked, internal-only full Chapter 1 generation/import workflow. It does not generate audio automatically, call the ElevenLabs API, publish audio, expose public audio, add a Listen Now CTA, add AudioObject metadata, change payment behavior, or approve production.

## Approval Basis

- Sample audio status: `INTERNAL_SAMPLE_ONLY`
- Sample sync status: `HOLD_SYNC_QA_REQUIRED`
- Human listening QA: `9.5/10` in every required dimension
- Approved next step: `READY_FOR_FULL_CHAPTER_INTERNAL_ONLY`
- Provider: `ElevenLabs`
- Voice: `Rachel`
- Voice ID: `21m00Tcm4TlvDq8ikWAM`

## Required Guardrails

- public_audio_release: `PUBLIC_AUDIO_RELEASE_BLOCKED`
- production_approved: false
- listen_now_cta_allowed: false
- audio_object_metadata_allowed: false
- full_book_generation_allowed: false
- payment_behavior_changed: false
- provider_api_called_by_repo: false
- automatic_generation_by_repo: false

## Internal Workflow Directory

- Workflow directory: `internal/audiobook_lab/dracula/en/chapter-1-elevenlabs-full/`
- Clean full-chapter narration text: `full_chapter_narration_text.txt`
- Sync/source draft with sentence IDs: `full_chapter_sync_source_with_ids.txt`
- Compatibility sync/source draft: `full_chapter_text.txt`
- Sentence map: `sentence_map.json`
- Chunk manifest with clean `narration_text`: `chunk_manifest.json`
- Generation brief: `elevenlabs_full_chapter_generation_brief.md`
- Pronunciation notes: `pronunciation_notes.md`
- Cost controls: `cost_control_plan.md`
- Import location: `imported_audio/`

Only `full_chapter_narration_text.txt` or an individual chunk's clean `narration_text` may be pasted into ElevenLabs. The sync/source files and sentence map preserve alignment evidence only.

## Chunking Plan

- Chunk count: `27`
- Sentence count: `220`
- Chunk IDs: stable `c001` through `c027`
- Sentence IDs: stable `s001` through `s220`
- Recommended chunk length: 45-120 seconds where text boundaries allow it
- Generation method: manual ElevenLabs UI/Studio chunk-by-chunk
- Text hash per chunk: required
- Settings hash per chunk: required
- Paragraph boundaries: preserved by chunk metadata; long paragraphs are split only at sentence boundaries when needed
- Non-narrated source separators are represented as pause metadata, not spoken text.

## Import Command

Validate narration text before any manual generation:

```bash
npm run elevenlabs:validate-narration-text
```

Run import only after the owner manually downloads all chunk audio files into the internal import directory:

```bash
npm run elevenlabs:full-chapter-import
```

Expected import state:

- audio_status: `INTERNAL_FULL_CHAPTER_ONLY`
- sync_status: `HOLD_SYNC_QA_REQUIRED`
- public_audio_allowed: false
- production_approved: false

## Explicit Non-Approvals

- No public release.
- No public audio route.
- No public player.
- No Listen Now CTA.
- No AudioObject metadata.
- No frontend/public audio.
- No frontend/build audio.
- No production approval.
- No full-book generation.
- No sentence IDs, source comments, markdown, or sync-source text in ElevenLabs generation input.
