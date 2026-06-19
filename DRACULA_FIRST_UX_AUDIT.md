# Dracula First UX Audit

Status: `PASS_WITH_IMPLEMENTED_FIXES`

## Public UX Surfaces Audited

| Surface | Finding | Action |
| --- | --- | --- |
| Homepage hero | Broad library message implied many readable books. | Replaced with Dracula-first controlled launch message. |
| Homepage carousel | Previously showed live book count and many covers. | Replaced with three controlled launch slides. |
| Homepage shelves | Previously exposed broad categories. | Replaced with live Dracula shelf plus pipeline, reading path draft, and audio QA notes. |
| Library page | Previously rendered API book grid as live catalog. | Replaced with controlled shelves; Dracula only is readable. |
| Category filters | Could imply empty/fake open shelves. | Replaced with controlled filters: All, Live, Pipeline, Reading Paths, Audiobooks. |
| Book cards | Unapproved titles could show reader CTAs. | Added card truth gate. Non-Dracula titles show Coming Soon / Notify Me only. |
| Dracula book page | Needed source, rights, audio, and scope clarity. | Added controlled release note and Dracula-specific CTAs. |
| Dracula reader page | Needed no audio CTA and reader-start tracking. | Dracula narration is disabled; reader events are tracked. |
| Header CTA | Generic Start Reading implied a broad open catalog. | Changed to Start Dracula. |
| Crawler-visible claims | CRA shell cannot fully prerender dynamic route metadata. | Updated copy/SEO hook and documented PASS_WITH_WARNINGS. |

## Classification

| Title / Surface | Classification | Reader Link | Book JSON-LD | Notes |
| --- | --- | --- | --- | --- |
| Dracula | LIVE_APPROVED | Yes | Yes | Tier A approved core reading candidate only. |
| Frankenstein | COMING_SOON_PIPELINE | No | No | Notify Me only. |
| Sherlock Holmes | COMING_SOON_PIPELINE | No | No | Notify Me only. |
| Sultana's Dream | COMING_SOON_PIPELINE | No | No | Notify Me only. |
| Calculus Made Easy | COMING_SOON_PIPELINE | No | No | Notify Me only. |
| Other public DB books | HIDDEN | No | No | Public APIs are gated to Dracula only. |

## Result

Dracula is the only live approved title in the public UX. Unapproved items are not presented as readable products.
