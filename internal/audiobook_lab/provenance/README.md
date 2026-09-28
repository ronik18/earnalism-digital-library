# Private audiobook provenance pipeline

This contract is for internal generation and audition evidence. It never makes
an audiobook public. The existing package-v2 builder remains the only package
constructor and remains gated by controlled title truth, QA, rights, and
package-build authorization.

## Project Gutenberg #269 source binding

The internal source binding for *The Open Window* is
`the-open-window-gutenberg-269-source-binding.json`. The source is the
Gutenberg #269 anthology; normalization isolates the exact story interval
from `THE OPEN WINDOW` up to (but excluding) `THE TREASURE SHIP`. It preserves
paragraph breaks, joins hard-wrapped lines with one space, emits UTF-8 NFC and
LF, and strips Gutenberg header/footer material. Source and rights records stay
internal/admin-only.

To normalize a previously downloaded source without network access:

```sh
python3 scripts/audiobook_provenance.py normalize-gutenberg-269-story \
  --input /path/to/pg269.txt \
  --output /path/to/private/the-open-window.txt \
  --manifest /path/to/private/the-open-window-source-binding.json
```

The content itself is not written to this repository by that command unless
the operator selects a repository path. The checked-in binding contains hashes
and the extraction contract, not the source text.

## Audition and generation controls

`scripts/audiobook_provenance.py` provides deterministic job IDs, explicit
English Kokoro voice inventory, audition audio hashing, runtime capture,
segment provenance, QA/license references, storage receipt binding, and a
rights workflow bundle that reports missing evidence without fabricating it.
The notebook exposes three candidate English voices (`af_heart`, `af_bella`,
`af_nicole`) in a private audition function. The function is opt-in and is not
run as part of this change. Successful synthesis bytes are individually
SHA-256 bound in `audition_manifest.json`; the manifest cannot authorize full
generation or public release.

Full generation requires all of the following at execution time:

- `OWNER_FULL_GENERATION_APPROVED=True`;
- `OWNER_SELECTED_VOICE` set to one explicit compatible voice and identical to
  the synthesis `VOICE`;
- immutable Kokoro snapshot revision and captured model artifact hash;
- the existing title, rights, QA, content, listening, and storage gates.

The notebook defaults `OWNER_PILOT_APPROVED`,
`OWNER_FULL_GENERATION_APPROVED`, `OWNER_PUBLIC_RELEASE_INTENT`, and
`GO_LIVE_ENABLED` to `False`. No provider call, CUDA run, upload, storage
mutation, package activation, or catalog change is part of validation.

## Provenance and release-candidate handoff

`audiobook_segment_provenance.v1.schema.json` and
`audiobook_generation_provenance.v1.schema.json` bind text/audio hashes,
runtime, voice, QA evidence, license references, and storage receipts. Missing
rights artifacts remain `BLOCKED_MISSING_EVIDENCE`; their evidence references
are not decisions or approvals.

When all required QA and owner authorization artifacts actually exist, call
`create_package_v2_candidate` from the helper module or use the guarded
`internal/audiobook_lab/scripts/audiobook_package_builder_v2.py
build-qa-candidate` command. This builds a private release candidate only; it
does not upload, activate, or publish it. A verified primary/DR receipt is a
separate later handoff and must match the candidate asset hashes.

Kokoro's explicit voice inventory in this implementation supports English
only. Bengali remains fail-closed for Kokoro; Bengali audiobook work must use
the campaign's approved provider/voice path or move to human narration or a
licensed audio import packet.
