# Sprint 1 Publication Stage 2 Execution Log

Generated: `2026-07-12T22:00:32Z`

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
58. PR `#109` was classified `EVIDENCE_ONLY_FAIL_CLOSED` with source/test guardrails, no public release-state changes, and green checks; it was squash-merged as `5b20775` without deleting branches.
59. Generated The Open Window human narration packet with sanitized manuscript, narrator brief, failed-TTS summary, audio-format/delivery requirements, QA/release checklist, deterministic hashes, and an exact received-audio validation command. No provider call or release mutation ran.
60. Reclassified The Open Window as `HUMAN_NARRATION_OR_ALTERNATE_PROVIDER_REQUIRED`; public reader remains enabled and public audio remains hidden.
61. D19 diagnosis found the historical group-only repair chunks unavailable, so unverifiable group reuse was rejected. The cheapest safe path is fresh title-only regeneration rather than stale legacy audio reuse.
62. Repaired Bengali TTS-only sanitation to remove D19's standalone trailing source year while leaving canonical reader text unchanged. Prepared text is 6,485 characters in five groups with SHA-256 `79b0deba6032c36ab919e4ef4786fc62aa55c9c53c328dfbcf49f03a0f7d05fe`.
63. Added exact title-specific representative evidence for Sarvam `bulbul:v3` / `pooja` / `dialogue_human_touch`: score `9.4`, confidence `0.95`, no fatal flags. The generic guard accepts it only when the selected slug/arm matches and explicit title-specific opt-in is present.
64. Added a D19 lock-safe preflight/execute wrapper. Non-paid preflight passed source, rights, sanitation, cover, reader, and representative gates; TTS `$0.0389`, ASR `$0.0544`, and configured QA `$0.0500` total `$0.1433` estimated.
65. Both provider keys were present, but every required budget/approval/ASR/listening environment gate was absent. The wrapper stopped before lock acquisition; provider calls, spend, TTS, ASR, upload, publication, and release mutations remained zero.
66. Production revalidation confirmed The Open Window, D19, and `bn-066` remain audio-disabled with `404` audiobook endpoints, while A Ghost Story and `book-2b9853ec52` remain `APPROVED / QA_PASSED` with `206` range responses.
67. Started the parallel Yes+Yes coordinator from isolated `origin/main` commit `ed42790`; the dirty primary checkout was not modified.
68. Launched six non-paid title/release-truth agents. Paid calls remain serialized and no agent may edit the paid lock or invoke providers.
69. Live-shell verification found every required Sprint/TTS/ASR/listening budget and approval variable missing. Sarvam, OpenAI, and Google credentials plus Google ADC are available; ElevenLabs and Azure Speech credentials are absent.
70. Reran D19's lock-safe non-paid preflight. All source/rights/sanitation/cover/reader/representative gates passed; the `$0.1433` paid pipeline stopped before lock acquisition and provider access.
71. This run made zero provider calls, spent `$0.00`, published zero new audiobooks, and left the lock byte-for-byte at active/current-holder-none/empty-next-holders.
72. The bn-066 private workspace produced a non-paid three-chunk/four-language calibration plan: six calls, 785.215 seconds, estimated `$0.1047`; execution remained blocked by missing caps and the unheld lock.
73. Medium/long English preflight ranked nine reader-live/audio-hidden titles at `$85.7074` conditional total; no full generation is authorized before per-title representative auditions.
74. Approved-audio guard reproduced a Reader timestamp schema regression: production uses seconds while the frontend consumed milliseconds. Both approved endpoints and hashes remained valid.
75. Implemented timestamp normalization plus a browser gate that requires clicked playback to advance; focused frontend and Python tests pass.
76. Production validation identified eight blocked titles with 88 direct storage URL occurrences in controlled publication packets. The repo fields were scrubbed fail-closed; approved book 2b and A Ghost Story packets were unchanged.
77. Remote Cloudinary/B2 objects still require revocation or privacy changes because no storage credentials are present.
78. Removed the legacy static `/audio/*` SPA/cache path by routing it to removed-content.
79. Reconciled serialized evidence through the final D19 ASR repair checkpoint at a conservative estimated `$9.75400 / $175`; estimated remaining budget is `$165.24600`, while actual provider billing remains unknown.
80. Confirmed release truth remains exactly 32 public readers and two public audiobooks: `book-2b9853ec52` and `a-ghost-story`. This reconciliation claims zero new publications and made no code, lock, audio, upload, metadata, endpoint, deployment, or release-state mutation.
81. D19's later private Google candidate passes full TTS, six listening samples at `9.4` with confidence `0.95` and no fatal flags, and measured paragraph/stanza sync with `auto_estimated_sync=false`.
82. Corrected D19's objective release truth: raw ASR/source is `0.6838`, below mandatory `9.7`. The construction audit `10.0` is source-provenance evidence only and is not an ASR substitute.
83. Classified D19 as `AUTOMATED_ASR_ARMS_EXHAUSTED_NORMALIZATION_REPAIR_REQUIRED_PRIVATE_TTS_PASS`. Upload, release-packet construction, admin metadata mutation, endpoint enablement, browser release QA, and publication remain blocked.
84. Muchiram's full private QA bottomed at `7.8`, confidence `0.85`, with robotic, mechanical, and list-reading fatal flags; targeted Achird and slower Aoede attempts bottomed at `7.4` and `7.8`. It moves to its prepared source-bound narration/licensed-audio packet.
85. F5's Google Aoede and Sarvam Pooja bounded auditions both bottomed at `7.8`; the Google attempt carried robotic/mechanical fatal flags. It moves to its prepared source-bound narration/licensed-audio packet.
86. Sredni Vashtar failed Studio-C at `7.3` with robotic/mechanical flags and Chirp Achird at `8.5`. The Gift of the Magi failed three bounded auditions at `8.5`, `7.2`, and `8.3`, with robotic/mechanical flags on Chirp Aoede. The Tell-Tale Heart failed contextual and slow-contextual Studio-C at `8.5` and `8.4`.
87. Classified Sredni, Gift, and Tell as `HUMAN_NARRATION_OR_LICENSED_AUDIO_IMPORT_REQUIRED`; each next command builds a source-bound packet without provider or publication work.
88. Preserved the two deferred long classics, every other title's exclusion/defer rule, and every unaffected per-title blocker and next command.
89. Final D19 ASR probes: Google `latest_long`/`bn-IN` unsupported; OpenAI `gpt-4o-transcribe`/`bn` best `6.7606`. Next exact command: `PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/bengali_asr_normalization.py --self-test`.
90. Stage 2G ran the owner-authorized title-only Sarvam `bulbul:v3` / `pooja` / `dialogue_human_touch` wrapper for D19 under `$1` title-pilot, ASR, and listening sub-caps. Five fresh groups produced a private `627.875833s` MP3 with no fallback, local, or stale reuse.
91. The QA verifier now requires raw audio-derived ASR and explicit audio-derived first/last checks; the static construction audit can only support provenance and cannot satisfy the release gate.
92. Raw ASR/source scored `1.3504 / 10`; first and last checks failed. Six listening samples scored `8.0`, `8.0`, `9.4`, `9.4`, `9.4`, and `8.0`; minimum confidence was `0.85`, with fatal list-reading rhythm.
93. D19 is `ASR_SOURCE_MISMATCH` with secondary `LISTENING_QA_REPAIR_REQUIRED`. No upload, release packet, metadata mutation, endpoint enablement, deployment, or publication ran.
94. Stage 2G estimated spend is `$0.4226`; cumulative Sprint estimate is `$10.1766 / $175`, leaving `$164.8234`. Actual provider billing remains unknown.
95. The lock restored byte-for-byte to SHA-256 `ab57e15c5329256304014ea8a77e086b7ec5748a0fee6423f772f350ef58b50e`, active with no holder or allowed next holders.
96. Automated Google and Sarvam D19 retries stop. The next executable track is the generated source-bound human narration packet followed by received-audio validation and full release QA.
97. Started the parallel Yes+Yes acceleration from clean `origin/main` commit `3709321`; the dirty primary checkout remained untouched.
98. Launched six read-only agents for approved controls, short Bengali, short English, medium/long English, Bengali long/repair, and release-truth validation. Agents made no paid calls or lock mutations.
99. The parent shell lacked budget/approval exports, so the owner-supplied values were bound inline to the one serialized paid attempt. Sarvam, OpenAI, and Google credential variables were present; Google client-library default credentials resolved the configured project.
100. `dsires-baby` passed private input preflight: 11,974 characters, one chapter, rights and sanitation pass, source SHA-256 `587455ed554ef64d19f0ea7dcd31940d242aa759f5132b6514b130efa4a64a89`.
101. Its bounded Studio-C audition dry-run passed at `$0.03616` for 1,808 representative characters, but the execute step failed DNS resolution before synthesis. The result records zero synthesis calls and no generated audio; no listening QA or release mutation ran.
102. The shared lock restored byte-for-byte to SHA-256 `ab57e15c5329256304014ea8a77e086b7ec5748a0fee6423f772f350ef58b50e`, active with no holder and no allowed next holders.
103. No additional spend was booked, so the conservative Sprint checkpoint remains `$10.1766 / $175` with `$164.8234` remaining. Public audiobook truth remains exactly `book-2b9853ec52` and `a-ghost-story`.
104. The approved-audio regression lane found stale D19 controlled-publication metadata that still claimed public audio approval and retained 11 direct audiobook URLs per mirror despite its disabled reader manifest.
105. Repaired both root and backend D19 packets fail-closed: reader access preserved, audio flags false, provider/asset fields empty, approval `PUBLIC_AUDIO_RELEASE_NOT_APPROVED`, and checksum manifests rebound.
106. Added explicit D19 safety coverage and reader-only packet validation. The focused backend release-truth suite passes `35/35`; both packet mirrors are byte-identical and contain no audiobook URL.
