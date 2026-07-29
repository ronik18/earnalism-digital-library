# Muchiram source-bound release attempt — 2026-07-29

## Outcome

Muchiram remains reader-live and audio-hidden. No candidate passed the complete
release gate, so no private production upload, metadata activation, public
endpoint, or Listen control was created.

## What was completed

- Revalidated the clean manuscript and all source hashes.
- Ran four exact source passages through a new Sarvam
  `bulbul:v3` / `ratan` / `literary_warm_pacing` fingerprint.
- Rejudged the two samples that had initially been duration-clipped using their
  complete source WAV files.
- Ran an open-source, non-cloned Bengali VITS opening pilot and one
  source-preserving sentence-breathing variant.
- Evaluated both VITS variants with Bengali-native Saaras ASR.
- Inspected the AI Doc Maker preview and attempted both direct and browser
  retrieval of its full output.
- Reverified production catalog truth and the hidden Muchiram audio endpoint.

## Exact results

| Candidate | Best objective/listening result | Decision |
| --- | --- | --- |
| Sarvam Ratan, four exact passages | Minimum listening `6.5`, confidence `0.85`; robotic, mechanical, and list-reading fatal flags | Closed |
| Open-source Bengali VITS opening | Normalized ASR `9.54`, coverage `0.9703`, first/last pass | Closed below `9.7` / `0.98` |
| VITS sentence-breathing variant | Normalized ASR `9.54`, coverage `0.9612`, first/last pass | Closed; no improvement |
| AI Doc Maker `fancy` | Preview source is recognizable, but the full delivery returns `429` and the browser reports missing/login-required; plan/attribution status is unknown | Do not import |

## Release truth

- Public readers: `32/32`.
- Public audiobooks: `4/32`.
- Muchiram stream endpoint: `404`.
- `paid_tts.lock` was restored after every provider call.
- No public media or release-state mutation occurred.

## Fastest safe continuation

Use the existing narration packet and deliver one complete, rights-cleared
recording:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py \
  --slug muchiram-gurer-jibanchorit \
  --candidate-kind human_narration \
  --asset-root . \
  --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets \
  --received-audio /absolute/path/to/complete-rights-cleared-muchiram.wav
```

The delivery must then pass exact ASR/source `>=9.7`, coverage `>=0.98`,
first/last and ordered-content integrity, measured sync, six-sample listening
`>=9.2` with confidence `>=0.90` and no fatal flags, private upload/checksum,
metadata, endpoint `206`, and browser playback before activation.
