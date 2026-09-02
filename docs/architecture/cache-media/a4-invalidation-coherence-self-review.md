# A4 invalidation and coherence self-review

| Finding | Classification | Result |
| --- | --- | --- |
| Stale fill after version change | BLOCKER | Suppressed before SET. |
| Broad/legacy invalidation | BLOCKER | None; generation or exact v2 delete only. |
| Singleflight cancellation/leak | BLOCKER | Shielded waiters and finally cleanup tested. |
| Cross-user/key flight collision | BLOCKER | policy/key/version digest identity. |
| Redis-required correctness | BLOCKER | None; local singleflight and source fallback. |
| Distributed lock interoperability | REQUIRED_BEFORE_RELEASE | Not justified and disabled; real Redis integration unavailable. |

No A4 blocker remains.
