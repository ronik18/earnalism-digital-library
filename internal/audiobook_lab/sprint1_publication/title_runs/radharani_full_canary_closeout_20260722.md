# Radharani full-title canary closeout

Status: `NO GO — AUDIO HIDDEN`

The single owner-authorized Radharani canary generated a complete private Sarvam `bulbul:v3` / `ratan` / `literary_warm_pacing` audiobook, but it did not pass the non-substitutable audio-derived manuscript gate. Nothing was uploaded, exposed, or published.

## Evidence summary

- Source, rights, sanitation, front cover, and back cover: `PASS`.
- Reused representative audition: `9.4`, confidence `0.95`, no fatal flags.
- Private full-title TTS: `PASS`; 28/28 groups fresh, 3,563.116 seconds, SHA-256 `defeb886a990c68d297770f5d61c1ee239683c114fe06346751296a81f9476d8`.
- Raw `whisper-1`/auto ASR: `1.0962/10`, coverage `0.1096`, token order `0.1033`, first and last boundaries failed.
- Distinct `gpt-4o-mini-transcribe`/`bn` calibration: opening `7.9085`, middle `9.0441` with last-boundary failure, ending blocked by provider quota. The two completed samples had Bengali-script ratios of `0.9875` and `0.9882`, but script correctness does not replace exact source agreement.
- Zero-cost local multilingual Whisper `medium` with explicit `bn` was attempted once on the bound opening/middle/ending sample set. The process was killed with exit `137` during group 0 before it emitted JSON, a transcript, or word timestamps; groups 13 and 27 never started. The last process snapshot showed at least 37 seconds elapsed, 255% CPU, and 14.4% process memory on a 16 GiB host. Exact wall time was unavailable because `/usr/bin/time` was terminated before reporting.
- Measured sync, six-sample listening, private upload, metadata, and browser gates: not run because ASR failed first.
- Production audiobook endpoint: HTTP `404`; Radharani remains reader-live/audio-hidden.

## Cost and lock

- Estimated completed provider work for this canary: `$0.7363` (`$0.2281` TTS + `$0.4751` full ASR + `$0.0331` completed calibration calls).
- Conservative reserved pilot estimate: `$0.7539`, below the `$5.00` pilot cap.
- Actual provider billing was not reported.
- The authoritative paid lock was restored byte-for-byte after both paid stages. Terminal SHA-256: `24f5a1751ab3124898c0d5436e75ff7ea0244ef6f82718dcb4c461b3b2c3e482`; holder `none`; allowed next holders `[]`.

## Decision

Do not repeat the Sarvam TTS, `whisper-1`/auto, `gpt-4o-mini-transcribe`/`bn`, or local Whisper `medium`/`bn` fingerprints. Keep the title hidden from audiobook surfaces. A future attempt must use a materially different Bengali ASR provider or source-bound licensed/human narration evidence and must still pass every objective and downstream gate.
