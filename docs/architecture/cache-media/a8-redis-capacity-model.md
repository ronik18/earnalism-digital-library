# A8 Redis capacity model

`LOCAL_AND_EPHEMERAL_BENCHMARKS_ARE_NOT_PRODUCTION_PERFORMANCE_PROOF`.

The [machine-readable model](a8-redis-capacity-model.json) uses exact synthetic
key `MEMORY USAGE` measurements from isolated Redis 7.4.11. Each policy's
steady-state estimate is `observed_memory_bytes × scenario_cardinality ×
replication_persistence_multiplier`. The expected scenario total is 2,600,000
bytes and the all-at-limit scenario total is 26,000,000 bytes, both with a
multiplier of one because this is not a production topology measurement.

Production Redis capacity confidence is `LIMITED`: cardinality, topology,
configured limits, and traffic are deliberately not inferred from a lab run.
Transient locks, local singleflight state, and metrics state are separated from
steady cache memory because no production measurements exist for those terms.
