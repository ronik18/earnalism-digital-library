from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.first_batch_dry_run import first_batch_products, first_batch_report_json, run_first_batch_dry_run
from scripts.first_batch_dry_run import write_reports


def test_first_batch_contains_exactly_10_products():
    report = run_first_batch_dry_run({"dry_run": True})
    data = first_batch_report_json(report)

    assert data["dry_run"] is True
    assert data["summary"]["selected"] == 10
    assert [product["product_title"] for product in data["products"]] == [
        "Anandamath Visual Study Companion",
        "Devdas Study Edition",
        "Abol Tabol Illustrated Reader",
        "Sultana's Dream Feminist Sci-Fi Edition",
        "Sherlock Holmes Logic Workbook",
        "Dracula Gothic Fiction Visual Guide",
        "Frankenstein Science & Ethics Guide",
        "Tagore Short Stories for Young Readers",
        "Calculus Made Easy Visual Guide",
        "Chander Pahar Adventure Companion",
    ]


def test_each_product_has_required_dry_run_artifacts():
    report = run_first_batch_dry_run({"dry_run": True})
    data = first_batch_report_json(report)
    required_keys = {
        "rights_report",
        "demand_score",
        "source_metadata",
        "ingestion_status",
        "edition_draft",
        "study_guide_draft",
        "visual_explainer_draft",
        "quiz",
        "reading_challenge",
        "seo_draft",
        "audiobook_preview_script",
        "audio_preview",
        "qa_report",
        "publication_readiness_score",
        "publication_readiness_status",
    }

    for product in data["products"]:
        assert required_keys.issubset(product)
        assert product["dry_run"] is True
        assert product["rights_report"]["public_publish_allowed"] is False
        assert product["edition_draft"]["public"] is False
        assert product["seo_draft"]["public"] is False


def test_ready_items_are_marked_publication_draft_only():
    report = run_first_batch_dry_run({"dry_run": True})
    data = first_batch_report_json(report)
    ready = [product for product in data["products"] if product["publication_readiness_status"] == "READY_FOR_PUBLICATION_DRAFT"]

    assert ready
    assert all(product["rights_report"]["rights_tier"] == "A" for product in ready)
    assert data["summary"]["public_publish_actions"] == 0
    assert all(product["publication_readiness_status"] != "PUBLISHED" for product in data["products"])


def test_tier_b_items_are_region_gated_not_global_ready():
    report = run_first_batch_dry_run({"dry_run": True})
    tier_b = [product for product in first_batch_report_json(report)["products"] if product["rights_report"]["rights_tier"] == "B"]

    assert tier_b
    assert all(product["rights_report"]["rights_status"] == "REGION_GATED_APPROVED" for product in tier_b)
    assert all(product["publication_readiness_status"] == "REGION_GATED_DRAFT_REVIEW" for product in tier_b)


def test_unsafe_items_are_quarantined():
    products = first_batch_products()
    products[0]["rights_metadata"] = {
        "rights_tier": "C",
        "verification_status": "blocked",
        "publication_region": "global",
        "blocked_reason": "Unsafe modern edition rights.",
    }
    report = run_first_batch_dry_run({"dry_run": True, "products": products})
    first = first_batch_report_json(report)["products"][0]

    assert first["publication_readiness_status"] == "QUARANTINED_DRY_RUN"
    assert first["blocked_reasons"]
    assert first["qa_report"]["qa_status"] == "BLOCKED"


def test_audio_preview_is_skipped_without_provider():
    report = run_first_batch_dry_run({"dry_run": True})
    statuses = {product["audio_preview"]["status"] for product in first_batch_report_json(report)["products"]}

    assert "SKIPPED_PROVIDER_NOT_CONFIGURED" in statuses
    assert all(status != "GENERATED" for status in statuses)


def test_audio_preview_plan_requires_provider_and_budget():
    report = run_first_batch_dry_run({"dry_run": True, "audio_provider_configured": True, "audio_preview_budget": 2})
    statuses = [product["audio_preview"]["status"] for product in first_batch_report_json(report)["products"]]

    assert "PREVIEW_PLAN_READY_DRY_RUN" in statuses
    assert "SKIPPED_BUDGET_EXCEEDED" in statuses
    assert "GENERATED" not in statuses


def test_non_dry_run_and_publish_are_blocked():
    non_dry_run = run_first_batch_dry_run({"dry_run": False})
    publish = run_first_batch_dry_run({"dry_run": True, "publish": True})

    assert non_dry_run.status == "BLOCKED_NON_DRY_RUN"
    assert non_dry_run.products == []
    assert publish.status == "BLOCKED_PUBLICATION_DISABLED"
    assert publish.products == []


def test_reports_write_json_csv_markdown_and_root_report(tmp_path: Path):
    report = run_first_batch_dry_run({"dry_run": True})
    json_path, csv_path, markdown_path, root_markdown_path = write_reports(report, tmp_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    csv_text = csv_path.read_text(encoding="utf-8")
    markdown = markdown_path.read_text(encoding="utf-8")
    root_markdown = root_markdown_path.read_text(encoding="utf-8")

    assert data["summary"]["selected"] == 10
    assert "publication_readiness_status" in csv_text
    assert "First Batch Dry-Run Report" in markdown
    assert markdown == root_markdown


def test_cli_sample_generates_reports(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/first_batch_dry_run.py",
            "--sample",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "First batch dry-run complete" in completed.stdout
    assert (tmp_path / "first_batch_dry_run_report.json").exists()
    assert (tmp_path / "first_batch_dry_run_report.csv").exists()
    assert (tmp_path / "first_batch_dry_run_report.md").exists()


def test_cli_rejects_publish_options(tmp_path: Path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/first_batch_dry_run.py",
            "--sample",
            "--publish",
            "--output-dir",
            str(tmp_path),
        ],
        text=True,
        capture_output=True,
    )

    assert completed.returncode != 0
    assert "dry-run only" in completed.stderr
