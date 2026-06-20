# Dracula Book SEO Report

Status: `PASS` locally.

## `/book/dracula` Raw HTML

| Check | Result |
| --- | --- |
| Title | `Dracula by Bram Stoker | The Earnalism Digital Library` |
| Meta description | Mentions Dracula, Bram Stoker, Chapter 1 free, 7-day reading pass, and audio not available yet. |
| Canonical | `https://theearnalism.com/book/dracula` |
| Robots | `index,follow` |
| Open Graph | `og:type=book`, Dracula title, description, URL, image, and site name present. |
| Twitter | `summary_large_image`, Dracula title, description, and image present. |
| JSON-LD | `WebPage`, `Book`, and `BreadcrumbList` present before hydration. |
| Source evidence | Project Gutenberg eBook #345 is included only because the controlled artifact source evidence is present and approved. |
| Ratings/reviews | No fake `aggregateRating` or `review` markup. |
| Audio claim | No audiobook availability or Listen Now claim. |

## Book JSON-LD Policy

The Book JSON-LD uses only controlled evidence:

- `name`: Dracula
- `author`: Bram Stoker
- `inLanguage`: en
- `publisher`: The Earnalism
- `url`: `https://theearnalism.com/book/dracula`
- `sameAs`: `https://www.gutenberg.org/ebooks/345`
- Chapter 1 preview is represented as a free `hasPart`; the full book is not falsely marked free.

No reviews, ratings, testimonials, awards, fake offers, or audiobook claims are emitted.
