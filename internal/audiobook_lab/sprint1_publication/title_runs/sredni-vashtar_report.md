# Sredni Vashtar Audio Handoff Report

Generated: `2026-07-12T22:04:03Z`

- Classification: `HUMAN_NARRATION_OR_LICENSED_ALTERNATE_PROVIDER_REQUIRED`
- Public reader: `Yes`
- Public audiobook: `No`
- Controlled source hash: `089628df1446736886ddae93252fc070854ec17606ade714a70ba77b55e6ea02`
- Audition sanitized-source SHA-256: `44e3bebedecc69c907b8739b5c6996932505df2cb140c05a4d55b9ca9d2bfd21`

## Existing Evidence

- Google Studio-C fingerprint `fd3f6a8020d44fb4c6bc59aa7c9488f078662e8bccb3e637b18c8984d69297bb` scored `8.4, 9.4, 7.3, 8.4`; minimum confidence `0.80`; fatal flags `mechanical_cadence_detected` and `robotic_texture_detected`: `internal/audiobook_lab/private_runs/google_english/sredni-vashtar/audition/fd3f6a8020d44fb4/audition_listening_evidence.json`.
- Final Chirp3-HD-Achird fingerprint `3855fd15b4ecf50d4fc5ff20fab6f8ad1ea7329a6a374da3d4e9e762f40d547e` scored `9.4, 9.4, 8.5, 9.4`; minimum confidence `0.90`: `internal/audiobook_lab/private_runs/google_english/sredni-vashtar/audition/3855fd15b4ecf50d/audition_listening_evidence.json`.

Both bounded attempts miss the owner `9.4` floor on every representative passage. Public audio remains hidden.

## Human / Licensed Import Packet

- Packet: `internal/audiobook_lab/sprint1_publication/human_narration_packets/sredni-vashtar`
- Packet fingerprint SHA-256: `ad621794b937bd94e82e71870c4768fff42ce79b2f98f22ea74a2e4e532c02a6`
- Sanitized manuscript SHA-256: `7d3a52056069e59d30cc15d474a3612479800dc01345f06719447b060a54fe94`
- Exact received-audio validation command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug sredni-vashtar --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

No provider call, lock change, release mutation, publication, or audio copy was performed by this report task.
