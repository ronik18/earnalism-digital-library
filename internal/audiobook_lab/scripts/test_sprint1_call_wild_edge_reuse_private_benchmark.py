#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import unittest


PATH = Path(__file__).with_name("sprint1_call_wild_edge_reuse_private_benchmark.py")
SPEC = importlib.util.spec_from_file_location("call_wild_edge_benchmark", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CallWildEdgeBenchmarkTests(unittest.TestCase):
    def test_canonical_sidecar_binding_is_complete(self):
        tokens, canonical = MODULE.source_and_metadata()
        _audio, _sidecar, alignment = MODULE.validate_candidate(MODULE.DEFAULT_BUNDLE, tokens)
        self.assertEqual(canonical["source_sha256"], MODULE.SOURCE_SHA256)
        self.assertEqual(alignment["coverage"], 1.0)
        self.assertEqual(alignment["sidecar_word_count"], 32374)
        self.assertEqual(len(alignment["approved_abbreviation_expansions"]), 3)

    def test_benchmark_fingerprint_and_publication_state_are_closed(self):
        self.assertEqual(
            MODULE.BENCHMARK_FINGERPRINT,
            "5cc0e9048d63631aa43dd21819334b44c62a495bbb27823bdbc519549352ce76",
        )
        self.assertNotIn("frontend/public", str(MODULE.DEFAULT_PRIVATE_DIR))
        self.assertNotIn("frontend/build", str(MODULE.DEFAULT_PRIVATE_DIR))

    def test_substitution_cannot_pass_ordered_gate(self):
        metrics = MODULE.ordered_metrics("yellow metal", "yellow medal")
        self.assertFalse(metrics["asr_gate_pass"])
        self.assertLess(metrics["score"], 10.0)


if __name__ == "__main__":
    unittest.main()
