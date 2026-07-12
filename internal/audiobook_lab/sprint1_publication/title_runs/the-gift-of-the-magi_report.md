# The Gift of the Magi Audio Handoff Report

Generated: `2026-07-12T22:04:03Z`

- Classification: `HUMAN_NARRATION_OR_LICENSED_ALTERNATE_PROVIDER_REQUIRED`
- Public reader: `Yes`
- Public audiobook: `No`
- Controlled source hash: `490b76d444db0d952f5286f60c4ec2834ab91731d47e42dc94a3639d9183d295`
- Audition sanitized-source SHA-256: `67c1074aea0203a04f3116f42fa85c01cdec12d9646a25f0b119c3834d921ea7`

## Existing Evidence

- Studio-C fingerprint `75a6fbc43a06e181677d1f4a2afc2508416d7f0b137d325f79948df48a04fabe` scored `9.5, 9.4, 8.5, 9.4`: `internal/audiobook_lab/private_runs/google_english/the-gift-of-the-magi/audition/75a6fbc43a06e181/audition_listening_evidence.json`.
- Contextual Studio-C fingerprint `716473a1705c4aa3e6ea718f2c117668875215ac368540f6402b4dab47932f43` scored `9.5, 9.4, 8.3, 9.5`: `internal/audiobook_lab/private_runs/google_english/the-gift-of-the-magi/audition/716473a1705c4aa3/audition_listening_evidence.json`.
- Final Chirp3-HD-Aoede fingerprint `cda6b9c871c9751f8ade43db4ec0c71b865c9ac0ba5ab5a63a49c6fbf2b13ddd` scored `9.4, 9.4, 7.2, 9.5`; minimum confidence `0.90`; fatal flags `mechanical_cadence_detected` and `robotic_texture_detected`: `internal/audiobook_lab/private_runs/google_english/the-gift-of-the-magi/audition/cda6b9c871c9751f/audition_listening_evidence.json`.

All bounded attempts miss the owner `9.4` floor on every representative passage. Public audio remains hidden.

## Human / Licensed Import Packet

- Packet: `internal/audiobook_lab/sprint1_publication/human_narration_packets/the-gift-of-the-magi`
- Packet fingerprint SHA-256: `dd28671d62a54782d8c313134e1d5a60d2ab9fba2f4b74f5593f57939c2ce604`
- Sanitized manuscript SHA-256: `be7f050f1affc65144172ae7157ad10ab8a8ee698e196623ff072fe410f4ec5e`
- Exact received-audio validation command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-gift-of-the-magi --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

No provider call, lock change, release mutation, publication, or audio copy was performed by this report task.
