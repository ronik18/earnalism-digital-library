# Dracula SEO Verification

Status: `PASS_WITH_WARNINGS`

Implemented:

- Homepage title/description now describe the Dracula controlled launch.
- Library title/description state Dracula is the only live approved release.
- Dracula book page title/description/canonical are route-specific in the client.
- Dracula Book JSON-LD is emitted only for the approved live slug.
- Unapproved books are hidden from public book API responses and reader manifests.

Warnings:

- The frontend is a CRA SPA. Dynamic route metadata is applied client-side, not server-rendered.
- Durable search/social previews for `/book/dracula` would benefit from prerender/SSR/static snapshot work.

Launch impact:

- UX truthfulness is fixed.
- SEO score remains capped below 10 until per-route crawler-visible metadata is server-rendered or prerendered.
