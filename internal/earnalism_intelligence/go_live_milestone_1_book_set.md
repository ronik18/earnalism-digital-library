# Go-Live Milestone 1 Book Set Freeze

Generated: `2026-07-11T14:55:20+05:30`

Decision: freeze a 34-title target set without changing source, release gates, routing, publication, or audio exposure.

## Evidence Boundary

- A live API refresh was unavailable in this execution environment. DNS resolution failed and browser access to the API origin was unavailable.
- Current public truth therefore comes from the same-day production closeout packet evaluated at main commit `12fc406001bc82be0fd377bde864b64a1694d479`.
- Reader-route classification for titles outside that packet uses the clean backend runtime allowlist in `/tmp/earnalism-bn066-hide-hotfix` at `99a85d933047e84bec0bfac027dfe5502b4d7c99`.
- Display metadata and catalog existence use `earnalism_book_inventory_for_launch.json` plus controlled-publication artifacts.
- Dirty workspace audio flags are not release evidence. Only `book-2b9853ec52` is public audio approved.

## Summary

| Measure | Count |
| --- | ---: |
| Proposed entries | 35 |
| Unique titles after deduplication | 34 |
| Bengali titles | 10 |
| English titles | 24 |
| Public readers | 11 |
| Fail-closed reader targets | 23 |
| Public audio approved | 1 |
| Audio hidden | 33 |

## Exact Bengali Set

| Slug | Display title | Author | Reader | Audio |
| --- | --- | --- | --- | --- |
| `book-2b9853ec52` | দুই বিঘা জমি | রবীন্দ্রনাথ ঠাকুর | `PUBLIC_READER` | `PUBLIC_AUDIO_APPROVED` |
| `bn-066` | আনন্দমঠ | বঙ্কিমচন্দ্র চট্টোপাধ্যায় | `PUBLIC_READER` | `AUDIO_HIDDEN` |
| `radharani` | রাধারাণী | বঙ্কিমচন্দ্র চট্টোপাধ্যায় | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `nishkriti` | নিষ্কৃতি | শরৎচন্দ্র চট্টোপাধ্যায় | `PUBLIC_READER` | `AUDIO_HIDDEN` |
| `muchiram-gurer-jibanchorit` | মুচিরাম গুড়ের জীবনচরিত | বঙ্কিমচন্দ্র চট্টোপাধ্যায় | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `book-d19e96859f` | গিন্নি | রবীন্দ্রনাথ ঠাকুর | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `book-f5d593e1f4` | রামকানাইয়ের নির্বুদ্ধিতা | রবীন্দ্রনাথ ঠাকুর | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `pather-panchali` | পথের পাঁচালী / Pather Panchali | Bibhutibhushan Bandyopadhyay | `PUBLIC_READER` | `AUDIO_HIDDEN` |
| `devdas` | দেবদাস / Devdas | Sarat Chandra Chattopadhyay | `PUBLIC_READER` | `AUDIO_HIDDEN` |
| `book-edfcf810c5` | ক্ষুধিত পাষাণ | রবীন্দ্রনাথ ঠাকুর | `FAIL_CLOSED` | `AUDIO_HIDDEN` |

`book-2b9853ec52` is already the current slug for দুই বিঘা জমি, so the proposed duplicate entry was removed. The current Bengali record for ক্ষুধিত পাষাণ is `book-edfcf810c5`; `hungry-stones` is a separate English-language reader edition.

## Exact English Set

| Slug | Display title | Author | Reader | Audio |
| --- | --- | --- | --- | --- |
| `a-ghost-story` | A Ghost Story | Mark Twain | `PUBLIC_READER` | `AUDIO_HIDDEN` |
| `dracula` | Dracula | Bram Stoker | `PUBLIC_READER` | `AUDIO_HIDDEN` |
| `frankenstein` | Frankenstein | Mary Wollstonecraft Shelley | `PUBLIC_READER` | `AUDIO_HIDDEN` |
| `jekyll-and-hyde` | The Strange Case of Dr. Jekyll and Mr. Hyde | Robert Louis Stevenson | `PUBLIC_READER` | `AUDIO_HIDDEN` |
| `picture-of-dorian-gray` | The Picture of Dorian Gray | Oscar Wilde | `PUBLIC_READER` | `AUDIO_HIDDEN` |
| `the-time-machine` | The Time Machine | H. G. Wells | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `the-call-of-the-wild` | The Call of the Wild | Jack London | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `white-fang` | White Fang | Jack London | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `great-expectations` | Great Expectations | Charles Dickens | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `jane-eyre` | Jane Eyre | Charlotte Brontë | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `pride-and-prejudice` | Pride and Prejudice | Jane Austen | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `the-secret-garden` | The Secret Garden | Frances Hodgson Burnett | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `alices-adventures-in-wonderland` | Alice's Adventures in Wonderland | Lewis Carroll | `PUBLIC_READER` | `AUDIO_HIDDEN` |
| `the-gift-of-the-magi` | The Gift of the Magi | O. Henry | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `the-tell-tale-heart` | The Tell-Tale Heart | Edgar Allan Poe | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `the-open-window` | The Open Window | Saki | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `sredni-vashtar` | Sredni Vashtar | Saki | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `dsires-baby` | Désirée's Baby | Kate Chopin | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `the-cop-and-the-anthem` | The Cop and the Anthem | O. Henry | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `the-last-leaf` | The Last Leaf | O. Henry | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `the-masque-of-the-red-death` | The Masque of the Red Death | Edgar Allan Poe | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `the-yellow-wallpaper` | The Yellow Wallpaper | Charlotte Perkins Gilman | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `the-monkeys-paw` | The Monkey's Paw | W.W. Jacobs | `FAIL_CLOSED` | `AUDIO_HIDDEN` |
| `the-necklace` | The Necklace | Guy de Maupassant | `FAIL_CLOSED` | `AUDIO_HIDDEN` |

## Public Audiobook Set

Only `book-2b9853ec52` is `PUBLIC_AUDIO_APPROVED`. It has same-day production API/manifest evidence, release gate `APPROVED`, QA status `QA_PASSED`, and evidence-gated Listen controls.

`bn-066` and `a-ghost-story` are public readers with audio hidden. Every other title is also audio hidden regardless of local audiobook flags or assets.

## Identifier Normalization

| Proposed identifier | Frozen identifier | Decision |
| --- | --- | --- |
| `current slug for দুই বিঘা জমি` | `book-2b9853ec52` | Duplicate removed; title retained once. |
| `current slug for ক্ষুধিত পাষাণ` | `book-edfcf810c5` | Bengali catalog record selected. |
| `hungry-stones` | Excluded from Bengali slot | Separate English reader edition. |
| `the-strange-case-of-dr-jekyll-and-mr-hyde` | `jekyll-and-hyde` | Runtime alias normalized. |
| `the-picture-of-dorian-gray` | `picture-of-dorian-gray` | Runtime alias normalized. |
| `dsires-baby` | `dsires-baby` | Existing legacy slug preserved for Désirée's Baby. |

## Freeze Decision

- No title concept from the proposed set was removed.
- One duplicate identifier and three non-canonical aliases were excluded from the exact slug set.
- Catalog-backed but non-routable titles remain `FAIL_CLOSED`; this freeze does not publish them.
- No source, release gate, public audio state, or paid-audio workflow changed.
