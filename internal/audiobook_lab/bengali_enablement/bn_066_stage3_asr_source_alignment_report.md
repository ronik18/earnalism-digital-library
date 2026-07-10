# bn-066 Stage 3 ASR / Source Alignment Report

Generated: 2026-07-10T17:34:29Z

## Result

`ASR_CHECKPOINT_REPAIR_REQUIRED`

A bounded full-book ASR/source alignment attempt was authorized and started for `bn-066`, using the existing `asr_sync_hook.py` path against the private Stage 2 MP3. The hook added and passed the ASR budget guard, then progressed through chunked OpenAI transcription until a provider response stalled around `group_0079`. The process was interrupted fail-closed so `paid_tts.lock` could be restored. This is not a final title NO-GO; it is a resumability defect in the ASR workflow.

## Budget Gate

- Gate added/found: `EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD`
- ASR cap used: `3 USD`
- Total cap used: `5 USD`
- Prior TTS estimate: `1.2226 USD`
- Full ASR estimate: `2.86 USD`
- Listening QA estimate: `0.3 USD`
- Total planned estimate: `4.3826 USD`
- Guard artifact: `internal/audiobook_lab/bengali_enablement/bn_066_stage2_full_book_tts/asr_sync_budget_guard.json`

## Execution

- ASR ran: `true`
- ASR completed: `false`
- Last observed chunk: `group_0079` of `152`
- Complete transcript written: `false`
- Alignment diagnosis written: `false`
- Actual provider billing: not reported by provider tools
- Stage 3B provider calls run: `false`
- Checkpointing source repair: implemented in `internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py`

## Results

- Source alignment score: not available
- Normalized Bengali score: not available
- Phonetic/shadow score: not available
- First words match: not proven by ASR
- Last words match: not proven by ASR
- Per-chunk health: not available

## Classification

`ASR_CHECKPOINT_REPAIR_REQUIRED`

## Next Action

Run the owner-approved bounded ASR resume command with checkpointing enabled, request timeout set, retry cap set, and explicit ASR retry budget cap present. Do not publish or expose Listen until ASR/source alignment and listening QA pass.
