# A8 audio repeatability

Run `33704138466` measured three comparable 126-sample audio rounds at the exact
benchmark head. Each used the same synthetic fixtures, 1/5/20 concurrency, the
same bounded 1 MiB storage reads, and the same ephemeral Python 3.11/Redis 7.4.11
runner. All correctness, range/status, cancellation-cleanup, and resource gates
passed in every round. The p95 spread was 11.353430 ms; timing is reported only
as local/ephemeral evidence, not production performance proof.

Result: `PASS_NO_MATERIAL_REPEATABLE_REGRESSION`.
