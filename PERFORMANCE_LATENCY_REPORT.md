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
| Total JS bytes | 1057282 |
| Route lazy loading | True |
| Health endpoint | True |
| Redis detected | True |
| Byte-range audio | True |
| Load evidence status | OPERATOR_REQUIRED |

## Largest Built JS Files

| File | Bytes |
| --- | --- |
| main.ac0e8c2c.js | 368000 |
| 629.a0085754.chunk.js | 134908 |
| 308.ce3dd7d6.chunk.js | 121810 |
| 634.a32aa715.chunk.js | 111184 |
| 133.1683d239.chunk.js | 65954 |
| 681.b9f5f9c6.chunk.js | 39795 |
| 789.810092c1.chunk.js | 33598 |
| 176.c96dae99.chunk.js | 27077 |

No k6 load test was executed by this launch audit. If no result file is present, latency and autoscaling evidence remain operator-required.
