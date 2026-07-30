# Jekyll and Hyde private editorial cover candidate

## Decision

This is a private, pending-review front/back candidate for **The Strange Case of Dr. Jekyll and Mr. Hyde** by **Robert Louis Stevenson**. It is not canonical, has not been uploaded, and cannot change reader or audiobook release truth.

## Source and rights

- Front source: Charles Raymond Macauley, Chapter 2 Drawing 1, Scott-Thaw 1904 edition.
- Back source: Charles Raymond Macauley, Chapter 10 Drawing 2, Scott-Thaw 1904 edition.
- Rights evidence: Public Domain Mark 1.0 source records, exact URLs and hashes in `source_rights_evidence.json`.
- Front source SHA-256: `1848b89196669aeb7c0ea097d4821dc20cab09cca968d9bd854f85e68413f374`.
- Back source SHA-256: `e48ba094dde8140e7894d6f9963b9674f395a6de98dcaf3766d1eb452e4628be`.
- The Commons longer-term-jurisdiction caveat is retained. This packet does not claim unrestricted worldwide rights.
- Composition: deterministic Pillow crop, duotone treatment, borders, panels, and controlled-catalog text overlay.
- AI-generated imagery: no.
- Placeholder art: no.

## Exact catalog copy

- Title: `The Strange Case of Dr. Jekyll and Mr. Hyde`
- Author: `Robert Louis Stevenson`
- Back copy: `A clean Earnalism reader edition of The Strange Case of Dr. Jekyll and Mr. Hyde, prepared from a legally cleared public-domain classic source with source boilerplate removed.`

No distinct approved editorial back-copy field exists, so no new marketing copy was invented.

## Technical checks

- Front master: 1600 × 2400 JPEG, `144ee406937db6f4f206c9d3518de3679aea5268ec933295fda888e7a2838157`, 490667 bytes.
- Back master: 1600 × 2400 JPEG, `a1aa1144de8b0ba0c80442101322ae84c7ebf7fd25de83bfc7064d2c5c31ff4a`, 380546 bytes.
- Thumbnail derivatives: 320 × 480 WebP, each at or below 80 KiB.
- Feature derivatives: 800 × 1200 WebP, each at or below 180 KiB.
- Geometry validation: zero text-box overlaps; every text box remains inside both the safe margin and its content panel.
- Small-card type floors and deterministic foreground/panel contrast checks pass.
- Both controlled-publication mirrors remained byte-for-byte unchanged.

## Pending review

Automated preparation does not approve this cover. Visual inspection and owner/editorial review remain mandatory. Any later private admin upload must remain `ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW`; canonical promotion requires a separate hash-bound decision and territorial-rights confirmation.

## Next exact command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q internal/audiobook_lab/scripts/test_prepare_jekyll_editorial_cover.py
```
