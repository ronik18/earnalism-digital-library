# Désirée's Baby Autonomous V2 Report

Generated: `2026-07-13T05:59:30Z`

- Slug: `dsires-baby`
- Public reader: `Yes`
- Public audiobook: `No`
- Source/rights/sanitation: `PASS`
- Source: `11,974` characters, one chapter, SHA-256 `587455ed554ef64d19f0ea7dcd31940d242aa759f5132b6514b130efa4a64a89`
- Provider/voices: Google Cloud TTS / `en-GB-Studio-C` and `en-GB-Chirp3-HD-Achird`
- Audition fingerprints: `bccf002da4e9713e3870b602c07e65ae1ad0a49fbd1904e5730b823a0d605d4e`, `dcef93a40f30b3529eb8958c039aaa309ae2753d44208e0fce5d3a4b754241fa`
- Estimated combined TTS and listening QA: `$0.47232`; actual provider billing not reported
- Lock: restored byte-for-byte to `active`, holder `none`, allowed next holders `[]`
- Final state: `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED`

## Listening QA

| Passage | Score | Confidence | Fatal flags |
| --- | ---: | ---: | --- |
| opening | 9.4 | 0.95 | none |
| middle | 8.4 | 0.90 | none |
| dialogue_or_risk | 7.5 | 0.85 | robotic texture; mechanical cadence |
| ending | 9.4 | 0.95 | none |

The source-bound Studio-C candidate failed the required all-sample `9.4` and confidence `0.9` gates. The dialogue passage was rushed and mechanically delivered. Full TTS, ASR, upload, release-state mutation, and publication did not run. This exact Studio-C fingerprint must not be repeated.

The materially different Achird candidate scored `9.4, 9.4, 7.2, 9.4` at minimum confidence `0.90`; the dialogue passage again triggered fatal robotic texture and mechanical cadence. This fingerprint must not be repeated. The two-family automated retry limit is exhausted.

## Next Command

Validate a received source-bound human narration or licensed-audio candidate against the generated packet:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug dsires-baby --candidate-kind human_narration --asset-root . --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav
```

No audio was uploaded, published, copied to a public frontend path, or approved for release.
