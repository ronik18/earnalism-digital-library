# Désirée's Baby Stage 2H Report

Generated: `2026-07-13T04:50:38Z`

- Slug: `dsires-baby`
- Public reader: `Yes`
- Public audiobook: `No`
- Source/rights/sanitation: `PASS`
- Source: `11,974` characters, one chapter, SHA-256 `587455ed554ef64d19f0ea7dcd31940d242aa759f5132b6514b130efa4a64a89`
- Provider/voice: Google Cloud TTS / `en-GB-Studio-C`
- Audition fingerprint: `bccf002da4e9713e3870b602c07e65ae1ad0a49fbd1904e5730b823a0d605d4e`
- Private audition manifest: `/private/tmp/earnalism-dsires-stage-acceleration-private/dsires-baby/audition/bccf002da4e9713e/audition_manifest.json`
- TTS estimate: `$0.03616`; actual provider billing not reported
- Listening-QA estimate: `$0.20`; actual provider billing not reported
- Stage estimate: `$0.23616`
- Lock: restored byte-for-byte to `active`, holder `none`, allowed next holders `[]`
- Final state: `ALTERNATE_VOICE_AUDITION_REQUIRED`

## Listening QA

| Passage | Score | Confidence | Fatal flags |
| --- | ---: | ---: | --- |
| opening | 9.4 | 0.95 | none |
| middle | 8.4 | 0.90 | none |
| dialogue_or_risk | 7.5 | 0.85 | robotic texture; mechanical cadence |
| ending | 9.4 | 0.95 | none |

The source-bound Studio-C candidate failed the required all-sample `9.4` and confidence `0.9` gates. The dialogue passage was rushed and mechanically delivered. Full TTS, ASR, upload, release-state mutation, and publication did not run. This exact Studio-C fingerprint must not be repeated.

## Next Command

Run one materially different, source-bound Chirp3-HD-Achird audition. If it also fails, stop automated Google retries and create the human narration/licensed-audio packet.

```bash
SPRINT1_TOTAL_AUDIO_BUDGET_USD=175 SPRINT1_MAX_USD_PER_TITLE=30 MAX_TTS_BUDGET_USD=175 EARNALISM_STOP_ON_BUDGET_EXCEEDED=true EARNALISM_APPROVE_GOOGLE_TTS_AUDITIONS=true EARNALISM_GOOGLE_TTS_MAX_ESTIMATED_USD=1 EARNALISM_APPROVE_GOOGLE_ENGLISH_PRIVATE_AUDITION=true EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD=2 EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD=0.05 EARNALISM_ENABLE_OPENAI_LISTENING_QA=true EARNALISM_OPENAI_LISTENING_QA_MODEL=gpt-audio PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_google_english_private_pipeline.py audition --sanitized-source /tmp/earnalism-dsires-stage-acceleration-input/dsires-baby/sanitized_source.txt --input-manifest /tmp/earnalism-dsires-stage-acceleration-input/dsires-baby/input_manifest.json --paid-lock /Users/ronikbasak/Documents/GitHub/earnalism-digital-library/internal/earnalism_intelligence/locks/paid_tts.lock --private-output-dir /tmp/earnalism-dsires-stage-acceleration-private --voice en-GB-Chirp3-HD-Achird --language-code en-GB --usd-per-million-chars 20 --run-budget-usd 1 --title-budget-usd 30 --title-spend-usd 0.23616 --sprint-budget-usd 175 --sprint-spend-usd 10.41276 --minimum-listening-score 9.4 --minimum-listening-confidence 0.9 --speaking-rate 0.90 --execute
```

No audio was uploaded, published, copied to a public frontend path, or approved for release.
