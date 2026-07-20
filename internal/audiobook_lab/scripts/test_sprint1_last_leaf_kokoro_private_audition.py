#!/usr/bin/env python3
"""Focused tests for The Last Leaf's private Kokoro preflight."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_last_leaf_kokoro_private_audition.py")
SPEC = importlib.util.spec_from_file_location("last_leaf_private_audition", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.BASE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class LastLeafPrivatePreflightTests(unittest.TestCase):
    def test_exact_catalog_source_and_four_risk_passages(self) -> None:
        chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        self.assertEqual(chapter.name, "chapter-001.json")
        self.assertEqual(
            [item["passage_id"] for item in passages],
            [
                "opening_literary_setting",
                "johnsy_leaf_dialogue",
                "behrman_dialect_emotion",
                "final_masterpiece_reveal",
            ],
        )
        self.assertEqual(sum(item["characters"] for item in passages), 2302)
        self.assertEqual(
            [item["text_sha256"] for item in passages],
            [item["sha256"] for item in MODULE.PASSAGE_SPECS],
        )

    def test_dialect_overrides_are_exact_and_source_preserving(self) -> None:
        _chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        dialect = next(
            item["text"]
            for item in passages
            if item["passage_id"] == "behrman_dialect_emotion"
        )
        expected = {
            "Vass": "vˈAs",
            "Vy": "vˌI",
            "bose": "bˈOz",
            "de": "də",
            "der": "dɛɹ",
            "dere": "dˈɛɹ",
            "dey": "dA",
            "haf": "hˈæf",
            "lettle": "lˈɛTᵊl",
            "mit": "mˈɪt",
            "prain": "pɹˈAn",
            "pusiness": "pˈɪznəs",
        }
        self.assertEqual(MODULE.SOURCE_DIALECT_PRONUNCIATION_BINDINGS, expected)
        for source_token, phonemes in expected.items():
            with self.subTest(source_token=source_token):
                self.assertRegex(dialect, rf"\b{re.escape(source_token)}\b")
                self.assertEqual(MODULE.PRONUNCIATION_OVERRIDES[source_token], phonemes)
        self.assertEqual(len(dialect), 432)
        self.assertEqual(
            MODULE.BASE.sha256_text(dialect),
            "3ee0d5877dcd681e530ea3dc56fe0c7b11614d3bec736c9ca485799c897fafc1",
        )

    def test_pinned_fallback_free_g2p_resolves_all_source_dialect_tokens(self) -> None:
        program = f"""
import importlib.util
import json
import re
from pathlib import Path
from misaki import en as misaki_en

script = Path({str(SCRIPT)!r})
spec = importlib.util.spec_from_file_location("last_leaf_g2p_contract", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
_chapter, passages = module.controlled_source(module.BASE.ROOT, module.SLUG)
dialect = next(item["text"] for item in passages if item["passage_id"] == "behrman_dialect_emotion")
g2p = misaki_en.G2P(trf=False, british=False, fallback=None, unk="")
g2p.lexicon.golds.update(module.PRONUNCIATION_OVERRIDES)
g2p.lexicon.golds.update({{key.lower(): value for key, value in module.PRONUNCIATION_OVERRIDES.items()}})
_phonemes, tokens = g2p(dialect)
unresolved = sorted({{
    str(token.text)
    for token in tokens
    if re.search(r"[A-Za-z0-9]", str(token.text or ""))
    and not str(token.phonemes or "").strip()
}})
resolved = {{
    str(token.text): str(token.phonemes)
    for token in tokens
    if str(token.text) in module.SOURCE_DIALECT_PRONUNCIATION_BINDINGS
}}
print(json.dumps({{"fallback_is_none": g2p.fallback is None, "unresolved": unresolved, "resolved": resolved}}, sort_keys=True))
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
        self.assertIs(payload["fallback_is_none"], True)
        self.assertEqual(payload["unresolved"], [])
        self.assertEqual(
            payload["resolved"], MODULE.SOURCE_DIALECT_PRONUNCIATION_BINDINGS
        )

    def test_exact_title_or_author_change_fails_closed(self) -> None:
        original = MODULE.BASE.read_json
        for key in ("title", "author"):
            def changed(path: Path, target: str = key):
                value = original(path)
                if path.name == "public_book.json":
                    value = copy.deepcopy(value)
                    value[target] = "synthetic metadata"
                return value

            with self.subTest(key=key), mock.patch.object(
                MODULE.BASE, "read_json", side_effect=changed
            ):
                with self.assertRaisesRegex(
                    MODULE.BASE.KokoroTitlePilotError,
                    f"catalog truth changed for {key}",
                ):
                    MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_audio_enabled_catalog_mutation_fails_closed(self) -> None:
        original = MODULE.BASE.read_json

        def changed(path: Path):
            value = original(path)
            if path.name == "public_book.json":
                value = copy.deepcopy(value)
                value["audiobook_enabled"] = True
            return value

        with mock.patch.object(MODULE.BASE, "read_json", side_effect=changed):
            with self.assertRaisesRegex(
                MODULE.BASE.KokoroTitlePilotError, "audiobook_enabled"
            ):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_audio_release_approval_mutation_fails_closed(self) -> None:
        original = MODULE.BASE.read_json

        def changed(path: Path):
            value = original(path)
            if path.name == "approval_evidence.json":
                value = copy.deepcopy(value)
                value["audio_public_release"] = "PUBLIC_AUDIO_RELEASE_APPROVED"
            return value

        with mock.patch.object(MODULE.BASE, "read_json", side_effect=changed):
            with self.assertRaisesRegex(
                MODULE.BASE.KokoroTitlePilotError, "audio-hidden"
            ):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_wrong_slug_is_refused(self) -> None:
        with self.assertRaisesRegex(
            MODULE.BASE.KokoroTitlePilotError, "only the-last-leaf"
        ):
            MODULE.controlled_source(REPO, "the-open-window")

    def test_profile_uses_hash_pinned_materially_different_voice(self) -> None:
        self.assertEqual(MODULE.VOICE, "af_sarah")
        self.assertNotEqual(
            MODULE.VOICE_SHA256, MODULE.PREVIOUS_KOKORO_VOICE_SHA256
        )
        voice = MODULE.DEFAULT_ARTIFACT_DIR / f"voices/{MODULE.VOICE}.pt"
        self.assertTrue(voice.is_file())
        self.assertEqual(MODULE.BASE.sha256_file(voice), MODULE.VOICE_SHA256)

    def test_preflight_pins_model_config_voice_and_whisper_hashes(self) -> None:
        _paths, evidence = MODULE.BASE.validate_artifacts(
            MODULE.DEFAULT_ARTIFACT_DIR, MODULE.DEFAULT_WHISPER_CACHE
        )
        self.assertEqual(evidence["model"]["sha256"], MODULE.MODEL_SHA256)
        self.assertEqual(evidence["config"]["sha256"], MODULE.CONFIG_SHA256)
        self.assertEqual(evidence["voice"]["sha256"], MODULE.VOICE_SHA256)
        self.assertEqual(evidence["whisper"]["sha256"], MODULE.WHISPER_SHA256)

    def test_fingerprint_is_title_specific_and_not_a_prior_attempt(self) -> None:
        _chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.BASE.attempt_fingerprint(passages)
        self.assertEqual(len(fingerprint), 64)
        self.assertNotIn(
            fingerprint,
            {str(item["fingerprint"]) for item in MODULE.PRIOR_ATTEMPTS},
        )
        self.assertIn(
            "b62c996d97def9e3f805eba13be2aa2b29ebf03858200657b2c959676b9d4935",
            {str(item["fingerprint"]) for item in MODULE.PRIOR_ATTEMPTS},
        )
        self.assertNotEqual(
            fingerprint, hashlib.sha256(MODULE.SLUG.encode("utf-8")).hexdigest()
        )

    def test_no_repeat_guard_rejects_persisted_execution_fingerprint(self) -> None:
        _chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.BASE.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "memory.json"
            ledger.write_text(
                json.dumps({"attempt_fingerprint": fingerprint}), encoding="utf-8"
            )
            with mock.patch.object(MODULE.BASE, "NO_REPEAT_FILES", (ledger,)):
                with self.assertRaisesRegex(
                    MODULE.BASE.KokoroTitlePilotError, "already exists"
                ):
                    MODULE.BASE.ensure_not_repeated(
                        fingerprint, Path(tmp) / "missing-evidence.json"
                    )

    def test_public_output_path_is_refused(self) -> None:
        with self.assertRaisesRegex(
            MODULE.BASE.KokoroTitlePilotError, "public audio path"
        ):
            MODULE.BASE.assert_private_audio_path(
                REPO / "frontend/public/audio/the-last-leaf"
            )

    def test_preflight_contract_is_private_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "preflight.json"
            lock = Path(tmp) / "paid_tts.lock"
            lock.write_text(
                json.dumps(
                    {
                        "status": "active",
                        "current_holder": "none",
                        "allowed_next_holders": [],
                    }
                ),
                encoding="utf-8",
            )
            fake_artifacts = {
                name: Path(tmp) / name
                for name in ("model", "config", "voice", "whisper")
            }
            fake_evidence = {
                name: {"path": str(path), "sha256": "a" * 64, "size_bytes": 1}
                for name, path in fake_artifacts.items()
            }
            with mock.patch.object(
                MODULE.BASE, "runtime_evidence", return_value={"pinned": True}
            ), mock.patch.object(
                MODULE.BASE,
                "validate_artifacts",
                return_value=(fake_artifacts, fake_evidence),
            ), mock.patch.object(MODULE.BASE, "NO_REPEAT_FILES", ()):
                payload, _passages, _artifacts = MODULE.last_leaf_preflight(
                    asset_root=REPO,
                    slug=MODULE.SLUG,
                    profile=MODULE.PROFILE,
                    artifact_dir=MODULE.DEFAULT_ARTIFACT_DIR,
                    whisper_cache_dir=MODULE.DEFAULT_WHISPER_CACHE,
                    private_output_dir=MODULE.DEFAULT_PRIVATE_OUTPUT,
                    output=output,
                    paid_lock=lock,
                )
        self.assertIs(payload["engine"]["g2p_fallback_enabled"], False)
        self.assertIs(payload["catalog_truth"]["audiobook_enabled"], False)
        self.assertIs(payload["catalog_truth"]["audio_enabled"], False)
        self.assertIs(
            payload["next_stage_contract"]["execution_performed_by_this_preflight"],
            False,
        )
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertIs(payload["safety"]["upload_performed"], False)
        self.assertIs(payload["safety"]["publication_performed"], False)
        self.assertIs(payload["safety"]["release_gate_mutated"], False)
        command = payload["next_stage_contract"]["exact_execute_command"]
        self.assertIn("--execute", command)
        self.assertIn("the-last-leaf", command)
        self.assertIn("af-sarah", command)

    def test_pinned_interpreter_dry_run_writes_preflight_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "preflight.json"
            # The production ledger now correctly closes this completed
            # fingerprint. Run the pinned-runtime preflight with only the
            # no-repeat input isolated; production guard behavior remains
            # covered by the explicit persisted-fingerprint test above.
            pinned_code = f"""
import importlib.util
from pathlib import Path

script = Path({str(SCRIPT)!r})
spec = importlib.util.spec_from_file_location("last_leaf_pinned_test", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.configure_base()
module.BASE.NO_REPEAT_FILES = ()
raise SystemExit(module.BASE.main(module.expand_defaults([
    "--preflight", "--output", {str(output)!r}
])))
"""
            result = subprocess.run(
                [
                    str(PINNED_PYTHON),
                    "-c",
                    pinned_code,
                ],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["status"], "READY_FOR_PRIVATE_REPRESENTATIVE_EXECUTION"
        )
        self.assertEqual(payload["scope"]["slug"], MODULE.SLUG)
        self.assertEqual(payload["scope"]["title"], MODULE.TITLE)
        self.assertEqual(payload["scope"]["author"], MODULE.AUTHOR)
        self.assertEqual(payload["engine"]["voice"], MODULE.VOICE)
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertEqual(payload["safety"]["provider_calls"], 0)
        self.assertNotIn("samples", payload)
        self.assertNotIn("asr", payload)


if __name__ == "__main__":
    unittest.main()
