#!/usr/bin/env python3
"""Focused tests for the private Secret Garden af_bella profile."""

from __future__ import annotations

import importlib.util
import io
import inspect
import json
from contextlib import redirect_stdout
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name(
    "sprint1_secret_garden_af_bella_private_audition.py"
)
SPEC = importlib.util.spec_from_file_location("secret_garden_profile", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class SecretGardenAfBellaTests(unittest.TestCase):
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

    def test_attempt_fingerprint_is_pinned_and_recorded_closed(self) -> None:
        _source, passages = MODULE.controlled_source(MODULE.BASE.ROOT, MODULE.SLUG)
        fingerprint = MODULE.BASE.attempt_fingerprint(passages)
        self.assertEqual(fingerprint, MODULE.EXPECTED_ATTEMPT_FINGERPRINT)
        with self.assertRaisesRegex(
            MODULE.BASE.KokoroTitlePilotError,
            "attempt fingerprint already exists",
        ):
            MODULE.BASE.ensure_not_repeated(fingerprint, MODULE.DEFAULT_OUTPUT)

    def test_durable_evidence_repeat_is_rejected(self) -> None:
        fingerprint = MODULE.EXPECTED_ATTEMPT_FINGERPRINT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = (
                root
                / "internal/audiobook_lab/sprint1_publication/"
                "sprint1_provider_failure_registry.json"
            )
            registry.parent.mkdir(parents=True)
            registry.write_text(
                json.dumps({"attempt_fingerprint": fingerprint}), encoding="utf-8"
            )
            with patch.object(MODULE.BASE, "ROOT", root):
                with self.assertRaises(MODULE.BASE.KokoroTitlePilotError):
                    MODULE.ensure_not_repeated(fingerprint, root / "new-output.json")

    @unittest.skipUnless(PINNED_PYTHON.is_file(), "pinned audio runtime missing")
    def test_pinned_runtime_g2p_is_fallback_free(self) -> None:
        command = (
            "import importlib.util; from pathlib import Path; "
            f"p=Path({str(SCRIPT)!r}); "
            "s=importlib.util.spec_from_file_location('sg',p); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "_, passages=m.controlled_source(m.BASE.ROOT,m.SLUG); "
            "reports=m.g2p_preflight(passages); "
            "assert len(reports)==4; assert all(not x['unresolved_tokens'] for x in reports)"
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
        self.assertIs(book["audio_enabled"], False)
        self.assertIs(book["audiobook_enabled"], False)

    def test_private_path_and_g2p_configuration_are_fail_closed(self) -> None:
        self.assertEqual(MODULE.BASE.KOKORO_LANG_CODE, "a")
        self.assertIs(MODULE.BASE.G2P_BRITISH, False)
        with self.assertRaises(MODULE.BASE.KokoroTitlePilotError):
            MODULE.BASE.assert_private_audio_path(
                Path(tempfile.gettempdir()) / "frontend/public/secret-garden.wav"
            )

    def test_asr_reverify_is_disabled_until_audio_hashes_are_pinned(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = MODULE.main(["--asr-reverify-existing"])
        self.assertEqual(code, 2)
        self.assertIn("disabled until", output.getvalue())

    @unittest.skipUnless(PINNED_PYTHON.is_file(), "pinned audio runtime missing")
    def test_cli_and_source_have_no_listening_upload_or_publication_surface(self) -> None:
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
