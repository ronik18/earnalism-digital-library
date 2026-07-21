#!/usr/bin/env python3
"""Focused tests for The Time Machine ``bm_george`` private profile."""

from __future__ import annotations

import importlib.util
import io
import inspect
from contextlib import redirect_stdout
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name(
    "sprint1_time_machine_bm_george_private_audition.py"
)
SPEC = importlib.util.spec_from_file_location("time_machine_profile", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class TimeMachineBmGeorgeTests(unittest.TestCase):
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

    def test_attempt_fingerprint_is_pinned_and_closed_after_execution(self) -> None:
        _source, passages = MODULE.controlled_source(MODULE.BASE.ROOT, MODULE.SLUG)
        fingerprint = MODULE.BASE.attempt_fingerprint(passages)
        self.assertEqual(fingerprint, MODULE.EXPECTED_ATTEMPT_FINGERPRINT)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                MODULE.BASE.KokoroTitlePilotError,
                "attempt fingerprint already exists",
            ):
                MODULE.BASE.ensure_not_repeated(
                    fingerprint, Path(directory) / "new-evidence.json"
                )

    @unittest.skipUnless(PINNED_PYTHON.is_file(), "pinned audio runtime missing")
    def test_pinned_runtime_g2p_is_british_and_fallback_free(self) -> None:
        command = (
            "import importlib.util; from pathlib import Path; "
            f"p=Path({str(SCRIPT)!r}); "
            "s=importlib.util.spec_from_file_location('tm',p); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "_, passages=m.controlled_source(m.BASE.ROOT,m.SLUG); "
            "reports=m.g2p_preflight(passages); "
            "assert len(reports)==4; "
            "assert all(not x['unresolved_tokens'] for x in reports); "
            "assert all(not x['fallback_enabled'] for x in reports)"
        )
        result = subprocess.run(
            [str(PINNED_PYTHON), "-c", command],
            cwd=MODULE.BASE.ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rights_create_permission_does_not_approve_public_audio(self) -> None:
        root = MODULE.BASE.ROOT / "data/controlled_publications" / MODULE.SLUG
        book = MODULE.BASE.read_json(root / "public_book.json")
        approval = MODULE.BASE.read_json(root / "approval_evidence.json")
        self.assertIs(approval["audiobook_use_approved"], True)
        self.assertEqual(
            approval["audio_public_release"], "PUBLIC_AUDIO_RELEASE_NOT_APPROVED"
        )
        self.assertIs(approval["audiobook_enabled"], False)
        self.assertIs(book["audio_enabled"], False)
        self.assertIs(book["audiobook_enabled"], False)

    def test_voice_and_private_path_are_fail_closed(self) -> None:
        self.assertEqual(MODULE.BASE.VOICE, "bm_george")
        self.assertEqual(MODULE.BASE.VOICE_SHA256, MODULE.VOICE_SHA256)
        self.assertEqual(MODULE.BASE.KOKORO_LANG_CODE, "b")
        self.assertIs(MODULE.BASE.G2P_BRITISH, True)
        with self.assertRaises(MODULE.BASE.KokoroTitlePilotError):
            MODULE.BASE.assert_private_audio_path(
                Path(tempfile.gettempdir()) / "frontend/public/time-machine.wav"
            )

    def test_asr_reverify_is_disabled_until_audio_hashes_are_pinned(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = MODULE.main(["--asr-reverify-existing"])
        self.assertEqual(code, 2)
        self.assertIn("disabled until", output.getvalue())

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
        self.assertIn("--preflight", result.stdout)
        self.assertIn("--execute", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertNotIn("--publish", result.stdout)


if __name__ == "__main__":
    unittest.main()
