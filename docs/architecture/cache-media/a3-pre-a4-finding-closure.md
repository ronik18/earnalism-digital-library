# A3 pre-A4 finding closure

`A3-FINDING-001` was the single `REQUIRED_BEFORE_A4` finding: partial invalidation coverage and absent request coalescing. It is not silently downgraded. A4 closes it through a source-backed dependency map, precise v2 invalidation, stale-fill suppression, and bounded process-local singleflight. This affects cache coherence only; source-of-truth correctness and authorization remain authoritative.
