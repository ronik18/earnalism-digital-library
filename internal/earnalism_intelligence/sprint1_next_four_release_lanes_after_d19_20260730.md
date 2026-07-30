# Sprint 1: next four release lanes after D19

Generated from `origin/main` commit `8e56e1af` on 2026-07-30. This is a
planning and preflight artifact, not publication authorization.

## Result

The finite conveyor has exactly four still-untried titles in its
`one_bounded_representative_candidate_then_source_bound_delivery` route after
excluding Jekyll and Pride, whose one title attempts are already consumed:

1. `picture-of-dorian-gray`
2. `frankenstein`
3. `white-fang`
4. `dracula`

The rank is shortest **safe release path**, not raw manuscript length. Dorian
has canonical/backend source parity and a recoverable historical cover pair.
Frankenstein is slightly shorter but its two controlled-publication roots
produce different manuscripts. White Fang is shorter still but has no retained
cover pair. Dracula has canonical covers, but its canonical chapters fail the
existing source-binding utility and its two roots diverge.

Public truth remains **32 readers / 4 audiobooks**:
`book-2b9853ec52`, `a-ghost-story`, `sredni-vashtar`, and `the-open-window`.
All four lanes in this report remain audio-hidden.

## Why this is the best first arm

Google `en-GB-Chirp3-HD-Charon` at rate `0.94` is the strongest current
title-adjacent English evidence. On Jekyll it passed four normalized objective
samples at `10.0`, four listening samples at `9.4`, confidence `0.95`, and no
fatal flags. That result chooses a first arm; it does **not** transfer quality
approval to another book.

Each lane therefore gets a new exact-text four-passage fingerprint. Jekyll's
fingerprint `8f3cb33e...` is not reused. No Studio-C, Achird, Kokoro, VoxCPM2,
Qwen, CosyVoice, or Chatterbox failure is reinterpreted as a pass.

The dry preflight produced:

| Rank | Title | Exact source result | New Charon fingerprint | Estimated audition synthesis |
|---:|---|---|---|---:|
| 1 | The Picture of Dorian Gray | PASS; 21 chapters, 428,577 chars, roots match | `b83e0703280dcf9deb42594ca5f12cbb127c559d89bfe53458a2ff527a6c3b5d` | $0.02256 |
| 2 | Frankenstein; or, The Modern Prometheus | PASS from canonical root; 28 chapters, 418,383 chars; backend differs | `54bdcd5feb7357f0ec752943fe3f8e8e937905fcaf8b6c75e097d1737a18ee7c` | $0.03026 |
| 3 | White Fang | PASS; 25 chapters, 401,043 chars, roots match | `f82171d76d1bbba34222c0deb831fc219c4c571b07ee8a519ee7d3de1b77e3b4` | $0.03486 |
| 4 | Dracula | BLOCKED; all 27 canonical chapters omit `bookSlug`; roots differ | not materialized | $0 |

These estimates are dry-run arithmetic only. No provider call or billing
occurred.

## Exact blockers

### 1. The Picture of Dorian Gray

- Canonical source preparation passes and both controlled roots match.
- Canonical front/back cover fields are empty.
- A historical Cloudinary pair exists under
  `the-picture-of-dorian-gray`, not the canonical
  `picture-of-dorian-gray`; it must be exact-title audited and
  checksum-promoted, not copied by similarity.
- Representative audio, objective QA, listening QA, full title, measured sync,
  package, endpoint, and browser gates are unrun.

### 2. Frankenstein

- Canonical source preparation passes at
  `e8f149a1...`; the backend mirror prepares as `abc8f361...`.
- Canonical cover fields are empty. An exact-slug historical Cloudinary pair
  exists but is not canonical truth.
- Reconcile the root divergence and checksum-promote a reviewed cover pair
  before admitting one title-specific representative candidate.

### 3. White Fang

- Canonical source preparation passes and both controlled roots match.
- Neither canonical truth nor the cover audit retains an exact front/back pair.
- A new rights-cleared, editorially reviewed cover pair is the prerequisite.

### 4. Dracula

- Canonical front/back covers are present.
- The canonical `data/` root has no `bookSlug` on any of 27 chapters, so
  `sprint1_prepare_google_english_input.py` fails closed on chapter 1.
- The backend mirror passes but produces a different, shorter source
  (`3e7f5f40...`, 848,683 chars), so using it would silently bypass canonical
  root selection.
- Repair and checksum-review canonical chapter binding; do not generate an
  attempt fingerprint before that repair.

## Provider-free fallback

For every lane, the non-synthetic alternative is an exact rights-cleared
licensed recording import. Literary public-domain status does not clear a
particular recording. The delivery must carry recording rights, provenance,
exact audio SHA-256, and an exact manuscript binding. No retained audio was
admitted: there are zero MP3/WAV/FLAC files under the current
`internal/audiobook_lab`, and historical filenames or object URLs are not
rights/source evidence.

Example packet command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/build_narration_import_packet.py \
  --slug picture-of-dorian-gray \
  --candidate-kind licensed_audio_import \
  --asset-root . \
  --output-root /private/tmp/earnalism-next-four-licensed-import
```

## Safe concurrency

Run cover review, root-parity reconciliation, source preparation, and empty
licensed-import packet preparation in parallel. Keep provider execution,
title admission, full generation, catalog mutation, deployment, and production
verification serialized by title. Planning four lanes does not authorize four
simultaneous generation waves.

No audio was generated, no provider was called, no asset was uploaded, no
controlled-publication or release state was changed, and
`paid_tts.lock` is absent from this `origin/main` baseline and was neither read
nor modified.

## Next exact command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 internal/audiobook_lab/scripts/sprint1_prepare_google_english_input.py \
  --slug picture-of-dorian-gray \
  --controlled-root data/controlled_publications \
  --output-root /private/tmp/earnalism-next-four-source-freeze
```

Then inspect the authenticated canonical cover queue before any provider
execution:

```bash
curl -fsS \
  -H "Authorization: Bearer ${EARNALISM_ADMIN_TOKEN:?}" \
  https://api.theearnalism.com/api/admin/books/cover-status \
  | jq '.books[] | select(.slug == "picture-of-dorian-gray")'
```
