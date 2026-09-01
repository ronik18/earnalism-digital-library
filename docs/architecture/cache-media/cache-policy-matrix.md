# Cache policy and capacity matrix

Default direction: durable object storage/CDN for large bytes; Redis only for bounded metadata/state. Every estimate is an assumption requiring post-release measurement.

## Evidence

| Topic | Current finding | Evidence |
|---|---|---|
| public catalog | CACHE; max 256000 bytes | Observed public cache implementation |
| home/public shelf | CACHE; max 128000 bytes | Observed public cache implementation |
| book metadata | CACHE; max 64000 bytes | Observed public cache implementation |
| chapter metadata | CACHE; max 64000 bytes | Observed reader cache implementation |
| Reader content | CONDITIONAL; max 262144 bytes | Current implementation lacks max-size guard |
| Listener manifest | CACHE; max 131072 bytes | Observed metadata cache |
| audio object metadata | CONDITIONAL; max 8192 bytes | Requires production measurements |
| signed URL/delivery manifest | CONDITIONAL; max 8192 bytes | No signed URL cache currently |
| article/journal metadata | CACHE; max 65536 bytes | Observed public cache pattern |
| entitlement lookup | CONDITIONAL; max 2048 bytes | Sensitive; cache only with exact invalidation |
| session/user lookup | CACHE; max 8192 bytes | Observed current cache |
| processing/transcode state | CONDITIONAL; max 8192 bytes | No stable current contract |
| waveform/page-count metadata | CONDITIONAL; max 65536 bytes | No active product path for waveform/PDF |
| negative not-found | CONDITIONAL; max 256 bytes | Avoid caching protected authorization denials |
| request coalescing locks | CONDITIONAL; max 256 bytes | No cache-fill singleflight currently |
| idempotency state | CONDITIONAL; max 16384 bytes | Route-specific design needed |
| complete PDF binary | DO_NOT_CACHE; max 0 bytes | No active PDF route; Redis unsuitable for large bytes |
| complete audio binary | DO_NOT_CACHE; max 0 bytes | Repository policy rejects audiobook binaries |
| arbitrary Range fragments | DO_NOT_CACHE; max 0 bytes | B2 range streaming is durable-storage concern |
