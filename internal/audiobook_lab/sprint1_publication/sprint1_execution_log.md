# Sprint 1 Publication Stage 2 Execution Log

Generated: `2026-07-12T07:44:15Z`

1. Loaded active Earnalism intelligence, Sprint 1 matrices, release evidence, and lock state.
2. Confirmed 32 active audio targets and 2 deferred long classics.
3. Confirmed required paid runtime gates were absent; made zero provider calls and spent $0.00.
4. Ran bn-066 three-chunk calibration in dry-run mode only; planned 6 calls at $0.1047 and blocked before provider access.
5. Audited production API: 15 active reader routes live, 17 returning 404.
6. Diagnosed Railway package parity plus legacy audio-approval contradictions in reader packets.
7. Prepared, merged, and deployed reader-only fix PR #101 (`faf8587` / Railway `4e190b99-acec-4755-83db-82cbe15bd852`).
8. Validation: 64 focused tests pass; 491 JSON files parse and listed checksums match; cover audit 71 scanned/0 typography-only/0 broken.
9. Broad backend test run: 612 passed, 71 failed, 49 errors; failures include local-service dependencies and legacy Dracula-only assumptions, so this is documented rather than called green.
10. Diagnosed cache-header CORS regression, merged PR #102 (`11f0de6`), and deployed Railway `9100d4d8-47b5-4859-94b5-9ca118cff32c`.
11. Final production API validation: 32/32 book endpoints and manifests HTTP 200; only book-2b9853ec52 audio enabled.
12. Final production UI validation: 132/132 desktop/mobile route checks pass.
13. No new public-audio approval, paid audio, lock mutation, static fallback, browser speech, or word-level sync claim occurred.
14. Stage 2A verified all ten required live-shell budget/listening-QA gates were missing; OpenAI, Sarvam, and Google credentials were detected without exposing values, while ElevenLabs was absent and not required for the existing-audio reuse path.
15. Repaired non-paid preflight external-output handling and added hash-bound local sidecar reuse so A Ghost Story can run listening QA without retranscription or stale public metadata.
16. A Ghost Story preflight passed rights, sanitation, asset hash, ASR/source `9.7882`, and first/last boundaries. Schema-3 listening QA did not run; spend remained `$0.00`.
17. Production stayed fail-closed: book and manifest `200`, manifest audio disabled, no public audio assets, audiobook endpoint `404`. No queue title after A Ghost Story was paid-processed because the global runtime gates were absent.
18. Added and dry-ran a lock-safe A Ghost Story listening-QA wrapper; it validates exact caps and hash-bound sidecars, acquires only `sprint1_publication_stage2a`, and restores the original lock bytes in `finally`.
19. Stage 2B supplied all required caps inline and ran six bounded `gpt-audio` listening judgments against the hash-verified A Ghost Story asset. Estimated QA spend was `$0.30`; actual provider billing was not reported.
20. Listening QA blocked release: minimum sample score `8.3`, confidence `0.90`, with pacing `7.9` and emotional expression `8.2` on `middle_60s`; no fatal flags were detected.
21. No TTS, ASR, upload, publication, deployment, or release-gate mutation occurred. A Ghost Story stayed reader-public/audio-hidden, and no later queue title was processed.
22. The paid lock was restored byte-for-byte to active/current-holder-none/empty-next-holders. The wrapper now returns nonzero for a blocked hook and prevents repeating the same completed audio-hash/model QA attempt.
