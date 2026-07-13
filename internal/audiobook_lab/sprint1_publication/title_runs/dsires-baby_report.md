# Désirée's Baby Parallel Sprint Report

Generated: `2026-07-13T04:13:10Z`

- Slug: `dsires-baby`
- Language: `English`
- Assigned lane: `3 - Short English Lane`
- Assigned agent: `Pasteur (019f59ac-9e6a-73d2-ae2e-1ea2b5b0468b)`
- Public reader: `Yes`
- Public audiobook: `No`
- Quality evidence: `NOT_RUN_NO_AUDIO_GENERATED`
- Estimated remaining cost: `$0.1669`
- Final state: `PROVIDER_NETWORK_REACHABILITY_REQUIRED`
- Blocker: `GOOGLE_TTS_DNS_UNAVAILABLE_IN_CURRENT_EXECUTION_SANDBOX_BEFORE_SYNTHESIS`
- Evidence: `internal/audiobook_lab/sprint1_publication/title_runs/dsires-baby_release_gate_evidence.json`
- Next action: Retry the same source-bound bounded Studio-C audition from a network-enabled shell.

## Preflight And Attempt

- Controlled source: `11,974` sanitized characters, one chapter, SHA-256 `587455ed554ef64d19f0ea7dcd31940d242aa759f5132b6514b130efa4a64a89`.
- Rights and sanitation: `PASS`.
- Historical Piper candidate: excluded because per-voice commercial/speaker rights remain on hold.
- Google audition: four source-bound samples, `1,808` billable characters, estimated `$0.03616`.
- Result: DNS resolution failed before synthesis; `provider_calls_ran=false`, `synthesis_calls=0`, no audio, no listening QA, no release mutation.
- Lock: restored byte-for-byte to SHA-256 `ab57e15c5329256304014ea8a77e086b7ec5748a0fee6423f772f350ef58b50e`.
- Spend booked: `$0.00`; actual provider billing is unavailable and no synthesis call occurred.

## Next Command

```bash
SPRINT1_TOTAL_AUDIO_BUDGET_USD=175 SPRINT1_MAX_USD_PER_TITLE=30 MAX_TTS_BUDGET_USD=175 EARNALISM_STOP_ON_BUDGET_EXCEEDED=true EARNALISM_APPROVE_GOOGLE_TTS_AUDITIONS=true EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD=40 EARNALISM_APPROVE_GOOGLE_ENGLISH_PRIVATE_AUDITION=true PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_google_english_private_pipeline.py audition --sanitized-source /tmp/earnalism-dsires-stage-acceleration-input/dsires-baby/sanitized_source.txt --input-manifest /tmp/earnalism-dsires-stage-acceleration-input/dsires-baby/input_manifest.json --paid-lock /Users/ronikbasak/Documents/GitHub/earnalism-digital-library/internal/earnalism_intelligence/locks/paid_tts.lock --private-output-dir /tmp/earnalism-dsires-stage-acceleration-private --voice en-GB-Studio-C --language-code en-GB --usd-per-million-chars 20 --run-budget-usd 1 --title-budget-usd 30 --sprint-budget-usd 175 --sprint-spend-usd 10.1766 --minimum-listening-score 9.4 --minimum-listening-confidence 0.9 --speaking-rate 0.94 --execute
```

No provider call, release-gate mutation, or public audio exposure was performed by this materializer.
