# A8 cost and resource model

`LOCAL_AND_EPHEMERAL_BENCHMARKS_ARE_NOT_PRODUCTION_PERFORMANCE_PROOF`.

No monthly currency saving is calculated. Production traffic, hit ratio,
provider costs, Redis pricing, and topology were intentionally not accessed.
The model records symbolic formulas for steady cache, transient locks,
process-local singleflight, and metric state; it exposes the observed lab
memory and the scenario totals without presenting them as production usage.
