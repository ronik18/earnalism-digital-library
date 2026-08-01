# Sprint 1 Scoped Storage Containment Targets

## Scope

- Active Sprint 1 slugs: **32**
- Deferred exclusions: great-expectations, jane-eyre
- Reviewed Sprint 1 stale/unapproved objects: **135**
- Reachable execution targets: **70**
- Already contained with verified private retention: **35**
- Inaccessible without matching private retention: **30**
- Exact approved package objects protected: **10**
- Non-Sprint reviewed targets deferred by owner: **471**

## Remaining Target Package

- Cloudinary: **70**
- B2: **0**
- MP3: **6**
- Sidecars: **64**
- Known remaining bytes: **206,710,025**
- Remaining objects with unknown size: **48**

The target list contains only currently reachable active-Sprint-1 objects. Every entry must be copied to the confirmed-private QA bucket and verified by byte size and source SHA-256 before its old public delivery can be revoked.

The 30 inaccessible objects without matching private retention are not current storage-bypass risks, but they remain a separate evidence-recovery gap rather than being falsely classified as successfully contained.

## Per-Slug State

| Slug | Reviewed | Reachable target | Retained + inaccessible | Inaccessible, retention missing |
|---|---:|---:|---:|---:|
| a-ghost-story | 3 | 0 | 3 | 0 |
| alices-adventures-in-wonderland | 10 | 8 | 2 | 0 |
| bn-066 | 5 | 0 | 5 | 0 |
| book-2b9853ec52 | 1 | 0 | 1 | 0 |
| book-d19e96859f | 6 | 0 | 1 | 5 |
| book-edfcf810c5 | 6 | 0 | 1 | 5 |
| book-f5d593e1f4 | 6 | 0 | 1 | 5 |
| devdas | 0 | 0 | 0 | 0 |
| dracula | 0 | 0 | 0 | 0 |
| dsires-baby | 6 | 4 | 2 | 0 |
| frankenstein | 0 | 0 | 0 | 0 |
| jekyll-and-hyde | 0 | 0 | 0 | 0 |
| muchiram-gurer-jibanchorit | 6 | 0 | 1 | 5 |
| nishkriti | 10 | 4 | 1 | 5 |
| pather-panchali | 0 | 0 | 0 | 0 |
| picture-of-dorian-gray | 0 | 0 | 0 | 0 |
| pride-and-prejudice | 0 | 0 | 0 | 0 |
| radharani | 6 | 0 | 1 | 5 |
| sredni-vashtar | 6 | 4 | 2 | 0 |
| the-call-of-the-wild | 5 | 4 | 1 | 0 |
| the-cop-and-the-anthem | 6 | 4 | 2 | 0 |
| the-gift-of-the-magi | 6 | 4 | 2 | 0 |
| the-last-leaf | 6 | 4 | 2 | 0 |
| the-masque-of-the-red-death | 6 | 4 | 2 | 0 |
| the-monkeys-paw | 6 | 4 | 2 | 0 |
| the-necklace | 5 | 4 | 1 | 0 |
| the-open-window | 6 | 4 | 2 | 0 |
| the-secret-garden | 0 | 0 | 0 | 0 |
| the-tell-tale-heart | 6 | 6 | 0 | 0 |
| the-time-machine | 5 | 5 | 0 | 0 |
| the-yellow-wallpaper | 6 | 6 | 0 | 0 |
| white-fang | 1 | 1 | 0 | 0 |

## Hard Exclusions

The exact approved public packages for book-2b9853ec52 and a-ghost-story are protected. Stale versions remain eligible only when listed under targets. No non-Sprint object and no deferred long classic is present in the executable target list.
