# B2 Live Audio Cleanup Validation

Generated: `2026-07-20T05:35:01Z`

## Outcome

- Live audiobooks retained: **4**
- Exact live B2 assets retained: **20**
- Permanently deleted non-live public-origin versions: **42**
- Storage reclaimed: **7,396,374,442 bytes** (about **6.89 GiB**)
- Deletion errors: **0**
- Post-delete candidates: **0**
- Pre-delete plan SHA-256: `4cdadb65e5e80092d3b5982b09ed5a7149a6ba4b3b44d464526c17d63799d27f`

## Live bindings

| Slug | B2 store | Assets | Production MP3 |
| --- | --- | ---: | --- |
| `book-2b9853ec52` | primary / `earnalism-audiobooks` | 5 | HTTP 206 |
| `a-ghost-story` | primary / `earnalism-audiobooks` | 5 | HTTP 206 |
| `sredni-vashtar` | primary / `earnalism-audiobooks` | 5 | HTTP 206 |
| `the-open-window` | private / `earnalism-private-qa-audio` | 5 | HTTP 206 through gated proxy |

The primary live MP3 origins returned HTTP 200 with `Accept-Ranges: bytes`. The Open Window origin returned HTTP 401, while its release-gated Earnalism route returned HTTP 206.

## Post-delete proof

- All four production MP3 routes returned a 1,024-byte HTTP 206 range response.
- All sixteen production sidecar routes returned HTTP 200.
- Deleted Great Expectations polished, old A Ghost Story, and legacy Dracula origin URLs returned HTTP 404.
- `bn-066`, `radharani`, `nishkriti`, `book-d19e96859f`, `book-f5d593e1f4`, `muchiram-gurer-jibanchorit`, `dsires-baby`, and `pather-panchali` audiobook routes returned HTTP 404.
- Fresh B2 inventory reported 20 live assets, zero cleanup candidates, and zero blockers.

## Retention boundary

The primary public-origin bucket now contains only fifteen exact live assets. The private-audio bucket retains The Open Window's five live objects plus referenced private QA/campaign evidence. Those private objects are not exposed by catalog truth and were intentionally preserved because they remain active evidence for the remaining audiobook work.
