#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import unittest


PATH = Path(__file__).with_name("sprint1_call_wild_am_michael_private_audition.py")
SPEC = importlib.util.spec_from_file_location("call_wild_am_michael_profile", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CallWildAmMichaelProfileTests(unittest.TestCase):
    def test_controlled_source_and_fingerprint_are_exact(self):
        _chapter_path, passages = MODULE.controlled_source(MODULE.BASE.ROOT, MODULE.SLUG)
        self.assertEqual(len(passages), 4)
        self.assertEqual(sum(item["characters"] for item in passages), 4476)
        self.assertEqual(
            MODULE.attempt_fingerprint(passages),
            "19e1586592c3d553ea9e7dcd6d2273e894f05869f760a6f072419f7028de4903",
        )

    def test_g2p_is_fallback_free_and_hash_bound(self):
        _chapter_path, passages = MODULE.controlled_source(MODULE.BASE.ROOT, MODULE.SLUG)
        reports = MODULE.PROFILE_BASE.g2p_preflight(passages)
        self.assertEqual(len(reports), 4)
        self.assertTrue(all(item["fallback_enabled"] is False for item in reports))
        self.assertTrue(all(item["unresolved_tokens"] == [] for item in reports))

    def test_voice_and_private_output_are_pinned(self):
        self.assertEqual(MODULE.VOICE, "am_michael")
        self.assertEqual(
            MODULE.VOICE_SHA256,
            "9a443b79a4b22489a5b0ab7c651a0bcd1a30bef675c28333f06971abbd47bd37",
        )
        self.assertNotIn("frontend/public", str(MODULE.DEFAULT_PRIVATE_DIR))
        self.assertNotIn("frontend/build", str(MODULE.DEFAULT_PRIVATE_DIR))


if __name__ == "__main__":
    unittest.main()
