# bn-066 Stage 1F Pooja Audition With Bounded Listening QA Report

Generated: 2026-07-10T09:31:50Z

## Result

`AUDITION_PASS`

Stage 1F added a fail-closed OpenAI listening-QA budget gate and ran exactly one `bn-066` representative audition with Sarvam `pooja` and `literary_warm_pacing`.

## Budget

- Authorized total cap: `5.00 USD`
- Listening-QA sub-cap: `1.00 USD`
- Estimated TTS cost: `0.0119 USD`
- Estimated listening-QA cost: `0.05 USD`
- Estimated total spend: `0.0619 USD`
- Actual provider billing: not reported by provider tools
- Estimated remaining budget: `4.9381 USD`

## Lock

- Before: active, `current_holder: none`, `allowed_next_holders: []`
- During: `audiobook_enablement_sprint_1`
- After: active, `current_holder: none`, `allowed_next_holders: []`

## Output

- Provider: `sarvam`
- Voice: `pooja`
- Style: `literary_warm_pacing`
- Audio path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa/auditions/sarvam/pooja/narrative_opening_0b81b0844d4d_clipped.mp3`
- Source WAV path: `internal/audiobook_lab/bengali_enablement/bn_066_stage1f_pooja_audition_bounded_listening_qa/auditions/sarvam/pooja/narrative_opening_0b81b0844d4d.wav`
- Duration: `45.0` seconds

## Listening QA

- Status: `PASS`
- Release policy: `bengali_audiobook_acceptance_v2_92`
- Overall listening score: `9.3`
- Confidence: `0.95`
- Naturalness: `9.5`
- Pronunciation: `9.4`
- Emotional expression: `9.3`
- Punctuation pause: `9.2`
- Pacing: `9.1`
- Continuity: `9.4`
- Anti-robotic texture: `9.6`
- Anti-choppy join: `9.5`
- Listener enjoyment: `9.3`
- Fatal flags: none
- Frontmatter present: false
- Judge blockers: none

## ASR / Source

ASR/source alignment was not run in this stage. The existing available ASR path uses provider-backed transcription, and this sprint only added a bounded listening-QA gate. Run ASR/source alignment in the full-book owner-approved stage with its own bounded cap and objective gates.

## Readiness

`bn-066` is ready for a full-book TTS owner-approval prompt. It is not ready for public Listen, upload, publication, or release-gate approval.

## Release Truth

- No full-book TTS.
- No upload or publication.
- No public Listen CTA.
- No release-gate mutation.
- No static `/audio/...` fallback.
- No browser speech fallback.
- No word-level sync claim.
- No AudioObject for non-approved audio.
