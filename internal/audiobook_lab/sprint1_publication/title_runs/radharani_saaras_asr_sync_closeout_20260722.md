# Radharani Saaras ASR and sync closeout

Radharani remains **NO-GO / audio-hidden**. The fresh private Sarvam `ratan` narration was not uploaded or published.

## What improved

- Saaras v3 with explicit `bn-IN` correctly exposed that the earlier mixed-script OpenAI transcript was an evaluator failure.
- A deterministic ordered Bengali projection scored `9.776`, `9.818`, and `9.737` normalized; phonetic projection scored `9.936`, `9.898`, and `9.883`. These are useful diagnostics only and do not replace the raw release score.
- Raw scores were only `8.6275`, `8.8971`, and `8.7179`. Strict reanalysis also found unexplained missing/extra phonetic spans in every sample, so none passes the current exact-content policy.

## Why it did not release

- The checkpointed full run stopped after group 1. Group 0's historical recorded pass is superseded: its raw score was `8.6275` and strict reanalysis found two missing and three extra spans. Group 1 scored raw `8.3099`, normalized `9.606`, and retained four missing and five extra spans. Zero groups pass the current policy.
- Sarvam REST returned measured clip segments, not usable word timestamps. The distinct `verbatim` arm returned segment-only timestamps for all three bounded samples.
- Local Whisper base transcription reached only `3.416` phonetic projection and `0.3416` coverage.
- Stable Whisper base forced alignment reported 141/191 words unaligned and 20/41 failed segments, with mean probability `0.0758`; it was rejected.
- Six-sample listening, upload/checksum, metadata, endpoint, and browser gates were not run.

Conservative cumulative Radharani estimate is `$0.8895` against the approved `$5` cap; actual provider billing was not reported. The paid lock is idle and restored to SHA-256 `24f5a1751ab3124898c0d5436e75ff7ea0244ef6f82718dcb4c461b3b2c3e482`.

Production truth remains HTTP `404` for Radharani audio. Do not repeat any closed fingerprint or describe segment timing as word-level sync.
