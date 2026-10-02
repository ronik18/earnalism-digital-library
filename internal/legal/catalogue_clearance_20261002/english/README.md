# English text source reconciliation — 2026-10-02

Scope: canonical non-live English Reader packages; no cover review, audio publication, launch allowlist, payment, entitlement or customer mutations.

## Evidence

- `matrix.json`: all 90 canonical non-live English Reader rows, including the superseded Jekyll alias which must not be reactivated.
- `source_receipts.json`: 61 distinct official Project Gutenberg metadata and raw-text receipts, all HTTP 200, with actual timestamps, resolved URLs and byte hashes. Bibliographic metadata preserves translator/editor identities separately from authors.
- `publication_fact_receipts.json`: actual British Library primary Alice first-publication/death facts, university-library Frankenstein publication facts, museum Pride publication verification, and current Gutenberg reuse/trademark policy. Direct HTTP failures remain recorded; successful browser verification is identified separately.
- `priority_edition_reviews.json`: exact chapter comparison and boundary review for Alice, Frankenstein, Dracula and Pride.
- `verified_text_repairs.json`: exact source-supported Frankenstein narrative restoration.
- `source_boundary_reviews.json`: the initial 70 exact-match candidates checked for between-chapter narrative gaps; none have substantial internal gaps (all interchapter residuals are below 75 characters). This does not automatically clear anthology boundaries/translations.
- `additional_verified_text_repairs.json`: explicit Pride old/new edition migration and Dracula preface restoration, including preserved old chapter hash bindings.
- `noncover_text_clearances.json`: three actual owner-delegated objective text-clearance records (Alice, Frankenstein, Pride), with no cover/audio/runtime authorization.
- `prepared_slugs.json`: 85 source-supported canonical packages with evidence bindings and regenerated schema-valid, unexposed text preparation manifests.

## Findings

72 packages have ordered whole-chapter text containment against their official source after NFC/whitespace normalization only. This is **not** a blanket full-edition approval: omitted material, translator/editor layers, first publication and jurisdiction must be verified separately. Fourteen packages differ or lack chapter bodies; four have non-Gutenberg/missing source evidence. Historical source/content hashes were retained. Current receipts and actual chapter aggregate identities are bound separately. Alice, Frankenstein and Pride explicitly bind current retrieved source identities for their new non-cover clearance records; old identity history is preserved, never relabelled as reproduced.

Alice's twelve narrative bodies match the exact #11 Millennium Fulcrum Edition 3.0. Its interchapter gaps are chapter labels, and its tail reaches the Gutenberg END marker. British Library record confirms underlying first publication 1865 and author death 1898; no illustrations were imported. Its objective non-cover text/source/rights/publication clearance is complete under owner delegation; cover display and runtime registration/activation remain deferred.

Frankenstein #84 has 28 represented chapter bodies. The chapter 11 import had swallowed the first narrative phrase into its heading. The exact phrase was restored into the body, the title became `Chapter 11`, and chapter/public Reader metadata and checksums were regenerated. Do not substitute #41445 (1818) or #42324 (1831) for #84 without an explicit edition migration. Primary first-publication evidence is separate from exact electronic edition identity.

Pride #1342 catalog was updated on 2026-09-29 (raw header says September 1, retained as source discrepancy). Its illustrated 1894 edition has now been explicitly migrated into a text-only Austen narrative: all 61 chapters are extracted, illustration captions removed with balanced bracket parsing, and the separately authored Saintsbury preface excluded. Old immutable identity is preserved in source_identity_history; no historical approval is transferred. All 61 bodies now match the documented transformed source. Dracula's original literary preface has been restored as chapter-000 ahead of its 27 chapters, with sequential Reader order; all 28 bodies match. Its protected rights 451 and launch hold remain unchanged.

Two regenerated manifests (`the-art-of-money-getting`, `the-selfish-giant`) report `READY_FOR_APPROVAL`, not exposed. Alice, Frankenstein and Pride now also report `READY_FOR_APPROVAL`; the other 80 source-supported packages are `BLOCKED`, not exposed. This is schema/preparation status, not runtime publication authority.

## Owner delegation and decision schema

Current `rights_decision_gate.py` checks accepted registry digest, exact components, territories, uses, dates, evidence hashes, nonempty reviewer attribution, legal basis and satisfied conditions. It does not impose a particular human identity. Current direct owner delegation can be attributed truthfully to an automated executor acting under that delegation **after objective conditions are met**. Missing accepted records are therefore preparation work, not an automatic request for another owner approval. Three local accepted NON_COVER text records and edition-bound publication authorizations were generated under this actual delegation for Alice, Frankenstein and Pride. They exclude cover display/audio and remain absent from the production registry/live allowlist. Historical source identities are retained, while actual retrieved source bytes and current Reader corpus now bind the accepted edition records. No objective condition is silently waived.

## Verification

Fourteen focused tests pass, including punctuation/order preservation, containment versus completeness, known-live exclusion, alias preservation, and exact Frankenstein restoration. All 85 conveyor outputs validate; all remain unexposed. No audio artifact was edited or enabled.

```sh
python3 -m unittest scripts/test_reconcile_english_source_evidence.py -v
python3 scripts/reconcile_english_source_evidence.py
```

The second command reuses `/tmp/earnalism-english-source-reconciliation` raw snapshots if present. To refresh actual official receipts deliberately, use `--fetch` with a new output directory or remove only the specific stale receipt; do not repeatedly download unchanged source batches. An offline run without cached source bodies reports `NOT_RETRIEVED`, never a fabricated comparison PASS.

## Missing chapter restoration

`missing_chapter_restorations.json` records actual official source section boundaries and hashes for the restored scientific-management chapter 004, the Suicide Club selected cycle, and Ward No. 6 (Constance Garnett translation). Their dangling metadata was not deleted to conceal narrative loss. All restored bodies match the exact source; text-only preparation remains unexposed and does not create territorial rights or publication approval for these titles.

## Current superseding checkpoint

The current matrix covers 90 non-live English packages. 86 now carry local accepted, edition-bound **non-cover text** decisions and authorizations under the current owner delegation; these are not production registry entries or live approvals. Each ready matrix row links current source/body/chapter identities to independent whole-work boundary evidence in `current_whole_work_boundary_verification.json`; containment alone remains explicitly insufficient. All 86 current publication manifests report rights APPROVED; cover/publication deployment and runtime gates remain separate.

The four remaining rows are Eyesore (39/53 canonical chapters, damaged-source glyph verification incomplete), Metamorphosis (commercial translation permission unresolved, including contradictory primary Johnston permission declarations), and two empty superseded aliases for already-live canonical titles. `eyesore_manuscript_verification_hold.json` records actual original-volume review and the precise engineering hold. No partial OCR draft has been installed as cleared text. `kafka_alternative_permission_review.json` preserves the primary conflicting permission evidence.

This section supersedes the earlier intermediate counts and three-title description above. Current focused source tests: 19 passed. Milverton now restores its omitted opening; Gatsby, Jane Eyre, Hound and Frankenstein restore actual author matter from their same verified editions. No cover, audio or runtime publication authorization was broadened.
