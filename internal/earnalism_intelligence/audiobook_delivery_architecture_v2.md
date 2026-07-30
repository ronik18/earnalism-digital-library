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

## New-title QA-candidate package producer

`audiobook_package_builder_v2.py build-qa-candidate` removes the circular
dependency on an already-public legacy audiobook. It is intentionally narrower
than a general import path: the first accepted source contract is the exact
private Google English `full_generation_manifest.json` produced by
`sprint1_google_english_private_pipeline.py`.

The command fails before writing output unless all of the following agree:

- both controlled-publication mirrors, every controlled chapter, and every
  checksum;
- the live reader identity, exact title/author, tier-A rights, audiobook-use
  clearance, and still-blocked public-audio state;
- active front and back cover approval events, dimensions, hashes, URLs, and
  cover-rights statements;
- the exact canonical sanitized manuscript and ordered Google chunk hashes;
- full audio-derived ASR/source `>= 9.7`, coverage `>= 0.98`, first/last spans,
  and explicit no-missing/no-duplicate/no-reorder/no-unexpected-content
  evidence for every chunk and the aggregate;
- measured, non-estimated source-bound sync plus one-to-one audio-derived word
  timestamps;
- exactly six distinct source/audio-bound full-title listening samples, every
  active platform score threshold, confidence `>= 0.90`, and all fatal flags
  false; and
- an explicit descriptor conforming to
  `audiobook_qa_candidate_release_evidence.v1.schema.json`, hash-binding the
  full manifest, objective QA, listening QA, controlled documents, and every
  chapter while authorizing package construction only.

The builder maps the raw transcript token sequence to exact audio-derived
timestamp groups, then maps those source-bound tokens onto canonical chapter
paragraphs. A timestamp group may contain more than one spoken token, but the
builder rejects any canonical paragraph cut that would fall inside that group.
It creates chapter-aligned 96-kbps mono MP3 delivery segments near ten minutes
and never over twelve minutes, cutting only at measured canonical paragraph
boundaries. Every unchanged provider MP3 is retained under
`provenance/provider/audio/`; the assembled mono PCM/WAV master is retained for
future re-encoding. Segment timestamp JSON, VTT, and metadata sidecars remain
hash-bound and explicitly set `auto_estimated_sync=false`.

The resulting upload plan is `RELEASE_CANDIDATE`, but the build result retains
these blockers until separate operations prove them:

- `PRIVATE_B2_PRIMARY_UPLOAD_REQUIRED`
- `PRIVATE_B2_DR_REPLICA_REQUIRED`
- `CONTROLLED_RELEASE_ACTIVATION_REQUIRED`
- `PRODUCTION_ENDPOINT_AND_BROWSER_PROOF_REQUIRED`

The command performs no provider call, upload, catalog mutation, release-gate
change, public-asset write, or paid-lock access:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  internal/audiobook_lab/scripts/audiobook_package_builder_v2.py \
  build-qa-candidate \
  --slug <slug> \
  --full-manifest <private-run>/full_generation_manifest.json \
  --objective-qa <private-run>/full_audio_derived_qa.json \
  --listening-qa <private-run>/full_listening_qa.json \
  --release-evidence <private-run>/qa_candidate_release_evidence.json \
  --output-dir <empty-private-package-dir>
```

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
