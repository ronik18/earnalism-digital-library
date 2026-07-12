# The Open Window Stage 2D Replacement-Provider Audition

Generated: `2026-07-12T17:22:03Z`

## Decision

- Public reader: `YES`
- Public audiobook: `NO`
- Existing Piper asset: disallowed for public release
- Google Studio-C representative audition: `REPAIR_REQUIRED`
- Full TTS, upload, manifest mutation, and publication: `NOT_RUN`
- Classification: `AUDIO_HIDDEN_GOOGLE_STUDIO_C_TWILIGHT_TRANSITION_REPAIR_REQUIRED`

## Boundaries

The audition was bound to the ready controlled-publication chapter at `data/controlled_publications/the-open-window/chapters/chapter-001.json`, sanitized SHA-256 `f43d04cc2097668e91190ada89e283ad4908c360c4d7f6011a44b8f83d9659be`. Four story-specific samples covered opening dialogue, the shooting-party tragedy, the twilight return, and the spaniel explanation/ending. Every generated sample remained below the `30s` cap.

## Results

| Attempt | Voice/style | Sample scores | Minimum confidence | Fatal flags | Decision |
| --- | --- | --- | ---: | --- | --- |
| Baseline | Google `en-GB-Studio-C`, rate `0.94` | `9.4`, `8.4`, `8.0`, `8.4` | `0.85` | none | repair required |
| Single prosody retry | Google `en-GB-Studio-C`, source-preserving SSML at `88%` | `9.5`, `9.4`, `8.5`, `9.4` | `0.90` | none | repair required |

The bounded prosody retry materially improved three passages, but `twilight_return` remained below the `9.4` owner minimum at `8.5`. No third attempt or full generation ran.

## Budget And Lock

- Baseline estimate: `$0.2178`
- Prosody retry estimate: `$0.2178`
- Estimated title spend: `$0.4356`
- Estimated Sprint 1 cumulative spend: `$4.0684`
- Estimated budget remaining: `$170.9316`
- Actual provider billing: not reported
- `paid_tts.lock`: restored byte-for-byte to active/current-holder-none/empty-next-holders after both attempts

## Exact Next Command

This command requires a separate owner approval for one final voice change. It remains representative-only and cannot publish:

```bash
PYTHONDONTWRITEBYTECODE=1 \
SPRINT1_TOTAL_AUDIO_BUDGET_USD=175 \
SPRINT1_MAX_USD_PER_TITLE=30 \
MAX_TTS_BUDGET_USD=175 \
EARNALISM_STOP_ON_BUDGET_EXCEEDED=true \
EARNALISM_APPROVE_GOOGLE_TTS_AUDITIONS=true \
EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD=1 \
EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS=0.02 \
EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD=2 \
EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD=0.05 \
EARNALISM_ENABLE_OPENAI_LISTENING_QA=true \
EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio \
python3 internal/audiobook_lab/scripts/sprint1_stage2d_the_open_window_google_audition.py \
  --voice en-GB-Studio-B \
  --prior-sprint-estimated-spend-usd 4.0684 \
  --prior-title-estimated-spend-usd 0.4356 \
  --asset-root /Users/ronikbasak/Documents/GitHub/earnalism-digital-library \
  --output-root /tmp/earnalism-the-open-window-stage2d-google-audition
```
