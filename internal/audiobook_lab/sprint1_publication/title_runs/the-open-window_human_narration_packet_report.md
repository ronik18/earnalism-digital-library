# The Open Window Stage 2F Human Narration Packet

## Decision

`HUMAN_NARRATION_OR_ALTERNATE_PROVIDER_REQUIRED`

The public reader remains available and public audio remains hidden. The disallowed Piper asset and failed Google Studio-C/Studio-B candidates are not release candidates. No provider call, upload, publication, or release-state mutation ran in Stage 2F.

Production revalidation returned an audio-disabled manifest with empty public assets and a `404` audiobook endpoint.

## Packet

- Directory: `internal/audiobook_lab/sprint1_publication/human_narration_packets/the-open-window`
- Source-bound manuscript: `clean_manuscript.txt`
- Narrator brief and pronunciation/style guidance: `narrator_brief.md`
- Failed TTS evidence: `failed_tts_evidence_summary.md`
- Delivery requirements: `delivery_checklist.md`
- QA and release gates: `qa_release_checklist.md`
- Hash/provenance metadata: `metadata.json`

The packet requires natural, understated literary delivery and explicitly rejects list-reading rhythm, robotic texture, mechanical cadence, overacting, source boilerplate, music, and added text.

## Next Command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_prepare_human_narration_packet.py \
  --slug the-open-window \
  --asset-root /Users/ronikbasak/Documents/GitHub/earnalism-digital-library \
  --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets \
  --received-audio /absolute/path/to/received_narration.wav
```

Passing this format/checksum preflight does not publish audio. ASR/source, first/last, listening, manifest, endpoint, frontend, production, and owner release gates remain mandatory.
