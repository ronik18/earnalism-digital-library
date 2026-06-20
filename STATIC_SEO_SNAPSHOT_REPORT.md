# Static SEO Snapshot Report

Status: `PASS` locally after `npm --prefix frontend run build`.

## Build Output

The post-build snapshot generator writes:

| Route | Snapshot |
| --- | --- |
| `/` | `frontend/build/index.html` |
| `/book/dracula` | `frontend/build/book/dracula/index.html` |
| `/library` | `frontend/build/library/index.html` |
| `/pricing` | `frontend/build/pricing/index.html` |
| `/journal` | `frontend/build/journal/index.html` |
| `/contact` | `frontend/build/contact/index.html` |
| `/reader/dracula` | `frontend/build/reader/dracula/index.html` |

The snapshots preserve the React root and compiled JS/CSS bundles, so hydrated UX remains controlled by the existing CRA app.

## Vercel Static Serving

`frontend/vercel.json` uses `outputDirectory: build`, and the final SPA rewrite excludes only asset files before falling back to `/index.html`. Vercel serves physical files from `build` before that fallback, so these generated files are eligible to answer the matching routes directly:

| Route | Static file served before fallback |
| --- | --- |
| `/book/dracula` | `frontend/build/book/dracula/index.html` |
| `/library` | `frontend/build/library/index.html` |
| `/reader/dracula` | `frontend/build/reader/dracula/index.html` |

## Policy

- Dracula remains the only live approved core reading title.
- `/book/dracula` is indexable and canonical.
- `/reader/dracula` is `noindex,follow` and canonicalized to `/book/dracula`.
- The sitemap includes Dracula as the only book URL and excludes reader/audio/demo/pipeline reading routes.
- Robots allows `/reader/dracula` so crawlers can observe its noindex/canonical while the rest of `/reader/` stays blocked.

## Validation Evidence

`npm run launch:seo-audit` now reports `PASS`.

The audit verifies raw HTML for title, description, canonical, Open Graph, Twitter cards, Book JSON-LD, BreadcrumbList JSON-LD, no fake ratings/reviews, no audio availability claim, no broad live-catalog claim, and no client-only placeholder metadata.

After deploy, `npm run launch:social-preview-audit:prod` verifies the same raw HTML social-preview contract against `https://theearnalism.com` for `/`, `/book/dracula`, `/library`, and `/reader/dracula`. The reader route remains `noindex,follow` and canonicalized to `/book/dracula`.
