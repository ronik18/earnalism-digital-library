# Bengali Audiobook Completion Campaign Policy

Status: active
Policy version: bengali_audiobook_acceptance_v2_92
Scope: the 31 Bengali titles already approved reader-only with audio hidden.

## Mission

Every Bengali campaign title must end in exactly one durable state:

- `BENGALI_AUDIOBOOK_LIVE`
- `HUMAN_NARRATION_REQUIRED`
- `LICENSED_AUDIO_IMPORT_REQUIRED`
- `EXTERNAL_ACTION_REQUIRED`

The campaign is resumable. Each run must read campaign state, provider memory,
title history, and the campaign ledger before attempting work.

## Release Gates

Listening gate:

- representative or full-book listening score `>= 9.2`
- confidence `>= 0.90`
- no fatal red flags:
  - `robotic_texture_detected`
  - `mechanical_cadence_detected`
  - `list_reading_rhythm_detected`
  - `choppy_joins_detected`
  - `fallback_tts_detected`

Objective gates:

- source/content/TOC PASS
- rights PASS
- covers PASS
- ASR/manuscript match `>= 9.7`
- first and last words match
- no missing, duplicated, or reordered content
- measured paragraph/stanza sync or better
- `auto_estimated_sync=false`
- upload/checksum PASS
- metadata approval PASS
- audiobook endpoint `200/206`
- browser gate PASS
- blocker list empty

Never publish from an isolated high-scoring sample. A representative audition
must pass before a full audiobook pilot can run, and a full pilot must pass all
objective gates before any canary or wave is allowed.

## Optimizer Rules

Primary automated provider: Sarvam `bulbul:v3`.

Use the provider memory to avoid duplicate failed settings. Cache attempts by:

- provider
- model
- voice
- style profile
- text-prep variant
- postprocess variant
- passage/text hash

Allowed TTS-only prep variants:

- `canonical_clean`
- `punctuation_normalized`
- `literary_pause_control`
- `dialogue_human_touch`
- `anti_list_reading_flow`
- `anti_mechanical_cadence`
- `stanza_paragraph_breathing`
- `emotional_but_restrained`
- `child_voice_avoidance`
- `calm_literary_storyteller`

The canonical reader manuscript must not be changed for TTS prep.

## Iteration And Escalation

Per title:

- duplicate attempt count is zero.
- no more than two near-identical same-provider attempts.
- if three materially different settings fail to improve by at least 0.2, treat that as a plateau.
- if repeated fatal red flags persist, treat that as a plateau.
- if representative score remains below 8.8 after materially different settings, treat that as a plateau.

Plateau means switch strategy, not abandon the title:

1. new text-prep family
2. new voice family
3. new provider only with evidence or credentials
4. human narration packet
5. licensed audio import packet

## Scale Policy

Scale only after evidence:

1. one full pilot passes and publishes
2. then 3-title canary
3. then 10-title wave
4. then remaining titles

Any systemic failure pauses the wave and returns the campaign to optimizer or
escalation mode.

## Cost And Approval Gates

Paid/provider work requires explicit env gates:

- `EARNALISM_APPROVE_SARVAM_CORRECTIVE_AUDITIONS=true`
- `EARNALISM_APPROVE_BENGALI_PROVIDER_BAKEOFF=true`
- `EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS=true`
- `EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN=true`
- `EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD` set
- `EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE` set
- `EARNALISM_STOP_ON_BUDGET_EXCEEDED=true`

If approval or budget is missing, do not call providers. Write state, reports,
and the exact continuation command.

## Reader-Only Protection

Bengali reader-only/audio-hidden status must remain intact until an audiobook
passes every gate. Do not expose audio controls, stale audio, fallback audio, or
estimated sync while a title is in campaign states before `BENGALI_AUDIOBOOK_LIVE`.
