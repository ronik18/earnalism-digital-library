#!/usr/bin/env python3
"""Focused tests for the distinct Secret Garden bf_emma profile."""

from __future__ import annotations

import importlib.util
import inspect
import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name(
    "sprint1_secret_garden_bf_emma_private_audition.py"
)
SPEC = importlib.util.spec_from_file_location("secret_garden_bf_emma", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class SecretGardenBfEmmaTests(unittest.TestCase):
    def test_voice_and_g2p_are_materially_distinct_and_pinned(self) -> None:
        self.assertEqual(MODULE.VOICE, "bf_emma")
        self.assertNotEqual(MODULE.VOICE_SHA256, MODULE.PREVIOUS_VOICE_SHA256)
        self.assertEqual(MODULE.PROFILE_BASE.BASE.KOKORO_LANG_CODE, "b")
        self.assertIs(MODULE.PROFILE_BASE.BASE.G2P_BRITISH, True)
        self.assertEqual(MODULE.SPEED, 0.94)
        self.assertEqual(MODULE.PROFILE_BASE.BASE.VOICE_SHA256, MODULE.VOICE_SHA256)

    def test_attempt_fingerprint_is_distinct_pinned_and_recorded_closed(self) -> None:
        _source, passages = MODULE.PROFILE_BASE.controlled_source(
            MODULE.PROFILE_BASE.BASE.ROOT, MODULE.PROFILE_BASE.SLUG
        )
        fingerprint = MODULE.PROFILE_BASE.BASE.attempt_fingerprint(passages)
        self.assertEqual(fingerprint, MODULE.EXPECTED_ATTEMPT_FINGERPRINT)
        self.assertNotEqual(fingerprint, MODULE.AF_BELLA_ATTEMPT_FINGERPRINT)
        with self.assertRaisesRegex(
            MODULE.PROFILE_BASE.BASE.KokoroTitlePilotError,
            "attempt fingerprint already exists",
        ):
            MODULE.PROFILE_BASE.BASE.ensure_not_repeated(fingerprint, MODULE.DEFAULT_OUTPUT)

    @unittest.skipUnless(PINNED_PYTHON.is_file(), "pinned audio runtime missing")
    def test_british_g2p_is_fallback_free_and_hash_bound(self) -> None:
        command = (
            "import importlib.util; from pathlib import Path; "
            f"p=Path({str(SCRIPT)!r}); "
            "s=importlib.util.spec_from_file_location('sgb',p); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "_,ps=m.PROFILE_BASE.controlled_source(m.PROFILE_BASE.BASE.ROOT,m.PROFILE_BASE.SLUG); "
            "reports=m.PROFILE_BASE.g2p_preflight(ps); "
            "assert {x['passage_id']:x['phoneme_sha256'] for x in reports}==m.EXPECTED_PHONEME_HASHES; "
            "assert all(not x['unresolved_tokens'] for x in reports)"
        )
        result = subprocess.run(
            [str(PINNED_PYTHON), "-c", command],
            cwd=MODULE.PROFILE_BASE.BASE.ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(PINNED_PYTHON.is_file(), "pinned audio runtime missing")
    def test_cli_has_no_listening_upload_or_publication_surface(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn("speechSynthesis", source)
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=MODULE.PROFILE_BASE.BASE.ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--preflight", result.stdout)
        self.assertIn("--execute", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertNotIn("--publish", result.stdout)


if __name__ == "__main__":
    unittest.main()
