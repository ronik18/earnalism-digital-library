# Growth Analytics Readiness

Status: `PASS_WITH_WARNINGS`

| Event | Detected |
| --- | --- |
| homepage_view | True |
| first_time_site_tour_shown | True |
| first_time_site_tour_completed | True |
| first_time_site_tour_skipped | True |
| hero_read_chapter_free_click | True |
| dracula_book_page_view | True |
| start_dracula_click | True |
| reader_opened | True |
| reader_locked_state | True |
| reader_low_balance_state | True |
| pricing_page_view | True |
| reading_pack_selected | True |
| checkout_started | True |
| payment_success_return | True |
| payment_failed_or_cancelled | True |
| wallet_credited_visible | True |
| continue_reading_click | True |
| return_resume_reading_click | True |
| core_web_vital | True |
| page_view | True |
| book_view | True |
| preview_start | True |
| dracula_preview_start | True |
| dracula_start_reading_click | True |
| dracula_reading_pass_click | True |
| reading_started | True |
| chapter_1_completed | True |
| reading_session_completed | False |
| pricing_view | True |
| pricing_pack_rendered | False |
| pricing_pack_cta_click | True |
| reading_time_explainer_rendered | False |
| dracula_continue_from_pricing_click | True |
| checkout_start | True |
| payment_success | True |
| payment_failed | True |
| newsletter_joined | False |
| referral_invited | False |
| referral_converted | False |
| institution_interest | False |
| support_complaint_created | False |
| audio_preview_played | False |
| cta_clicked | False |
| bengali_gothic_pipeline_view | True |
| kshudhita_pashan_notify_click | False |
| kshudhita_pashan_audio_interest_click | False |
| bengali_voice_sample_interest | False |
| bengali_gothic_reading_circle_click | False |

Schema artifact: `/private/var/folders/yd/zn1ydw_50ts7mj_ldjxbyd3m0000gn/T/pytest-of-ronikbasak/pytest-14/test_all_audit_writes_required0/launch/analytics_event_schema.json`
Mock sink supported: `True`

| Mock Validator | Value |
| --- | --- |
| status | PASS |
| mock_payload_count | 48 |
| covered_events | ['homepage_view', 'first_time_site_tour_shown', 'first_time_site_tour_completed', 'first_time_site_tour_skipped', 'hero_read_chapter_free_click', 'dracula_book_page_view', 'start_dracula_click', 'reader_opened', 'reader_locked_state', 'reader_low_balance_state', 'pricing_page_view', 'reading_pack_selected', 'checkout_started', 'payment_success_return', 'payment_failed_or_cancelled', 'wallet_credited_visible', 'continue_reading_click', 'return_resume_reading_click', 'core_web_vital', 'page_view', 'book_view', 'preview_start', 'dracula_preview_start', 'dracula_start_reading_click', 'dracula_reading_pass_click', 'reading_started', 'chapter_1_completed', 'reading_session_completed', 'pricing_view', 'pricing_pack_rendered', 'pricing_pack_cta_click', 'reading_time_explainer_rendered', 'dracula_continue_from_pricing_click', 'checkout_start', 'payment_success', 'payment_failed', 'newsletter_joined', 'referral_invited', 'referral_converted', 'institution_interest', 'support_complaint_created', 'audio_preview_played', 'cta_clicked', 'bengali_gothic_pipeline_view', 'kshudhita_pashan_notify_click', 'kshudhita_pashan_audio_interest_click', 'bengali_voice_sample_interest', 'bengali_gothic_reading_circle_click'] |
| coverage_complete | True |
| errors | [] |
| external_calls | [] |

Tests must keep analytics mocked/disabled and must not send real events. Canonical events are schema-validated through a mock sink; production analytics should still be verified after operator-approved deployment.
