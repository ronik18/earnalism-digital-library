# Sprint 1 deterministic audiobook release conveyor

Status: `ACTIVE`

The goal remains 32/32 production readers and 32/32 production audiobooks. The
current verified baseline is 32 readers and four audiobooks, leaving 28
audio-hidden titles.

## What changes now

Model exploration is finite. A title may use at most one new synthetic family,
one targeted repair, one full-title generation after a representative pass,
and one post-full-title section repair. A failed fingerprint is never retried.
Changing a cutoff or obtaining one attractive sample can never approve a
release.

Every title must leave the conveyor in a named state:

- `PRODUCTION_LIVE_VERIFIED`
- `FULL_RELEASE_PIPELINE_ACTIVE`
- `SOURCE_BOUND_DELIVERY_REQUIRED`
- `PREREQUISITE_REPAIR_REQUIRED`
- `EXTERNAL_PROCUREMENT_ACTION_REQUIRED`

There is no indefinite `try another model` state.

## Current routing

- Four titles are already `PRODUCTION_LIVE_VERIFIED`.
- Nineteen titles, including **The Gift of the Magi**, **The Tell-Tale
  Heart**, have exhausted their useful synthetic evidence and now require one
  exact source-bound narration or licensed-audio delivery. They receive no more
  synthetic pilots.
- Eight previously untested English titles may receive exactly one
  four-passage candidate evaluation. Failure sends the title directly to
  source-bound delivery.
- **The Time Machine** moves directly to source-bound delivery. Its retained
  `bm_george` diagnostic was only one sample and the recorded provider family
  is already closed; repeating it would violate the no-repeat rule.
- **Pather Panchali** must repair its source, rights, and cover prerequisites
  before any audio candidate is allowed.

## Gift terminal result

The final Qwen3 Base MLX 8-bit sample was a valid 24 kHz PCM-16 WAV, but
`1.417947%` of its samples were full-scale clipped. Its exact SHA-256 is
`da573f24abea837e30a5a8b2ac9d1082f692c66661f17a2e3589840bd29729bf`.
Normalization cannot reconstruct clipped waveform peaks, so ASR and listening
spend were skipped. Gift remains audio-hidden and moves to its existing
source-bound delivery packet.

## Release truth

The active listening floor is `8.9`, confidence is `0.90`, ordinary dimensions
must be at least `8.9`, anti-robotic and anti-choppy dimensions must be at least
`9.2`, and fatal flags must be absent. ASR/manuscript remains `9.7`, coverage
remains `0.98`, and exact first/last/order, measured sync, rights, covers,
checksum, metadata, endpoint, browser playback, and an empty blocker list are
mandatory.

## Active title

**The Call of the Wild** consumed its one permitted synthetic-family attempt
with four private OpenAI `gpt-4o-mini-tts` / `verse` representative clips.
Their raw ASR/manuscript scores were `9.6032`, `9.5000`, `9.7041`, and `9.5849`;
coverage was below `0.98` for every passage, and every passage failed exact
ordered-content integrity. Listening QA was correctly skipped.

The paid lock restored byte-for-byte. The exact failed fingerprint will not be
retried, the audio remains private and hidden, and the title now requires an
exact rights-cleared source-bound delivery.

Next exact command:

`PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py --slug the-call-of-the-wild --candidate-kind licensed_audio_import --asset-root . --output-root internal/audiobook_lab/sprint1_publication/licensed_audio_import --received-audio /absolute/path/to/received_narration.wav`
