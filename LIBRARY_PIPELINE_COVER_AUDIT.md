# Library Pipeline Cover Audit

Status: READY_FOR_REVIEW_PENDING_VALIDATION

## Summary

The library now distinguishes between real local cover evidence and designed placeholders. It does not pretend all pipeline titles have production-ready covers.

## Cover Inventory

| Title | Slug | Public status | Cover source | Library treatment | Public CTA |
| --- | --- | --- | --- | --- | --- |
| Dracula | `dracula` | Live reading-only release | `frontend/public/assets/books/dracula/dracula-front-cover.webp` and back cover | Premium live reading object | Read Chapter 1 Free, Start Dracula, Get 7-Day Reading Pass |
| The Hungry Stones / Kshudhita Pashan | `kshudhita-pashan` | Pipeline-only | `frontend/public/assets/books/kshudhita-pashan/kshudhita-pashan-front.webp` and back cover | Real front/back covers shown as pipeline evidence | Notify Me, Reading Circle only |
| Frankenstein | `frankenstein` | Pipeline-only | No safe local production cover found in current controlled pipeline | Designed Earnalism shelf placeholder | Notify Me only |
| Sherlock Holmes | `sherlock-holmes` | Pipeline-only | No safe local production cover found in current controlled pipeline | Designed Earnalism shelf placeholder | Notify Me only |
| Sultana's Dream | `sultanas-dream` | Pipeline-only | No safe local production cover found in current controlled pipeline | Designed Earnalism shelf placeholder | Notify Me only |
| Calculus Made Easy | `calculus-made-easy` | Pipeline-only | No safe local production cover found in current controlled pipeline | Designed Earnalism shelf placeholder | Notify Me only |

## Findings

- Pipeline cards previously risked feeling unfinished when no cover existed.
- Kshudhita Pashan had local owner-provided cover assets available and now uses them in the library pipeline spotlight.
- Other pipeline titles remain visibly in preparation instead of showing misleading live-style cover art.
- No fake links, fake covers, or public reading CTAs were introduced.

## Public Claims

- Kshudhita Pashan is not public-readable.
- Pipeline books do not show Start Reading, payment, or audio CTAs.
- Public audiobook release remains blocked.
- No broad catalog availability claim is introduced.
