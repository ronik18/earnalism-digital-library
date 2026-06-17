# Earnalism Growth Metrics And Analytics Plan

Goal: measure growth, conversion, retention, and repeat reading-time purchases without re-architecting analytics.

Existing helper:

- `frontend/src/lib/funnelAnalytics.js` exposes `trackFunnelEvent(event, metadata)`.
- Backend endpoint: `/api/analytics/events`.

## KPI Dashboard

| KPI | Definition | Primary Split |
| --- | --- | --- |
| Landing page visits | Sessions on `/`, `/library`, `/book/:slug`, campaign landing URLs | UTM source, country, device |
| Signup clicks | Clicks on sign-in/sign-up CTAs | UTM source, page |
| Book previews | Reader opens from preview CTAs | Book slug, shelf, source |
| Reader opens | Successful `/reader/:slug` render | Language, book, source |
| Next/previous page usage | Reader page navigation events | Book, chapter, language |
| Audiobook plays | Play clicks on reader audio control | Book, language, provider |
| Payment-flow starts | Clicks from pricing pack or book payment CTA | Pack, book, source |
| Successful purchases | Verified Razorpay or test-mode success event | Pack, amount, source |
| Reading-time purchases | Minutes purchased by pack | Reader cohort, source |
| Returning readers | Readers with more than one session in 7/30 days | Source, book category |
| Revenue per reader | Paid revenue / paying readers | Source, campaign |
| Conversion rate by source | Purchase count / landing sessions | UTM source/medium/campaign |
| UTM attribution | First-touch and last-touch campaign parameters | Source, medium, content |

## Recommended Event Names

Use these event names consistently in frontend instrumentation and backend reporting:

| Event | When It Fires | Required Metadata |
| --- | --- | --- |
| `landing_page_view` | Campaign page/home/library view | `utm_source`, `utm_medium`, `utm_campaign`, `path` |
| `signup_cta_click` | Header, pricing, reader lock, or account CTA | `source_component`, `path` |
| `book_preview_click` | Preview CTA from card/book page | `book_slug`, `category_slug`, `source_component` |
| `reader_open` | Reader route successfully opens | `book_slug`, `language`, `chapter_id` |
| `reader_next_page_click` | Next page control clicked | `book_slug`, `chapter_id`, `page_index` |
| `reader_prev_page_click` | Previous page control clicked | `book_slug`, `chapter_id`, `page_index` |
| `audiobook_play_click` | Reader audio play button clicked | `book_slug`, `language`, `provider` |
| `payment_flow_start` | Pricing pack button or book payment CTA clicked | `pack_id`, `book_slug`, `price_inr` |
| `purchase_success` | Server verifies payment or test purchase completes | `pack_id`, `amount_inr`, `minutes` |
| `returning_reader_session` | Known reader returns within 7/30 days | `reader_id_hash`, `days_since_last_seen` |

## Minimal Instrumentation Suggestions

Do not re-architect analytics. Add small calls around existing user-facing actions:

- Header and hero CTAs: `signup_cta_click` or `book_preview_click`.
- Book cards: `book_preview_click`.
- Reader page mount: `reader_open`.
- Reader next/previous buttons: `reader_next_page_click`, `reader_prev_page_click`.
- Audio play button: `audiobook_play_click`.
- Pricing pack button: `payment_flow_start`.
- Payment success handler: `purchase_success`.

## UTM Standard

Use these parameters:

```text
utm_source=linkedin|x|instagram|facebook|youtube|whatsapp|newsletter|google_ads|meta_ads
utm_medium=organic|paid_social|video|email|community|retargeting
utm_campaign=100_day_growth
utm_content=site_tour_90s|pay_time_30s|preview_20s|bengali_30s|carousel_launch|profile_link
utm_term=optional_keyword_or_audience
```

Example:

```text
https://theearnalism.com/library?utm_source=linkedin&utm_medium=organic&utm_campaign=100_day_growth&utm_content=site_tour_90s
```

## Campaign Scorecard

Weekly scorecard fields:

- Spend by channel.
- Impressions.
- Click-through rate.
- Landing page sessions.
- Preview starts.
- Reader opens.
- Audio plays.
- Pricing starts.
- Purchases.
- Revenue.
- Cost per preview.
- Cost per reader open.
- Cost per purchase.
- Repeat purchase rate.
- Top 10 books by preview-to-purchase conversion.

## Quality Guardrails

- Track only lawful, privacy-safe metadata.
- Do not store passwords, full payment details, or raw card data.
- Hash reader identifiers where possible.
- Keep campaign performance claims internal unless independently proven.
- Treat 1000X revenue as an internal stretch target, not a public promise.
