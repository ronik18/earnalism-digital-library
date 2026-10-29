# Owner-produced source-unit package preparation

This adds the Selfish Giant preparation path using the same immutable package,
source-unit timing, primary/DR finalization and downstream release checks used
by the retained Open Window successor. It does not copy Open Window identities,
85-point representation, scores, adoption or production coverage. Existing
Google and frozen Open Window validation paths remain unchanged.

## Trust boundary

`internal/audiobook_lab/release_gate/owner_produced_package_adoptions.json` is a
separately reviewed registry. This source candidate adopts only the exact
Selfish Giant package recorded in `selfish-giant-20261029/`, with downstream
storage, activation and production acceptance still blocked. The module cannot take a caller-selected registry path or generate an
adoption. A future exact record must bind:

- Selfish Giant title/author, current controlled source/manuscript, complete
  original WAV/MP3 masters, measured24k mono samples and ordered delivery map.
- Actual generation/provenance, objective QA, resolved material-wording review,
  owner-scoped voice direction, model/voice licence, source edition, exact per-unit source-offset/text manifest, cover reuse
  and producer authority evidence digests. No numeric listening scores are
  created or required by this representation.
- Pinned Qwen custom-voice revision, stock Ryan and runtime code revision SHA.
- Actual owner authority reference and its immutable evidence, with no
  unresolved material defects or wording findings.
- A separately accepted, valid, non-revoked IN/audio_stream record in the
  existing rights registry, binding the exact source, manuscript, masters and
  ordered audio components. Reader approval cannot substitute.

The registry review must inspect the real linked evidence. A JSON status alone
is not a legal, acoustic or production assertion. Test adoptions are injected
only in unit-test memory; none is checked into either production registry.

## Local bundle and command

Consolidate the exact existing files under one private bundle directory. The
bundle JSON schema is `earnalism.owner-produced-local-package.v1`. Fields:

- `release_descriptor`: `audiobook_release_descriptor.v1`, exact identity and
  measured duration/sample count, evidence hashes, generation pins,
  `SOURCE_UNIT_PARAGRAPH_BOUNDS_ONLY`, highlighting false and explicit
  `owner_produced_source_units.v1` candidate representation/adoption digest.
- `package_identity`: storage-independent tracks/chunks with exact measured
  word/paragraph ranges, cumulative times and audio/timestamps/VTT/metadata
  SHA/size/type. No provider locators or guessed VersionIds.
- `master_wav`, `master_mp3`, `manuscript`: relative path+SHA references.
- `evidence_files`: exact named path+SHA references for every evidence role.
- `source_units`: ordered generation IDs, optional `delivery_segment_id` for many-to-one delivery grouping, exact canonical source text, `source_start`/`source_end` character offsets, `text_sha256`, and inclusive `start_word`/`end_word`. The exact manifest SHA is pinned by reviewed adoption and descriptor; each unit must match its actual source slice and delivery word bounds. Only whitespace may separate slices. Spoken layout/case overlays remain separate provenance; no word-level highlighting is claimed.
- The descriptor/adoption also pin `reader_paragraph_map_sha256`; adoption pins current `reader_content_sha256`. Preparation runs existing local Reader reflow through Node and maps its exact text back to canonical offsets. Contiguous generation units may share one delivery chunk only when the outer bounds align to actual Reader paragraphs. Raw hardwrapped lines and generation-unit indices must not masquerade as displayed paragraphs.

For the exact current Selfish source,136 raw blankline blocks reflow to23 displayed Reader paragraphs. The20 generation units can be losslessly concatenated into6 paragraph-aligned delivery groups, preserving all originals; this grouping is source-only until actual samples/durations and joins are checked. The large group must measure at most720000ms under the existing package limit. If it exceeds that, only genuine measured paragraph cuts may subdivide it; never proportionally estimate timing.
- `asset_files`: `<segment_id>-<role>` path+SHA references for each delivery file.

Run from the qualified isolated source:

```sh
python3 internal/audiobook_lab/scripts/owner_produced_package.py \
  --bundle /absolute/private/bundle/bundle.json \
  --output-dir /absolute/private/new-package-directory
```

This verifies full local bytes, PCM or IEEE-float original WAV framing without
conversion, lexical source coverage, exact adopted identity and complete
contiguous delivery mapping. It writes a descriptor, generic package semantics
and immutable upload plan including both masters. Output must not already exist.
No inference, encoding, network, canonical mutation, upload or publication runs.

Use existing `audiobook_package_storage_v2.py` for separately authorized scoped
primary/DR uploads and full-byte verification; use existing
`audiobook_package_builder_v2.py finalize` for actual receipt VersionIds. The
manager revalidates canonical package hash/schema/storage/time/count/identity,
rights, receipts, hidden fallback and source mirrors before canary staging.

All four downstream blockers remain: private primary storage, independent DR,
controlled release activation, production endpoint/browser evidence. Public
promotion still requires the existing exact acceptance path. LOCAL decoder or
fixture tests must never be labelled production playback/accounting evidence.
No paid customer session, US access, global rollout or auto-deploy setting is
changed by preparation.

## Focused verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s internal/audiobook_lab/scripts -p test_owner_produced_package.py -v
```

Fixtures use synthetic non-audio bytes and local PCM/float framing. They prove
admission/failure behavior, generic receipt finalization compatibility and
preservation of output history; they do not qualify a real master or release.
Actual retained Qwen IEEE-float WAV was also read-only parsed during preparation;
its bytes were not modified.

## Lifetime India control

The owner explicitly chose lifetime availability for this exact India
`audio_stream` package. `valid_until: "LIFETIME"` is an explicit non-expiring
control, not an arbitrary distant date. `valid_from`, trusted territory, exact
components, registry digest, accepted status and revocation remain enforced.
Existing finite records and accepted US/India Reader records are unchanged.
This source adoption grants no US access, downloads, upload, deployment or
customer-session authority. Retain primary/DR assets without automatic deletion;
actual provider retention and independent replicas remain unqualified.

The 12:57.120 master uses 20 retained originals, six paragraph-aligned groups,
23 actual Reader paragraphs, and no estimated word highlighting. Evidence
records preserve actual ASR limitations and targeted owner wording answers;
no full-title human listening score or production playback is claimed. Local
source preparation does not install an active/public release pointer.
