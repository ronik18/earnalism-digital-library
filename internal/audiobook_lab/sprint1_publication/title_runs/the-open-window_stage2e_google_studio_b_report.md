# The Open Window Stage 2E Google Studio-B Report

- Owner decision: `AUTHORIZE_STAGE_2E_THE_OPEN_WINDOW_STUDIO_B_AUDITION_AND_PUBLICATION_IF_PASS`
- Run: `sprint1-stage2e-the-open-window-en-gb-studio-b`
- Provider / voice: Google Cloud TTS / `en-GB-Studio-B`
- Scope: four source-bound representative passages, each capped at 30 seconds
- Result: `AUDITION_REPAIR_REQUIRED`
- Full generation: not run
- Publication or release-gate mutation: not run

## Listening Results

| Passage | Overall | Confidence | Fatal flags |
| --- | ---: | ---: | --- |
| `opening_dialogue` | 9.4 | 0.95 | none |
| `shooting_party_tragedy` | 9.5 | 0.95 | none |
| `twilight_return` | 7.2 | 0.90 | robotic texture; mechanical cadence |
| `spaniel_explanation_ending` | 9.4 | 0.95 | none |

The final Studio-B audition did not clear the representative gate. The twilight transition regressed below the prior Studio-C prosody score of 8.5 and introduced two fatal delivery flags. The failure is provider/voice/prosody quality, not source, rights, sanitation, or reader availability.

## Budget And Lock

- Estimated Google TTS: `$0.0178`
- Estimated OpenAI listening QA: `$0.2000`
- Estimated Stage 2E spend: `$0.2178`
- Estimated title cumulative spend: `$0.6534`
- Estimated Sprint 1 cumulative spend: `$4.2862 / $175.0000`
- Estimated Sprint 1 remaining: `$170.7138`
- Actual provider billing: not reported
- Lock restored byte-for-byte: yes
- Lock SHA-256 before/after: `ab57e15c5329256304014ea8a77e086b7ec5748a0fee6423f772f350ef58b50e`

## Release Decision

The Open Window remains public-reader/audio-hidden. No Piper asset, failed Studio-C candidate, or failed Studio-B sample may be exposed. No full TTS, upload, production manifest, endpoint, frontend Listen state, or `AudioObject` was created.

## Exact Repair Command

This non-provider command prepares a source-bound human narration packet. It does not generate audio, call providers, or mutate release gates. Automated Google retries stop here because Studio-C and Studio-B both failed the same transition and Studio-B introduced fatal delivery flags.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_prepare_human_narration_packet.py --slug the-open-window --asset-root /Users/ronikbasak/Documents/GitHub/earnalism-digital-library --output-root internal/audiobook_lab/sprint1_publication/human_narration_packets
```
