from __future__ import annotations

import json
from pathlib import Path

from scripts.launch_readiness_audit import (
    ROOT,
    audit_audio,
    audit_production_parity,
    audit_seo,
    local_removed_route_status,
    run_audits,
    write_mode_outputs,
)


def test_shop_is_routed_to_removed_content_locally():
    vercel_config = json.loads((ROOT / "frontend" / "vercel.json").read_text(encoding="utf-8"))
    route = local_removed_route_status("/shop", vercel_config)

    assert route["matched"] == "removed-content"
    assert route["status"] == 410
    assert route["x_robots_tag"] == "noindex, nofollow, noarchive"


def test_production_parity_local_mode_has_no_shell_200_for_removed_routes():
    audit = audit_production_parity(fetch_production=False)

    assert audit["status"] == "PASS"
    assert audit["fetch_production"] is False
    assert all(row["status"] != 200 for row in audit["local_removed_routes"])
    assert all(row["generic_shell"] is False for row in audit["local_removed_routes"])


def test_seo_audit_excludes_demo_urls_and_keeps_deindexing_strategy():
    audit = audit_seo()

    assert audit["sitemap"]["demo_url_count"] == 0
    assert audit["robots"]["retired_routes_crawlable"] is True
    assert audit["robots"]["private_routes_blocked"] is True
    assert audit["static_html"]["homepage_meta_complete"] is True


def test_audio_audit_detects_remote_upload_guards():
    audit = audit_audio()

    assert audit["guards"]["remote_upload_guard_present"] is True
    assert audit["guards"]["voice_pipeline_dry_run_only"] is True


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
        ROOT / "GROWTH_ANALYTICS_READINESS.md",
        ROOT / "APPROVED_TO_PUBLISH.template.md",
    ]

    assert audits["scorecard"]["recommendation"] == "HOLD_FOR_FIXES"
    assert all(path.exists() for path in required)
    assert (ROOT / "LAUNCH_CATALOG_ACTION_PLAN.csv").exists()
    assert (tmp_path / "launch" / "launch_readiness.json").exists()
