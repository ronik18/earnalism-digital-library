from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_public_pages_reference_contract import validate


ROOT = Path(__file__).resolve().parents[1]


class PublicPagesReferenceContractTests(unittest.TestCase):
    def test_repository_contract_is_valid(self) -> None:
        result = validate(ROOT)
        self.assertTrue(result["valid"], result["errors"])

    def test_mobile_cannot_claim_full_viewport_pixel_certification(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            for relative in [
                "docs/design-references/public-pages-reference-capability.json",
                "docs/design-references/responsive-reference-board.png",
                "docs/design-references/commerce-desktop.png",
                "uat/contracts/public-pages-visual-contract-v2.json",
            ]:
                destination = temp / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / relative).read_bytes())
            capability_path = temp / "docs/design-references/public-pages-reference-capability.json"
            capability = json.loads(capability_path.read_text())
            capability["states"]["home-mobile"]["full_mobile_pixel_match_status"] = "PASSED"
            capability_path.write_text(json.dumps(capability))
            result = validate(temp)
            self.assertFalse(result["valid"])
            self.assertIn("home-mobile: incomplete mobile panel must not claim full-viewport pixel certification", result["errors"])

    def test_unsafe_mask_expansion_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            for relative in [
                "docs/design-references/public-pages-reference-capability.json",
                "docs/design-references/responsive-reference-board.png",
                "docs/design-references/commerce-desktop.png",
                "uat/contracts/public-pages-visual-contract-v2.json",
            ]:
                destination = temp / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / relative).read_bytes())
            contract_path = temp / "uat/contracts/public-pages-visual-contract-v2.json"
            contract = json.loads(contract_path.read_text())
            contract["reference_region_fidelity_gate"]["dynamic_masks"].append("hero")
            contract_path.write_text(json.dumps(contract))
            result = validate(temp)
            self.assertFalse(result["valid"])
            self.assertIn("dynamic mask categories differ from the approved set", result["errors"])
