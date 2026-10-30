# Independent model source review — nine cover replacements

Reviewed read-only on 2026-10-30 in `/private/tmp/earnalism-nine-cover-release-20261030`, against base `e79e76d9b060bd7bf72e87a0de7452e8135cceb7`. This is model technical review, not human legal sign-off or production verification.

At review capture, 171 changed/new files had canonical sorted `(path, SHA-256)` JSON-list digest `4f216d045628ee3bbd0493fd57b027bab9957271df5f9e59e1b50bf778eec5dc` (compact JSON separators). Root's subsequent ledger additions need their own final diff inspection; this is a working-candidate snapshot, not an invented commit identity.

## Conclusion

No blocking source-scope defect found. Cover-only successor bindings preserve existing acceptance scope and operational state. Deployment scope and actual version verification remain separate release gates.

## Fresh independent checks

- Compared every changed JSON field against the base. All nine public_book changes are cover URLs/aliases, dimensions, cover status or cover provenance SHA. No noncover public field changed.
- All nine rights_decision documents are identical outside `components`: decision identity, operator, territories, uses, acceptance status and legal basis remain unchanged. Registry changes are the nine corresponding record hashes and a cover replacement historical record; unrelated registry fields, audio package bindings and revocations are unchanged.
- All nine publication manifests are identical after excluding their cover URL, public/approval artifact hashes and derived self-hash. Reader status/exposure, audio release, chapter identities and other publication state remain unchanged. Open Window and Selfish Giant retain their existing protected audio state; this is preservation, not fresh audio acceptance.
- Reader bootstrap rows differ only in canonical record SHA pins; all other row and top-level fields match the base.
- Existing cover_provenance documents are retained verbatim as parsed objects under `previous_provenance`; new exact delivery evidence is separate. The source candidate explicitly reports production_verified=false and model visual review qualification.
- Every file in all nine canonical package directories matches its backend mirror byte for byte.
- No diff exists for server.py, launch configurations, catalog exclusions, chapter files, reader manifests or source evidence.
- Independently invoked `scripts.verify_catalogue_clearance_batch.verify(Path.cwd(), base='e79e76d9b060bd7bf72e87a0de7452e8135cceb7')`: PASS, nine changed packages, no issues, reviewed authority bindings valid. Its audio_exposed=true accurately reflects existing protected audio, not newly enabled audio.
- `git diff --check`: exit 0.

## Test adaptation review

The Open Window artifact test pins exact new asset hashes and verifies local static delivery bytes plus immutable stored-original URL identity. It no longer falsely requires an unavailable Cloudinary version_id for the static delivery event. Historical version-ID evidence remains asserted. Audio descriptor checks and public audio URL non-leak assertions remain. No runtime code change accompanies this test update.

## Limits and remaining gates

Root reports 126 focused and 375 expanded tests, three frontend tests, production build, 172 snapshots/3701 assertions and contract freshness passing. This review does not relabel those reports as independently rerun tests. Existing export/font/component evidence is referenced; no fresh external rights determination was invented here. Source checks do not prove runtime backend source identity, deployment compatibility, served asset hashes or live customer mapping. Those require the authorized release lane's exact final commit, deployment and canary evidence.

Next action: root inspects only its final ledger additions, binds this review to the final commit/tree, and completes normal required review/CI and deployment-scope checks before release.
