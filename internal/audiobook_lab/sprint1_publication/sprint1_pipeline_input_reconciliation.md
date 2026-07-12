# Sprint1 Pipeline Input Reconciliation

Generated: `2026-07-12T21:07:38Z`

Mode: `NON_PAID_RECONCILIATION_ONLY`. This reconciliation called no provider and performed no TTS, ASR, upload, metadata, browser, or publication mutation. Concurrent provider evidence was inspected read-only.

## Scope And Rules

- Active scope is the 32 rows in `sprint1_publication_matrix.json` with `sprint1_audio_target=true`; `great-expectations` and `jane-eyre` remain excluded.
- Canonical hashes are calculated from sorted chapter JSON content using the exact recipe recorded in the JSON artifact. Counts are Unicode code points before provider-specific text preparation.
- Import-manifest coverage and controlled reader-manifest coverage are separate. All 32 have a matching canonical reader manifest; only five occur in tracked book import manifests.
- Missing `sanitized_text_reports/*.json` links in the matrix were not accepted as evidence. Sanitation was rechecked from selected chapter content plus `source_evidence.json`.
- `ready_for_audition` excludes titles whose next safe action is reuse validation, ASR calibration, full-title generation after a passed audition, containment, human narration, or no action because audio is already approved.

## Summary

- Active titles: `32`
- Ready for a new provider audition: `5` (`radharani`, `jekyll-and-hyde`, `picture-of-dorian-gray`, `pride-and-prejudice`, `the-secret-garden`)
- Blocked or audition not next stage: `27`
- Tracked import-manifest inclusion: `5/32`; canonical controlled reader manifests: `32/32`
- Rights PASS: `31/32`; cover PASS: `25/32`; sanitation PASS: `32/32`
- Root/backend manuscript hash match: `27/32`; backend selected as canonical: `4/32`
- Cover-blocked slugs: `pather-panchali`, `devdas`, `book-edfcf810c5`, `white-fang`, `the-last-leaf`, `the-masque-of-the-red-death`, `the-monkeys-paw`
- Non-matching or backend-only source cases: `bn-066`, `nishkriti`, `dracula`, `frankenstein`, `alices-adventures-in-wonderland`

## Per-Title Matrix

| Slug | Canonical source | SHA-256 | Chars | Manifest inclusion | Rights | Cover | Sanitation | Ready for audition | Exact blocker |
| --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| `book-2b9853ec52` | `data/controlled_publications/book-2b9853ec52/chapters` (1 files) | `788851c603ab1700f9e33bdfdc6a3e3c04f2ebb79890b88bc8c88f138270095d` | 3,284 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_NOT_REQUIRED: APPROVED_PUBLIC_AUDIO_ALREADY_EXISTS` |
| `bn-066` | `backend/data/controlled_publications/bn-066/chapters` (46 files) | `7501f43779da66a2fb871a905c3244c9d9c4503605e937c3d600b9d293842475` | 203,763 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `PIPELINE_SOURCE_OVERRIDE_REQUIRED: CANONICAL_SOURCE_IS_UNDER_BACKEND_DATA_BUT_CURRENT_RELEASE_FACTORY_MANUSCRIPT_LOADER_READS_ROOT_DATA; AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_AUDIO_ASR_CALIBRATION_REQUIRED` |
| `radharani` | `data/controlled_publications/radharani/chapters` (8 files) | `53b00ba494263f54f97c8c94bb64ed6e07e1819fc8060aafee90f57ea5a9541d` | 38,022 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | Yes | `NONE` |
| `nishkriti` | `backend/data/controlled_publications/nishkriti/chapters` (9 files) | `a36660028d968e39750206b4c186797ca9c53b2fe1ce18466556a307909ea384` | 83,686 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `PIPELINE_SOURCE_OVERRIDE_REQUIRED: CANONICAL_SOURCE_IS_UNDER_BACKEND_DATA_BUT_CURRENT_RELEASE_FACTORY_MANUSCRIPT_LOADER_READS_ROOT_DATA; PUBLIC_UNAPPROVED_STORAGE_OBJECT_REVOCATION_REQUIRED` |
| `muchiram-gurer-jibanchorit` | `data/controlled_publications/muchiram-gurer-jibanchorit/chapters` (2 files) | `b0c5e8602ff0e54593e677700bffe4b84cd7053bd2019c1ca71957fa43cd3216` | 5,971 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: REPRESENTATIVE_AUDITION_ALREADY_PASSED_2026-07-12T21:01:58Z_GOOGLE_BN-IN-CHIRP3-HD-AOEDE_SCORE_9.3_CONFIDENCE_0.95_NO_FATAL_FLAGS; NEXT_STAGE_IS_ONE_GUARDED_FULL_PILOT` |
| `book-d19e96859f` | `data/controlled_publications/book-d19e96859f/chapters` (1 files) | `ad4532ec513d4241d852a83595c027390b6c8dd2a9196a6d58fdfb84cbed25bf` | 6,516 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: REPRESENTATIVE_AUDITION_ALREADY_PASSED_FOR_PREPARED_SHA256_79b0deba6032c36ab919e4ef4786fc62aa55c9c53c328dfbcf49f03a0f7d05fe; NEXT_STAGE_IS_GUARDED_FULL_TITLE_TTS` |
| `book-f5d593e1f4` | `data/controlled_publications/book-f5d593e1f4/chapters` (1 files) | `c522d934b4b141b0cd0e199749b6f75d8fe839c6894ce21aec47c61546f3760e` | 9,494 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_PLAN_CONFLICT: PUBLICATION_MATRIX_REQUIRES_FAILED_GROUP_7_REPAIR BUT_PARALLEL_BOARD_SAYS_FRESH_SOURCE_BOUND_REPRESENTATIVE_AUDITION` |
| `pather-panchali` | `data/controlled_publications/pather-panchali/chapters` (12 files) | `96a22ce7d7dbd2fff2cc18d358afb970e62275736e58815d11243e2cc3fc3681` | 125,479 | import + reader | BLOCKED_OWNER_DOCUMENT_REQUIRED | BLOCKED_TITLE_SPECIFIC_PREFLIGHT | PASS | No | `OWNER_DOCUMENT_REQUIRED_FOR_AUDIO_RIGHTS_SOURCE_COVER` |
| `devdas` | `data/controlled_publications/devdas/chapters` (16 files) | `beae74b36ef993e95682141c401f9376c185da87204243e8b8680024e8205e6c` | 152,769 | import + reader | PASS | BLOCKED_TITLE_SPECIFIC_PREFLIGHT | PASS | No | `TITLE_SPECIFIC_COVER_PREFLIGHT_REQUIRED` |
| `book-edfcf810c5` | `data/controlled_publications/book-edfcf810c5/chapters` (1 files) | `aefaba33524c79363c765ae74d6e315b6b53a524ebff2e114037aec8bf7ab383` | 22,104 | reader only | PASS | BLOCKED_TITLE_SPECIFIC_PREFLIGHT | PASS | No | `TITLE_SPECIFIC_COVER_PREFLIGHT_REQUIRED; AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `a-ghost-story` | `data/controlled_publications/a-ghost-story/chapters` (1 files) | `968351200b062cf31d6c33abaa40d30a4b5cc117163c160de175f8fe8c9bb093` | 13,047 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_NOT_REQUIRED: APPROVED_PUBLIC_AUDIO_ALREADY_EXISTS` |
| `dracula` | `backend/data/controlled_publications/dracula/chapters` (27 files) | `3e7f5f40c82df29bca74745eab7afab200ee57318b813b118dc9b5b9c664aeb9` | 848,683 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `PIPELINE_SOURCE_OVERRIDE_REQUIRED: CANONICAL_SOURCE_IS_UNDER_BACKEND_DATA_BUT_CURRENT_RELEASE_FACTORY_MANUSCRIPT_LOADER_READS_ROOT_DATA; ROOT_BACKEND_MANUSCRIPT_DIVERGENCE: ROOT_SHA256_a9b4c970185b51e95c6904301b5d4273bf7058fd5aab37da9e5a88281c20273e_CHARS_881120_CONTAINS_RAW_HTML; BACKEND_CANONICAL_SHA256_3e7f5f40c82df29bca74745eab7afab200ee57318b813b118dc9b5b9c664aeb9_CHARS_848683_IS_CLEAN` |
| `frankenstein` | `data/controlled_publications/frankenstein/chapters` (28 files) | `e8f149a1b23a3685cadc719366afc66a4be48c869c7bce804ec9ed00d44f8028` | 418,383 | import + reader | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `ROOT_BACKEND_CANONICAL_SOURCE_CONFLICT: ROOT_SHA256_e8f149a1b23a3685cadc719366afc66a4be48c869c7bce804ec9ed00d44f8028_CHARS_418383; BACKEND_SHA256_abc8f3619bc79d5ab6e73a865bb76635028789d72e14c2387b40f6db59dfc35f_CHARS_423804` |
| `jekyll-and-hyde` | `data/controlled_publications/jekyll-and-hyde/chapters` (11 files) | `0e8cc7fb6c18abd38def7c85cc2a8f4907bde5f11db48e36ba7fd9afff7fdc8e` | 138,182 | import + reader | PASS | PASS_GRAPHICAL_RUNTIME_FALLBACK | PASS | Yes | `NONE` |
| `picture-of-dorian-gray` | `data/controlled_publications/picture-of-dorian-gray/chapters` (21 files) | `fb64fa570b93f43f1c13973df889bd30e024fc27124a53a5a4427fd6de179d00` | 428,577 | import + reader | PASS | PASS_GRAPHICAL_RUNTIME_FALLBACK | PASS | Yes | `NONE` |
| `the-time-machine` | `data/controlled_publications/the-time-machine/chapters` (16 files) | `cb7c2b70194eeb8f0376f5ece4d6a5fdce547fbfca23d4c842337f2c024fe1e8` | 181,242 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHAPTER_COUNT_PREFLIGHT_REQUIRED` |
| `the-call-of-the-wild` | `data/controlled_publications/the-call-of-the-wild/chapters` (7 files) | `36bf2714954e352c1c6a5fbbe65af1e77ab622e709e42907cd9451eda0982916` | 177,305 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `white-fang` | `data/controlled_publications/white-fang/chapters` (25 files) | `1196a80b33f6fc76d5608f5e2420317801d8e7af838a698d1a8ec37138ec25dc` | 401,043 | reader only | PASS | BLOCKED_NO_APPROVED_FRONT_BACK_OR_EXPLICIT_FALLBACK | PASS | No | `APPROVED_FRONT_AND_BACK_COVER_EVIDENCE_REQUIRED` |
| `pride-and-prejudice` | `data/controlled_publications/pride-and-prejudice/chapters` (61 files) | `5691170107bb90c5911ca24588394c37973d4d277a6ede4e2d86d8be23ff479c` | 692,224 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | Yes | `NONE` |
| `the-secret-garden` | `data/controlled_publications/the-secret-garden/chapters` (27 files) | `4aac34ad4bda3586f1a062b24b3ca271a96edef7e4938d13042d0595f692f3a3` | 431,542 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | Yes | `NONE` |
| `alices-adventures-in-wonderland` | `backend/data/controlled_publications/alices-adventures-in-wonderland/chapters` (12 files) | `c8cd98430bcaa621dd206b8d3c880b34ca3daf4776e4b89c8a10d8c5f84cb2d3` | 144,843 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `PIPELINE_SOURCE_OVERRIDE_REQUIRED: CANONICAL_SOURCE_IS_UNDER_BACKEND_DATA_BUT_CURRENT_RELEASE_FACTORY_MANUSCRIPT_LOADER_READS_ROOT_DATA; PUBLIC_UNAPPROVED_STORAGE_OBJECT_REVOCATION_REQUIRED` |
| `the-gift-of-the-magi` | `data/controlled_publications/the-gift-of-the-magi/chapters` (1 files) | `67c1074aea0203a04f3116f42fa85c01cdec12d9646a25f0b119c3834d921ea7` | 11,299 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `the-tell-tale-heart` | `data/controlled_publications/the-tell-tale-heart/chapters` (1 files) | `8e725a8220dca763fdd5286315016d1ae3071cb5f068e830e1e2b8ed16037bdb` | 11,487 | reader only | PASS | PASS_GRAPHICAL_RUNTIME_FALLBACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `the-open-window` | `data/controlled_publications/the-open-window/chapters` (1 files) | `3e9f1a07afa3dcda9b56a0b8eec6f5f36f41502dc6ab75d5efefc85891fde3cb` | 6,919 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUTOMATED_AUDITION_NOT_APPROVED: LATEST STUDIO_B_TWILIGHT SAMPLE SCORED 7.2 WITH ROBOTIC_AND_MECHANICAL_FATAL_FLAGS; HUMAN_NARRATION_OR_EXPLICIT_ALTERNATE_PROVIDER_APPROVAL_REQUIRED` |
| `sredni-vashtar` | `data/controlled_publications/sredni-vashtar/chapters` (1 files) | `44e3bebedecc69c907b8739b5c6996932505df2cb140c05a4d55b9ca9d2bfd21` | 10,374 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `dsires-baby` | `data/controlled_publications/dsires-baby/chapters` (1 files) | `587455ed554ef64d19f0ea7dcd31940d242aa759f5132b6514b130efa4a64a89` | 11,974 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `the-cop-and-the-anthem` | `data/controlled_publications/the-cop-and-the-anthem/chapters` (1 files) | `c0b36ffec25e389cd57133b025e9055ecf16e75c5a541380251f7c99d843ef9f` | 13,233 | reader only | PASS | PASS_DIRECT_FRONT_BACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `the-last-leaf` | `data/controlled_publications/the-last-leaf/chapters` (1 files) | `f1281c55388f41893d10ecac60944c704ae0d0571cbdb7d09d67cd124ccd432d` | 12,936 | reader only | PASS | BLOCKED_NO_APPROVED_FRONT_BACK_OR_EXPLICIT_FALLBACK | PASS | No | `APPROVED_FRONT_AND_BACK_COVER_EVIDENCE_REQUIRED; AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `the-masque-of-the-red-death` | `data/controlled_publications/the-masque-of-the-red-death/chapters` (1 files) | `4044f55c14bad61d0ba2af3ce8fa5c5d6e98878498f8976034a44f156d74fff8` | 13,886 | reader only | PASS | BLOCKED_NO_APPROVED_FRONT_BACK_OR_EXPLICIT_FALLBACK | PASS | No | `APPROVED_FRONT_AND_BACK_COVER_EVIDENCE_REQUIRED; AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `the-yellow-wallpaper` | `data/controlled_publications/the-yellow-wallpaper/chapters` (1 files) | `9fd5bcecd51b2033192b62a87b4278c630e12eaebf1cd7c9d5e6243e1c478a3e` | 31,800 | reader only | PASS | PASS_GRAPHICAL_RUNTIME_FALLBACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `the-monkeys-paw` | `data/controlled_publications/the-monkeys-paw/chapters` (3 files) | `dd2d51938751b06ab49f84e7734f9b195056cb5b3bb658778d479624035b8fbd` | 22,076 | reader only | PASS | BLOCKED_NO_APPROVED_FRONT_BACK_OR_EXPLICIT_FALLBACK | PASS | No | `APPROVED_FRONT_AND_BACK_COVER_EVIDENCE_REQUIRED; AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |
| `the-necklace` | `data/controlled_publications/the-necklace/chapters` (1 files) | `1fcc13e8afa53c8a818623b3383a110f014063634ab8b1a16eb615e54f6ad0e7` | 16,095 | reader only | PASS | PASS_GRAPHICAL_RUNTIME_FALLBACK | PASS | No | `AUDITION_NOT_NEXT_STAGE: NON_PAID_PRIVATE_ASSET_CHECKSUM_SOURCE_QA_PREFLIGHT_REQUIRED` |

## Evidence Boundaries

- Current Sprint1 truth: `internal/audiobook_lab/sprint1_publication/sprint1_publication_matrix.json`, `sprint1_parallel_execution_board.json`, and title-run evidence.
- Canonical reader/source/rights packets: `data/controlled_publications/<slug>/` and `backend/data/controlled_publications/<slug>/`.
- Import manifests: `book_import_manifest.batch-1.json` and `book_import_manifests/business_entrepreneurship_public_domain_20260609.json`; ignored default `book_import_manifest.json` is absent in this worktree.
- Cover evidence: controlled `public_book.json`, `graphical_cover_generation_report.json`, active cover policy, and the latest Sprint1 board.
- Concurrent evidence observed read-only: `bengali_representative_audition_report.json` and `muchiram_google_chirp_audition_lock_report.json` supersede the older matrix next-stage state for `muchiram-gurer-jibanchorit`.
- Audition readiness is not release approval. Every listening, ASR, measured-sync, upload/checksum, metadata, endpoint, browser, and empty-blocker gate remains required after any future approved paid work.

## Next Exact Command

No paid command is authorized by this reconciliation. Validate the artifacts and diff scope only:

```bash
python3 -m json.tool internal/audiobook_lab/sprint1_publication/sprint1_pipeline_input_reconciliation.json >/dev/null && git diff --check -- internal/audiobook_lab/sprint1_publication/sprint1_pipeline_input_reconciliation.json internal/audiobook_lab/sprint1_publication/sprint1_pipeline_input_reconciliation.md
```
