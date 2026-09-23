# Catalogue resource cleanup inventory — 2026-09-23

Scope: current three-title India pilot. Yugalanguriya remains `HOLD` and is
not being re-cleared. No released literary text, cover, rights decision,
publication manifest, or launch configuration was modified.

## Resource decisions

| Resource group | Classification | Action | Evidence / reason |
| --- | --- | --- | --- |
| `content/books/yugalanguriya/**` (13 files) | Required provenance evidence | Archived byte-for-byte at `internal/archives/held_titles/yugalanguriya/source-book/` | Source book, ten chapter files, raw source and rights note preserved. No text or reading was edited. |
| Root and backend Yugalanguriya controlled packages (17 files each) | Unsafe unreleased runtime resource + duplicate mirror | One copy archived at `internal/archives/held_titles/yugalanguriya/controlled-publication-package/`; both former runtime paths removed | SHA-256 comparison of all 17 files between the archived package and the prior root package: 17 matched, 0 mismatched. No publication manifest was found. The archived `public_book.json` contains stale LIVE/audio flags and remote audio URLs; it is explicitly non-runtime. The second approval file is retained, not treated as another approval. |
| `data/controlled_publications/a-ghost-story/chapters 2/chapter-001.json` and its backend mirror | Historical alternate + duplicate mirror | One copy archived at `internal/archives/historical_publication_resources/a-ghost-story/alternate-chapters-2/chapter-001.json`; duplicate removed | Neither path is referenced by the active public book or reader manifest. The two prior copies had identical SHA-256 `b15048c461ac21010ca571517cea29ef21813a64c4ef410c91aa80339166ecee`. The alternate differs from the canonical chapter, so it was preserved rather than discarded. |
| `backend/data/graphical_cover_generation_report.json` | Required internal cover-audit evidence | Retained unchanged | Yugalanguriya occurs only in `reused_covers`; runtime reads this report's fallback/visual-exclusion arrays, not this list, and it does not create a catalogue/SEO/Reader record. |
| `backend/data/rights_decision_registry.json` Yugalanguriya entry | Required rights evidence | Retained unchanged | Registry continues to record `HOLD`. |
| Yugalanguriya's prior audio sidecars/sync research under `internal/audiobook_lab/` | Historical archive | Retained unchanged | Internal generation/provenance records, not public-reader resources. Public audio remains disabled by launch configuration. |
| Frozen `backend/tests/fixtures/controlled-package-inventory.v1.json` snapshot | Required historical test fixture | Retained; current inventory test excludes only archived Yugalanguriya and asserts its historical snapshot remains present | Fixture labels itself `VERSIONED_ENGINEERING_SNAPSHOT_NOT_RELEASE_AUTHORITY`; it is not a live catalog source. |
| Pilot resource sets for A Ghost Story, The Tell-Tale Heart and Radharani | Active production resources | Retained unchanged | Focused parity/content-hash test verifies required publication files, ordered chapter manifests, per-chapter content SHA-256, and accepted rights status. |

## Public-surface checks

- Both controlled-launch files remain byte-identical, list exactly the three
  released pilot titles, use `PILOT_FULL_FREE`, and keep paid commerce, credit
  debit and audio disabled.
- Yugalanguriya remains absent from both active publication roots, both
  release/audio allowlists, and the generated public sitemap. Existing
  fail-closed Reader/API and SEO tests remain in force.
- The fixed-scope admin publication inspector now reads identity metadata
  from the archive and marks it `ARCHIVED`; it does not restore runtime
  publication eligibility.
- Cleanup intentionally does not delete ambiguous, dynamically loaded,
  historical audiobook, audit, rights, source, or unknown assets.

## Validation added

`backend/tests/test_controlled_launch_parity.py` verifies the three live
publication resource/hash sets and the archived Yugalanguriya hold. The
catalog-wide chapter-index regression continues to use its frozen snapshot
while excluding only the now-archived Yugalanguriya package from the current
runtime set.
