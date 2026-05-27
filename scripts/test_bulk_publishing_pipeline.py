from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from scripts import bulk_publishing_pipeline as pipeline
from scripts import import_books


class BulkPublishingPipelineTests(unittest.TestCase):
    def test_strip_api_suffix_only_removes_terminal_api(self) -> None:
        self.assertEqual(
            pipeline.strip_api_suffix("https://api.theearnalism.com/api"),
            "https://api.theearnalism.com",
        )
        self.assertEqual(
            pipeline.strip_api_suffix("https://api.theearnalism.com/api/v2"),
            "https://api.theearnalism.com/api/v2",
        )

    def test_publish_stage_builds_publish_approved_command(self) -> None:
        args = Namespace(
            manifest=Path("book_import_manifest.json"),
            api_url="https://api.theearnalism.com",
            frontend_url="https://theearnalism.com",
            audio_output_dir=Path("audio_output"),
            public_audio_dir=Path("frontend/public/audio"),
            stage="publish",
            update_existing_drafts=False,
            all_drafts=False,
            book_slug=["agentic-ai-with-python"],
            skip_audio=True,
            skip_qa=False,
            trust_existing_admin_rights=True,
            env_file=[Path(".secrets/earnalism-import.env")],
        )

        command = pipeline.build_production_command(args, Path("out/production"))

        self.assertIn("--publish-approved", command)
        self.assertNotIn("--upload-drafts", command)
        self.assertIn("--book-slug", command)
        self.assertIn("agentic-ai-with-python", command)
        self.assertIn("--trust-existing-admin-rights", command)

    def test_import_upload_command_uploads_and_updates_drafts(self) -> None:
        args = Namespace(
            manifest=Path("book_import_manifest.json"),
            api_url="https://api.theearnalism.com",
            update_existing_drafts=True,
            ignore_published_duplicates=True,
        )

        command = pipeline.build_import_upload_command(args, Path("out/import"))

        self.assertIn("--upload", command)
        self.assertIn("--api-url", command)
        self.assertIn("https://api.theearnalism.com", command)
        self.assertIn("--update-existing-drafts", command)
        self.assertIn("--ignore-published-duplicates", command)

    def test_importer_accepts_gutenberg_manifest_urls(self) -> None:
        self.assertTrue(import_books.is_gutenberg_type("gutenberg_html"))
        self.assertTrue(import_books.is_gutenberg_url("https://www.gutenberg.org/ebooks/84"))

        candidates = import_books.source_url_candidates(
            "[gutenberg.org](https://www.gutenberg.org/ebooks/84)",
            "gutenberg_html",
        )

        self.assertEqual(candidates[0], "https://www.gutenberg.org/cache/epub/84/pg84.txt")
        self.assertIn("https://www.gutenberg.org/ebooks/84", candidates)

    def test_importer_maps_legacy_book_categories_to_current_shelves(self) -> None:
        warnings: list[str] = []
        meta = import_books.metadata_defaults(
            {"title": "A Story", "author": "A Writer", "category_slug": "children-classics"},
            word_count=1200,
            warnings=warnings,
        )

        self.assertEqual(meta["category_slug"], "young-readers")
        self.assertTrue(any("migrated to 'young-readers'" in warning for warning in warnings))

    def test_importer_maps_manifest_children_category_to_young_readers(self) -> None:
        warnings: list[str] = []
        meta = import_books.metadata_defaults(
            {"title": "A Story", "author": "A Writer", "category_slug": "childrens-literature"},
            word_count=1200,
            warnings=warnings,
        )

        self.assertEqual(meta["category_slug"], "young-readers")

    def test_importer_defaults_unknown_book_categories_to_literary_fiction(self) -> None:
        warnings: list[str] = []
        meta = import_books.metadata_defaults(
            {"title": "A Story", "author": "A Writer", "category_slug": "uncategorized"},
            word_count=1200,
            warnings=warnings,
        )

        self.assertEqual(meta["category_slug"], "literary-fiction")
        self.assertTrue(any("not a current shelf" in warning for warning in warnings))

    def test_go_live_decision_requires_published_books(self) -> None:
        phases = [
            pipeline.PhaseResult(name="publish_go_books", status="passed", data={"published": ["ready-book"]}),
            pipeline.PhaseResult(name="landing_slideshow_sync", status="passed"),
        ]

        self.assertEqual(pipeline.pipeline_decision("go-live", phases), "PUBLISHED_AND_SLIDESHOW_SYNCED")

    def test_slideshow_sync_verifies_published_slugs_and_covers(self) -> None:
        args = Namespace(api_url="https://api.theearnalism.com", frontend_url="https://theearnalism.com")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                pipeline,
                "fetch_json_url",
                return_value=[{"slug": "ready-book", "cover_image_url": "https://example.com/cover.png"}],
            ):
                phase = pipeline.verify_landing_slideshow_phase(args, Path(tmp), ["ready-book"])

            self.assertEqual(phase.status, "passed")
            self.assertTrue((Path(tmp) / "landing_slideshow_sync.json").exists())

    def test_skipped_import_books_fail_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report_dir = base / "20260524T000000Z"
            report_dir.mkdir(parents=True)
            pipeline.write_json(
                report_dir / "dry_run_report.json",
                {
                    "total_books": 1,
                    "passed_validation_count": 0,
                    "skipped_count": 1,
                    "uploaded_books": [],
                    "skipped_books": [{"title": "Blocked", "reasons": ["rights failed"]}],
                },
            )

            phase = pipeline.PhaseResult(name="import_dry_run", status="passed")
            enriched = pipeline.enrich_import_phase(phase, base, allow_skipped=False)

            self.assertEqual(enriched.status, "failed")
            self.assertEqual(enriched.data["skipped_count"], 1)
            self.assertIn("dry_run_report", enriched.artifacts)

    def test_agentic_package_check_accepts_ready_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "final_package"
            reports = package / "reports"
            reports.mkdir(parents=True)
            for suffix in ("md", "docx", "pdf"):
                (package / f"{pipeline.AGENTIC_SLUG_UNDERSCORE}_publication_ready.{suffix}").write_text("ok", encoding="utf-8")
            pipeline.write_json(
                package / "book_metadata.json",
                {
                    "title": pipeline.AGENTIC_TITLE,
                    "is_published": False,
                    "availability": "draft",
                    "audiobook_enabled": False,
                    "generate_audiobook": False,
                },
            )
            (reports / "final_publication_readiness_report.md").write_text(
                "\n".join(
                    [
                        "DOCX opens/generated: success",
                        "DOCX structural open check: success",
                        "PDF generated: success",
                        "PDF structural open check: success",
                        "Audiobook disabled: yes",
                        "Secret-like strings in final package: 0",
                        "Code fences balanced: yes",
                        "Live publishing triggered: no",
                    ]
                ),
                encoding="utf-8",
            )

            phase = pipeline.check_agentic_package(root, root / "run")

            self.assertEqual(phase.status, "passed")
            self.assertTrue((root / "run" / "agentic_ai_readiness_check.json").exists())

    def test_production_phase_collects_nested_upload_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report_dir = base / "production" / "20260524T000000Z"
            upload_dir = report_dir / "import_books" / "20260524T000001Z"
            upload_dir.mkdir(parents=True)
            pipeline.write_json(
                report_dir / "book_production_report.json",
                {
                    "publish_approved": False,
                    "published": [],
                    "results": [{"slug": "ready-book", "title": "Ready", "verdict": "GO", "gates": []}],
                },
            )
            pipeline.write_json(
                upload_dir / "upload_report.json",
                {
                    "uploaded_books": [{"slug": "ready-book", "title": "Ready", "id": "abc"}],
                    "skipped_books": [],
                },
            )

            phase = pipeline.PhaseResult(name="production_gates", status="passed")
            enriched = pipeline.enrich_production_phase(phase, base, allow_skipped_imports=False)

            self.assertEqual(enriched.status, "passed")
            self.assertEqual(enriched.data["uploaded_books"][0]["slug"], "ready-book")
            self.assertIn("import_upload_report", enriched.artifacts)

    def test_latency_risk_holdbacks_do_not_fail_safe_publish_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report_dir = base / "production" / "20260524T000000Z"
            report_dir.mkdir(parents=True)
            pipeline.write_json(
                report_dir / "book_production_report.json",
                {
                    "publish_approved": True,
                    "published": ["safe-book"],
                    "results": [
                        {"slug": "safe-book", "title": "Safe", "verdict": "GO", "gates": []},
                        {
                            "slug": "large-book",
                            "title": "Large",
                            "verdict": "NO-GO",
                            "gates": [
                                {
                                    "name": "latency_risk",
                                    "ok": False,
                                    "detail": "held as draft for latency/timeout risk",
                                }
                            ],
                        },
                    ],
                },
            )

            phase = pipeline.PhaseResult(name="production_gates", status="failed", returncode=2)
            enriched = pipeline.enrich_production_phase(
                phase,
                base,
                allow_skipped_imports=False,
                allow_latency_holdbacks=True,
            )

            self.assertEqual(enriched.status, "passed")
            self.assertEqual(enriched.data["published"], ["safe-book"])
            self.assertEqual(enriched.data["latency_holdbacks"][0]["slug"], "large-book")
            self.assertEqual(enriched.data["no_go_books"], [])


if __name__ == "__main__":
    unittest.main()
