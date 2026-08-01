# Sprint 1 Next Two Audiobooks Fast-Path Candidate Ranking

Run ID: `sprint1_next_two_audio_fastpath_20260715`

Starting production YES+YES count: `3/32` (`book-2b9853ec52`, `a-ghost-story`, `sredni-vashtar`).

No new audiobook was published in this run. `bn-066` received the only paid call, a bounded ASR language calibration on existing private audio. It failed closed with `ASR_LANGUAGE_CONFIG_REPAIR_REQUIRED`, so the title remains audio-hidden.

## Ranking

1. `radharani` - Cleanest next paid candidate. Existing reuse audio is rejected by prior ASR/source failure, but source/rights/sanitation/cover preflight is clean enough for a bounded alternate-provider representative audition.
2. `nishkriti` - Same path as `radharani`, but longer and higher-cost, so it ranks second.
3. `book-edfcf810c5` - Has a private retained candidate, but source binding is weak and production cover linkage is not clean. Repair cover linkage before audio spend.
4. `devdas` - Cover linkage and cost preflight required; no release-ready reuse candidate.
5. `jekyll-and-hyde` - English fallback only; cover/linkage and length make it lower confidence for this fast-path sprint.

## Immediate Recommendation

Use the `radharani` bounded representative audition command recorded in `next_two_audio_fastpath_results.json`. Do not run full TTS until the representative audition passes the current sprint gate: every listening sample `>= 9.4`, confidence `>= 0.9`, and no fatal flags.
