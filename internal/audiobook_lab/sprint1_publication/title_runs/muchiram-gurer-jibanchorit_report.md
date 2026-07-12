# মুচিরাম গুড়ের জীবনচরিত Parallel Sprint Report

Generated: `2026-07-12T19:35:15Z`

- Slug: `muchiram-gurer-jibanchorit`
- Language: `Bengali`
- Assigned lane: `2 - Short Bengali High-ROI Lane`
- Assigned agent: `Galileo (019f57d2-7210-7930-96bd-df620ee5d77d)`
- Public reader: `Yes`
- Public audiobook: `No`
- Quality evidence: `0.039/10 ASR-source; representative timed out`
- Estimated remaining cost: `$0.1447`
- Final state: `SPRINT_TARGET_INCOMPLETE`
- Blocker: `TITLE_AUDIO_RELEASE_GATES_INCOMPLETE; PAID_RUNTIME_ENV_GATES_MISSING`
- Evidence: `internal/audiobook_lab/release_gate/muchiram-gurer-jibanchorit_20260705T150228Z/goliveevidence.json`
- Next action: Complete reader PR if applicable, then run the title's bounded audio repair path after runtime gates are supplied

## Next Command

```bash
python3 internal/audiobook_lab/scripts/bengali_tts_provider_bakeoff.py --manifest book_import_manifest.batch-1.json --candidate-slugs muchiram-gurer-jibanchorit --max-passages 1 --max-seconds-per-sample 20 --providers sarvam --max-voices-per-provider 1 --voice-filter sarvam:ratan --style-profiles literary_warm_pacing --bengali-audiobook-92-rescue --fail-closed --run-dir internal/audiobook_lab/sprint1_publication/muchiram_split_audition
```

No provider call, release-gate mutation, or public audio exposure was performed by this materializer.
