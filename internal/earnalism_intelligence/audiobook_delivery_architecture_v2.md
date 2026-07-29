# Earnalism Audiobook Delivery Architecture v2

Status: implemented as a release-safe runtime contract; no title was approved,
published, uploaded, or otherwise moved through a release gate by this change.

## Decision

Use immutable, source-bound audiobook packages made of chapter-aligned segments
no longer than 12 minutes. Store audio and timestamp sidecars in the existing
private Backblaze B2 delivery store. The browser receives only a small
same-origin manifest and same-origin segment URLs.

This replaces neither editorial QA nor controlled-publication truth. A package
is visible only when the title already passes the existing reader and audiobook
release checks.

## Canonical package

The machine-readable contract is
`internal/audiobook_lab/schemas/audiobook_package_manifest.v2.schema.json`.

The server additionally fails closed unless:

- the package slug matches the requested controlled-publication slug;
- the manuscript SHA-256 matches the controlled record's source or content
  hash;
- release evidence, package version, segment IDs, audio SHA-256 values, and
  timestamp SHA-256 values are present;
- track and segment order is deterministic;
- word ranges and cumulative durations are contiguous;
- the declared segment count and duration match the exact segments;
- every segment is at most 12 minutes; and
- every media location resolves to configured Backblaze B2 storage.

Raw storage URLs, manuscript hashes, and release-evidence identifiers are not
projected into the public reader manifest.

## Runtime delivery

- `GET|HEAD /api/reader/book/{slug}/audiobook/manifest`
- `GET|HEAD /api/reader/book/{slug}/audiobook/packages/{package_version}/segments/{segment_id}`
- `GET|HEAD /api/reader/book/{slug}/audiobook/packages/{package_version}/segments/{segment_id}/timestamps`

An unknown title, hidden audio title, stale package version, unknown segment,
invalid package, or unmatched storage location returns a fail-closed response.
Segment delivery reuses native B2 Range reads and the existing private browser
cache policy. Redis remains for small shared metadata/state only; audio bytes
are never copied into Redis.

## Reader behavior

The Reader accepts both the legacy approved monolithic package and package v2.
For package v2 it selects the segment covering the current chapter/page word
offset, advances to the next immutable segment within the same chapter, and
changes playback rate without restarting.

The MP3 is not assigned to the audio element on page load, hover, focus, or
touch. Loading begins only after the reader activates the play control. Small
JSON manifests and timestamp sidecars remain cacheable metadata.

## Parallel production boundary

Independent workers may prepare private, source-bound title packages in
parallel. Promotion remains serialized per title:

1. complete the exact full-title audio and timestamps;
2. pass the existing rights, covers, ASR/manuscript, ordered-content, measured
   sync, listening, checksum, and editorial gates;
3. upload immutable segments and verify every checksum;
4. bind package v2 to controlled-publication truth;
5. verify manifest, Range `206`, and browser playback; and
6. only then approve public exposure through the existing release workflow.

No worker may update audiobook approval merely because package generation or
upload succeeded.

## Rollout

The runtime is backward compatible and remains dormant for titles without an
`audiobook_package` field. The safest first rollout is one already approved
audio title, repackaged byte-for-byte into v2 segments, followed by endpoint and
browser comparison against the current production playback. New title
publication is a separate, later release decision.

Next exact validation command:

```bash
python3 -m pytest backend/tests/test_b2_audiobook_routing.py backend/tests/test_redis_cache_policy.py -q
```
