# The Tell-Tale Heart canonical cover truth

Status: `CANONICAL_FRONT_BACK_COMPLETE`

The exact 1600 × 2400 editorial pair for **The Tell-Tale Heart** by
**Edgar Allan Poe** has passed full-resolution and 320 px visual review,
private content-addressed upload, remote full-download checksum verification,
and separate canonical promotion.

- Front SHA-256: `474742edf3427ac414565c05b170cb83e855b223951be3ed22cc597ddf6f673d`
- Back SHA-256: `540a24ebdfef56fefe99f23aba4166c3ada20dd421132480eaf3546b07b8934d`
- Source artwork: Odilon Redon, *The Tell-Tale Heart* (1883)
- Rights basis: verified public-domain artwork and faithful reproduction,
  Public Domain Mark 1.0
- Controlled publication mirrors: exact parity
- Reader state: unchanged and live
- Audiobook state: unchanged and hidden

The dated `sprint1_missing_cover_inventory_20260728` remains an immutable
historical snapshot. This reconciliation is the current cover-truth evidence
and removes the title from runtime graphical fallback use.

Next exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q backend/tests/test_admin_book_cover_upload.py backend/tests/test_admin_book_cover_promotion.py
```
