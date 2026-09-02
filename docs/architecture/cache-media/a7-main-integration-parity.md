# A7 main-integration parity

PR #345 was at `ba05a8cc60cbb5ecdad821e304347b15615660f5` before the A7
integration. `origin/main` was `1a23ad2f2a04176faa0afb753f7144af2f437d0d`,
which contains released PR #344. The branch merged it normally as
`b277cc3129a4b9f87f4af93f56352b2af208ac02`; the merge had zero conflicts.

The merge-base inventory found 114 mainline-changed paths, 146 PR345-changed
paths, and zero intersecting paths. In particular, mainline introduced no
post-base `backend/cache/**` or `backend/media/**` changes. A pre-merge
checkpoint verified repository and PR ancestry, changed files, and hashes with
zero missing files, hash mismatches, or contamination.

Post-merge cache/media and protected-audio regression selection passed 186
tests. Two separate public-audio-safety failures are preserved baseline
controlled-publication data state: their test and inputs did not change across
the merge. The normal merge therefore preserves the A1–A6 runtime contract;
the only A7 runtime source change is documented in the lifecycle result.
