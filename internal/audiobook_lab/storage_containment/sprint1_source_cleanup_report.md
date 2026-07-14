# Sprint 1 Direct Audio Source Cleanup Report

## Result

`SPRINT1_RUNTIME_AUDIO_SOURCE_FAIL_CLOSED`

Owner authorization: `AUTHORIZE_P0_REMOVE_SPRINT1_UNAPPROVED_DIRECT_AUDIO_REFERENCES_FROM_PUBLIC_SOURCE.`

The cleanup was performed against `e4641f4` after the scoped storage evidence reported `SPRINT1_STORAGE_BYPASS_CONTAINED`. It changed deployable source only. No remote storage, TTS, ASR, upload, publication, Listen state, or paid TTS lock operation occurred.

## Scope Reconciliation

The authoritative checklist named 23 runtime records. On the current baseline, two listed root mirrors are absent and two backend mirrors contain the effective records, leaving 23 records in the current audit scope. Seventeen were already fail-closed. Six public-book records still contained stale direct-package or provider metadata and were cleaned.

The cleanup removed 44 direct-URL field occurrences representing 10 unique stale Cloudinary URLs from the four F5/Muchiram mirror records. Alice and Nishkriti had no remaining direct URL but retained stale provider, voice, asset-slug, and update metadata; those fields were cleared.

## Release Truth

- `book-2b9853ec52` remains `APPROVED / QA_PASSED` and retains its exact B2 package ending in `book-2b9853ec52_mp3_a974819392d7.mp3`.
- `a-ghost-story` remains `APPROVED / QA_PASSED` and retains its exact B2 package ending in `a-ghost-story_mp3_c0e52985ee1e.mp3`.
- All other 30 active Sprint 1 manifests serialize `audio.enabled=false` with empty provider, voice, URL, assets, release gate, and QA fields.
- F5 and Muchiram historical reconstructed approval records now explicitly block public audio instead of contradicting the release-gated manifest.
- Reader metadata, chapter content, covers, rights, language, titles, and authors were preserved.

## Changed Runtime Slugs

- `alices-adventures-in-wonderland`: cleared stale Cloudinary provider/voice/asset metadata.
- `nishkriti`: cleared stale Cloudinary provider/voice/asset metadata.
- `book-f5d593e1f4`: removed stale Cloudinary MP3/sidecar packages and failed audio enablement closed in both mirrors.
- `muchiram-gurer-jibanchorit`: removed stale Cloudinary MP3/sidecar packages and failed audio enablement closed in both mirrors.

Checksum manifests were updated for every modified controlled-publication packet.

## Validation

- Focused cleanup tests: `13 passed`.
- Backend release-truth tests: `62 passed` in one focused run.
- Frontend release-truth tests: `5` suites, `39` tests passed.
- Controlled-publication checksums: `PASS`.
- Post-cleanup active-Sprint scan: zero unapproved direct audio URLs in deployable controlled-publication source.
- Approved direct source records: four mirrors for exactly two approved titles.
- Frontend public/build audio files: zero.
- Static `/audio/*` requests remain routed to removed content; browser speech fallback, word-level sync claims, non-approved `AudioObject`, and public `.in` contact email were not found in runtime source.
- Production results are appended during PR close-out.

## Residual Risk

`NONSPRINT_REMOTE_CONTAINMENT_DEFERRED_BY_OWNER`

The 471 reviewed non-Sprint objects remain outside this authorization. Thirty already-inaccessible scoped objects lack private-retention evidence but expose no current public bypass. Neither category was modified in this cleanup.
