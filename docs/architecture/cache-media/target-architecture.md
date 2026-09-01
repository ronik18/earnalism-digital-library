# Target architecture decision record

Proposal only. No production behavior changed in this checkpoint.

## Redis

- one lifecycle-owned shared async client
- short timeouts and bounded retry
- cache-aside, graceful source fallback
- versioned namespaced user/resource keys
- bounded safe JSON codec; migrate away from pickle
- maximum serialized-value guard
- TTL jitter, precise invalidation, conservative negative cache
- cross-replica singleflight
- hit/miss/bypass/error/latency/value-size/invalidation metrics
- no correctness dependency and no large binary values

## Media

- durable B2/object storage remains source of truth
- protected media stays same-origin authorized proxy; any signed URL decision requires explicit authorization class
- stream without complete buffering
- maintain Range, ETag, conditional semantics and private cache controls
- close upstream body on completion/error/cancellation

## PDF

No customer PDF subsystem until a product path exists.
