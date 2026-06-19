# Book SEO Prerender Plan

Current status: `BLOCKED_FOR_BOOK_SEO`

CRA book pages currently load book data client-side. That means crawlers may see generic metadata before the API response arrives, so book SEO remains `BLOCKED_FOR_BOOK_SEO`.

## Safe Metadata Policy

- Do not emit fake Book JSON-LD.
- Do not emit Book JSON-LD for books without approved Tier A rights metadata.
- Use only available book fields: title, author, language, category, description, cover image, and audiobook availability.
- Keep unknown/unapproved books out of structured Book schema.

## Closure Options

1. Add static snapshot generation for priority `/book/:slug` pages from approved book data.
2. Move public book pages to SSR/static generation in a future frontend migration.
3. Keep generic CRA metadata for non-priority titles and explicitly noindex unsafe/unapproved books.

## Priority Routes

| Route |
| --- |
| / |
| /library |
| /pricing |
| /book/the-principles-of-scientific-management |
| /book/acres-of-diamonds |
| /book/my-life-and-work |
| /book/the-science-of-getting-rich |
| /book/the-art-of-money-getting |
