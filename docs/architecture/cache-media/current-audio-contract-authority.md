# Current audio security contract authority

Reader manifests intentionally return an empty `assets` object and empty `url`. Playback and package endpoints accept the current `Request` and principal signature, authorize an active Reading Pass lease before protected-object reads, and apply private no-store response protection.

The authoritative tests prove authorization before bytes, no public playable assets or raw provider URLs, valid range behavior, malformed and unsatisfiable range rejection, and package HEAD/ETag behavior. Disabled titles fail closed before a lease challenge. This replaces the historical public-proxy route expectation; it does not change delivery behavior.
