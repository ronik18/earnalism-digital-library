# English Audiobook Model Research Report

Recommendation: continue with an internal bake-off; do not publish audio.

## Findings

- Chatterbox TTS is the primary expressive benchmark, subject to approved reference/style voice governance.
- Kokoro 82M is the fast local baseline for speed and chunking validation.
- Dia is useful for dialogue comparison but requires license review and nonverbal-tag restraint.
- F5-TTS and XTTS-v2 remain research-only until license and model-card review are complete.

## Safety Decision

- Dracula remains readable only; audio is still disabled.
- No public audiobook endpoint, public audio URL, or Listen Now CTA is introduced.
- No external provider is called.
- No local synthesis is executed by default.

## Next Internal Step

Run:

```bash
npm run audiobook:english-model-bakeoff:plan
npm run audiobook:english-model-bakeoff:dry-run
npm run audiobook:english-model-bakeoff:evaluate
npm run audiobook:release-gate
```

Local synthesis can be considered only after explicit owner approval and remains internal review only.

