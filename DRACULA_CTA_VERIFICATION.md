# Dracula CTA Verification

Status: `PASS`

Tracked events added to the frontend analytics allowlist:

- `homepage_dracula_cta_click`
- `dracula_book_view`
- `dracula_preview_start`
- `dracula_start_reading_click`
- `dracula_reading_pass_click`
- `dracula_reader_start`
- `dracula_chapter_1_complete`
- `dracula_notify_me_click`
- existing payment events remain available: `pricing_view`, `checkout_start`, `payment_success`, `payment_failed`

Rules:

- No PII is sent by the new CTA metadata.
- Future-title CTAs use Notify Me and do not point to reader/payment.
- Dracula reader and reading-pass CTAs have distinct events.
