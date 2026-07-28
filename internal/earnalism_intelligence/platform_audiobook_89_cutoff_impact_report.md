# Platform audiobook 8.9 cutoff impact

Status: `ACTIVE — ZERO NEW FULL-TITLE RELEASE-READY`

All subjective listening dimensions now use the same release floor: `8.9`,
with confidence `>= 0.90` and no fatal flags. The objective fidelity gate is
not a listening score and remains unchanged: ASR/manuscript `>= 9.7`, coverage
`>= 0.98`, exact first/last/order, measured sync, rights, covers, checksum,
metadata, endpoint, browser playback, and an empty blocker list are mandatory.

The production baseline remains 32 readers and four audiobooks:
`book-2b9853ec52`, `a-ghost-story`, `sredni-vashtar`, and `the-open-window`.

## Immediate publication audit

| Candidate | Best listening evidence | Blocking release evidence |
| --- | ---: | --- |
| `the-gift-of-the-magi` | representative minimum `9.5` | full-title order and measured-sync fail; full-title listening and delivery incomplete |
| `the-tell-tale-heart` | derivative full-title `9.0` | ordered-content integrity and exact delivery package incomplete |
| `the-time-machine` | representative `9.0` | emotional expression `8.0`; no full-title package |
| `radharani` | representative `9.4` | full-title raw ASR/manuscript `1.0962`; exact content, sync, and delivery incomplete |
| `the-secret-garden` | representative minimum `9.0` | chapter checkpoint exact-order fail; measured sync `9.6262`; no full title |
| `dsires-baby` | one representative result `9.2` | fatal robotic, mechanical, and choppy flags; no full-title package |

No non-live title became release-ready from this policy change, so no hidden
audio was exposed and no publication state was mutated. The fastest valid next
path remains completion or replacement of an exact source-bound full-title
package; lowering a listening score cannot repair missing or mismatched words.
