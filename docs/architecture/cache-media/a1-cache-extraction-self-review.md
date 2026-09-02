# A1.1 strict self-review

| Classification | Finding |
|---|---|
| REQUIRED_BEFORE_A2 | Pickle/zlib remains current behavior for parity. A2 must replace it through a separately approved migration. |
| REQUIRED_BEFORE_RELEASE | Obtain production Redis/object and stream-cancellation evidence before staging or release. |
| POST_RELEASE_MONITORING | Observe cache hit/miss/error/media-skip counters, Redis memory, and connection health after a future deployment. |
| OPTIONAL | Consider a future typed cache-runtime facade once A2 changes the codec contract. |

Reviewed PASS: one construction path in `backend.cache.client`; no import-time Redis connection; no circular import from cache modules to server; server aliases synchronize legacy monkeypatches; lifecycle, fallback, key, codec, TTL, metrics, route, audio, data, and PR #344 parity tests are covered. A1 blockers: 0.
