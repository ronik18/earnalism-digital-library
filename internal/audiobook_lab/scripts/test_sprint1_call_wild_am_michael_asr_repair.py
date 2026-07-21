#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import unittest


PATH = Path(__file__).with_name("sprint1_call_wild_am_michael_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("call_wild_am_michael_repair", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CallWildAmMichaelRepairTests(unittest.TestCase):
    def test_input_and_repair_contract_are_hash_bound(self):
        evidence, samples, passages = MODULE.CORE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(evidence["scope"]["slug"], MODULE.PROFILE.SLUG)
        self.assertEqual(len(samples), 4)
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            MODULE.repair_fingerprint(),
            "0b990e5c8efbc8fd8eebbe347a95d36922bc00c16f814911136e4a047888b36c",
        )

    def test_only_documented_compound_equivalence_is_applied(self):
        evaluated, applications = MODULE.CORE.apply_equivalences(
            "opening_exposition", "a tidewater dog and yellow medal"
        )
        self.assertIn("tide-water", evaluated)
        self.assertIn("yellow medal", evaluated)
        self.assertEqual(len(applications), 1)

    def test_substantive_residuals_are_forbidden(self):
        joined = " ".join(MODULE.FORBIDDEN_NORMALIZATIONS)
        self.assertIn("metal / medal", joined)
        self.assertIn("feigned / feign", joined)
        self.assertIn("coated / coded", joined)


if __name__ == "__main__":
    unittest.main()
