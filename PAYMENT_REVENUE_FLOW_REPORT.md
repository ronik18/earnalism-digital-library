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
Smoke artifact: `/private/var/folders/yd/zn1ydw_50ts7mj_ldjxbyd3m0000gn/T/pytest-of-ronikbasak/pytest-14/test_all_audit_writes_required0/launch/payment_smoke.json`

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
| webhook_secret_required | True |
| verify_scopes_intent_to_user | True |
| bad_verify_signature_fails_intent | True |
| failed_payment_marked_failed | True |
| simulator_disabled_outside_test | True |
| test_mode_smoke_script_detected | True |
| idempotent_credit_detected | True |
| stale_intent_expiry_detected | True |
| wallet_credit_idempotency_test_detected | True |
| webhook_idempotency_test_detected | True |
| admin_reconcile_idempotency_test_detected | True |
| post_payment_wallet_refresh_detected | True |
| post_payment_return_route_exists | True |
| wallet_truth_copy_detected | True |
| no_subscription_autorenewal_copy_detected | True |
| no_permanent_ownership_claim_detected | True |
| no_public_audiobook_sale_detected | True |
| analytics_schema_has_payment_events | True |

Revenue launch remains HOLD until a separate controlled Razorpay test-mode payment smoke verifies a real checkout window, wallet credit, webhook idempotency, payment_failed analytics, and post-payment return in production.
