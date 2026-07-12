# Human Narration Brief: The Open Window

Author: Saki
Language: English

## Pronunciation And Style Notes
- Calm, intimate classic-story narration with understated tension and dry wit.
- Keep Vera poised and controlled; do not overact the ghost-story reveal.
- Avoid list-reading rhythm, mechanical cadence, rushed twilight transitions, and synthetic resets.
- Preserve names and quoted dialogue exactly as written.

## Target Narration Style
Natural literary pacing, restrained emotional expression, clear dialogue changes, and deliberate punctuation pauses.

Use only `clean_manuscript.txt`. Preserve every word and paragraph in order.
Do not add music, sound effects, source boilerplate, page numbers, or narration credits.

## Required Audio Format
Deliver one clean WAV (PCM, 44.1/48 kHz, mono or stereo) or high-bitrate MP3 (44.1/48 kHz).
No normalization clipping, denoising artifacts, music, room tone jumps, or lossy re-encoding chains.

## Chapter And Section Boundaries
This controlled edition has one chapter. Preserve paragraph boundaries and leave natural silence at scene/paragraph transitions.
Do not insert spoken chapter numbers, credits, source notices, or any text absent from the manuscript.

See `failed_tts_evidence_summary.md`, `delivery_checklist.md`, and `qa_release_checklist.md`.

## Exact Validation Command After Delivery
`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_prepare_human_narration_packet.py --slug the-open-window --asset-root /Users/ronikbasak/Documents/GitHub/earnalism-digital-library --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets --received-audio /absolute/path/to/received_narration.wav`
