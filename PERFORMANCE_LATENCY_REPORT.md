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
| JS file count | 22 |
| Total JS bytes | 1025736 |
| Route lazy loading | True |
| Health endpoint | True |
| Redis detected | True |
| Byte-range audio | True |
| Load evidence status | OPERATOR_REQUIRED |

## Largest Built JS Files

| File | Bytes |
| --- | --- |
| main.1c32cc24.js | 514523 |
| 944.72a1d5ad.chunk.js | 171467 |
| 83.2eb0f2e9.chunk.js | 106699 |
| 813.e13eff59.chunk.js | 65950 |
| 596.ad8d1d21.chunk.js | 30301 |
| 426.40f4a695.chunk.js | 23689 |
| 93.107b10de.chunk.js | 17261 |
| 587.4630570e.chunk.js | 12900 |

No k6 load test was executed by this launch audit. If no result file is present, latency and autoscaling evidence remain operator-required.
