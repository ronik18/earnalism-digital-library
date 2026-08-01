# Bengali Audiobook Future Strategy

## Current Decision

Automated Bengali audiobook generation is paused for this sprint under `AUDIO_PROVIDER_QUALITY_LIMIT_CONFIRMED`.

This is not a permanent abandonment of Bengali audiobooks. It is a release-safety decision based on representative evidence: isolated high-quality samples do not prove that a full Bengali audiobook will feel premium, continuous, natural, and trustworthy.

## Why Automated Bengali TTS Is Paused

- OpenAI Bengali narration did not meet the premium literary listening threshold in prior runs.
- Sarvam `bulbul:v3` synthesis works and produced promising isolated samples.
- The strongest isolated Sarvam seed, `pooja` with `dialogue_human_touch`, reached 9.6 with confidence 0.95.
- The representative Sarvam seed-rescue failed to generalize: representative score 7.9, confidence 0.85.
- The failed representative passages showed `list_reading_rhythm_detected` and `mechanical_cadence_detected`.
- No full Bengali pilot was generated.
- No ASR, sync, upload, metadata approval, browser gate, or public audiobook exposure was run.

## Acceptance Criteria For Reopening

Automated Bengali audio can be reopened only when at least one of these exists:

- A new Bengali provider/model with representative audition score >= 9.3, confidence >= 0.90, and no fatal red flags.
- An improved Sarvam model/voice with fresh capability evidence and representative passage coverage.
- A human/professional narration workflow with representative audition pass.
- A licensed audiobook import path with rights, provenance, ASR/manuscript match, and measured sync.
- A manually approved exceptional sample set covering opening narration, dialogue, emotional prose, punctuation-heavy prose, and ending-style narration.

## Human Or Professional Narration Path

1. Select one short, rights-cleared Bengali title with reader route and covers already passing.
2. Audition one narrator on five representative passages.
3. Require `PREMIUM_AUDIO_APPROVED` or better under the tiered listening policy.
4. Record pronunciation, emotional continuity, pacing, anti-robotic texture, anti-choppy joins, and listener enjoyment scores.
5. Generate exactly one full pilot.
6. Run ASR/manuscript match, first/last span checks, and content-order checks.
7. Use measured paragraph/stanza sync if word sync is not reliable.
8. Publish only after upload/checksum, metadata approval, endpoint, and browser gates pass.

## Licensed Audiobook Import Path

1. Verify commercial-use audio rights and source provenance.
2. Confirm the audio is not stale, mismatched, fallback, placeholder, robotic, or low quality.
3. Build sidecars from the final audio hash.
4. Require ASR/manuscript match >= 9.7 and first/last word match.
5. Accept measured paragraph/stanza sync where it preserves a premium experience.
6. Keep audiobook controls hidden until all gates pass.

## Cost Estimate Categories

- Low: representative audition only, short samples, no upload or production mutation.
- Medium: one full short-title pilot with ASR, measured sync, listening QA, and browser validation.
- High: full catalog audiobook expansion, which is not authorized until a pilot passes.

## Do Not Do

- Do not generate full Bengali audiobooks from isolated sample quality.
- Do not rerun stale local Bengali audio.
- Do not publish robotic, list-reading, mechanical, choppy, fallback, placeholder, stale, or mismatched audio.
- Do not expose Bengali audiobook controls until objective gates and listening tier pass.
- Do not use estimated sync for premium audiobook release.
- Do not let Bengali audiobook blockers hide valid reader-only books.

## Current Business Path

Keep Bengali reader-only books live with audio hidden. Continue UX, merge/deploy, and catalog reader improvements while the Bengali audio lane waits for materially new evidence.
