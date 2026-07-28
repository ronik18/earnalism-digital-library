# Alice's Adventures in Wonderland Parallel Sprint Report

Updated: `2026-07-28T05:52:03Z`

- Slug: `alices-adventures-in-wonderland`
- Language: `English`
- Assigned lane: `4 - Medium/Long English Lane`
- Assigned agent: `Goodall (019f57d2-7aed-7840-95b5-642a9a5ed578)`
- Public reader: `Yes`
- Public audiobook: `No`
- Quality evidence: `3/4 exact representative ASR passes; one exact-order failure`
- Local generation cost: `$0.00`
- Listening QA spend: `$0.00` because the objective gate failed first
- Final state: `SOURCE_BOUND_DELIVERY_REQUIRED`
- Blocker: `KOKORO_BF_EMMA_REPRESENTATIVE_EXACT_ORDER_FAILURE; PUBLIC_UNAPPROVED_STORAGE_OBJECT_REVOCATION_REQUIRED; SOURCE_BOUND_FULL_TITLE_DELIVERY_MISSING`
- Evidence: `internal/audiobook_lab/sprint1_publication/title_runs/alices-adventures-in-wonderland_kokoro_bf_emma_asr_repair_v1.json`
- Next action: Supply one exact rights-cleared full-title recording through the prepared source-bound packet, revoke the old unapproved remote object, and run all release gates.

## Next Command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug alices-adventures-in-wonderland --candidate-kind licensed_audio_import --asset-root . --output-root internal/audiobook_lab/sprint1_publication/licensed_audio_import --received-audio /absolute/path/to/received_narration.wav
```

The bounded Kokoro `bf_emma` / British-G2P pilot used four private source-bound
passages. The single retained-WAV repair produced ASR scores
`10.0/9.9408/10.0/10.0`; three passages passed exact content. The Caterpillar
dialogue still omitted one repeated source token `I`, so ordered-content
integrity failed. Listening QA and full-title generation were correctly
skipped. The exact synthesis and repair fingerprints are closed.

No paid synthesis, listening call, upload, release-gate mutation, or public
audio exposure was performed. The source-bound packet is ready at
`internal/audiobook_lab/sprint1_publication/licensed_audio_import/alices-adventures-in-wonderland/metadata.json`.

## Storage Containment

Classification: `PUBLIC_UNAPPROVED_STORAGE_OBJECT_REACHABLE`. Eleven direct URL occurrences were removed from the controlled publication packet. The API/UI remains audio-hidden; remote Cloudinary object revocation or privacy enforcement is still required before any new audition or release work.
