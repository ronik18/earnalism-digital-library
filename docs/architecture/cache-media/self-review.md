# Strict self-review

| Classification | Finding |
|---|---|
| REQUIRED_BEFORE_IMPLEMENTATION | Replace pickle decoder with bounded safe codec and a versioned migration. |
| REQUIRED_BEFORE_IMPLEMENTATION | Define a hard serialized-value ceiling and singleflight policy. |
| REQUIRED_BEFORE_IMPLEMENTATION | Prove every mutation event invalidates any affected sensitive cache. |
| REQUIRED_BEFORE_IMPLEMENTATION | Untouched `origin/main` audio-source cleanup regression fails: `book-2b9853ec52` controlled artifact is absent and checksum assertions for `book-2b9853ec52` and `nishkriti` differ from their manifests. This checkpoint does not alter controlled publication data. |
| REQUIRED_BEFORE_IMPLEMENTATION | Untouched `origin/main` legacy audio routing/package tests also fail (13 failures): they assert removed package-descriptor helpers, public manifest asset exposure, and old request signatures that conflict with the current lease-authorized, empty-public-assets route contract. This checkpoint does not restore legacy behavior. |
| REQUIRED_BEFORE_RELEASE | Obtain redacted Railway/Redis/object-store metrics and verify stream cancellation under an authorized staging path. |
| REQUIRED_BEFORE_RELEASE | Keep protected audio authorization ahead of all object reads; no raw provider URL leak. |
| POST_RELEASE_MONITORING | Cache hit/miss/bypass/error/value-size, B2 bytes/range failures, latency/RSS, and eviction behavior. |
| OPTIONAL | Customer PDF delivery remains out of scope until an active product requirement exists. |

Self-review result: no production source, workflow, deployment, secret, or PR #344 file is changed by this checkpoint.
