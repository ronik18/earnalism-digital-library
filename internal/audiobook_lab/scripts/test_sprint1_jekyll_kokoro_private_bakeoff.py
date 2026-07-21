#!/usr/bin/env python3
"""Focused tests for the private Jekyll two-voice Kokoro bakeoff."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("sprint1_jekyll_kokoro_private_bakeoff.py")
SPEC = importlib.util.spec_from_file_location("jekyll_bakeoff", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class JekyllKokoroPrivateBakeoffTests(unittest.TestCase):
    def test_four_passages_bind_complete_canonical_source(self) -> None:
        source, passages = MODULE.controlled_source(MODULE.BASE.ROOT, MODULE.SLUG)
        self.assertTrue(source.is_dir())
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            [item["text_sha256"] for item in passages],
            [item["sha256"] for item in MODULE.PASSAGE_SPECS],
        )
        self.assertEqual(
            sum(item["characters"] for item in passages),
            MODULE.EXPECTED_PASSAGE_CHARACTERS,
        )

    def test_voice_fingerprints_are_distinct_and_pinned(self) -> None:
        _source, passages = MODULE.controlled_source(MODULE.BASE.ROOT, MODULE.SLUG)
        observed: dict[str, str] = {}
        for voice in sorted(MODULE.VOICE_PROFILES):
            MODULE.configure_base(voice)
            observed[voice] = MODULE.BASE.attempt_fingerprint(passages)
            self.assertEqual(
                observed[voice],
                MODULE.VOICE_PROFILES[voice]["expected_attempt_fingerprint"],
            )
        self.assertEqual(len(set(observed.values())), 2)

    @unittest.skipUnless(PINNED_PYTHON.is_file(), "pinned audio runtime missing")
    def test_both_g2p_profiles_are_fallback_free(self) -> None:
        command = "\n".join(
            (
                "import importlib.util",
                "from pathlib import Path",
                f"p=Path({str(SCRIPT)!r})",
                "s=importlib.util.spec_from_file_location('jk',p)",
                "m=importlib.util.module_from_spec(s)",
                "s.loader.exec_module(m)",
                "_, passages=m.controlled_source(m.BASE.ROOT,m.SLUG)",
                "for voice in sorted(m.VOICE_PROFILES):",
                "    m.configure_base(voice)",
                "    reports=m.g2p_preflight(passages)",
                "    assert len(reports)==4",
                "    assert all(not x['unresolved_tokens'] for x in reports)",
                "    assert all(not x['fallback_enabled'] for x in reports)",
            )
        )
        result = subprocess.run(
            [str(PINNED_PYTHON), "-c", command],
            cwd=MODULE.BASE.ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cover_gap_and_public_audio_remain_fail_closed(self) -> None:
        root = MODULE.BASE.ROOT / "data/controlled_publications" / MODULE.SLUG
        book = MODULE.BASE.read_json(root / "public_book.json")
        approval = MODULE.BASE.read_json(root / "approval_evidence.json")
        self.assertIsNone(book.get("cover_url"))
        self.assertIsNone(book.get("back_cover_url"))
        self.assertIs(approval["audiobook_use_approved"], True)
        self.assertEqual(approval["audio_public_release"], "PUBLIC_AUDIO_RELEASE_BLOCKED")
        self.assertIs(book["audio_enabled"], False)
        self.assertIs(book["audiobook_enabled"], False)

    def test_private_path_is_enforced_for_each_voice(self) -> None:
        for voice in MODULE.VOICE_PROFILES:
            MODULE.configure_base(voice)
            self.assertEqual(MODULE.BASE.VOICE, voice)
            self.assertEqual(
                MODULE.BASE.VOICE_SHA256,
                MODULE.VOICE_PROFILES[voice]["voice_sha256"],
            )
        with self.assertRaises(MODULE.BASE.KokoroTitlePilotError):
            MODULE.BASE.assert_private_audio_path(
                Path(tempfile.gettempdir()) / "frontend/public/jekyll.wav"
            )

    @unittest.skipUnless(PINNED_PYTHON.is_file(), "pinned audio runtime missing")
    def test_cli_has_no_listening_upload_or_publication_surface(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn("--upload", source)
        self.assertNotIn("--publish", source)
        self.assertNotIn("speechSynthesis", source)
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=MODULE.BASE.ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--voice", result.stdout)
        self.assertIn("--preflight", result.stdout)
        self.assertIn("--execute", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertNotIn("--publish", result.stdout)


if __name__ == "__main__":
    unittest.main()
