# Dracula Production API Availability Failure

Generated: 2026-06-20

## Captured Production Facts

- `GET https://api.theearnalism.com/api/healthz` returned `200 OK`.
- `GET https://api.theearnalism.com/api/books` returned `[]`.
- `GET https://api.theearnalism.com/api/books/dracula` returned `404 Book not found`.
- `GET https://api.theearnalism.com/api/reader/book/dracula/manifest` returned `404 Book not found`.
- `GET https://api.theearnalism.com/api/reader/book/dracula/audiobook` returned `404 Audiobook asset not found`.

## Failure Meaning

- The backend service is alive.
- The frontend production deployment is live.
- The unsafe broad catalog leak appears fixed.
- Dracula is not being exposed as the controlled live item.
- The reader manifest failure is caused by the same missing or rejected Dracula lookup.
- Ads and real-user UX video approval remain blocked until Dracula API and reader manifest pass production canaries.

## Decision

- `KEEP_DRACULA_LIVE` only after backend catalog truth and post-production canaries pass.
- `HOLD_ADS`.
- `HOLD_REAL_USER_UX_VIDEO_AUDIT`.
- Do not rollback unless production routes become broadly unsafe or unavailable.
