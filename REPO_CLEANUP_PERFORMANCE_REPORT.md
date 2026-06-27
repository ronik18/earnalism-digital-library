# Repo Cleanup Performance Report

## Public Asset Scan

Tracked/public asset review found 32 files under frontend/public in the working tree.

| Asset | Size bytes | Note |
| --- | ---: | --- |
| frontend/public/assets/shelves/bengali.jpg | 764758 | OWNER_REVIEW_FOR_OPTIMIZATION |
| frontend/public/assets/books/dracula/dracula-back-cover.jpg | 451248 | OWNER_REVIEW_FOR_OPTIMIZATION |
| frontend/public/assets/books/dracula/dracula-front-cover.jpg | 443331 | OWNER_REVIEW_FOR_OPTIMIZATION |
| frontend/public/assets/books/agentic-ai-with-python/back-cover.jpg | 405142 | OWNER_REVIEW_FOR_OPTIMIZATION |
| frontend/public/assets/shelves/history-politics.jpg | 367823 | watch LCP/cache impact |
| frontend/public/assets/books/dracula/dracula-back-cover.webp | 363176 | watch LCP/cache impact |
| frontend/public/assets/books/dracula/dracula-front-cover.webp | 342050 | watch LCP/cache impact |
| frontend/public/assets/books/agentic-ai-with-python/front-cover.jpg | 340664 | watch LCP/cache impact |
| frontend/public/assets/shelves/bengali-classics.jpg | 291520 | watch LCP/cache impact |
| frontend/public/assets/shelves/self-growth.jpg | 265221 | watch LCP/cache impact |
| frontend/public/assets/shelves/literature.jpg | 262472 | watch LCP/cache impact |
| frontend/public/assets/shelves/business.jpg | 226570 | watch LCP/cache impact |
| frontend/public/assets/books/kshudhita-pashan/kshudhita-pashan-front.webp | 224502 | watch LCP/cache impact |
| frontend/public/assets/shelves/history-strategy.jpg | 221437 | watch LCP/cache impact |
| frontend/public/assets/shelves/adventure.jpg | 218363 | watch LCP/cache impact |

## Bundle Impact

- Code-path bundle impact expected: neutral. No frontend runtime code was changed in this cleanup pass.
- Active repo paths reduced by quarantining 25 duplicate files, about 167155 bytes of active-path clutter.
- Owner-provenance images were not recompressed or modified.
- No audio files were introduced under public/build paths.
