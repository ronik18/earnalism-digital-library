#!/usr/bin/env python3
"""Focused tests for the distinct Monkey's Paw ``bf_emma`` pilot."""

from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name(
    "sprint1_monkeys_paw_bf_emma_private_audition.py"
)
SPEC = importlib.util.spec_from_file_location("monkeys_paw_bf_emma", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PROFILE = MODULE.PROFILE_BASE
REPO = PROFILE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class MonkeysPawBfEmmaPilotTests(unittest.TestCase):
    def test_profile_is_checksum_distinct_and_british(self) -> None:
        self.assertEqual(MODULE.VOICE, "bf_emma")
        self.assertEqual(
            MODULE.VOICE_SHA256,
            "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701",
        )
        self.assertNotEqual(MODULE.VOICE_SHA256, MODULE.PREVIOUS_VOICE_SHA256)
        self.assertEqual(MODULE.KOKORO_LANG_CODE, "b")
        self.assertIs(MODULE.G2P_BRITISH, True)
        self.assertEqual(MODULE.SPEED, 0.94)
        self.assertEqual(PROFILE.BASE.KOKORO_LANG_CODE, "b")
        self.assertIs(PROFILE.BASE.G2P_BRITISH, True)

    def test_attempt_fingerprint_is_exact_recorded_and_scans_af_evidence(self) -> None:
        _chapters, passages = PROFILE.controlled_source(REPO, PROFILE.SLUG)
        observed = PROFILE.attempt_fingerprint(passages)
        self.assertEqual(observed, MODULE.EXPECTED_ATTEMPT_FINGERPRINT)
        self.assertIn(MODULE.AF_BELLA_EVIDENCE, PROFILE.NO_REPEAT_FILES)
        self.assertIn(MODULE.AF_BELLA_REPAIR_EVIDENCE, PROFILE.NO_REPEAT_FILES)
        recorded = set()
        for path in PROFILE.NO_REPEAT_FILES:
            if path.is_file():
                recorded.update(PROFILE._fingerprints(PROFILE.read_json(path)))
        self.assertIn(observed, recorded)

    def test_british_fallback_free_g2p_is_hash_pinned(self) -> None:
        program = f"""
import importlib.util,json
from pathlib import Path
script=Path({str(SCRIPT)!r})
spec=importlib.util.spec_from_file_location('monkeys_bf_g2p',script)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
profile=module.PROFILE_BASE
_chapters,passages=profile.controlled_source(profile.ROOT,profile.SLUG)
print(json.dumps(profile.validate_g2p(passages),sort_keys=True))
"""
        result = subprocess.run(
            [str(PINNED_PYTHON), "-c", program],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["lang_code"], "b")
        self.assertIs(payload["british"], True)
        self.assertIsNone(payload["fallback"])
        self.assertEqual(
            {
                item["passage_id"]: item["phoneme_sha256"]
                for item in payload["reports"]
            },
            MODULE.PHONEME_HASHES,
        )
        self.assertTrue(
            all(item["unresolved_tokens"] == [] for item in payload["reports"])
        )

    def test_pinned_preflight_rejects_completed_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence.json"
            private = Path(temporary) / "private"
            result = subprocess.run(
                [
                    str(PINNED_PYTHON),
                    str(SCRIPT),
                    "--preflight",
                    "--asset-root",
                    str(REPO),
                    "--private-output-dir",
                    str(private),
                    "--output",
                    str(output),
                ],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
            payload = json.loads(result.stdout or result.stderr)
        self.assertEqual(payload["status"], "BLOCKED_FAIL_CLOSED")
        self.assertIn("attempt fingerprint already exists", payload["error"])
        self.assertFalse(output.exists())
        self.assertFalse(private.exists())

    def test_generic_synthesizer_uses_profile_locale_switches(self) -> None:
        source = inspect.getsource(PROFILE.BASE.synthesize)
        self.assertIn("KOKORO_LANG_CODE", source)
        self.assertIn("G2P_BRITISH", source)
        self.assertNotIn('KPipeline(lang_code="a"', source)

    def test_cli_has_no_paid_upload_or_publication_surface(self) -> None:
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--execute", result.stdout)
        self.assertNotIn("paid-lock", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertNotIn("--publish", result.stdout)


if __name__ == "__main__":
    unittest.main()
