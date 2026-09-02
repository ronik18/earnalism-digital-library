# A6 PDF scope parity

The before/after comparison uses the pre-A6 commit `4dfdff0df66f1d3ce7dc0fc38cb0db3de5bc9699` and the rebased A6 head before this evidence file. Public OpenAPI and customer-route inventory SHA-256 values are unchanged. The active policy registry, v2 key schema, limits, TTL/jitter authority, invalidation/coherence authority, audio/media tree, controlled-publication data tree, frontend tree, and PR #344 overlap all remain unchanged.

The only runtime changes are the central data-URI classifier and the corresponding policy-invalid v2 read result. This rejects disallowed embedded values before Redis SET and treats an existing invalid current-v2 value as an exact-key-cleaned miss. The source loader and customer response semantics remain unchanged. No customer PDF response exists.
