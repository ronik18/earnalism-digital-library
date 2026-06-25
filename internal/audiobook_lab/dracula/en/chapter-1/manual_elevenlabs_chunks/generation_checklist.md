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

- Use the ElevenLabs UI/Studio manually; this repo must not call the ElevenLabs API.
- Generate one chunk at a time, in the exact order below.
- Use voice Rachel / `21m00Tcm4TlvDq8ikWAM` for every chunk.
- Use no beta services, no voice cloning, and no ElevenReader.
- Download each generated audio file using the exact expected filename shown below.
- Regenerate only failed chunks after QA; do not regenerate chunks that already pass.

1. `c001.txt` -> `dracula-chapter-1-elevenlabs-rachel-c001.mp3`
2. `c002.txt` -> `dracula-chapter-1-elevenlabs-rachel-c002.mp3`
3. `c003.txt` -> `dracula-chapter-1-elevenlabs-rachel-c003.mp3`
4. `c004.txt` -> `dracula-chapter-1-elevenlabs-rachel-c004.mp3`
5. `c005.txt` -> `dracula-chapter-1-elevenlabs-rachel-c005.mp3`
6. `c006.txt` -> `dracula-chapter-1-elevenlabs-rachel-c006.mp3`
7. `c007.txt` -> `dracula-chapter-1-elevenlabs-rachel-c007.mp3`
8. `c008.txt` -> `dracula-chapter-1-elevenlabs-rachel-c008.mp3`
9. `c009.txt` -> `dracula-chapter-1-elevenlabs-rachel-c009.mp3`
10. `c010.txt` -> `dracula-chapter-1-elevenlabs-rachel-c010.mp3`
11. `c011.txt` -> `dracula-chapter-1-elevenlabs-rachel-c011.mp3`
12. `c012.txt` -> `dracula-chapter-1-elevenlabs-rachel-c012.mp3`
13. `c013.txt` -> `dracula-chapter-1-elevenlabs-rachel-c013.mp3`
14. `c014.txt` -> `dracula-chapter-1-elevenlabs-rachel-c014.mp3`
15. `c015.txt` -> `dracula-chapter-1-elevenlabs-rachel-c015.mp3`
16. `c016.txt` -> `dracula-chapter-1-elevenlabs-rachel-c016.mp3`
17. `c017.txt` -> `dracula-chapter-1-elevenlabs-rachel-c017.mp3`
18. `c018.txt` -> `dracula-chapter-1-elevenlabs-rachel-c018.mp3`
19. `c019.txt` -> `dracula-chapter-1-elevenlabs-rachel-c019.mp3`
20. `c020.txt` -> `dracula-chapter-1-elevenlabs-rachel-c020.mp3`
21. `c021.txt` -> `dracula-chapter-1-elevenlabs-rachel-c021.mp3`
22. `c022.txt` -> `dracula-chapter-1-elevenlabs-rachel-c022.mp3`
23. `c023.txt` -> `dracula-chapter-1-elevenlabs-rachel-c023.mp3`
24. `c024.txt` -> `dracula-chapter-1-elevenlabs-rachel-c024.mp3`
25. `c025.txt` -> `dracula-chapter-1-elevenlabs-rachel-c025.mp3`
26. `c026.txt` -> `dracula-chapter-1-elevenlabs-rachel-c026.mp3`
27. `c027.txt` -> `dracula-chapter-1-elevenlabs-rachel-c027.mp3`

## Save Location

- Save downloads only under `internal/audiobook_lab/dracula/en/chapter-1/imported_audio/`.
- Do not upload generated audio to `frontend/public` or `frontend/build`.
- Keep this as internal review audio until every release gate is explicitly approved.
- Do not publish audio, add public listening calls to action, add structured audio metadata, or mark production approved.
