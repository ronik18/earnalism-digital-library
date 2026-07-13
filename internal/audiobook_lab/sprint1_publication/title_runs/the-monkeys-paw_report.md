# The Monkey's Paw Autonomous Sprint Report

Generated: `2026-07-13T06:22:19Z`

- Public reader: `Yes`
- Public audiobook: `No`
- Final state: `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED`
- Conservative estimated spend: `$1.92142`; actual provider billing was not reported
- Release mutation/upload: `none`

Studio-C failed representative QA (`8.4, 9.4, 8.3, 9.4`). Chirp3-HD-Achird passed its representative gate (`9.4` for all four samples), so a 14-chunk private full candidate was generated. Its ASR/source score was `9.8333` with first/last checks passing, but the ending sample scored `7.5` with robotic/mechanical flags.

One source-bound ending-only repair at `0.84` pacing raised the ending to `9.4`. The repaired candidate remained source-correct (`ASR/source 9.8519`, first/last PASS), but repeat full QA scored two other sections `8.4`. Since the all-samples `9.4` gate still failed after two voice families and a targeted repair, automated TTS attempts are closed for this title.

## Next Command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-monkeys-paw --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

All paid wrappers restored `paid_tts.lock`. Private audio remains under `/tmp`; no generated media was added to public assets.
