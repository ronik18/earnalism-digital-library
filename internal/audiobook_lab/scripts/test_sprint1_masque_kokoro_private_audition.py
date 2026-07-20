#!/usr/bin/env python3
"""Focused tests for The Masque of the Red Death Kokoro preflight."""

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


SCRIPT = Path(__file__).with_name("sprint1_masque_kokoro_private_audition.py")
SPEC = importlib.util.spec_from_file_location("masque_private_audition", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.BASE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class MasquePrivatePreflightTests(unittest.TestCase):
    def test_exact_catalog_source_rights_and_four_risk_passages(self) -> None:
        chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        self.assertEqual(chapter.name, "chapter-001.json")
        self.assertEqual(
            [item["passage_id"] for item in passages],
            [
                "opening_plague_and_prospero",
                "black_room_blood_light",
                "ebony_clock_tension",
                "final_confrontation_and_dominion",
            ],
        )
        self.assertEqual(sum(item["characters"] for item in passages), 3077)
        self.assertEqual(
            [item["text_sha256"] for item in passages],
            [item["sha256"] for item in MODULE.PASSAGE_SPECS],
        )

    def test_pronunciation_overrides_are_source_bound(self) -> None:
        _chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        combined = " ".join(item["text"] for item in passages)
        expected = {
            "Avatar": "ˈavətɑː",
            "Prospero": "pɹˈɒspəɹˌQ",
            "brazier": "bɹˈAzɪə",
            "candelabrum": "kˌandɪlˈɑːbɹəm",
            "cerements": "sˈɪəmᵊnts",
            "harken": "hˈɑːkən",
            "illimitable": "ɪlˈɪmɪtəbᵊl",
        }
        self.assertEqual(MODULE.PRONUNCIATION_OVERRIDES, expected)
        for source_token in expected:
            with self.subTest(source_token=source_token):
                self.assertRegex(combined, rf"\b{re.escape(source_token)}\b")

    def test_pinned_british_fallback_free_g2p_resolves_all_passages(self) -> None:
        program = f"""
import importlib.util
import json
import re
from pathlib import Path
from misaki import en as misaki_en

script = Path({str(SCRIPT)!r})
spec = importlib.util.spec_from_file_location("masque_g2p_contract", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
_chapter, passages = module.controlled_source(module.BASE.ROOT, module.SLUG)
g2p = misaki_en.G2P(trf=False, british=True, fallback=None, unk="")
g2p.lexicon.golds.update(module.PRONUNCIATION_OVERRIDES)
g2p.lexicon.golds.update({{key.lower(): value for key, value in module.PRONUNCIATION_OVERRIDES.items()}})
unresolved = {{}}
resolved = {{}}
for passage in passages:
    _phonemes, tokens = g2p(passage["text"])
    missing = sorted({{
        str(token.text)
        for token in tokens
        if re.search(r"[A-Za-z0-9]", str(token.text or ""))
        and not str(token.phonemes or "").strip()
    }})
    unresolved[passage["passage_id"]] = missing
    for token in tokens:
        if str(token.text) in module.PRONUNCIATION_OVERRIDES:
            resolved[str(token.text)] = str(token.phonemes)
print(json.dumps({{
    "fallback_is_none": g2p.fallback is None,
    "british": module.G2P_BRITISH,
    "lang_code": module.PIPELINE_LANG_CODE,
    "unresolved": unresolved,
    "resolved": resolved,
}}, sort_keys=True))
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
        self.assertIs(payload["british"], True)
        self.assertEqual(payload["lang_code"], "b")
        self.assertEqual(payload["unresolved"], {item["passage_id"]: [] for item in MODULE.PASSAGE_SPECS})
        self.assertEqual(payload["resolved"], MODULE.PRONUNCIATION_OVERRIDES)

    def test_exact_title_author_or_rights_change_fails_closed(self) -> None:
        original = MODULE.BASE.read_json
        cases = (
            ("public_book.json", "title", "synthetic title", "catalog truth changed for title"),
            ("public_book.json", "author", "synthetic author", "catalog truth changed for author"),
            ("source_evidence.json", "rights_basis", "unknown", "source evidence changed for rights_basis"),
        )
        for filename, key, replacement, message in cases:
            def changed(path: Path, target_file: str = filename, target_key: str = key):
                value = original(path)
                if path.name == target_file:
                    value = copy.deepcopy(value)
                    value[target_key] = replacement
                return value

            with self.subTest(key=key), mock.patch.object(
                MODULE.BASE, "read_json", side_effect=changed
            ):
                with self.assertRaisesRegex(MODULE.BASE.KokoroTitlePilotError, message):
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

    def test_prior_provider_fingerprint_change_fails_closed(self) -> None:
        original = MODULE.BASE.read_json

        def changed(path: Path):
            value = original(path)
            if path == MODULE.CANONICAL_RELEASE_EVIDENCE:
                value = copy.deepcopy(value)
                value["attempts"][0]["fingerprint"] = "invented"
            return value

        with mock.patch.object(MODULE.BASE, "read_json", side_effect=changed):
            with self.assertRaisesRegex(
                MODULE.BASE.KokoroTitlePilotError,
                "canonical prior attempt evidence changed",
            ):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_wrong_slug_is_refused(self) -> None:
        with self.assertRaisesRegex(
            MODULE.BASE.KokoroTitlePilotError, "only the-masque-of-the-red-death"
        ):
            MODULE.controlled_source(REPO, "the-open-window")

    def test_profile_uses_hash_pinned_distinct_british_voice(self) -> None:
        self.assertEqual(MODULE.VOICE, "bf_emma")
        self.assertTrue(MODULE.G2P_BRITISH)
        self.assertEqual(MODULE.PIPELINE_LANG_CODE, "b")
        self.assertTrue(
            all(
                MODULE.VOICE_SHA256 != digest
                for digest in MODULE.OTHER_LOCAL_KOKORO_VOICE_HASHES.values()
            )
        )
        voice = MODULE.DEFAULT_ARTIFACT_DIR / f"voices/{MODULE.VOICE}.pt"
        self.assertTrue(voice.is_file())
        self.assertEqual(MODULE.BASE.sha256_file(voice), MODULE.VOICE_SHA256)
        self.assertIs(MODULE.BASE.synthesize, MODULE.synthesize_british)

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
        self.assertEqual(
            {str(item["fingerprint"]) for item in MODULE.PRIOR_ATTEMPTS},
            {"6f561b31503df395", "c648177b25f4a6c4"},
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
                REPO / "frontend/public/audio/the-masque-of-the-red-death"
            )

    def test_preflight_contract_is_private_audio_hidden_and_fail_closed(self) -> None:
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
                payload, _passages, _artifacts = MODULE.masque_preflight(
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
        self.assertEqual(payload["engine"]["pipeline_lang_code"], "b")
        self.assertIs(payload["engine"]["g2p_british"], True)
        self.assertIs(payload["catalog_truth"]["audiobook_enabled"], False)
        self.assertIs(payload["catalog_truth"]["audio_enabled"], False)
        self.assertEqual(
            payload["catalog_truth"]["audio_public_release"],
            "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
        )
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertIs(payload["safety"]["upload_performed"], False)
        self.assertIs(payload["safety"]["publication_performed"], False)
        self.assertIs(payload["safety"]["release_gate_mutated"], False)
        command = payload["next_stage_contract"]["exact_execute_command"]
        self.assertIn("--execute", command)
        self.assertIn("the-masque-of-the-red-death", command)
        self.assertIn("bf-emma", command)

    def test_pinned_interpreter_dry_run_writes_preflight_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "preflight.json"
            pinned_code = f"""
import importlib.util
from pathlib import Path

script = Path({str(SCRIPT)!r})
spec = importlib.util.spec_from_file_location("masque_pinned_test", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.configure_base()
module.BASE.NO_REPEAT_FILES = ()
raise SystemExit(module.BASE.main(module.expand_defaults([
    "--preflight", "--output", {str(output)!r}
])))
"""
            result = subprocess.run(
                [str(PINNED_PYTHON), "-c", pinned_code],
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
