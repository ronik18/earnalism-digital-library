#!/usr/bin/env python3
"""Regression checks for the read-only India launch compliance package."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_india_launch_compliance_package.py"
SPEC = importlib.util.spec_from_file_location("india_launch_package", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


class IndiaLaunchCompliancePackageTests(unittest.TestCase):
    def build(self, output: Path) -> dict:
        result = subprocess.run(
            [
                "python3", str(SCRIPT), "--output-dir", str(output),
                "--candidate-sha", git("rev-parse", "HEAD"),
                "--candidate-tree", git("rev-parse", "HEAD^{tree}"),
                "--production-surface-sha", "314c040f16aaf12931b1b340ae1d222bb87037e6291f1e3752173b98365326d0",
            ],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        self.assertIn('"result": "PASS"', result.stdout)
        return json.loads((output / "india-book-rights-matrix.json").read_text(encoding="utf-8"))

    def test_india_scope_is_four_titles_and_never_releases_a_title(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.build(Path(temporary))
        rows = package["india_book_rights_matrix"]
        self.assertEqual([row["slug"] for row in rows], list(MODULE.PILOT_SLUGS))
        self.assertTrue(all(row["country_scope"] == ["IN"] for row in rows))
        self.assertTrue(all(row["india_title_status"] == "HOLD" for row in rows))
        self.assertTrue(all(not row["india_title_ready"] for row in rows))
        self.assertTrue(all(row["india_title_predicate"]["result"] == "HOLD" for row in rows))
        self.assertEqual(package["scope"]["audio"], "AUDIO_DISABLED_NOT_IN_LAUNCH_SCOPE")
        self.assertEqual(package["scope"]["customer_ready"], "NOT_DECLARED")

    def test_copyright_and_integrity_are_independent_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.build(Path(temporary))
        rows = {row["slug"]: row for row in package["india_book_rights_matrix"]}
        for row in rows.values():
            self.assertEqual(row["india_copyright_proof"]["status"], "INDIA_COPYRIGHT_EVIDENCE_COMPLETE")
            self.assertEqual(row["india_copyright_proof"]["statutory_category"], "ORDINARY_PUBLISHED_LITERARY_WORK_SECTION_22")
            self.assertRegex(row["india_copyright_proof"]["author_death_year"].__str__(), r"^\d{4}$")
            self.assertRegex(row["textual_integrity_proof"]["earnalism_canonical_text_hash"], r"^[0-9a-f]{64}$")
            self.assertGreater(len(row["textual_integrity_proof"]["canonical_chapter_hashes"]), 0)
            self.assertNotEqual(row["textual_integrity_proof"]["source_identifier"], "NOT_RECORDED")
            self.assertEqual(row["cover_provenance"]["status"], "OWNER_DECLARATION_PENDING_SIGNATURE")
            self.assertTrue(row["textual_integrity_proof"]["current_raw_source_path"].endswith("raw/source.txt"))
        self.assertEqual(rows["a-ghost-story"]["textual_integrity_proof"]["status"], "TEXT_VERIFIED")
        self.assertEqual(rows["the-tell-tale-heart"]["textual_integrity_proof"]["status"], "TEXT_VERIFIED")
        self.assertTrue(rows["the-tell-tale-heart"]["textual_integrity_proof"]["source_to_canonical_comparison"]["all_chapters_found_in_order"])
        self.assertIn("aggregate publication hash", rows["the-tell-tale-heart"]["textual_integrity_proof"]["material_differences"])
        self.assertEqual(rows["radharani"]["textual_integrity_proof"]["status"], "TEXT_VERIFIED")
        self.assertEqual(rows["radharani"]["translation_and_editorial_material"]["status"], "SOURCE_LAYER_PROVENANCE_DOCUMENTED")
        self.assertEqual(
            rows["radharani"]["translation_and_editorial_material"]["source_layer_provenance"]["verification_result"],
            "TEXT_VERIFIED",
        )
        self.assertEqual(rows["yugalanguriya"]["textual_integrity_proof"]["status"], "TEXT_REVIEW_REQUIRED")
        observations = rows["yugalanguriya"]["textual_integrity_proof"]["facsimile_observation_comparison"]
        self.assertEqual(observations["resolved_observation_count"], 9)
        self.assertEqual(observations["unresolved_observation_count"], 2)
        self.assertEqual(
            observations["unresolved_locations"],
            ["chapter-001 opening", "chapter-004 opening"],
        )
        self.assertEqual(len(package["editorial_correction_ledger"]["unresolved_source_discrepancies"]), 2)
        self.assertEqual(rows["a-ghost-story"]["audio_scope"]["current_launch_status"], "AUDIO_DISABLED_NOT_IN_LAUNCH_SCOPE")
        self.assertEqual(rows["a-ghost-story"]["audio_scope"]["voice_type"], "PROVIDER_AUTHORIZED_SYNTHETIC_VOICE")
        self.assertIn("listening-QA", rows["the-tell-tale-heart"]["audio_scope"]["candidate_status_if_audio_scope_changes"])

    def test_website_matrix_identifies_actual_public_page_and_fact_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.build(Path(temporary))
        matrix = {row["area"]: row for row in package["india_website_legal_matrix"]}
        self.assertEqual(matrix["privacy and data inventory"]["status"], "ACTION_REQUIRED")
        self.assertIn("launch date is not recorded", matrix["privacy and data inventory"]["in_force_on_launch_date"])
        self.assertEqual(matrix["legal pages and contact/grievance information"]["status"], "ACTION_REQUIRED")
        self.assertTrue(matrix["consumer and e-commerce"]["launch_blocker"])
        self.assertFalse(package["conclusion"]["india_launch_legal_checks_complete"])

    def test_unsigned_declaration_lists_pilot_assets_without_claiming_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            self.build(output)
            declaration = (output / "cover-artwork-declaration.md").read_text(encoding="utf-8")
        self.assertIn("UNSIGNED FACTUAL DECLARATION TEMPLATE", declaration)
        self.assertIn("Signature/Confirmation: ____________________________", declaration)
        self.assertIn("were graphically designed by me", declaration)
        self.assertIn("PRODUCT_OWNER (owner-stated; signature pending)", declaration)
        self.assertIn("OWNER_CONFIRMATION_REQUIRED", declaration)
        self.assertNotIn("FIRST_PARTY_COVER_PROVENANCE_CONFIRMED", declaration)
        self.assertEqual(declaration.count("| A Ghost Story — front |"), 1)
        self.assertNotIn("| Dracula — front |", declaration)

    def test_internal_website_drafts_are_generated_but_not_public_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            self.build(output)
            drafts = (output / "unpublished-india-website-legal-drafts.md").read_text(encoding="utf-8")
        self.assertIn("UNPUBLISHED_DO_NOT_REGISTER_ROUTE", drafts)
        self.assertIn("RECEIVED` → `UNDER_REVIEW`", drafts)
        self.assertIn("[OWNER INPUT REQUIRED: operator legal name]", drafts)
        self.assertNotIn("/privacy", (ROOT / "frontend" / "src" / "App.js").read_text(encoding="utf-8").lower())

    def test_decision_record_is_hash_bound_and_keeps_human_decision_fields_blank(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            self.build(output)
            record = json.loads((output / "india-release-decision-record-template.json").read_text(encoding="utf-8"))
            package_hash = MODULE.digest(output / "india-book-rights-matrix.json")
        self.assertEqual(record["status"], "UNSIGNED_TEMPLATE_ONLY")
        self.assertEqual(record["evidence_package"]["sha256"], package_hash)
        self.assertEqual(len(record["records"]), 4)
        self.assertTrue(all(item["DECISION"] is None for item in record["records"]))
        self.assertTrue(all(item["DECIDED_BY"] is None for item in record["records"]))


if __name__ == "__main__":
    unittest.main()
