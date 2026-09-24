# Source Rights Note: ইন্দিরা

- Title: ইন্দিরা
- Author: বঙ্কিমচন্দ্র চট্টোপাধ্যায়
- Author death year: 1894
- Original publication year: 1873
- Source URL: https://bn.wikisource.org/wiki/%E0%A6%87%E0%A6%A8%E0%A7%8D%E0%A6%A6%E0%A6%BF%E0%A6%B0%E0%A6%BE_(%E0%A6%AC%E0%A6%99%E0%A7%8D%E0%A6%95%E0%A6%BF%E0%A6%AE%E0%A6%9A%E0%A6%A8%E0%A7%8D%E0%A6%A6%E0%A7%8D%E0%A6%B0_%E0%A6%9A%E0%A6%9F%E0%A7%8D%E0%A6%9F%E0%A7%8B%E0%A6%AA%E0%A6%BE%E0%A6%A7%E0%A7%8D%E0%A6%AF%E0%A6%BE%E0%A6%AF%E0%A6%BC,_%E0%A7%A7%E0%A7%AE%E0%A7%AD%E0%A7%A9)
- Source type: wikisource_bengali_html
- Source format downloaded: text/plain
- Source license: Underlying Bengali literary text is public domain in India and the U.S.; Bengali Wikisource transcription/source layer is reused under CC BY-SA terms.
- Rights basis: Author died 1894. Published 1873. Public domain checks are enforced by the Earnalism import pipeline; source evidence kept internal/admin-only.
- Commercial use allowed: yes
- Reader-facing boilerplate removed: source furniture and repository-only matter excluded from reader edition.
- Updated at UTC: 2026-07-03T20:07:46Z
- Status: ready_for_auto_publication
- Blockers:
- None

Reader-facing Earnalism editions must not expose internal admin-only evidence files.

## Sprint 1 evidence correction (2026-09-24)

The earlier `ready_for_auto_publication` / `Blockers: None` assertion is superseded. The underlying work has India term evidence; the 1873 Wikisource transcription is CC BY-SA 4.0. A revision-bound diagnostic compared seven of eight chapters; normalized similarity was 0.98913–0.99548, with source headings/front matter still present and no complete mismatch classification. Chapter eight could not be fetched after HTTP 429. This is not `TEXT_VERIFIED`; the stored raw source and prior hashes do not close the discrepancy. This candidate remains held and is not publishable from this note.

Hash-bound cohort record: `data/title_rights_evidence/bengali-bankim-cohort-1.json` (`bn-060`).

## Indira chapter-six comparison follow-up (2026-09-24)

The exact Bengali Wikisource chapter-six revision [1910626](https://bn.wikisource.org/w/index.php?title=ইন্দিরা_(বঙ্কিমচন্দ্র_চট্টোপাধ্যায়,_১৮৭৩)/ষষ্ঠ_পরিচ্ছেদ&oldid=1910626) identifies the 1873 edition's pages 30–33. Its transcription continues after Earnalism's former chapter ending with two paragraphs before the Chapter 7 heading. Those paragraphs were verified against the 1873 facsimile, scan PDF page 35 (printed page 33; PDF SHA-256 `664191f5a7e2d8e6bbccd90d1c8ee947aa70f33b5924c1295d77b46f4114f067`), and restored verbatim from the revision-bound transcription. This resolves the chapter-six omission; it does not establish that the other seven chapter texts match the identified edition. Indira therefore remains `HOLD_SOURCE` pending those comparisons and remains unpublished. The original raw-source file and its hash are preserved unchanged.

The exact Bengali Wikisource chapter-eight revision [1910620](https://bn.wikisource.org/w/index.php?title=ইন্দিরা_(বঙ্কিমচন্দ্র_চট্টোপাধ্যায়,_১৮৭৩)/অষ্টম_পরিচ্ছেদ&oldid=1910620) identifies printed pages 38–45. After removing the source title/chapter headings, page markers and formatting whitespace only, its complete Bengali text matches Earnalism chapter 8. This closes chapter 8 only; the remaining six chapter comparisons (1–5 and 7) are still pending, so Indira remains unpublished and held.
