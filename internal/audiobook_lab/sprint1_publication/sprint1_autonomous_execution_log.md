# Sprint 1 Autonomous Execution Log

Generated: 2026-07-13T06:27:59+00:00
Owner decision: `AUTHORIZE_AUTONOMOUS_SPRINT1_AUDIO_PUBLICATION_WITH_SELF_GOVERNING_DECISION_TREE_AND_175_USD_CAP`

## Coordinator State

- Active titles: 32
- Public readers: 32
- Public audiobooks: 2
- Estimated spend checkpoint: $14.906140
- Estimated remaining budget: $160.093860
- Shared paid lock available: True
- Paid calls: serialized
- Publication: fail closed until every release gate passes

## Next Serialized Paid Action

- None. Continue non-paid repair or obtain external narration/rights evidence.

## Execution History

- `2026-07-13T05:47:09+00:00` `the-cop-and-the-anthem`: `AUDITION_GENERATION_COMPLETE_QA_PENDING` (return code `0`)
- `2026-07-13T05:51:27+00:00` `the-last-leaf`: `AUDITION_GENERATION_COMPLETE_QA_PENDING` (return code `0`)
- `2026-07-13T05:55:11+00:00` `the-masque-of-the-red-death`: `AUDITION_GENERATION_COMPLETE_QA_PENDING` (return code `0`)
- `2026-07-13T06:01:21+00:00` `the-necklace`: `AUDITION_GENERATION_COMPLETE_QA_PENDING` (return code `0`)
- `2026-07-13T06:05:58+00:00` `the-monkeys-paw`: `AUDITION_GENERATION_COMPLETE_QA_PENDING` (return code `0`)
- `2026-07-13T06:24:52+00:00` `the-yellow-wallpaper`: `AUDITION_GENERATION_COMPLETE_QA_PENDING` (return code `0`)

## Release Truth

No coordinator plan or audition result mutates a public release gate. Publication requires separate manifest, endpoint, frontend, and production validation evidence.

## Reconciled QA Outcomes

- `the-cop-and-the-anthem`, `the-last-leaf`, `the-masque-of-the-red-death`, `dsires-baby`, `the-necklace`, and `the-yellow-wallpaper`: Studio-C and Chirp3-HD-Achird representative QA both failed the all-samples `>=9.4` rule. Full TTS did not run.
- `the-monkeys-paw`: representative Chirp3-HD-Achird QA passed, private full TTS and raw ASR passed, but full listening QA failed before and after one bounded ending repair.
- Seven source-bound narration/import packets are ready; all processed titles remain public-reader/audio-hidden.
- Conservative estimated checkpoint: `$14.90614`; remaining authorized budget: `$160.09386`; actual billing: `UNKNOWN_NOT_REPORTED_BY_PROVIDERS`.
