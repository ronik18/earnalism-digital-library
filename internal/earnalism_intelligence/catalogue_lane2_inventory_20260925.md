# Lane 2 catalogue/title evidence inventory

Generated from clean detached `origin/main` (`1e210ebc2`) on 2026-09-25. Evidence-only; no publication, route, audio, or production state was mutated.

## Scope and exclusions

- Repository inventory: 229 catalogue rows (123 English, 106 Bengali) in `earnalism_book_inventory_for_launch.csv`; 161 are marked `reader_ready`, 171 have `public_domain_rights_status=PASS`.
- Existing commercial six-title release duplicates excluded from new-title clearance: `a-ghost-story`, `the-tell-tale-heart`, `radharani`, `a-white-heron`, `the-gift-of-the-magi`, `the-canterville-ghost`.
- Historical `dracula` core-reading release is also excluded from duplicate onboarding.
- `yugalanguriya` is explicitly HOLD and was not reopened.
- No title is marked released or exposed by this lane. Audio remains out of scope and hidden.

## Triage rules

`GREEN` requires repository evidence for source/rights, canonical content, a usable title record and cover evidence, with no unresolved material blocker. `AMBER_AUTOFIXABLE` means the title is promising but needs deterministic evidence/metadata/manifest/cover repair. `RED_EXTERNAL_BLOCKER` means a material rights, authorship, edition, translation, cover-ownership or other fact cannot be established from current authoritative evidence. No uncertainty was treated as clearance.

## Highest-confidence next batch

The following candidates have `public_domain_rights_status=PASS`, `reader_status=reader_ready`, source URL and title metadata in `content/books/*/book.json`, chapter payloads, and both cover URLs. They are **AMBER_AUTOFIXABLE**, not GREEN, because the current branch does not contain a per-title publication manifest binding and the release pipeline still needs explicit text/source hash and cover-provenance evidence. Bengali Wikisource rows additionally need source-layer licence/permalink/attribution/ShareAlike metadata; this concerns the transcription layer, not the underlying literary work.

| Title | Slug | Language | Source | Current blocker | Disposition |
| --- | --- | --- | --- | --- | --- |
| গিন্নি | `book-d19e96859f` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| মুচিরাম গুড়ের জীবনচরিত | `muchiram-gurer-jibanchorit` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| রামকানাইয়ের নির্বুদ্ধিতা | `book-f5d593e1f4` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| কাবুলিওয়ালা | `book-2e468c4990` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| খাতা | `book-0deb35c750` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| খোকাবাবুর প্রত্যাবর্তন | `book-c7f3ce526c` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| তারাপ্রসন্নের কীর্তি | `book-754da4eab8` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| দালিয়া | `book-a74c1a1451` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| দেনাপাওনা | `book-63afd5e9be` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| ব্যবধান | `book-2ddbed8293` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| স্বর্ণমৃগ | `book-d2fe532e1c` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| অপরিচিতা | `bn-027` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| আঁধারে আলো | `bn-041` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| ইন্দিরা | `bn-060` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| মহেশ | `bn-031` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| আনন্দমঠ | `bn-066` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| কমলাকান্তের দপ্তর | `bn-059` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| নিষ্কৃতি | `nishkriti` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| বড়দিদি | `bn-035` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| মেজদিদি | `bn-036` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| লোকরহস্য | `lokrahasya` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| মৃণালিনী | `mrinalini` | Bengali | Bengali Wikisource | source-layer licence/permalink + manifest/hash binding | AMBER_AUTOFIXABLE |
| Frankenstein | `frankenstein` | English | Earnalism historical import (Gutenberg URL) | historical-import provenance and manifest/hash binding need reconciling | AMBER_AUTOFIXABLE |
| The Adventures of Sherlock Holmes | `the-adventures-of-sherlock-holmes` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| Alice's Adventures in Wonderland | `alices-adventures-in-wonderland` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| Bharat at the Crossroads | `bharat-at-the-crossroads` | English | Reo Enterprise | original-work authorship/owner evidence and manifest binding | AMBER_AUTOFIXABLE |
| Pride and Prejudice | `pride-and-prejudice` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| The Enchanted April | `the-enchanted-april` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| The Great Gatsby | `the-great-gatsby` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| The Wonderful Wizard of Oz | `the-wonderful-wizard-of-oz` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| Acres of Diamonds | `acres-of-diamonds` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| Great Expectations | `great-expectations` | English | Earnalism historical import | historical-import provenance and manifest/hash binding need reconciling | AMBER_AUTOFIXABLE |
| My Life and Work | `my-life-and-work` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| The Art of Money Getting | `the-art-of-money-getting` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| The Call of the Wild | `the-call-of-the-wild` | English | Earnalism historical import | historical-import provenance and manifest/hash binding need reconciling | AMBER_AUTOFIXABLE |
| The Principles of Scientific Management | `the-principles-of-scientific-management` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| The Science of Getting Rich | `the-science-of-getting-rich` | English | Project Gutenberg | manifest/hash + cover provenance not yet bound | AMBER_AUTOFIXABLE |
| The Secret Garden | `the-secret-garden` | English | Earnalism historical import | historical-import provenance and manifest/hash binding need reconciling | AMBER_AUTOFIXABLE |
| The Time Machine | `the-time-machine` | English | Earnalism historical import | historical-import provenance and manifest/hash binding need reconciling | AMBER_AUTOFIXABLE |

## RED / HOLD observations

- `yugalanguriya` remains HOLD as explicitly directed.
- Any inventory row with `public_domain_rights_status=REVIEW_REQUIRED`, `reader_status=draft`, missing source URL, unresolved translator/edition status, or no defensible cover provenance is RED until the material fact is established. This includes the 58 rights-review rows and 68 draft rows in the inventory; no automatic clearance was asserted.
- Titles with only `DESIGNED_PLACEHOLDER_NO_SAFE_LOCAL_COVER` or `UNKNOWN` cover status are not release-ready; cover creation/ownership evidence is a separate blocker.
- Long-form or historical imports are not rejected solely for length, but must pass the same text-integrity and manifest gates.

## Required next evidence packet (per candidate)

1. Resolve source-layer licence/permalink and attribution/change notice for Bengali Wikisource, or record an equivalent authoritative source-layer basis.
2. Compute normalized source/text hashes from the exact imported chapters and bind them to a publication manifest; preserve material discrepancies rather than silently rewriting text.
3. Record cover asset provenance and dimensions; reject placeholders or unknown ownership.
4. Run existing controlled-publication precheck, text integrity, reader-render, SEO, and direct-backend fail-closed checks.
5. Release only after the commercial baseline is active; every title must inherit 3-page preview plus commercial entitlement, never full-free, with audio disabled.

No title from this lane is exposed, published, added to sitemap, or enabled for checkout by this inventory.
