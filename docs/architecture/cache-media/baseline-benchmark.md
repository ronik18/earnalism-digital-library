# Cache and Media Local Baseline Benchmark

Local synthetic evidence only; it is not production traffic or a performance-improvement claim.

| Fixture | Request | Concurrency | Status | p50 ms | p95 ms | Max ms | Response bytes |
|---|---|---:|---|---:|---:|---:|---:|
| 4096 | full | 1 | 200 | 0.008 | 0.008 | 0.008 | 4096 |
| 4096 | full | 5 | 200 | 0.003 | 0.005 | 0.005 | 4096 |
| 4096 | full | 20 | 200 | 0.001 | 0.002 | 0.003 | 4096 |
| 4096 | bytes=0-1023 | 1 | 206 | 0.083 | 0.083 | 0.083 | 1024 |
| 4096 | bytes=0-1023 | 5 | 206 | 0.006 | 0.013 | 0.013 | 1024 |
| 4096 | bytes=0-1023 | 20 | 206 | 0.004 | 0.008 | 0.015 | 1024 |
| 4096 | bytes=4194304-4195327 | 1 | 416 | 0.003 | 0.003 | 0.003 | 0 |
| 4096 | bytes=4194304-4195327 | 5 | 416 | 0.002 | 0.004 | 0.004 | 0 |
| 4096 | bytes=4194304-4195327 | 20 | 416 | 0.002 | 0.004 | 0.004 | 0 |
| 4096 | bytes=999999999- | 1 | 416 | 0.002 | 0.002 | 0.002 | 0 |
| 4096 | bytes=999999999- | 5 | 416 | 0.002 | 0.004 | 0.004 | 0 |
| 4096 | bytes=999999999- | 20 | 416 | 0.001 | 0.002 | 0.004 | 0 |
| 8388608 | full | 1 | 200 | 0.431 | 0.431 | 0.431 | 8388608 |
| 8388608 | full | 5 | 200 | 0.211 | 0.218 | 0.218 | 8388608 |
| 8388608 | full | 20 | 200 | 0.217 | 0.219 | 0.222 | 8388608 |
| 8388608 | bytes=0-1023 | 1 | 206 | 0.008 | 0.008 | 0.008 | 1024 |
| 8388608 | bytes=0-1023 | 5 | 206 | 0.005 | 0.009 | 0.009 | 1024 |
| 8388608 | bytes=0-1023 | 20 | 206 | 0.004 | 0.006 | 0.008 | 1024 |
| 8388608 | bytes=4194304-4195327 | 1 | 206 | 0.006 | 0.006 | 0.006 | 1024 |
| 8388608 | bytes=4194304-4195327 | 5 | 206 | 0.005 | 0.008 | 0.008 | 1024 |
| 8388608 | bytes=4194304-4195327 | 20 | 206 | 0.004 | 0.006 | 0.008 | 1024 |
| 8388608 | bytes=999999999- | 1 | 416 | 0.003 | 0.003 | 0.003 | 0 |
| 8388608 | bytes=999999999- | 5 | 416 | 0.002 | 0.003 | 0.003 | 0 |
| 8388608 | bytes=999999999- | 20 | 416 | 0.001 | 0.002 | 0.003 | 0 |

## Scope

- Current helpers: `backend/server.py:_parse_byte_range` and `_streaming_body_iterator`.
- Fixtures: in-memory 4 KiB and 8 MiB deterministic byte objects.
- No B2, Redis, Railway, network, credentials, or production HTTP was invoked.
- RSS values are process high-water marks, not a per-request allocation profile.
