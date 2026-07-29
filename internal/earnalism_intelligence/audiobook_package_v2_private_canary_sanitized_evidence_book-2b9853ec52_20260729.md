# Sanitized private package-v2 canary evidence

This durable record preserves the independently verified private-canary
storage facts for `book-2b9853ec52` without preserving credentials, account
identifiers, endpoints, regions, bucket names, object keys, or local asset
paths.

The companion JSON records:

- the SHA-256 of each of the six original canary artifacts;
- exact SHA-256, size, MIME type, and B2 VersionId for all 11 assets;
- upload, receipt, and independent re-download verification outcomes;
- preflight and verification counters; and
- the explicit `release_eligible: false` private-staging boundary.

The evidence proves private byte integrity only. It is not a production
primary receipt, DR receipt, Object Lock proof, final release manifest, or
authorization to promote package v2. The existing approved live delivery was
not changed.

Machine-readable evidence:

`internal/earnalism_intelligence/audiobook_package_v2_private_canary_sanitized_evidence_book-2b9853ec52_20260729.json`
