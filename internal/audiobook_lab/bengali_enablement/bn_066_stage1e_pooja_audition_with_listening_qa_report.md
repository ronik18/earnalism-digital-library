# bn-066 Stage 1E Pooja Audition With Listening QA Report

Generated: 2026-07-10T08:46:54Z

## Result

`AUDITION_BLOCKED_LISTENING_QA_BUDGET_GATE_MISSING`

Stage 1E verified the command-scoped paid TTS gates, `SARVAM_API_KEY`, `OPENAI_API_KEY`, `EARNALISM_ENABLE_OPENAI_LISTENING_QA=true`, and `EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio`. The listening-QA code path reads the model env, but no repo-enforced bounded OpenAI/listening-QA USD cap was found. Because the owner scope requires OpenAI listening QA to count under the same `5 USD` cap, the run stopped before lock acquisition and before any Sarvam or OpenAI provider call.

## Budget

- Authorized cap: `5.00 USD`
- Estimated TTS sample cost carried forward: `0.0119 USD`
- Actual spend: `0.00 USD`
- Budget remaining: `5.00 USD`
- Bounded listening-QA spend gate: missing

## Lock

- Before: active, `current_holder: none`, `allowed_next_holders: []`
- During: not acquired
- After: active, `current_holder: none`, `allowed_next_holders: []`

## Provider Plan

- Slug: `bn-066`
- Title: `Anandamath`
- Provider: `sarvam`
- Voice: `pooja`
- Style: `literary_warm_pacing`
- Max sample duration: `45` seconds
- Output audio path: none

## QA

- Listening QA: not run
- ASR/source alignment: not run
- First/last words: not run
- Classification: `AUDITION_REPAIR_REQUIRED`
- Full-book readiness: not ready for owner approval

## Release Truth

- No full-book TTS.
- No upload or publication.
- No public Listen CTA.
- No release-gate mutation.
- No static `/audio/...` fallback.
- No browser speech fallback.
- No word-level sync claim.
- No AudioObject for non-approved audio.

## Next Action

Add or authorize a repo-enforced bounded OpenAI/listening-QA USD cap gate, then rerun one `bn-066` Sarvam/pooja representative audition under the same `5 USD` total cap.
