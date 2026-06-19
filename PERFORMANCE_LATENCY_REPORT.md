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
| JS file count | 20 |
| Total JS bytes | 809090 |
| Route lazy loading | True |
| Health endpoint | True |
| Redis detected | True |
| Byte-range audio | True |
| Load evidence status | OPERATOR_REQUIRED |

## Largest Built JS Files

| File | Bytes |
| --- | --- |
| main.c1dcdab3.js | 361013 |
| 453.2ef94f91.chunk.js | 111336 |
| 429.44085a1a.chunk.js | 93263 |
| 556.3a2360f7.chunk.js | 65384 |
| 828.125aefc0.chunk.js | 40142 |
| 660.210aeb62.chunk.js | 22116 |
| 467.f5131a2b.chunk.js | 16614 |
| 565.4d3ed07c.chunk.js | 12592 |

No k6 load test was executed by this launch audit. If no result file is present, latency and autoscaling evidence remain operator-required.
