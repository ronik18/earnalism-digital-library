#!/usr/bin/env python3
"""Regression checks for the read-only copyright evidence package."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_copyright_rights_review_package.py"
SPEC = importlib.util.spec_from_file_location("copyright_review", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

HEAD = "2c70f35ad2810da19dc36017fc0ae834899cb4c0"
TREE = "5397b78b4475bdef5a22f52ff1125a4fe4e77dca"
SURFACE = "314c040f16aaf12931b1b340ae1d222bb87037e6291f1e3752173b98365326d0"


class CopyrightRightsReviewPackageTests(unittest.TestCase):
    def build(self, output: Path) -> dict:
        result = subprocess.run(
            ["python3", str(SCRIPT), "--output-dir", str(output), "--candidate-sha", HEAD, "--candidate-tree", TREE, "--production-surface-sha", SURFACE],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        self.assertIn('"result": "PASS"', result.stdout)
        return json.loads((output / "copyright-rights-inventory.json").read_text(encoding="utf-8"))

    def test_inventory_covers_every_controlled_publication_and_reports_current_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.build(Path(temporary))
        expected = sorted(
            {path.name for path in (ROOT / "data" / "controlled_publications").iterdir() if path.is_dir()}
            | {"yugalanguriya"}
        )
        self.assertEqual([item["slug"] for item in package["titles"]], expected)
        self.assertEqual(package["inventory_summary"]["title_count"], len(expected))
        self.assertEqual(package["inventory_summary"]["accepted_rights_record_count"], 6)
        self.assertEqual(package["inventory_summary"]["live_accepted_rights_record_count"], 3)
        self.assertEqual(package["inventory_summary"]["rights_accepted_unexposed_count"], 3)
        self.assertEqual(package["conclusion"], "INDIA_RELEASE_EVIDENCE_COMPLETE_FOR_CONTROLLED_ALLOWLIST")
        accepted = {title["slug"] for title in package["titles"] if title["title_release_status"] == "ACCEPTED_FOR_CONTROLLED_RELEASE"}
        self.assertEqual(accepted, {"a-ghost-story", "the-tell-tale-heart", "radharani"})
        rights_accepted_unexposed = {title["slug"] for title in package["titles"] if title["title_release_status"] == "RIGHTS_ACCEPTED_UNEXPOSED"}
        self.assertEqual(rights_accepted_unexposed, {"a-white-heron", "the-gift-of-the-magi", "the-canterville-ghost"})

    def test_component_schema_and_pilot_scope_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.build(Path(temporary))
        pilot = {title["slug"]: title for title in package["titles"] if title["slug"] in MODULE.PILOT_SLUGS}
        self.assertEqual(set(pilot), set(MODULE.PILOT_SLUGS))
        for title in pilot.values():
            expected_countries = ["IN"] if title["slug"] != "yugalanguriya" else ["IN", "US", "GB", "CA", "AU", "DE", "AE", "BD", "SG", "SA"]
            self.assertEqual(title["jurisdictions_assessed"], expected_countries)
            expected_status = "HOLD" if title["slug"] == "yugalanguriya" else "ACCEPTED_FOR_CONTROLLED_RELEASE"
            self.assertEqual(title["title_release_status"], expected_status)
            for row in title["components"]:
                self.assertEqual(tuple(row), MODULE.COMPONENT_FIELDS)
                self.assertNotEqual(row["decision"], "ACCEPTED")
        yugal = pilot["yugalanguriya"]
        front = next(row for row in yugal["components"] if row["asset_component"] == "front_cover_artwork")
        self.assertEqual(front["review_status"], "HOLD")
        audio = next(row for row in pilot["a-ghost-story"]["components"] if row["asset_component"] == "audio_narration_or_sound_recording")
        self.assertEqual(audio["review_status"], "HOLD")

    def test_package_binds_the_requested_candidate_and_current_hold_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            package = self.build(output)
            packet = (output / "qualified-review-packet.md").read_text(encoding="utf-8")
        self.assertEqual(package["generated_from"]["repository_head"], HEAD)
        self.assertEqual(package["generated_from"]["repository_tree"], TREE)
        self.assertEqual(package["generated_from"]["production_surface_sha256"], SURFACE)
        self.assertEqual(package["technical_fail_closed_evidence"]["result"], "PASS")
        self.assertTrue(package["technical_fail_closed_evidence"]["public_reader_exposure_enabled"])
        self.assertFalse(package["technical_fail_closed_evidence"]["public_audio_exposure_enabled"])
        self.assertIn("INDIA_RELEASE_EVIDENCE_COMPLETE_FOR_CONTROLLED_ALLOWLIST", packet)
        self.assertIn("Chapter V", packet)

    def test_malformed_chapter_asset_metadata_never_becomes_positive_visual_evidence(self) -> None:
        self.assertFalse(MODULE.chapter_declares_visual_asset({"image_count": "1"}))
        self.assertFalse(MODULE.chapter_declares_visual_asset({"image_count": True}))
        self.assertFalse(MODULE.chapter_declares_visual_asset({"image_count": -1}))
        self.assertTrue(MODULE.chapter_declares_visual_asset({"image_count": 1}))


if __name__ == "__main__":
    unittest.main()
