# ElevenLabs Dracula Full Chapter 1 Internal Generation Brief

This brief permits manual internal-only full Chapter 1 generation preparation. It does not call ElevenLabs, generate audio automatically, publish audio, approve production, add a public player, add a Listen Now CTA, or add AudioObject metadata.

## Required Provider Settings

- Provider: ElevenLabs
- Voice: Rachel
- Voice ID: `21m00Tcm4TlvDq8ikWAM`
- Model: stable non-beta TTS model only
- Manual workflow: ElevenLabs UI/Studio only
- API automation: forbidden
- Beta services: forbidden
- Voice cloning: forbidden
- ElevenReader: forbidden
- Public release: forbidden
- Production approval: blocked

## Source Files

- Clean full-chapter narration text: `full_chapter_narration_text.txt`
- Clean chunk narration text: `chunk_manifest.json` `chunks[].narration_text`
- Sync/source draft with sentence IDs: `full_chapter_sync_source_with_ids.txt`
- Sentence map: `sentence_map.json`
- Pronunciation notes: `pronunciation_notes.md`
- Cost controls: `cost_control_plan.md`

Only `full_chapter_narration_text.txt` or the clean `narration_text` field from an individual chunk may be pasted into ElevenLabs. `full_chapter_text.txt`, `full_chapter_sync_source_with_ids.txt`, and `sentence_map.json` preserve sync/source evidence and must not be used as generation text.

## Chunked Manual Generation Workflow

1. Confirm `ELEVENLABS_DRACULA_LISTENING_REVIEW_SCORECARD.md` records `READY_FOR_FULL_CHAPTER_INTERNAL_ONLY`.
2. Open ElevenLabs UI/Studio manually in the owner account.
3. Select Rachel, voice ID `21m00Tcm4TlvDq8ikWAM`.
4. Select only a stable non-beta TTS model.
5. Generate each `chunk_manifest.json` chunk separately from its clean `narration_text`; do not paste the entire chapter as one giant generation.
6. Keep each chunk near the recommended 45-120 second range where the text allows it.
7. Preserve paragraph boundaries and stable sentence IDs through `sentence_ids` metadata, not by pasting IDs into ElevenLabs.
8. Download each generated MP3 or WAV manually.
9. Save downloads only under `internal/audiobook_lab/dracula/en/chapter-1-elevenlabs-full/imported_audio/` using the `audio_filename` values in `chunk_manifest.json`.
10. Run `npm run elevenlabs:validate-narration-text` before generation and again before import.
11. Run `npm run elevenlabs:full-chapter-import` after all chunks are present.

## Absolute Guardrails

- Do not place audio under `frontend/public`.
- Do not place audio under `frontend/build`.
- Do not add Listen Now CTA.
- Do not add AudioObject metadata.
- Do not expose public audio URLs.
- Do not publish audio.
- Do not mark production approved.
- Do not generate a full book.
- Do not paste sentence IDs, source comments, markdown, or sync-only text into ElevenLabs.
