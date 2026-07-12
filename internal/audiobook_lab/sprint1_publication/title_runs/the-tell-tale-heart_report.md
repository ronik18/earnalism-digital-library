# The Tell-Tale Heart Audio Handoff Report

Generated: `2026-07-12T22:04:03Z`

- Classification: `HUMAN_NARRATION_OR_LICENSED_ALTERNATE_PROVIDER_REQUIRED`
- Public reader: `Yes`
- Public audiobook: `No`
- Controlled source hash: `f5d856baf4abec894c1fdc82f8676a416dc96efd3708162c04bcde0ff0a4579b`
- Audition sanitized-source SHA-256: `8e725a8220dca763fdd5286315016d1ae3071cb5f068e830e1e2b8ed16037bdb`

## Existing Evidence

- Contextual Studio-C fingerprint `4f7b571d8625924e82cb32ab3e1e3d33ae5123fc61c05a548dd0c4f2e9b304c4` scored `9.5, 8.4, 9.4, 9.6`; minimum confidence `0.90`: `internal/audiobook_lab/private_runs/google_english/the-tell-tale-heart/audition/4f7b571d8625924e/audition_listening_evidence.json`.
- Final slower Studio-C fingerprint `fd54248900cc4c9cc174fe327635781ac7749625e1bfd3635c897fb126ab632b` scored `9.4, 8.5, 9.4, 8.8`; minimum confidence `0.90`: `internal/audiobook_lab/private_runs/google_english/the-tell-tale-heart/audition/fd54248900cc4c9c/audition_listening_evidence.json`.

Both bounded attempts miss the owner `9.4` floor on every representative passage. Public audio remains hidden.

## Human / Licensed Import Packet

- Packet: `internal/audiobook_lab/sprint1_publication/human_narration_packets/the-tell-tale-heart`
- Packet fingerprint SHA-256: `ad6d7132c5b3cc1006afa8d3dc412c2829e5c5e19cb7e406b23ce8cfde4d34f7`
- Sanitized manuscript SHA-256: `df1b85c210aab99b3b14c106e0a28c4305e7c4dbc8aa16aa11f1877bb9502981`
- Exact received-audio validation command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-tell-tale-heart --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

No provider call, lock change, release mutation, publication, or audio copy was performed by this report task.
