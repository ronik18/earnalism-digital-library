# ElevenLabs Dracula Full Chapter 1 Cost-Control Plan

This plan is for one internal-only full Chapter 1 generation pass after the sample received human listening QA at 9.5/10. It does not approve public audio, production audio, full-book generation, or automated provider calls.

## Limits

- Generate manually in chunks from `chunk_manifest.json`.
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

1. Place manually downloaded chunk audio only under `internal/audiobook_lab/dracula/en/chapter-1-elevenlabs-full/imported_audio/`.
2. Run `npm run elevenlabs:full-chapter-import`.
3. Confirm `audio_status=INTERNAL_FULL_CHAPTER_ONLY`.
4. Confirm `public_audio_allowed=false`.
5. Complete full chapter listening QA.
6. Complete sentence-level sync QA.
7. Keep public release blocked until separate owner/legal/accessibility approval.

## Safety

- No ElevenLabs API call from this repository.
- No automatic generation.
- No public audio URL.
- No public player.
- No Listen Now CTA.
- No AudioObject metadata.
- No file under `frontend/public` or `frontend/build`.
