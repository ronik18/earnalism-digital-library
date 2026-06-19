from __future__ import annotations

import json
from pathlib import Path

from scripts.launch_readiness_audit import (
    ROOT,
    LAUNCH_EVENTS,
    analytics_event_schema,
    audit_audio,
    run_payment_smoke,
    audit_production_parity,
    audit_seo,
    local_removed_route_status,
    run_audits,
    validate_mock_analytics_events,
    validate_removed_route,
    write_mode_outputs,
)


def test_shop_is_routed_to_removed_content_locally():
    vercel_config = json.loads((ROOT / "frontend" / "vercel.json").read_text(encoding="utf-8"))
    route = local_removed_route_status("/shop", vercel_config)

    assert route["matched"] == "removed-content"
    assert route["status"] == 410
    assert route["x_robots_tag"] == "noindex, nofollow, noarchive"


def test_shop_slash_is_routed_to_removed_content_locally():
    vercel_config = json.loads((ROOT / "frontend" / "vercel.json").read_text(encoding="utf-8"))
    route = local_removed_route_status("/shop/", vercel_config)

    assert route["matched"] == "removed-content"
    assert route["status"] == 410
    assert route["x_robots_tag"] == "noindex, nofollow, noarchive"


def test_production_parity_local_mode_has_no_shell_200_for_removed_routes():
    audit = audit_production_parity(fetch_production=False)

    assert audit["status"] == "PASS"
    assert audit["fetch_production"] is False
    assert all(row["status"] != 200 for row in audit["local_removed_routes"])
    assert all(row["generic_shell"] is False for row in audit["local_removed_routes"])


def test_removed_route_redirect_is_blocker():
    issues = validate_removed_route(
        {"url": "https://theearnalism.com/shop", "status": 308, "x_robots_tag": "", "generic_shell": False},
        scope="Production",
    )

    assert any(issue.blocker for issue in issues)
    assert any("redirect HTTP 308" in issue.message for issue in issues)


def test_removed_route_generic_shell_is_blocker():
    issues = validate_removed_route(
        {"url": "https://theearnalism.com/product/patterned-wrap-dress", "status": 200, "x_robots_tag": "", "generic_shell": True},
        scope="Production",
    )

    assert any(issue.blocker for issue in issues)
    assert any("generic Earnalism shell" in issue.message for issue in issues)


def test_removed_route_http_200_is_blocker():
    issues = validate_removed_route(
        {"url": "https://theearnalism.com/fashion", "status": 200, "x_robots_tag": "", "generic_shell": False},
        scope="Production",
    )

    assert any(issue.blocker for issue in issues)
    assert any("HTTP 200" in issue.message for issue in issues)


def test_removed_route_missing_xrobots_is_blocker():
    issues = validate_removed_route(
        {"url": "https://theearnalism.com/product/patterned-wrap-dress", "status": 410, "x_robots_tag": "", "generic_shell": False},
        scope="Production",
    )

    assert any(issue.blocker for issue in issues)
    assert any("X-Robots-Tag" in issue.message for issue in issues)


def test_removed_route_valid_410_or_404_noindex_passes():
    for status in (404, 410):
        issues = validate_removed_route(
            {
                "url": "https://theearnalism.com/product/patterned-wrap-dress",
                "status": status,
                "x_robots_tag": "noindex, nofollow, noarchive",
                "generic_shell": False,
            },
            scope="Production",
        )

        assert issues == []


def test_seo_audit_excludes_demo_urls_and_keeps_deindexing_strategy():
    audit = audit_seo()

    assert audit["sitemap"]["demo_url_count"] == 0
    assert audit["robots"]["retired_routes_crawlable"] is True
    assert audit["robots"]["private_routes_blocked"] is True
    assert audit["static_html"]["homepage_meta_complete"] is True
    assert audit["static_html"]["unsafe_book_schema_emitted"] is False


def test_audio_audit_detects_remote_upload_guards():
    audit = audit_audio()

    assert audit["guards"]["remote_upload_guard_present"] is True
    assert audit["guards"]["voice_pipeline_dry_run_only"] is True
    assert audit["guards"]["final_action_plan_archived"] is True


def test_analytics_schema_mock_covers_all_launch_events_without_pii():
    schema = analytics_event_schema()
    result = validate_mock_analytics_events(schema)

    assert result["status"] == "PASS"
    assert result["coverage_complete"] is True
    assert sorted(result["covered_events"]) == sorted(LAUNCH_EVENTS)
    for event in schema["events"]:
        assert "email" in event["blocked_metadata_fields"]
        assert event["recipients"] == []
        assert event["provider_api_ids"] == []


def test_payment_smoke_is_dry_run_static(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.launch_readiness_audit.OUTPUT_DIR", tmp_path / "launch")

    smoke = run_payment_smoke()

    assert smoke["status"] == "PASS_TEST_MODE"
    assert smoke["mode"] == "dry_run_static"
    assert smoke["public_mutation"] is False
    assert smoke["external_calls"] == []
    assert smoke["checks"]["wallet_credit_idempotency_test_detected"] is True
    assert smoke["checks"]["webhook_idempotency_test_detected"] is True
    assert (tmp_path / "launch" / "payment_smoke.json").exists()


def test_all_audit_writes_required_reports_without_production_network(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.launch_readiness_audit.OUTPUT_DIR", tmp_path / "launch")
    audits = run_audits("all", fetch_production=False, production_base_url="https://example.invalid")
    write_mode_outputs("all", audits)

    required = [
        ROOT / "LAUNCH_READINESS_REPORT.md",
        ROOT / "LAUNCH_BLOCKERS.md",
        ROOT / "LAUNCH_FIXES_REPORT.md",
        ROOT / "PRODUCTION_PARITY_REPORT.md",
        ROOT / "SEO_CRAWLABILITY_REPORT.md",
        ROOT / "UX_CONVERSION_AUDIT.md",
        ROOT / "PERFORMANCE_LATENCY_REPORT.md",
        ROOT / "AUTOSCALING_READINESS_REPORT.md",
        ROOT / "SECURITY_PRIVACY_REVIEW.md",
        ROOT / "PAYMENT_REVENUE_FLOW_REPORT.md",
        ROOT / "AUDIOBOOK_READINESS_REPORT.md",
        ROOT / "FIRST_BATCH_SOURCE_RIGHTS_BACKFILL_PLAN.md",
        ROOT / "CONTROLLED_PUBLICATION_PRECHECK.md",
        ROOT / "PHASE13_VALIDATION_REPORT.md",
        ROOT / "PHASE13B_VALIDATION_REPORT.md",
        ROOT / "PHASE13_RAW_VERIFICATION.md",
        ROOT / "GROWTH_ANALYTICS_READINESS.md",
        ROOT / "APPROVED_TO_PUBLISH.template.md",
        ROOT / "FIRST_BATCH_REAL_SOURCE_MATRIX.md",
        ROOT / "FIRST_BATCH_REAL_SOURCE_BACKFILL_INPUT.template.json",
        ROOT / "POST_DEPLOY_VERIFICATION.md",
        ROOT / "BOOK_SEO_PRERENDER_PLAN.md",
        ROOT / "PHASE13C_VALIDATION_REPORT.md",
        ROOT / "FINAL_GO_NO_GO_DECISION.md",
    ]

    assert audits["scorecard"]["recommendation"] == "HOLD_FOR_FIXES"
    assert all(path.exists() for path in required)
    assert (ROOT / "LAUNCH_CATALOG_ACTION_PLAN.csv").exists()
    assert (ROOT / "FIRST_BATCH_REAL_SOURCE_MATRIX.csv").exists()
    assert not (ROOT / "APPROVED_TO_PUBLISH.md").exists()
    assert (tmp_path / "launch" / "launch_readiness.json").exists()
