# Lane 2 first-tranche clearance packet (2026-09-26)

Status: **AMBER_AUTOFIXABLE / not exposed**.

This packet records the first three deterministic candidates selected from the
existing inventory. It does not publish, add routes, add sitemap entries,
enable checkout, or change the commercial baseline.

## Candidates

| slug | language | rights/source | reader package | remaining blocker |
| --- | --- | --- | --- | --- |
| `alices-adventures-in-wonderland` | English | Project Gutenberg source URL, public-domain basis, source/content/provenance hashes present | approval, reader manifest, chapters, checksum manifest present | cover provenance is not separately recorded; no publication-manifest binding |
| `pride-and-prejudice` | English | Project Gutenberg source URL, public-domain basis, source/content/provenance hashes present | approval, reader manifest, chapters, checksum manifest present | cover provenance is not separately recorded; no publication-manifest binding |
| `frankenstein` | English | historical import evidence requires reconciliation | controlled package present | historical-import provenance and cover/manifest binding require reconciliation |

## Safety checks

- All three remain draft/non-public in their `content/books/*/book.json` records.
- Existing controlled-package approvals explicitly retain `allowCheckout=false`,
  `allowPayment=false`, and audio disabled.
- No `isPublic`, `isLive`, library exposure, payment, route, or production
  configuration was changed.
- No Yugalanguriya files or Lane 1/Lane 3 files were touched.

## Terminal disposition

No candidate reached GREEN. The existing package evidence is sufficient to
advance these titles from inventory-only review to an actionable AMBER batch,
but not to authorize release. The next deterministic work is to add factual
cover-provenance records and an explicit publication-manifest binding from the
exact package files; Frankenstein additionally needs reconciliation of its
historical-import provenance. Until those facts exist, `BATCH_1_GREEN_READY`
remains empty and this tranche remains unexposed.
