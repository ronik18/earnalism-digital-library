# Payment Revenue Flow Report

Status: `PASS_TEST_MODE`

| Check | Value |
| --- | --- |
| pricing_packs_render | True |
| razorpay_checkout_loaded | True |
| test_mode_banner | True |
| order_creation_endpoint | True |
| verify_endpoint | True |
| webhook_endpoint | True |
| webhook_signature | True |
| wallet_credit_idempotency | True |
| payment_tests_present | True |
| support_refund_copy | True |
| dry_run_payment_smoke_written | True |
| dry_run_payment_smoke_not_blocked | True |

## Dry-Run Payment Smoke

Smoke status: `PASS_TEST_MODE`
Smoke artifact: `/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/output/launch/payment_smoke.json`

| Smoke Check | Value |
| --- | --- |
| dry_run_only | True |
| no_external_razorpay_call | True |
| pricing_view_page_exists | True |
| checkout_start_event_detected | True |
| payment_success_event_detected | True |
| payment_failed_event_detected | True |
| test_mode_simulator_detected | True |
| real_order_endpoint_detected | True |
| verify_endpoint_detected | True |
| webhook_endpoint_detected | True |
| webhook_signature_detected | True |
| idempotent_credit_detected | True |
| wallet_credit_idempotency_test_detected | True |
| webhook_idempotency_test_detected | True |
| admin_reconcile_idempotency_test_detected | True |
| post_payment_wallet_refresh_detected | True |
| post_payment_return_route_exists | True |
| analytics_schema_has_payment_events | True |

Revenue launch remains HOLD until a separate controlled Razorpay test-mode payment smoke verifies a real checkout window, wallet credit, webhook idempotency, payment_failed analytics, and post-payment return in production.

## Dracula Candidate Use

Dracula uses payment evidence as `PASS_TEST_MODE` only.

It does not prove live-money readiness, does not mutate production payments or wallets, and does not enable any public publication flag.
