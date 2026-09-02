# A2 safe cache migration parity

PASS. A2 intentionally changes only application-cache keys and payload envelopes. Current TTL/jitter authority, source loaders, authorization ordering, targeted/generation invalidation, cache enable/disable behavior, non-cache Redis operational keys, audio/media, controlled-publication data, frontend, and PR #344 remain unchanged.

Legacy keys are never scanned, read, copied, or deleted by the v2 path. They retain their existing TTL and expire naturally. The expected release consideration is a cold v2 cache and temporary source-load increase. Old code can be restored without any Redis migration or cleanup.
