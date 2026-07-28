# Sprint 1 Missing / Invalid Cover Inventory

- Snapshot: `origin/main` at `9ccd1c345ed92a252f597d93083ce99c89cc589b`
- Sprint 1 source: `backend/data/home_hero_curation.json`
- Canonical cover records: `backend/data/controlled_publications/{slug}/public_book.json`
- Parity copy checked: `data/controlled_publications/{slug}/public_book.json`
- Audit date: 2026-07-28

## Summary

- Sprint 1 titles checked: **32**
- Valid canonical front/back URL pairs resolving as images: **20**
- Missing both front and back cover URLs: **11**
- Missing front only: **0**
- Missing back only: **0**
- Populated cover pairs with broken/unresolvable URLs: **0**
- Populated but title-mismatched cover pairs: **1**
- Total titles needing admin cover remediation: **12**

All 42 populated cover-side URLs returned HTTP `206` with `image/png` or
`image/webp` in a ranged GET. Missing means absent canonical source metadata,
not an HTTP failure.

## Titles needing cover remediation

| Slug | Title | Author | Language | Front status | Back status |
| --- | --- | --- | --- | --- | --- |
| `pather-panchali` | পথের পাঁচালী / Pather Panchali | Bibhutibhushan Bandyopadhyay | `bn` | Missing canonical URL | Missing canonical URL |
| `devdas` | দেবদাস / Devdas | Sarat Chandra Chattopadhyay | `bn` | Missing canonical URL | Missing canonical URL |
| `jekyll-and-hyde` | The Strange Case of Dr. Jekyll and Mr. Hyde | Robert Louis Stevenson | `en` | Missing canonical URL | Missing canonical URL |
| `picture-of-dorian-gray` | The Picture of Dorian Gray | Oscar Wilde | `en` | Missing canonical URL | Missing canonical URL |
| `white-fang` | White Fang | Jack London | `en` | Missing canonical URL | Missing canonical URL |
| `the-tell-tale-heart` | The Tell-Tale Heart | Edgar Allan Poe | `en` | Missing canonical URL | Missing canonical URL |
| `the-last-leaf` | The Last Leaf | O. Henry | `en` | Missing canonical URL | Missing canonical URL |
| `the-masque-of-the-red-death` | The Masque of the Red Death | Edgar Allan Poe | `en` | Missing canonical URL | Missing canonical URL |
| `the-yellow-wallpaper` | The Yellow Wallpaper | Charlotte Perkins Gilman | `en` | Missing canonical URL | Missing canonical URL |
| `the-monkeys-paw` | The Monkey's Paw | W.W. Jacobs | `en` | Missing canonical URL | Missing canonical URL |
| `the-necklace` | The Necklace | Guy de Maupassant | `en` | Missing canonical URL | Missing canonical URL |
| `a-ghost-story` | A Ghost Story | Mark Twain | `en` | URL resolves but displays “Bharat at the Crossroads” by Ronik Basak | Same unrelated-title mismatch |

## Evidence and governance

- Each missing pair is recorded in `backend/data/controlled_publications/{slug}/public_book.json` as `DESIGNED_PLACEHOLDER_NO_SAFE_LOCAL_COVER`.
- `a-ghost-story` is owner-excluded in `backend/data/home_hero_curation.json` because its populated canonical cover is title-mismatched.
- The backend and root controlled-publication copies are byte-identical for all 12 remediation titles.
- Runtime graphical fallbacks do not count as a canonical front/back pair.
- Admin uploads must not alter reader availability, audiobook release gates, or audio metadata.
- An uploaded admin candidate remains pending canonical review until the controlled-publication record is intentionally updated and audited.
