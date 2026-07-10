# bn-066 Stage 3D ASR Mismatch Diagnosis / Source Alignment Report

Generated: 2026-07-10T20:02:48Z

## Result

`ASR_LANGUAGE_CONFIG_AND_NORMALIZATION_REPAIR_REQUIRED`

The owner-authorized bounded resume completed all 152 OpenAI transcription chunks against the existing private Stage 2 audiobook. Every chunk wrote a durable `PASS` checkpoint; no chunk timed out, failed, or required a retry. The prior `group_0079` stall boundary was crossed successfully.

The resulting transcript does not satisfy the Bengali audiobook source gate. It is Devanagari-dominant mixed script, producing a raw source alignment score of `0.8403/10`, normalized Bengali score `0.0781`, phonetic projection score `0.211`, and projection confidence `0.0188`. Raw first and last ASR words do not match the manuscript boundaries.

Stage 3D made no provider calls. It diagnosed the saved checkpoints and repaired verifier semantics only.

## Budget And Lock

- Total cap: `5 USD`
- Stage 3C ASR retry cap: `3 USD`
- Estimated current ASR cost: `2.86 USD`
- Prior Stage 2 TTS estimate: `1.2226 USD`
- Estimated Stage 2 TTS plus Stage 3C ASR: `4.0826 USD`
- Listening-QA cap: `0.75 USD`
- Listening-QA spend in Stage 3C: `0 USD` because the source gate failed
- Actual ASR billing: not reported by provider tooling
- Prior partial Stage 3 ASR billing: unknown, with owner-accepted risk for this single retry
- Lock holder during run: `audiobook_enablement_sprint_3c_bn_066_asr_resume`
- Lock after run: active, `current_holder: none`, `allowed_next_holders: []`

## Checkpoint Completion

- Total: `152`
- PASS: `152`
- PROVIDER_TIMEOUT: `0`
- FAILED: `0`
- More than one attempt: `0`
- Checkpoint directory: `internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts/asr_checkpoints`

## Source Results

- ASR/source score: `0.8403/10` (`9.7` required)
- Raw similarity: `0.2028`
- Coverage: `0.084`
- Normalized Bengali score: `0.0781`
- Phonetic/shadow score: `0.211`
- Projection confidence: `0.0188`
- First words match: `false`
- Last words match: `false`
- Frontmatter absent: `true`
- Word timestamps returned: `21649`
- Raw ASR script classification: `mixed`
- Bengali characters: `22749` (`0.2801` of Bengali/Devanagari/Latin script characters)
- Devanagari characters: `57779` (`0.7113`)
- Latin characters: `700` (`0.0086`)
- ASR language code sent for Bengali: empty; `whisper-1` auto-detected each chunk independently

## Construction Audit

The static TTS provenance audit now passes with 100% TTS input coverage, canonical-to-clean-text score `1.0`, valid first/last prepared-text boundaries, matching group audio hashes, and all 152 groups present in order.

`group_repair.status: NOT_REQUESTED` is a legacy fresh-generation state, not a failed repair. The verifier now accepts it only when no repair was requested and the complete construction audit passes. New fresh-generation manifests emit `NOT_NEEDED`. If repair was required, attempted, failed, or evidence is incomplete, `NOT_REQUESTED` remains blocked.

Construction evidence is `PASS_DIAGNOSTIC_ONLY`; it does not override the failed ASR/source gate or authorize listening QA/release readiness.

## Mismatch Diagnosis

- `group_0000` and `group_0076` are more than 99.6% Devanagari script but phonetically follow their expected Bengali source chunks.
- `group_0151` is Bengali script and follows the expected ending dialogue, with ASR omissions and spelling variants.
- The prepared TTS manuscript reconstructs exactly from the chunk texts after normalization: score `10.0`, coverage `1.0`, and first/last boundaries pass.
- The raw display manuscript begins with source/page boilerplate; the TTS prepared source begins with literary content. This explains a source expectation layer mismatch.
- Existing projection first/last checks pass while raw first/last checks fail, confirming boundary-layer inconsistency rather than authorizing a pass.

Confirmed root causes: `ASR_LANGUAGE_CONFIG_REPAIR_REQUIRED`, `ASR_MODEL_OUTPUT_MIXED_SCRIPT`, `ASR_NORMALIZATION_REPAIR_REQUIRED`, `SOURCE_ALIGNMENT_LAYER_MISMATCH`, `FIRST_LAST_EXPECTATION_LAYER_MISMATCH`, and `GROUP_REPAIR_VERIFIER_SEMANTICS_BUG`.

`TRUE_AUDIO_SOURCE_MISMATCH`, `TTS_CHUNK_ORDER_MISMATCH`, and `CHECKPOINT_TRANSCRIPT_CORRUPT` are not proven.

## Listening QA

Listening QA did not run. The ASR/source gate failed first, so the hook stopped before spending the bounded listening-QA allowance.

## Release Status

`bn-066` is not ready for release-gate owner approval. The full audiobook remains private/audio-hidden. No upload, publication, Listen CTA, player UI, release-gate mutation, static audio fallback, browser speech fallback, word-level sync claim, AudioObject, paid Listen approval, or launch-wide 10/10 claim occurred.

## Next Action

Run an owner-authorized, bounded ASR language/model recalibration on a tiny representative set of existing chunks. Require Bengali-script output before any full alignment retry. If recalibrated Bengali-script ASR remains below threshold, repair normalization/alignment next. Do not regenerate TTS unless later evidence proves a true audio/source mismatch.
