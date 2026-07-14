# Sprint 1 EOD Audio Rescue Report

The closure run processed exactly one rescue candidate: `sredni-vashtar`. It reused the canonical private audio candidate and did not run TTS, ASR, or listening-provider calls.

## Sredni Result

- Candidate: `candidate-61355c7842dbcbae`
- Dedup group: `dedup-4fb10f2026b8c586`
- ASR/source: `9.8426`
- First/last: PASS
- Listening: `9.4, 9.4, 9.4, 9.5, 9.4, 9.4`
- Confidence: `0.95`
- Fatal flags: none
- Measured sync: `9.7997`, published mode planned as section-following
- Sidecar, manifest, upload checksum, and local release-state validation: PASS
- Release PR: #121, merged as `b337300763b874b434938ee09519208512be34bb`
- Incremental generation/QA cost: `$0.00`

Production publication did not complete. The Railway backend-root archive upload returned HTTP `500`; production remains audio-disabled and proxy `404`. The title is therefore not counted as public or YES+YES.

## Launch Effect

No new audiobook was added in production. EOD go-live remains approved for 32 public readers and the two existing evidence-gated audiobooks. Sredni should be the first post-launch action because it needs only deployment and production validation, not further audio generation.
