# Demand Scoring

Phase 3 ranks books and topics by growth potential before Earnalism spends
content-generation credits.

The system is deterministic and dry-run only. It does not call LLMs, TTS
providers, image APIs, paid APIs, or external search services.

## Purpose

Demand scoring helps decide which books or study topics should move into the
next production phase. It combines available internal demand signals, product
fit, education fit, SEO potential, audiobook potential, visual-study potential,
production complexity, and rights risk.

## Inputs

The CLI accepts:

- a plain JSON array of books/topics,
- an object with a `books` array,
- a Phase 1B-style catalog audit object with a `rows` array,
- Phase 2-style rights report rows when supplied as a JSON array.

When internal metrics are present, these fields are used:

- `page_views`
- `reading_starts`
- `reading_completions`

The same values can also be nested under `metrics` or `analytics`.

Missing internal metrics are treated as zero. The scorer does not fabricate
engagement data.

## Components And Weights

The current score is a 0-100 heuristic:

```text
positive signals
- engagement: log-scaled page views, reading starts, and completions
- category fit
- Bengali cultural fit
- school/college usefulness
- young reader usefulness
- SEO potential
- audiobook potential
- visual-study potential
- launch seed bonus

penalties
- production_complexity * 1.15
- rights_risk * 1.35
```

### Category Fit

Rewards books aligned with Earnalism shelves such as literary fiction, gothic
fiction, science fiction, adventure, young readers, and study material.

### Bengali Cultural Fit

Rewards Bengali-language books and works with strong Bengali cultural relevance,
including Tagore, Anandamath, Devdas, Chander Pahar, and Sultana's Dream.

### School/College Usefulness

Rewards items with classroom or exam utility, especially study material,
calculus, and widely studied classics.

### Young Reader Usefulness

Rewards books suitable for young readers, illustrated editions, adventure
stories, and approachable classics.

### SEO Potential

Rewards high-intent search surfaces such as major classics, Bengali books,
study topics, and launch-priority titles.

### Audiobook Potential

Rewards books likely to work well as narration-first experiences. Existing
audiobook assets increase confidence, but missing assets do not trigger
generation.

### Visual-Study Potential

Rewards books or topics that benefit from diagrams, illustrated context,
chapter maps, or visual explainers.

### Production Complexity Penalty

Long books, many chapters, Bengali production complexity, missing covers, and
study-guide complexity lower the score.

### Rights Risk Penalty

Rights risk lowers score. Tier C, blocked rights, missing rights metadata, or
unapproved rights status also change the item's action status so it cannot look
like a normal generation candidate.

## Launch Seed Bonus

The Phase 3 seed list receives a deterministic launch bonus:

- Anandamath
- Devdas
- Abol Tabol
- Sultana's Dream
- Sherlock Holmes
- Dracula
- Frankenstein
- Tagore Short Stories
- Calculus Made Easy
- Chander Pahar

## Action Status

Each output row includes:

- `READY_FOR_GENERATION`: Tier A approved and above the current score threshold.
- `REGION_GATED_PRIORITY`: Tier B approved and should remain region gated.
- `READY_FOR_RIGHTS_REVIEW`: rights metadata is missing or not approved.
- `BLOCKED_RIGHTS`: Tier C or explicit blocked reason.
- `LOW_PRIORITY`: rights-safe but below the current score threshold.

`BLOCKED_RIGHTS` and `READY_FOR_RIGHTS_REVIEW` items must not move into content
generation until Phase 2 rights work clears them.

## Running

Default seed-list report:

```bash
npm run demand:score
```

With a local export:

```bash
npm run demand:score -- --input output/catalog_audit/catalog_audit_report.json
```

## Outputs

The CLI writes:

- `output/demand/demand_priority_report.csv`
- `output/demand/demand_priority_report.md`
- `output/demand/demand_priority_report.json`

The CSV and JSON include:

- `priority_rank`
- `slug`
- `title`
- `category_slug`
- `language`
- `demand_score`
- `action_status`
- `blocking_reason`
- `recommended_product_format`
- `growth_rationale`
- `rights_risk`
- `production_complexity`
- `page_views`
- `reading_starts`
- `reading_completions`

## Interpreting Scores

High scores mean the book/topic is a strong candidate for the next production
phase, subject to action status.

Action status is the gate:

- Prioritize `READY_FOR_GENERATION`.
- Consider `REGION_GATED_PRIORITY` only for the approved region.
- Send `READY_FOR_RIGHTS_REVIEW` to Phase 2 backfill.
- Do not generate `BLOCKED_RIGHTS`.
- Defer `LOW_PRIORITY`.

## Phase 4 Use

Phase 4 ingestion should consume the reports as a queue input, filtering first
by action status and then by `priority_rank`. This prevents credit spend on
unsafe rights, weak demand, or high-complexity items.

## Limitations

- The weights are heuristics and should be tuned as real usage grows.
- Internal metrics are only used when present.
- No external market/search trend data is fetched in Phase 3.
- Rights status is consumed from available metadata; the scorer does not perform
  legal verification itself.
