# The Yellow Wallpaper Autonomous Sprint Report

Generated: `2026-07-13T06:26:30Z`

- Public reader: `Yes`
- Public audiobook: `No`
- Final state: `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED`
- Conservative estimated spend: `$0.47248`; actual provider billing was not reported

Studio-C and Chirp3-HD-Achird each scored `8.4, 9.4, 8.4, 8.4` at the source-bound representative gate. Confidence remained at least `0.90` and no fatal flags were raised, but three of four samples missed the required `9.4`. Full TTS, ASR, upload, publication, and release mutation did not run.

## Next Command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-yellow-wallpaper --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

Both paid attempts restored `paid_tts.lock`; private audition audio remains outside public assets.
