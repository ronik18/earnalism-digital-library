# Book SEO Prerender Plan

Current status: `PASS`

CRA book pages still hydrate client-side, but priority launch routes now use static SEO snapshots when `frontend/build` exists. The audit remains blocked only if `/book/dracula` lacks raw title, description, canonical, OG/Twitter tags, or Book JSON-LD before JavaScript runs.

## Safe Metadata Policy

- Do not emit fake Book JSON-LD.
- Do not emit Book JSON-LD for books without approved Tier A rights metadata.
- Use only available book fields: title, author, language, category, description, cover image, and audiobook availability.
- Keep unknown/unapproved books out of structured Book schema.

## Closure Options

1. Keep static snapshot generation for approved launch pages after every CRA build.
2. Move public book pages to SSR/static generation in a future frontend migration.
3. Keep generic CRA metadata for non-priority titles and explicitly noindex unsafe/unapproved books.

## Priority Routes

| Route |
| --- |
| / |
| /library |
| /pricing |
| /book/dracula |
