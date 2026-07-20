#!/usr/bin/env python3
"""Focused tests for the checksum-distinct Cop ``af_sarah`` adapter."""

from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_cop_af_sarah_private_audition.py")
SPEC = importlib.util.spec_from_file_location("cop_af_sarah", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = MODULE.BASE
REPO = BASE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class CopAfSarahPilotTests(unittest.TestCase):
    def test_profile_is_checksum_distinct_exactly_fingerprinted_and_recorded(self) -> None:
        _chapter, passages = BASE.controlled_source(REPO, BASE.ALLOWED_SLUG)
        self.assertEqual(MODULE.VOICE, "af_sarah")
        self.assertNotEqual(MODULE.VOICE_SHA256, MODULE.PREVIOUS_VOICE_SHA256)
        self.assertEqual(
            BASE.attempt_fingerprint(passages), MODULE.EXPECTED_ATTEMPT_FINGERPRINT
        )
        recorded = set()
        for path in BASE.NO_REPEAT_FILES:
            if path.is_file():
                recorded.update(BASE._fingerprints(BASE.read_json(path)))
        self.assertIn(MODULE.EXPECTED_ATTEMPT_FINGERPRINT, recorded)
        self.assertIn(MODULE.AF_BELLA_EVIDENCE, BASE.NO_REPEAT_FILES)
        self.assertIn(MODULE.AF_BELLA_LISTENING_EVIDENCE, BASE.NO_REPEAT_FILES)

    def test_canonical_source_rights_and_current_covers_pass(self) -> None:
        chapter, passages = BASE.controlled_source(REPO, BASE.ALLOWED_SLUG)
        self.assertTrue(chapter.is_file())
        self.assertEqual(len(passages), 4)
        book = BASE.read_json(
            REPO
            / "data/controlled_publications/the-cop-and-the-anthem/public_book.json"
        )
        self.assertEqual(book["title"], "The Cop and the Anthem")
        self.assertEqual(book["author"], "O. Henry")
        self.assertTrue(book.get("front_cover_url") or book.get("cover_url"))
        self.assertTrue(book.get("back_cover_url"))
        self.assertFalse(bool(book.get("audio_enabled")))

    def test_pinned_fallback_free_g2p_hashes(self) -> None:
        program = f"""
import importlib.util,json
from pathlib import Path
p=Path({str(SCRIPT)!r})
s=importlib.util.spec_from_file_location('cop_sarah_g2p',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
_chapter,passages=m.BASE.controlled_source(m.BASE.ROOT,m.BASE.ALLOWED_SLUG)
print(json.dumps({{x['passage_id']:x['phoneme_sha256'] for x in m.BASE.validate_g2p_passages(passages)}},sort_keys=True))
"""
        result = subprocess.run(
            [str(PINNED_PYTHON), "-c", program],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(json.loads(result.stdout), MODULE.EXPECTED_PHONEME_HASHES)

    def test_pinned_preflight_rejects_completed_fingerprint_without_new_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "preflight.json"
            private = root / "private"
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
            payload = json.loads(result.stderr or result.stdout)
        self.assertEqual(payload["status"], "BLOCKED_FAIL_CLOSED")
        self.assertIn("attempt fingerprint already exists", payload["error"])
        self.assertFalse(output.exists())
        self.assertFalse(private.exists())

    def test_reverify_is_bound_to_current_wavs_and_one_safe_equivalence(self) -> None:
        evidence = BASE.read_json(MODULE.DEFAULT_EVIDENCE)
        self.assertEqual(
            {item["passage_id"]: item["audio_sha256"] for item in evidence["samples"]},
            MODULE.EXPECTED_EXISTING_AUDIO_HASHES,
        )
        evaluated, applications = BASE.apply_source_equivalences(
            "waiter_dialogue", "on the callus pavement the waiters pitched him"
        )
        self.assertEqual(
            evaluated, "on the callous pavement the waiters pitched him"
        )
        self.assertEqual(len(applications), 1)
        self.assertNotIn(r"\bpitch\b", str(MODULE.SOURCE_EQUIVALENCE_POLICY))
        self.assertNotIn(r"\buse\b", str(MODULE.SOURCE_EQUIVALENCE_POLICY))

    def test_source_has_no_publication_or_browser_speech_fallback(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn("speechSynthesis", source)
        self.assertNotIn('"/audio/', source)
        self.assertNotIn("--publish", source)
        self.assertNotIn("--upload", source)


if __name__ == "__main__":
    unittest.main()
