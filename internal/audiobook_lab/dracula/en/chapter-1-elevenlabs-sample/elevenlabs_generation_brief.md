# ElevenLabs Dracula Internal Sample Generation Brief

This is an internal-only manual generation brief. It does not approve public
audio, production audio, provider API automation, full-chapter generation, or
full-audiobook generation.

## Provider And Voice

- Provider: ElevenLabs
- Account plan: Creator paid membership, pending owner/legal evidence.
- Voice: Rachel
- Voice ID: `21m00Tcm4TlvDq8ikWAM`
- Voice type: platform voice
- Model: use a stable non-beta ElevenLabs TTS model available in the owner UI.
- Beta services: forbidden.
- Voice cloning: forbidden.
- ElevenReader: forbidden.
- API automation: forbidden for this task.

## Text

- Use exactly `sample_text.txt`.
- Keep sentence IDs out of the generated narration if the UI would speak them;
  they are sync anchors for the repo packet.
- Target length: 2-3 minutes only.
- Do not generate a full chapter.
- Do not generate a full audiobook.

## Manual Owner Workflow

1. Confirm `internal/legal/elevenlabs/creator-membership-internal-eval-evidence.md`
   is complete and approved for internal evaluation only.
2. Open ElevenLabs Studio/UI manually.
3. Select Rachel, voice ID `21m00Tcm4TlvDq8ikWAM`.
4. Use only stable, non-beta TTS.
5. Generate a first 30-45 second test if the UI supports it.
6. If the short test passes, generate the 2-3 minute sample.
7. Download MP3 or WAV manually.
8. Place the downloaded file under:
   `internal/audiobook_lab/dracula/en/chapter-1-elevenlabs-sample/imported_audio/`
9. Run:
   `npm run elevenlabs:sample-import`

Never place audio under `frontend/public` or `frontend/build`.
