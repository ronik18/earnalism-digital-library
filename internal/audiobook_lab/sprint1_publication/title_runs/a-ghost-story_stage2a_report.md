# A Ghost Story Stage 2A Report

Generated: `2026-07-12T08:16:11Z`

## Decision

`SPRINT_TARGET_INCOMPLETE_RUNTIME_GATES_MISSING`

A Ghost Story remains a public reader with audio hidden. No public-audio state changed because all ten required live-shell budget and listening-QA gates were absent.

## Evidence

- Source/rights: `PASS`
- Sanitized text: `PASS` (`13,216` characters; `2,465` words)
- Existing private audio: `PASS` (`4,594,121` bytes; `765.573515` seconds)
- Audio SHA-256: `00190d747d2894a244545a260f10f4e06ccc597352d2767414acc4edfe6e5a55`
- ASR/source: `9.7882/10 PASS`
- First/last words: `PASS / PASS`
- Listening QA: `NOT_RUN_LIVE_SHELL_GATES_MISSING`
- Previous listening packet: `0.0`, confidence `0.8`; not release-valid
- Estimated listening QA: `6` samples x `$0.05` = `$0.30`
- Actual spend: `$0.00`

The preflight now supports external `/tmp` output roots. The ASR hook can also reuse local sidecars only when both the audio hash and sanitized-source hash match and sync/source scores remain at least `9.7`; this avoids unnecessary retranscription without trusting stale public metadata.

The bounded continuation wrapper passed dry-run validation. It forbids ASR provider fallback, requires exact listening-QA caps, and restores the original paid lock bytes on every normal exit path.

## Production Truth

- `/api/books/a-ghost-story`: `200`, reader enabled, audio disabled
- `/api/reader/book/a-ghost-story/manifest`: `200`, audio disabled, no provider/voice/URL/assets
- `/api/reader/book/a-ghost-story/audiobook`: `404` fail-closed
- Approved `book-2b9853ec52` range request: `206`, `1,024` bytes
- Production bundle: no browser speech API, static `/audio/` literal, or word-level sync claim
- Production contact: `.org` present; `.in` absent
- Public audio mutation: `none`
- New Listen/AudioObject exposure: `none`

## Next Command

Run from a shell where `OPENAI_API_KEY` remains available. The wrapper validates all caps and hash-bound sidecars, acquires `paid_tts.lock` as `sprint1_publication_stage2a`, runs only bounded listening QA, and restores the original lock bytes in `finally`.

```bash
env SPRINT1_TOTAL_AUDIO_BUDGET_USD=175 SPRINT1_MAX_USD_PER_TITLE=30 MAX_TTS_BUDGET_USD=175 EARNALISM_STOP_ON_BUDGET_EXCEEDED=true EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD=10 EARNALISM_ASR_RETRY_MAX_ESTIMATED_USD=10 EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE=0.008 EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD=2 EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD=0.05 EARNALISM_ENABLE_OPENAI_LISTENING_QA=true EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio python3 internal/audiobook_lab/scripts/sprint1_stage2a_a_ghost_story_listening_qa.py
```
