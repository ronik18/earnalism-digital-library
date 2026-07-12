# A Ghost Story Stage 2B Listening QA Report

Generated: `2026-07-12T09:35:33Z`

## Decision

`AUDIO_HIDDEN_LISTENING_QA_REPAIR_REQUIRED`

A Ghost Story was not published. Its existing audio passed source alignment and boundary checks but failed bounded listening QA, so the conditional publication authorization did not activate.

## Runtime Gates

All required total, per-title, ASR, retry, and listening-QA caps were present in the exact command process. `OPENAI_API_KEY` was present without being printed. The lock-safe wrapper acquired `sprint1_publication_stage2a` and restored the original lock bytes afterward.

## Evidence

- Existing audio: `4,594,121` bytes; `765.57` seconds
- Audio SHA-256: `00190d747d2894a244545a260f10f4e06ccc597352d2767414acc4edfe6e5a55`
- ASR/source: `9.7882/10 PASS`
- First/last words: `PASS / PASS`
- Listening samples: `6`
- Minimum listening score: `8.3/10 FAIL`
- Minimum confidence: `0.90`
- Fatal flags: none
- Weak sample: `middle_60s`, start `352.787s`
- Weak-sample pacing: `7.9`
- Weak-sample emotional expression: `8.2`
- Estimated listening-QA spend: `$0.30`
- Actual provider billing: not reported

Five samples scored `9.4-9.5`. The middle sample was judged draft quality because pacing was rushed and expression/punctuation shaping were not premium enough. This is a localized repair signal, not release approval.

## Release Truth

- Public reader: `Yes`
- Public audiobook: `No`
- Production manifest audio: disabled, empty public fields
- Production audiobook endpoint: `404` fail-closed
- New Listen/AudioObject exposure: none
- TTS/ASR calls: none
- Publication/deployment/release-gate mutation: none
- `book-2b9853ec52`: approved manifest remains enabled; range endpoint `206`
- `bn-066`: remains audio-hidden

## Next Command

Prepare the exact weak segment for a separately authorized targeted English literary-voice audition. This command is non-paid and does not repeat listening QA:

```bash
mkdir -p /tmp/earnalism-a-ghost-stage2c-middle-repair && ffmpeg -hide_banner -loglevel error -y -ss 352.787 -t 60 -i internal/audiobook_lab/release_gate/a-ghost-story_20260705T044404Z/a-ghost-story_existing_audio_candidate.mp3 /tmp/earnalism-a-ghost-stage2c-middle-repair/middle_60s_reference.mp3 && sed -n '173,240p' internal/audiobook_lab/release_gate/a-ghost-story_20260705T150049Z/clean_manuscript.txt > /tmp/earnalism-a-ghost-stage2c-middle-repair/middle_source.txt
```
