# Ginni Indic Parler/Aditi private preflight

Status: `PACKET_READY_EXECUTION_BLOCKED`

This run prepared one deterministic, provider-free representative audition
packet. It did not load a TTS model, generate audio, run ASR or listening QA,
inspect or touch `paid_tts.lock`, upload media, mutate release truth, or expose
audio.

## Candidate selection

The remaining hidden Sprint 1 Bengali titles were compared by canonical
manuscript length, source/rights readiness, cover readiness, and recorded
provider history.

| Order | Slug | Canonical characters | Decision |
| --- | --- | ---: | --- |
| 1 | `muchiram-gurer-jibanchorit` | 5,971 | Excluded: known automated plateau and human-narration escalation |
| 2 | `book-d19e96859f` | 6,459 | Selected: shortest source-bound, rights-clear, front/back-cover-ready alternative |
| 3 | `book-f5d593e1f4` | 9,419 | Not selected: longer and recorded Google/Sarvam plateau |
| 4 | `book-edfcf810c5` | 22,039 | Not selected: longer and three closed Gemini voice attempts |
| 5 | `radharani` | 38,022 | Not selected: longer and prior full-title fidelity failure |
| 6 | `nishkriti` | 83,686 | Not selected: longer and a closed Gemini voice attempt |
| 7 | `pather-panchali` | 125,479 | Not selected: cover/owner blockers remain |
| 8 | `devdas` | 152,769 | Not selected: missing canonical covers and closed Gemini attempts |
| 9 | `bn-066` | 202,901 | Not selected: longest remaining manuscript |

## Exact packet

- Title: `গিন্নি`
- Author: `রবীন্দ্রনাথ ঠাকুর`
- Canonical manuscript SHA-256:
  `3c184ef8918fee4686c3ac93e17c12d7108617099c70425948cdd7cbf36b68d5`
- Model: `ai4bharat/indic-parler-tts`
- Revision: `7b527af5ee8ed1f9a28d80b19703ed9bb8ba10ca`
- Voice: `Aditi`
- Representative passages: 4 exact source slices / 1,781 characters
- Attempt fingerprint:
  `0a5d983bf199e0288557c80840402a00f9160e17e533e327fdf950d81006c05a`

The four passages cover opening exposition, clause-heavy satire, child
dialogue, and the emotional ending. Offsets and hashes are recorded in the JSON
packet and recomputed from both controlled-publication mirrors by the focused
test.

## Rights and repository access

The official model card identifies the model as Apache-2.0 and describes it as
permissively licensed. Earnalism therefore records commercial use as permitted
by the model license.

Hugging Face separately labels the repository as publicly listed but gates file
access behind a signed-in contact-information/conditions acknowledgement. A
receipt for that acknowledgement is not present in this packet. That is a
non-blocking provenance note for the already-downloaded, hash-bound local
snapshot; it is not treated as a second commercial-rights gate or a reason to
block a private local audition.

## Current blocker

The pinned local model snapshot is present and its seven expected files,
including the 3,751,321,772-byte `model.safetensors`, match the recorded
SHA-256 contract. The existing `.venv-audio` runtime lacks `parler-tts`,
`accelerate`, and `scipy`.

The missing runtime dependencies are the only private-audition execution
blocker. Even after they are resolved, the first permitted action is a
four-passage private audition.
Full-title generation, upload, publication, and release-gate mutation remain
forbidden until that audition passes the active objective and listening gates.

## Next exact command

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/.venv-audio/bin/python internal/audiobook_lab/scripts/sprint1_d19_indic_parler_private_preflight.py --preflight --verify-runtime --model-snapshot-dir /Users/ronikbasak/.cache/huggingface/hub/models--ai4bharat--indic-parler-tts/snapshots/7b527af5ee8ed1f9a28d80b19703ed9bb8ba10ca --output /private/tmp/book-d19e96859f_indic_parler_aditi_runtime_preflight.json
```

At the time of this packet, that command correctly fails closed with:

```text
runtime dependencies missing: parler-tts, accelerate, scipy
```
