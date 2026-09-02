# A1.1 cache behavior parity

The only changed production source is the cache-extraction area of `backend/server.py`, now delegated to `backend/cache`. The independently calculated route inventory is unchanged at 137 routes (`e3f2c7122d031d3e156e3898a24e3bf50559c4b94fb2e3a704c774293bf71367`), and the 129-path OpenAPI surface is unchanged (`7b8307b1e03191cc0a27592c426402497e100c89c7ffa256c26d9d8accd8c412`). Redis environment-name inventory, key vectors, codec bytes, TTL vectors, cache-status schema, controlled-publication data, frontend production files, and PR #344 overlap are also unchanged.

The 51 audio-delivery function bodies are unchanged (`c642fb42df101f0a21e5ee8409d30b819845b843c883065a2c09c2cd04752a6d`). Current pickle/zlib behavior is deliberately preserved for A1 parity; this is not a security remediation. **A2_MIGRATION_REQUIRED**.
