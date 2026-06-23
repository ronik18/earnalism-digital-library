# ElevenLabs Dracula Sample Cost-Control Plan

This plan is for one internal evaluation sample only.

## Limits

- First pass: 30-45 seconds if the manual UI supports it.
- Second pass: 2-3 minutes only.
- Maximum source: `sample_text.txt`.
- Full chapter generation: blocked.
- Full audiobook generation: blocked.
- Repeat regeneration: blocked unless QA notes explain the defect.

## Required Evidence To Record

- `text_hash`
- `settings_hash`
- `voice_id`
- `provider`
- `generated_at`
- owner reviewer
- legal/internal review status
- QA decision

## Safety

- No ElevenLabs API call from this repository.
- No automatic generation.
- No public audio URL.
- No public player.
- No public audio metadata.
- No file under `frontend/public` or `frontend/build`.
