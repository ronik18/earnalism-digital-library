# Payment Revenue Flow Report

Status: `PASS_WITH_WARNINGS`

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

Revenue launch remains HOLD until a controlled Razorpay test-mode payment smoke verifies checkout_start, payment_success, payment_failed, wallet credit, and post-payment return.
