# Manual ElevenLabs Generation Checklist

## Settings

- Voice: Rachel
- Voice ID: `21m00Tcm4TlvDq8ikWAM`
- Model: Eleven Multilingual v2 or same stable non-beta model used in approved sample
- Speed: 0.85
- Stability: 60-65%
- Similarity: 75-80%
- Style Exaggeration: 5-10%
- Speaker Boost: On
- No beta services
- No voice cloning
- No ElevenReader

## Copy Order And Expected Filenames

1. `c001.txt` -> `dracula-chapter-1-elevenlabs-rachel-c001.mp3`
2. `c002.txt` -> `dracula-chapter-1-elevenlabs-rachel-c002.mp3`
3. `c003.txt` -> `dracula-chapter-1-elevenlabs-rachel-c003.mp3`

## Save Location

- Save downloads only under `internal/audiobook_lab/dracula/en/chapter-1/imported_audio/`.
- Do not upload generated audio to `frontend/public` or `frontend/build`.
- Keep this as internal review audio until every release gate is explicitly approved.
