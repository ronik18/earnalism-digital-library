# ElevenLabs Dracula Full Chapter 1 Cost-Control Plan

This plan is for one internal-only full Chapter 1 generation pass after the sample received human listening QA at 9.5/10. It does not approve public audio, production audio, full-book generation, or automated provider calls.

## Limits

- Generate manually in chunks from `chunk_manifest.json`.
- Paste only `chunks[].narration_text` into ElevenLabs for chunk generation.
- Chunk count: `27`.
- Recommended chunk length: 45-120 seconds where text boundaries allow it.
- Regenerate only failed chunks, not the full chapter.
- Do not generate Chapter 2 or any full-book audio.
- Do not use beta services, voice cloning, ElevenReader, or API automation.

## Required Evidence To Record Per Chunk

- `chunk_id`
- `audio_filename`
- `text_hash`
- `settings_hash`
- downloaded file hash after import
- owner reviewer
- QA issue notes if regeneration is required

## Import And QA Sequence

1. Run `npm run elevenlabs:validate-narration-text`.
2. Paste only `full_chapter_narration_text.txt` or a clean chunk `narration_text` into ElevenLabs.
3. Place manually downloaded chunk audio only under `internal/audiobook_lab/dracula/en/chapter-1-elevenlabs-full/imported_audio/`.
4. Run `npm run elevenlabs:full-chapter-import`.
5. Confirm `audio_status=INTERNAL_FULL_CHAPTER_ONLY`.
6. Confirm `public_audio_allowed=false`.
7. Complete full chapter listening QA.
8. Complete sentence-level sync QA.
9. Keep public release blocked until separate owner/legal/accessibility approval.

## Safety

- No ElevenLabs API call from this repository.
- No automatic generation.
- No public audio URL.
- No public player.
- No Listen Now CTA.
- No AudioObject metadata.
- No file under `frontend/public` or `frontend/build`.
- No sentence IDs, source comments, markdown, or sync-source text pasted into ElevenLabs.
