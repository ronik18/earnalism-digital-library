# মুচিরাম গুড়ের জীবনচরিত Audio Handoff Report

Generated: `2026-07-12T22:04:03Z`

- Slug: `muchiram-gurer-jibanchorit`
- Classification: `HUMAN_NARRATION_OR_LICENSED_ALTERNATE_PROVIDER_REQUIRED`
- Public reader: `Yes`
- Public audiobook: `No`
- Controlled source hash: `733466ffdadc8f5c0172023edd5c0ba7327387d65d0c46b1b881a26e303e800a`
- Full private candidate audio SHA-256: `dcafb32f428da7cff43a7fadc1db7ca79eed80880886abab250f4f886dcdea1a`

## Existing Evidence

- Google Aoede representative audition passed only at `9.3` / confidence `0.95`, with passage scores `9.4, 9.5, 9.3, 9.5`: `internal/audiobook_lab/sprint1_publication/title_runs/muchiram_google_chirp_audition/bengali_representative_audition_report.json`.
- Full-book QA fell to `7.8` / confidence `0.85` and recorded `robotic_texture_detected`, `mechanical_cadence_detected`, and `list_reading_rhythm_detected`: `internal/audiobook_lab/sprint1_publication/title_runs/muchiram_google_full_qa.json`.
- Achird targeted repair scored `9.5, 9.4, 7.4, 7.8`: `internal/audiobook_lab/sprint1_publication/title_runs/muchiram_google_targeted_repair_audition/bengali_representative_audition_report.json`.
- Final Aoede repair scored `9.4, 9.4, 7.9, 7.8`: `internal/audiobook_lab/sprint1_publication/title_runs/muchiram_google_aoede_slow_repair_audition/bengali_representative_audition_report.json`.

The isolated representative pass is not release approval. The full candidate and two bounded repair attempts establish an automated-provider plateau, so public audio remains hidden.

## Exact Received-Audio Validation Command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug muchiram-gurer-jibanchorit --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

No provider call, lock change, release mutation, publication, or audio copy was performed by this report task.
