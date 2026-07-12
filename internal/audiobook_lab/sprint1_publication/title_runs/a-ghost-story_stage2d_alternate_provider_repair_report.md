# A Ghost Story Stage 2D Alternate-Provider Repair

Generated: `2026-07-12`

Owner decision: `AUTHORIZE_STAGE_2D_A_GHOST_STORY_ALTERNATE_PROVIDER_REPAIR_AND_PUBLICATION_IF_PASS`

## Decision

- Public reader: `YES`
- Alternate-provider release QA: `PASS`
- Verified B2 upload: `PASS`
- Public source packet: `READY_FOR_PR`
- Production audiobook: `PENDING_NORMAL_DEPLOYMENT`
- Quality claim: measured release minimum passed; `10/10` is not claimed.

## Diagnosis And Repair

The Stage 2C OpenAI candidate had strong source fidelity but one `8.3` listening sample with list-reading rhythm. The defect was provider delivery rather than a sampling false negative. Google `en-GB-Studio-B` and baseline `en-GB-Studio-C` reproduced the weak middle cadence. One bounded, source-preserving Studio-C prosody repair at 88 percent produced three representative scores of `9.4`, confidence `0.95`, with no fatal flags.

Because safe cross-provider segment splicing was not supported by the release manifest, Stage 2D generated one new full Google Studio-C candidate. It used nine sentence-safe chunks and preserved the approved manuscript text exactly.

## Full Release QA

- Audio SHA-256: `c0e52985ee1e3e178b81d83157189251a667d64ecbc22bbc0940e6e4fc7bf904`
- Source SHA-256: `0f1e3de7855169bddac8ddca288aa3a63f8d6a742ce63c0b91aa947e5e2786d4`
- Duration: `880.944` seconds
- Size: `7,047,789` bytes
- ASR/source: `9.88/10`
- First words: `PASS`
- Last words: `PASS`
- Listening samples: `6`
- Listening range: `9.4-9.5`
- Minimum confidence: `0.95`
- Fatal flags: none
- Alignment: `openai_verbose_json_word_timestamps`
- Estimated timing: `false`
- Public copy contract: section-following narration only; no word-level sync claim.

## Upload

The existing upload hook stored the MP3, timestamps, VTT, chapters, and metadata in B2. It downloaded each object and verified exact SHA-256 and byte-size parity. A direct `Range: bytes=0-1023` request returned HTTP `206`, `Content-Type: audio/mpeg`, and exactly `1024` bytes.

No generated audio is stored under `frontend/public` or `frontend/build`.

## Budget

- Authorized Sprint 1 cap: `$175.00`
- Estimated Stage 2B through Stage 2D spend: `$3.6328`
- Estimated remaining cap: `$171.3672`
- Actual provider billing: `NOT_REPORTED`

## Release Guardrails

- `book-2b9853ec52` remains approved.
- `bn-066` remains audio-hidden.
- No other title is added to the audio allowlist.
- No static `/audio/...` fallback, browser speech fallback, or word-level sync claim is introduced.
- `paid_tts.lock` was restored byte-for-byte after every provider and upload operation.

## Next Command

```sh
gh pr create --base main --head codex/a-ghost-story-alternate-provider --title "Publish A Ghost Story audiobook after alternate-provider QA" --body-file /tmp/a-ghost-story-stage2d-pr-body.md
```
