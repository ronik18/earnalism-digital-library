# Performance Latency Report

Status: `PASS`

| Target | p95 ms |
| --- | --- |
| homepage_p95_ms | 1800 |
| library_p95_ms | 2200 |
| book_detail_p95_ms | 2200 |
| reader_preview_p95_ms | 2500 |
| api_book_detail_p95_ms | 500 |

| Signal | Value |
| --- | --- |
| JS file count | 23 |
| Total JS bytes | 1055582 |
| Route lazy loading | True |
| Health endpoint | True |
| Redis detected | True |
| Byte-range audio | True |
| Load evidence status | OPERATOR_REQUIRED |

## Largest Built JS Files

| File | Bytes |
| --- | --- |
| main.38ca4708.js | 368266 |
| 629.cd22323b.chunk.js | 134790 |
| 308.34e93c08.chunk.js | 120616 |
| 634.1cb9a652.chunk.js | 108938 |
| 133.1683d239.chunk.js | 65954 |
| 681.fef3455a.chunk.js | 39677 |
| 789.810092c1.chunk.js | 33598 |
| 176.4a49e3eb.chunk.js | 27934 |

No k6 load test was executed by this launch audit. If no result file is present, latency and autoscaling evidence remain operator-required.
