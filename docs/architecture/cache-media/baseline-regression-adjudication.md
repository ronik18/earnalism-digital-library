# Baseline regression adjudication

The untouched base and PR #345 head have the same three cleanup and 13 legacy-routing failures. PR #345 therefore did not introduce the failures.

`book-2b9853ec52` is an `OBSOLETE_CONTROLLED_FIXTURE`: it is excluded from the public catalog, absent from the live/audio allowlists, and rejected by the controlled runtime gate. `nishkriti` is a `TEST_ENVIRONMENT_PATH_DEFECT`: the runtime source has a matching manifest checksum and is audio-disabled; the observed mismatch is in a duplicate packaged historical manifest.

All 13 routing/package failures expected removed package helpers, public playable asset routes, or obsolete route signatures. Current protected route and range coverage replaces them. The detailed per-node authority decision, evidence, correction, and follow-up condition are in `baseline-regression-ledger.json`.
