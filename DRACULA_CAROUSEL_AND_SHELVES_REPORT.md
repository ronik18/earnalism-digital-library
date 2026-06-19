# Dracula Carousel And Shelves Report

Status: `PASS`

## Carousel

The homepage no longer uses the broad multi-book live carousel. It now has a controlled three-slide launch module:

1. Dracula by Bram Stoker - live controlled release.
2. Rights-safe source - Project Gutenberg eBook #345.
3. 7-Day Dracula Reading Path - draft, Notify Me only.

Only Dracula has reader CTAs. Pipeline/draft slides have Notify Me or source-note CTAs only.

## Shelves

The homepage and library now use honest controlled-launch shelves:

| Shelf | Public State |
| --- | --- |
| Live Controlled Release | Dracula only. |
| Coming Through the Rights-Safe Pipeline | Future titles are visible but not readable. |
| Reading Paths | Dracula path is draft; Notify Me only. |
| Audiobooks | Audio is not live; no play buttons. |

## Verification

- No "105 reading rooms open" claim remains in the changed homepage/library UX.
- No unapproved title links to `/reader/*`.
- Sitemap generation now includes one approved book route: `/book/dracula`.
- Public backend book/reader queries are gated to approved Dracula only.
