# A8 benchmark authority change

The benchmark authority changed only in `scripts/cache_media/run_a8_integrated_benchmark.py`.
Its runner digest changed from `30d570c4768b8859bb1bbdf06edc6c347a89714ed69416e4c1e327d9176fc25d`
to `9b60c27e4c30f0aabd1382da1563987ed58cf350440fcdb7b9be763bde253063` because
audio scenarios are now measured in three labelled rounds. This is classified as
`AUDIO_REPEATABILITY_HARNESS_EXPANSION`; a new exact-head benchmark is required.

The prior Redis benchmark at `216f0c3d793567447cec1f797e3f277ed44094b1` remains
`VALID_HISTORICAL_BENCHMARK_NOT_FINAL_CURRENT_AUTHORITY`. Benchmark workflow,
profile, fixtures, dependency authority, Redis configuration, cache/media runtime,
`backend/server.py`, and Reader/Listener runtime are unchanged between the prior
benchmark authority and the frozen benchmark head.
