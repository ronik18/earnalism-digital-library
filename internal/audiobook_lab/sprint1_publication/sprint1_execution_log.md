# Sprint 1 Publication Stage 2 Execution Log

Generated: `2026-07-12T17:22:03Z`

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
23. Stage 2C corrected the original middle sample to sentence boundaries and confirmed the existing audio had a real weak section (`6.8`, confidence `0.85`, robotic/mechanical flags).
24. Three bounded OpenAI selector arms were evaluated; `verse/mystery_suspense_narrator` was best at `9.5`, confidence `0.95`, with no fatal flags.
25. Full candidate v1 passed ASR at `9.7719` but exposed five mid-sentence TTS chunk boundaries and listening quality `8.3` in the weak section.
26. The boundary verifier now treats exact compound equivalence such as `bath-tub` and `bathtub` correctly while still rejecting missing endings.
27. Full candidate v2 used sentence-terminal chunks but ASR proved a 50-token provider omission, so it was rejected before listening QA.
28. Full candidate v3 used nine sentence-safe chunks capped at 1,600 characters. ASR/source passed at `9.928`, and first/last checks passed.
29. V3 listening QA still blocked release: minimum `8.3`, confidence `0.90`, and list-reading rhythm detected. OpenAI was classified as a provider-quality plateau; no further OpenAI variant was run.
30. Hash-bound ASR checkpointing now persists provider results before downstream gates, and six-sample selection now spans the actual full chunk sequence including the ending.
31. Estimated Stage 2B plus Stage 2C provider spend is `$2.3295`; actual billing was not reported. The lock was restored byte-for-byte after every paid command.
32. A Ghost Story remained reader-public/audio-hidden. No upload, publication, deployment, or release-gate mutation occurred.
33. The Open Window non-paid continuation confirmed production reader `200/200`, rights and sanitation PASS, and diagnostic ASR `9.7826` with a title-prefixed audio manuscript. Its Piper/synthetic asset remains ineligible for public audio.
34. Google Cloud TTS capability probing is blocked by ADC reauthentication, and ElevenLabs credentials are absent. Exact next command: `gcloud auth application-default login`.
35. Stage 2D restored Google ADC and ran bounded Studio-B and Studio-C auditions. Baseline middle samples scored `8.3`; one source-preserving Studio-C prosody repair passed three representative samples at `9.4`, confidence `0.95`, with no fatal flags.
36. One full Google Studio-C candidate was generated in nine sentence-safe chunks: `880.944s`, `7,047,789` bytes, SHA-256 `c0e52985ee1e3e178b81d83157189251a667d64ecbc22bbc0940e6e4fc7bf904`.
37. Full ASR/source passed at `9.88`, first/last checks passed, and six listening samples scored `9.4-9.5` with confidence `0.95` and no fatal flags. No `10/10` claim is made.
38. The B2 upload hook verified exact remote SHA-256 and byte-size parity for MP3, timestamps, VTT, chapters, and metadata. A direct 1,024-byte range request returned HTTP `206`.
39. Root and Railway controlled-publication packets now contain identical A Ghost Story release evidence/assets; the controlled audio allowlist contains only `book-2b9853ec52` and `a-ghost-story`.
40. The paid lock was restored byte-for-byte after every Stage 2D operation. No unrelated title, static audio fallback, browser speech fallback, or word-level sync claim was introduced.
41. Release PR `#105` merged as `684165108fa0fc6b9e87517f517ca10daf881fba`; manifest cache repair PR `#106` merged as `3d357bb164f850b081c13fd8fc23ccbd3896eee3`.
42. Railway deployment `8a14b747-b0f3-4da9-903c-96734ab58b2d` succeeded. Production now serves A Ghost Story manifest audio as Google `en-GB-Studio-C`, `APPROVED`, `QA_PASSED`, and the proxy returns HTTP `206` for the requested 1,024-byte range.
43. Production book UI shows `Audiobook Approved`, `Listen in Reader`, and `Section-following narration`; the reader creates a fully buffered approved audio element with no static fallback, browser speech, word-level claim, or non-approved `AudioObject`.
44. In-app media start was unavailable for both A Ghost Story and the existing approved `book-2b9853ec52` control, isolating the observation to that browser runtime rather than the new release endpoint.
45. Main regression and GO LIVE workflows passed. k6 completed `32,808/32,808` checks with zero HTTP failures; only the separately scoped catalog p95 threshold missed at `1.28s` versus `1.20s`, with no performance code change made in this sprint.
46. Three read-only sub-agent lanes audited The Open Window, the Bengali repair canaries, and Radharani/Nishkriti in parallel. They made no edits, provider calls, lock changes, or publication changes.
47. Added a title-specific The Open Window Google audition wrapper with controlled-source hash binding, four sub-30-second story passages, cumulative title/sprint budget guards, repeat-attempt protection, and byte-for-byte lock restoration. Six focused tests and schema-3 regression checks pass.
48. Google Studio-C baseline representative scores were `9.4`, `8.4`, `8.0`, and `8.4`; one authorized source-preserving prosody retry improved them to `9.5`, `9.4`, `8.5`, and `9.4`. No fatal flags were detected.
49. The twilight transition remained below the `9.4` owner minimum, so The Open Window stayed audio-hidden. No full TTS, upload, release-gate mutation, or publication ran.
50. Estimated The Open Window audition spend is `$0.4356`; cumulative Sprint 1 estimated spend is `$4.0684`, with `$170.9316` remaining. Actual provider billing was not reported, and the lock restored to its exact pre-run SHA-256 after both attempts.
51. Stage 2E corrected the audition wrapper to the authorized Studio-B-only owner decision and lock holder before any provider call, added a unique run ID, and preserved the strict `schema3_universal_9_7` listening policy.
52. The final bounded Studio-B audition scored `9.4`, `9.5`, `7.2`, and `9.4`. The twilight transition triggered robotic texture and mechanical cadence fatal flags, so representative QA failed.
53. No full TTS, upload, release-gate mutation, deployment, or public Listen exposure ran for The Open Window. It remains public-reader/audio-hidden.
54. Estimated Stage 2E spend is `$0.2178`; cumulative title estimate is `$0.6534`; cumulative Sprint 1 estimate is `$4.2862`, with `$170.7138` remaining. Actual provider billing was not reported.
55. The paid lock restored byte-for-byte to SHA-256 `ab57e15c5329256304014ea8a77e086b7ec5748a0fee6423f772f350ef58b50e` with `current_holder=none` and `allowed_next_holders=[]`.
56. Automated Google retries stop after the Studio-C and Studio-B failures. A non-provider source-bound human narration packet utility is the executable alternate path; the next queue item is an isolated, credential-stripped `book-d19e96859f` dry preflight.
57. The credential-stripped `book-d19e96859f` dry preflight completed with zero paid operations, zero provider credentials, and no publication. Reader, rights, source, and cover preflight passed; audio reuse failed closed because no reusable approved audio evidence was found. The next paid repair remains separately gated.
