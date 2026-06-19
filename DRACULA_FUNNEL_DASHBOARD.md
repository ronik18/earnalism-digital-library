# Dracula Funnel Dashboard

Status: `LOCAL_EVENT_MAP_READY`

Recommended funnel order:

1. `homepage_dracula_cta_click`
2. `dracula_book_view`
3. `dracula_preview_start`
4. `dracula_reader_start`
5. `dracula_chapter_1_complete`
6. `dracula_reading_pass_click`
7. `pricing_view`
8. `checkout_start`
9. `payment_success` or `payment_failed`

Guardrails:

- No unapproved-book CTA points to reading or payment.
- Notify Me events are separated with future-title metadata.
- Tests can use `createMockAnalyticsSink()` without hitting real analytics.
