# Lane 2 first activation batch review — 2026-09-29

## Authority and scope

The canonical `data/controlled_launch.json` authority at `origin/main` `32d71ab2bac1e6b30f2389b02c7ffcbaefe06051` lists six live-approved titles: `a-ghost-story`, `the-tell-tale-heart`, `radharani`, `a-white-heron`, `the-gift-of-the-magi`, and `the-canterville-ghost`. The local catalog-truth audit agrees. None of the 15 requested candidates is in that set, and none is in `data/catalog_exclusions.json`. Package-local `LIVE_APPROVED` strings and historical title decisions are not launch authorization.

This review is text/catalogue-only. No live allowlist or production data was changed. No rights, source, edition, cover, authorization, or audio evidence was created. No payment, entitlement, audio, or backend runtime files were edited.

## Candidate reconciliation

| Candidate | Current status | Safe deterministic work | Remaining non-fabricable blocker |
|---|---|---|---|
| `alices-adventures-in-wonderland` | Non-live; read-only because it is owned by the active rights-binding automation | None; left package unchanged | Accepted edition-bound rights decision, required structured rights metadata/review, cover provenance, and publication authorization are absent. |
| `sredni-vashtar` | Non-live; reader package has audio enabled metadata; not in live authority | None; left package untouched | Existing audio metadata makes the canonical validator require an audio hash; audio is out of scope. Rights decision, cover provenance, and edition-bound authorization also absent. |
| `dracula` | Non-live; manifest schema-valid; not exposed | Rebuilt deterministic checksum bundle and manifest binding | Accepted edition-bound rights decision (validator requires author death year, original publication year, and verification date), cover provenance, and publication authorization absent. |
| `book-d19e96859f` — গিন্নি | Non-live; manifest schema-valid; not exposed | Rebuilt deterministic checksum bundle and manifest binding from current package evidence | No accepted rights decision; Bengali Wikisource evidence lacks the required pinned source revision and complete attribution/license/share-alike/change-notice obligations; independent cover provenance and edition-bound publication authorization absent. |
| `book-f5d593e1f4` — রামকানাইয়ের নির্বুদ্ধিতা | Non-live; manifest schema-valid; not exposed | Rebuilt deterministic checksum bundle and manifest binding from current package evidence | Same missing accepted rights decision, pinned Wikisource revision/license obligations, independent cover provenance, and edition-bound authorization. |
| `book-4b944e64fa` — একরাত্রি | Non-live; audio enabled metadata; placeholder cover URL empty | None; left audio and package state untouched | Audio SHA required by package builder (audio out of scope); no accepted rights decision, no required Bengali source/license evidence binding, no independently proven cover, no edition-bound authorization. |
| `book-2e468c4990` — কাবুলিওয়ালা | Non-live; audio enabled metadata | None; left audio and package state untouched | Audio SHA required (audio out of scope); missing accepted rights decision, pinned Bengali source/license obligations, independent cover provenance, and edition-bound authorization. |
| `book-0deb35c750` — খাতা | Non-live; audio enabled metadata | None; left audio and package state untouched | Audio SHA required (audio out of scope); missing accepted rights decision, pinned Bengali source/license obligations, independent cover provenance, and edition-bound authorization. |
| `book-c7f3ce526c` — খোকাবাবুর প্রত্যাবর্তন | Non-live; audio enabled metadata | None; left audio and package state untouched | Audio SHA required (audio out of scope); missing accepted rights decision, pinned Bengali source/license obligations, independent cover provenance, and edition-bound authorization. |
| `book-1090573dff` — ছুটি | Non-live; audio enabled metadata; placeholder cover URL empty | None; left audio and package state untouched | Audio SHA required (audio out of scope); missing accepted rights decision, pinned Bengali source/license obligations, independently proven cover, and edition-bound authorization. |
| `book-754da4eab8` — তারাপ্রসন্নের কীর্তি | Non-live; audio enabled metadata | None; left audio and package state untouched | Audio SHA required (audio out of scope); missing accepted rights decision, pinned Bengali source/license obligations, independent cover provenance, and edition-bound authorization. |
| `book-a74c1a1451` — দালিয়া | Non-live; audio enabled metadata | None; left audio and package state untouched | Audio SHA required (audio out of scope); missing accepted rights decision, pinned Bengali source/license obligations, independent cover provenance, and edition-bound authorization. |
| `book-63afd5e9be` — দেনাপাওনা | Non-live; audio enabled metadata | None; left audio and package state untouched | Audio SHA required (audio out of scope); missing accepted rights decision, pinned Bengali source/license obligations, independent cover provenance, and edition-bound authorization. |
| `pride-and-prejudice` | Non-live; read-only because it is owned by the active rights-binding automation | None; left package unchanged | Accepted edition-bound rights decision, required structured rights metadata/review, cover provenance, and publication authorization absent. |
| `frankenstein` | Non-live; read-only because it is owned by the active rights-binding automation | None; left package unchanged | Source identity reconciliation is required (`Earnalism historical import` vs Project Gutenberg #84); accepted edition-bound rights decision, cover provenance, and publication authorization absent. |

Existing cover image URLs were not accepted as provenance. No `cover_provenance.json` exists in these 15 canonical packages. Bengali source URLs do not by themselves establish an exact source revision or satisfy the license attribution/share-alike/change-notice contract.

An expanded, read-only scan found `the-adventures-of-sherlock-holmes` outside the priority list. Its existing Gutenberg #1661 package passes the publication conveyor's reader-precheck with no content blockers. Its existing manifest was refreshed to non-exposed `READY_FOR_APPROVAL` from source evidence specifying India, and its existing checksum bundle verified. It is **technically ready but not activatable**: no accepted title-specific rights registry decision, independent cover-provenance record, edition-bound publication authorization, or successful production runtime release check exists.

The same scan found `agentic-ai-with-python`, `the-art-of-money-getting`, and `the-selfish-giant`; no changes were made. The first lacks an authoritative source URL and its apparent `APPROVED/exposed` manifest is not current launch authority. The latter two have audio-enabled package state (left untouched); `the-art-of-money-getting` also has source-use scope limitations. `the-selfish-giant` has historical title-history public-live wording, so it is not counted as a new activation candidate.

## Changes made

- Rebuilt checksum manifests for `dracula`, `book-d19e96859f`, and `book-f5d593e1f4` from files currently present in their canonical controlled-publication packages. Sherlock Holmes’ existing checksum bundle was already valid.
- Generated non-exposed `publication_manifest.json` files for `dracula`, `book-d19e96859f`, and `book-f5d593e1f4`; each is schema-valid but remains reader-release blocked. Refreshed Sherlock Holmes’ existing manifest from current evidence to `READY_FOR_APPROVAL`, not approved or exposed. Alice, Pride and Prejudice, and Frankenstein were inspected read-only because they belong to the active rights-binding automation. No `--publish-approved` operation was used.
- Left the nine audio-metadata packages unchanged. No audio state was altered or repaired.

## Validation

- Canonical local catalog audit: PASS; six live slugs match `controlled_launch.json`; zero exclusions intersect the requested candidates.
- Publication manifest schema validation: PASS for the three generated blocked manifests; all three remain not exposed and reader release BLOCKED on missing approved rights metadata/evidence.
- Sherlock Holmes publication precheck: `READY_FOR_APPROVAL`, `exposed=false`, with no manifest content blockers; activation remains blocked by independent cover provenance, accepted rights authorization, edition-bound publication authorization, and runtime release validation.
- Package checksum verification: PASS for the three rebuilt bundles and Sherlock Holmes’ pre-existing bundle. Alice’s active-task bundle also verifies; Pride and Prejudice and Frankenstein have one stale checksum binding each, left untouched for their active rights-binding automation.
- Reader chapter/file binding: PASS for the inspected candidate packages; this does not substitute for complete reader release approval.
- Production catalog/reader runtime: HOLD. The production API audit returned `RELEASE_PROXY_SCOPE_INVALID` / HTTP 451 for book and reader-manifest probes; runtime release readiness is therefore not proven.
- `scripts/controlled_publication_precheck.py`: PASS for its established Dracula-centric precheck, not an activation authorization for these candidates.
- `scripts/bengali_rights_package_validator.py`: FAIL/HOLD on its existing pilot-allowlist and launch-configuration assertions; no validator or launch config was changed to suppress that finding.
- `pytest` is unavailable in the selected Python runtime; no dependencies were installed. Repository CLI validation was used instead.

## Outcome and next action

`FIRST_NEW_TITLE_ACTIVATION_READY_BATCH=NOT_ACHIEVED`. Zero candidates satisfy all rights, edition, cover, authorization, package, publication, and runtime gates. The smallest non-fabricable next action is for the rights/evidence owner to supply title-specific accepted rights decisions, exact source/edition records (including complete Bengali source license obligations), independently sourced cover provenance, and edition-bound publication authorization. After evidence exists, rerun candidate validators and resolve the production `RELEASE_PROXY_SCOPE_INVALID` runtime gate before any controlled-launch change. No live approval change is proposed in this PR.


## Sherlock source/cover/runtime follow-up — 2026-09-29T06:51:05Z

- Exact-source identity is confirmed as Project Gutenberg eBook #1661. Current official raw snapshot SHA-256: `922e2a12ccb43a4c9544c260b2166c6ad2097aeb5957faeee113f173bb857cd0`. All twelve chapter bodies now compare equal after documented markup/whitespace normalization; two omitted text spans were restored in chapters 2 and 5. Rebound content/source/provenance hashes and package checksum/manifests.
- Replaced the inherited claim of India commercial clearance with `review_required`. The official Gutenberg notice establishes U.S. public-domain status and directs non-U.S. users to check local law; no title-specific accepted rights decision or edition-bound authorization exists. Package and runtime remain fail-closed.
- Added first-party Earnalism vector/typography front and back covers, both 800x1200, with asset hashes and no third-party art; both were visually inspected. Cover provenance is now present.
- Calibrated public same-origin scoped runtime probe: known-live `a-ghost-story` returns HTTP 200; Sherlock returns HTTP 451. Local gate gives Sherlock `ACCEPTED_DECISION_MISSING` for catalog and reader paths. No proxy/release check was weakened.
- No activation-ready title yet. Exact owner/legal decision packet: `internal/earnalism_intelligence/sherlock_holmes_publication_decision_packet_20260929.md`. Live allowlist unchanged.

- 2026-09-29T06:59:32Z — Audio/text coupling follow-up: canonical launch audio set is empty. The nine candidate packages retain local audio markers; the generic publication manifest keeps `required_for_reader_release=false`. Seven candidate manifests have incomplete package-claimed audio approvals (missing audio SHA); `sredni-vashtar` has an audio hash but remains outside runtime authority. The canonical text reader validator isolates audio-only discrepancies; a known-live `a-ghost-story` control with stale audio flags passes reader validation while failing audio validation. No package audio metadata or release state was changed. Replaced the stale `bn-066` test control (no longer in current live allowlist) with `a-ghost-story`.

- 2026-09-29T07:01:27Z — Seamless-brand CI exact failure was `binds both production-hash authorities to checked-in production source`; the expected hash was stale because the newly added first-party Sherlock cover assets are inputs under `frontend/public`. Recomputed the documented sorted per-file SHA-256 source fingerprint as `7650cbd519a6b0b9a0baed9cdf5d941d7ddc0864a96422771ae27f0ee5a0302c` and rebound both workflow job authorities to that value. No visual assertion or gate was weakened.
