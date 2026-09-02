# A2 safe cache self-review

| Finding | Classification | Result |
| --- | --- | --- |
| Active pickle execution | BLOCKER | PASS: active call sites use `encode_v2`/`decode_v2`; legacy codec is A1 characterization-only. |
| Type confusion/arbitrary constructor | BLOCKER | PASS: fixed type tags only; no payload-controlled imports/classes. |
| Decompression bomb/nesting | BLOCKER | PASS: fixed 1,048,576-byte post-decompression ceiling and depth 64. |
| Corrupt cache handling | BLOCKER | PASS: exact v2 delete, miss/source fallback, fresh write. |
| PII/signed URL in v2 key | BLOCKER | PASS: identity/resource are SHA-256 digests. |
| Duplicate Redis client/import-time connection | BLOCKER | PASS: injected shared client provider only. |
| Broad deletion, KEYS, or FLUSH | BLOCKER | PASS: none added. |
| Binary/media cache | BLOCKER | PASS: recursive media/binary exclusion preserved. |
| TTL/jitter/candidate/negative cache drift | BLOCKER | PASS: existing policy functions/callers retained. |
| Current invalidation completeness | REQUIRED_BEFORE_A4 | Existing partial generation/targeted invalidation preserved; A2 does not expand it. |
| Request coalescing | REQUIRED_BEFORE_A4 | Not introduced by A2. |
| Cold-v2 source-load increase | POST_RELEASE_MONITORING | Expected until old keys naturally expire; no legacy reads/copies/deletes. |

No A2 blocker remains.
