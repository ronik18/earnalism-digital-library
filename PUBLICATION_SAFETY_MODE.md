# Publication Safety Mode

Publication safety mode keeps newly imported books in draft/editorial review only. Dracula remains the only approved live reading release in the current allowlist.

## Required Draft Fields

Every newly imported book must be created with:

```json
{
  "readerStatus": "ready_for_editorial_review",
  "publicationStatus": "draft",
  "isPublic": false,
  "isLive": false,
  "showInPublicLibrary": false,
  "showInHomepage": false,
  "allowPublicReading": false,
  "allowCheckout": false,
  "allowPayment": false
}
```

The importer also sends `is_published: false` for backend compatibility.

## Public Exposure Rules

Newly imported books must not appear in:

- public navigation
- public search
- public library shelves
- homepage sections
- pricing flows
- sitemap output
- public metadata feeds
- live reader routes

If preview mode exists, books may be reviewed through internal developer or admin/editorial preview only. If preview mode is unavailable, imports should produce content files and metadata only, with no public route exposure.

## Current Allowlist

The approved release allowlist contains only:

- `dracula`

The 10 newly imported books are not allowlisted and must remain draft/editorial-review items.

## Manual Approval Gate

A book can move from draft to live only after a human editor/product owner confirms:

1. source URL reviewed
2. public-domain/legal note reviewed
3. raw source archived
4. cleaned chapters inspected
5. no Project Gutenberg or Wikisource boilerplate remains in reader-facing content
6. no unapproved cover art, images, introductions, annotations, translations, or publisher material included
7. chapter boundaries are correct
8. typography and formatting are reader-ready
9. Bengali Unicode displays correctly where applicable
10. the book is intentionally selected for public release

No automation may change `publicationStatus` from `draft` to `live`.

## Validation

Run:

```bash
python3 scripts/validate_publication_safety_mode.py path/to/import_manifest.json
```

The validation fails when a non-allowlisted book has `publicationStatus: "live"` or any public/live/checkout/payment flag set to true.

For generated import metadata, enforce the full exact-field contract:

```bash
python3 scripts/validate_publication_safety_mode.py --require-draft-fields output/book_import/metadata/example.json
```
