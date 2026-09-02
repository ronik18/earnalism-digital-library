# A3 Redis capacity model

PASS. For each policy, estimated entry memory is `(190 key bytes + stored envelope bytes + 128 object bytes) × 1.5`. Characterized values are small; the all-entries-at-limit figures are separate worst-case per-entry bounds. Production cardinality and live Redis memory are unavailable, so `PRODUCTION_REDIS_CAPACITY_CONFIDENCE` is `LIMITED` and no plan sufficiency or tier recommendation is made.
