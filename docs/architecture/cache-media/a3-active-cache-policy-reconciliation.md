# A3 active cache-policy reconciliation

PASS. Runtime A2 behavior is authoritative: exactly six active v2 application-cache namespaces are registered. Existing matrix entries for audio metadata, signed delivery, entitlement, editorial candidates, and other conditional/do-not-cache work remain inactive and were not enabled. TTL, jitter, negative caching, candidates, source fallback, authorization, and invalidation semantics are unchanged.

The defaults are finite, below the A2 1 MiB decoder ceiling, and provide at least 87x room above A2's 3,006-byte largest synthetic value. Production cardinality is unavailable, so capacity confidence remains limited.
