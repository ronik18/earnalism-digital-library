# Strict self-review

| Classification | Finding |
|---|---|
| REQUIRED_BEFORE_IMPLEMENTATION | Replace pickle decoder with bounded safe codec and a versioned migration. |
| REQUIRED_BEFORE_IMPLEMENTATION | Define a hard serialized-value ceiling and singleflight policy. |
| REQUIRED_BEFORE_IMPLEMENTATION | Prove every mutation event invalidates any affected sensitive cache. |
| REQUIRED_BEFORE_A1 | A1 may start only from the reproducible, fully adjudicated baseline recorded in `baseline-regression-ledger.json`; all originally failing test contracts must have final green replacement coverage. |
| REQUIRED_BEFORE_RELEASE | Obtain redacted Railway/Redis/object-store metrics and verify stream cancellation under an authorized staging path. |
| REQUIRED_BEFORE_RELEASE | Keep protected audio authorization ahead of all object reads; no raw provider URL leak. |
| POST_RELEASE_MONITORING | Cache hit/miss/bypass/error/value-size, B2 bytes/range failures, latency/RSS, and eviction behavior. |
| OPTIONAL | Customer PDF delivery remains out of scope until an active product requirement exists. |

## A1 boundary

A1 is a behavior-preserving interface extraction, not a cache optimization. It does not change cache keys, Redis behavior, serialization, audio delivery, release truth, or public media exposure. Unsafe pickle migration belongs to A2; maximum-value guard and metrics to A3; invalidation and singleflight to A4. Production metrics are required before staging/release, not before A1, and no optimization claim is made by A1.

Self-review result: no production source, workflow, deployment, secret, controlled-publication data, or PR #344 file is changed by this checkpoint.
