# Earnalism Rights Policy

This policy defines the deterministic rights checks required before any book,
edition, study guide, visual asset, audiobook, or source text is made public on
Earnalism.

This is an operational policy, not legal advice. Unclear cases must remain in
draft/quarantine until reviewed by a qualified human reviewer.

## Required Metadata

Every public book record must have rights metadata with:

- `work_title`
- `work_slug`
- `author_name`
- `author_death_year`
- `original_publication_year`
- `country_of_origin`
- `source_url`
- `source_name`
- `source_license`
- `translator_name`
- `translator_death_year`
- `illustrator_name`
- `illustrator_death_year`
- `editor_name`
- `edition_publication_year`
- `rights_tier`
- `verification_status`
- `blocked_reason`
- `publication_region`
- `verified_at`

## Rights Tiers

### Tier A

Tier A means the work is public domain in India and has strong global/source
confidence.

Minimum expectations:

- Author death year is known.
- The work satisfies the India life-plus-60 assumption.
- Source URL is present.
- Source name and source license are present.
- Source/license evidence indicates public domain or equivalent reuse rights.
- Verification status is `approved` or `verified`.
- `verified_at` is present.
- Global publishing is allowed only when the source confidence is strong.

### Tier B

Tier B means the work is public domain in India but uncertain elsewhere.

Rules:

- All base metadata is still required.
- India life-plus-60 must pass.
- Verification status must be `approved` or `verified`.
- `verified_at` must be present.
- Global publishing is blocked.
- Publication must be region gated with `publication_region` set to India or
  equivalent India-only value.

### Tier C

Tier C means the work is unclear or unsafe.

Rules:

- Public publishing is blocked.
- Public audiobook, visual asset, source text, edition, and study-guide
  publishing are blocked.
- The item may remain draft/quarantined for review.

## India Life-Plus-60 Assumption

The deterministic engine assumes literary/artistic public-domain eligibility in
India when:

```text
author_death_year + 60 < current_year
```

Missing author death year blocks public publishing.

## Translation Rights

Translations are separately protected.

Rules:

- If `translator_name` is present and `translator_death_year` is missing, public
  publishing is blocked.
- If translator death year is present but does not satisfy the India life-plus-60
  assumption, public publishing is blocked.
- Modern translations require separate verified rights evidence.

## Illustration Rights

Illustrations and covers are separately protected.

Rules:

- If `illustrator_name` is present and `illustrator_death_year` is missing,
  public publishing is blocked.
- If illustrator death year is present but does not satisfy the India
  life-plus-60 assumption, public publishing is blocked.
- Modern illustrations require separate verified rights evidence.

## Edition And Editorial Rights

Modern edited editions can introduce protected editorial material.

Rules:

- If `editor_name` is present and `edition_publication_year` is missing, the
  work is quarantined.
- If `editor_name` is present and `edition_publication_year` is later than
  `original_publication_year`, public publishing is blocked until separately
  verified.

## Source And License Requirements

Public publishing requires:

- Source URL.
- Source name.
- Source license.
- License/source evidence compatible with public-domain or commercially safe
  reuse.

Blocked or unsafe license signals include:

- all rights reserved
- non-commercial / NC
- orphan
- unknown
- unclear
- restricted

## Region-Gated Publishing

Tier B records cannot publish globally.

Allowed Tier B region values include India-only values such as:

- `india`
- `in`
- `india-only`
- `india_only`

## Draft Mode

Draft records may hold incomplete metadata, local asset mappings, source text,
or audiobook preparation artifacts while remaining unpublished.

Draft mode does not imply public rights approval.

## Blocked From Public Publishing

The following are blocked from public publishing without approved rights:

- Book detail pages.
- Reader/source text.
- Study guides.
- Covers and visual assets.
- Audiobooks.
- Modern translations.
- Modern illustrations.
- Modern edited editions.

## Human Review Required

Human/legal review is still required for:

- Any Tier C item.
- Any unclear license.
- Any modern translation.
- Any modern illustration.
- Any edited edition with protected editorial work.
- Any non-India/global publication uncertainty.
- Any record where source evidence is incomplete or contradictory.

