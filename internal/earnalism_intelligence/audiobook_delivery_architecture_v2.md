# Earnalism Audiobook Delivery Architecture v2

Status: **runtime, package builder, storage controls, reader behavior, and
release-control tooling implemented; production-primary/DR activation remains
fail-closed until its external evidence exists**.

## Decision

Use immutable, source-bound audiobook packages made of chapter-aligned MP3
segments. The ordered manifest is the logical page list; standard HTTP Range
requests provide seek, resume, and partial delivery. Audio bytes are not
paginated by an application API and are never stored in Redis.

For every approved title retain:

1. the unchanged provider/source file for provenance;
2. a final mono PCM/WAV master for future encoding; and
3. customer MP3 delivery segments, normally 96 kbps mono.

Prefer one file per chapter. Split only at a measured paragraph or stanza
boundary when a segment would exceed 12 minutes. Store exact timestamp JSON,
WebVTT, and metadata sidecars beside every segment.

## Canonical package

The contract is
`internal/audiobook_lab/schemas/audiobook_package_manifest.v2.schema.json`;
semantic validation lives in `backend/audiobook_packages.py`.

The package version is the SHA-256 of canonical JSON excluding only its own
`package_version` field. The validator also requires:

- the exact controlled slug, source SHA-256, manuscript SHA-256, and release
  descriptor SHA-256;
- deterministic tracks and segments with globally contiguous word, paragraph,
  and cumulative-time boundaries;
- segment duration at or below 12 minutes;
- exact SHA-256, byte size, MIME type, object key, and B2 VersionId for every
  MP3, timestamp, VTT, and metadata object;
- a private production object plus at least one distinct DR replica for every
  customer asset; and
- the immutable prefix
  `v1/prod/sprint1/{slug}/releases/{releaseDescriptorSha256}/`.

The public manifest contains only same-origin API URLs and reader-safe
metadata. It never contains a bucket, object key, raw B2 URL, VersionId,
replica, manuscript hash, or release-evidence record.

## Storage and durability

Use independently identified private primary and DR buckets in separate
accounts/regions. Released keys are never overwritten. Every upload and
replication is followed by a complete download and exact SHA-256/size check.
Production preflight requires:

- versioning enabled;
- private-bucket evidence;
- Governance Object Lock with active default retention;
- no lifecycle hiding or deletion that overlaps `v1/prod/`; and
- distinct account, credential, region, endpoint, and bucket identities.

The runtime receives only a bucket-scoped primary read credential. Controlled
operators use separate upload and retention-preflight credentials. Lifecycle
rules are read through the supported B2 Native `b2_list_buckets` API because
lifecycle-read capability support is inconsistent across the documented and
deployed B2 S3-compatible surfaces. The account, bucket name, and bucket ID in
the returned record must exactly match the authorized identity. Native API
requests reject every HTTP redirect before urllib can construct a second
request, preventing Basic or bearer authorization from moving to another URL.
The retention-preflight credential is read-only; its legacy environment
variable name still says `RETENTION_ADMIN` for compatibility. Exact
least-privilege capabilities are documented in the operator environment
example. Production deletion credentials are deliberately unsupported and
remain offline. The unpopulated operator contract is
`internal/audiobook_lab/config/audiobook_package_storage.env.example`. The
current and at least two prior approved releases are retained.

Private-QA staging is intentionally weaker and always records
`release_eligible: false`; a staging receipt can never finalize or activate a
production package.

## Runtime delivery

- `GET|HEAD /api/reader/book/{slug}/audiobook/manifest`
- `GET|HEAD /api/reader/book/{slug}/audiobook/packages/{packageVersion}/segments/{segmentId}`
- `GET|HEAD /api/reader/book/{slug}/audiobook/packages/{packageVersion}/segments/{segmentId}/timestamps`
- `GET|HEAD /api/reader/book/{slug}/audiobook/packages/{packageVersion}/segments/{segmentId}/vtt`
- `GET|HEAD /api/reader/book/{slug}/audiobook/packages/{packageVersion}/segments/{segmentId}/metadata`

The backend derives the exact private object from controlled truth; the client
cannot submit a B2 key or URL. Hidden, inactive, revoked, stale, cross-title,
unknown, or structurally invalid packages return `404`. Unsatisfiable or
malformed ranges return `416`; honored ranges return `206`. A storage response
that ignores or changes the requested range fails closed.

The existing monolithic endpoint stays available during migration.

## Reader and cache behavior

- Opening the Reader fetches metadata but transfers zero MP3 bytes.
- Explicit Play binds only the current segment to the native `<audio>` element.
- At 70% completion, the Reader warms only the next segment `HEAD` response and
  downloads its timestamp JSON; it does not prefetch the next MP3 body.
- Playback advances to the next segment, and exact-package progress
  `{packageVersion, segmentId, offset, speed}` is stored locally.
- TTFA, stall, seek, and segment-transition telemetry carry package/segment
  tags.
- The service worker continues to bypass Range and audio requests; browser HTTP
  caching and native Range behavior handle media.

Redis is limited to manifest metadata, authorization/feature state, progress if
server-side sync is later enabled, and aggregate telemetry. Binary media is
rejected by policy.

## Controlled rollout and rollback

Package selection is deterministic and sticky for the supported rollout values
`0`, `5`, `25`, and `100`. Catalog mutation is serialized and requires:

1. a canonical package that matches controlled source/manuscript truth;
2. exact release-eligible production-primary and DR receipts;
3. complete-download checks for the finalized release manifest in both stores;
4. the candidate plus no more than the current and two prior approved release
   descriptors; and
5. mirrored controlled-publication writes with checksum-manifest updates.

At 5% or 25%, non-candidate users continue on the approved legacy pointer. A
100% promotion moves the active pointer. Rollback changes only the controlled
pointer; immutable objects remain untouched.

Package construction, staging upload, or successful delivery optimization
cannot approve an audiobook. Rights, covers, source/ASR, ordered content,
measured sync, listening, editorial, storage, endpoint, and browser gates
remain independent and fail closed.

## Approved legacy package producer

`audiobook_package_builder_v2.py build-approved-legacy` generalizes package-v2
construction beyond the fixed canary without generalizing approval. It accepts
an exact local MP3 plus timestamp, VTT, chapter, and metadata sidecars only
when both controlled-publication mirrors and their checksums agree. The command
requires the existing public approval to prove ASR/manuscript `>= 9.7`,
coverage `>= 0.98`, first/last and ordered-content integrity, listening
`>= 9.2` at confidence `>= 0.90` with no fatal flags, measured paragraph or
stanza sync, tier-A approved rights, checksum-verified upload, endpoint `206`,
browser `PASS`, and an empty blocker list.

The builder rehashes every approved local asset against controlled truth before
writing output, preserves those assets and their approval/source/checksum
records as provenance, creates a mono PCM master, and encodes immutable
96-kbps mono MP3 segments at measured cue boundaries. The output upload plan is
`RELEASE_CANDIDATE`; it performs no upload, catalog mutation, or gate change.

## Canary state

The exact already-approved `book-2b9853ec52` narration has been repackaged into
two delivery segments without new synthesis and verified in private QA.
Production package-v2 activation is still blocked by the current evidence
listed in
`audiobook_package_v2_canary_book-2b9853ec52_20260729.json`.

Next exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  internal/audiobook_lab/scripts/audiobook_package_storage_v2.py preflight \
  --report /private/tmp/earnalism-package-v2-production-dr-preflight.json
```
