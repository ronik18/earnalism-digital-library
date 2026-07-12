# রামকানাইয়ের নির্বুদ্ধিতা Audio Handoff Report

Generated: `2026-07-12T22:04:03Z`

- Slug: `book-f5d593e1f4`
- Classification: `HUMAN_NARRATION_OR_LICENSED_ALTERNATE_PROVIDER_REQUIRED`
- Public reader: `Yes`
- Public audiobook: `No`
- Controlled source hash: `f4bd2ecf4d9eb2dc5e3917bc45965c768463a34d9ced5f1dfe1e1f336b300827`

## Existing Evidence

- Google `bn-IN-Chirp3-HD-Aoede` scored `9.4, 9.5, 7.8, 9.4`; the `7.8` passage had confidence `0.85` plus `robotic_texture_detected` and `mechanical_cadence_detected`: `internal/audiobook_lab/sprint1_publication/title_runs/book-f5d593e1f4_google_audition/bengali_representative_audition_report.json`.
- Final bounded Sarvam `bulbul:v3` / `pooja` scored `9.4, 9.4, 7.8, 9.4`, with minimum confidence `0.85`: `internal/audiobook_lab/sprint1_publication/title_runs/book-f5d593e1f4_sarvam_audition/bengali_representative_audition_report.json`.

Both bounded provider paths missed the Bengali `9.2` / `0.90` gate, and no complete full-book release evidence exists. Public audio remains hidden.

## Exact Received-Audio Validation Command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug book-f5d593e1f4 --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

No provider call, lock change, release mutation, publication, or audio copy was performed by this report task.
