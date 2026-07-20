#!/usr/bin/env python3
"""Focused tests for The Secret Garden's one-passage AF Bella repair."""

from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name(
    "sprint1_secret_garden_af_bella_targeted_resynthesis.py"
)
SPEC = importlib.util.spec_from_file_location("secret_garden_targeted", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class SecretGardenTargetedResynthesisTests(unittest.TestCase):
    def test_preparation_is_exact_and_lexically_identical(self) -> None:
        _passages, target = MODULE.canonical_passages()
        prepared, transformations = MODULE.prepare_text(target["text"])
        self.assertEqual(len(prepared), MODULE.PREPARED_TEXT_CHARACTERS)
        self.assertEqual(MODULE.sha256_text(prepared), MODULE.PREPARED_TEXT_SHA256)
        self.assertEqual(len(transformations), 6)
        self.assertEqual(
            MODULE.BASE.lexical_tokens(target["text"]),
            MODULE.BASE.lexical_tokens(prepared),
        )
        self.assertIn("... Who is going to dress me", prepared)
        self.assertIn("wait on thysen, a bit", prepared)
        self.assertIn("nurses, an bein washed, an dressed, an took", prepared)

    def test_prepared_g2p_is_fallback_free_and_pinned(self) -> None:
        program = f"""
import importlib.util,json
from pathlib import Path
p=Path({str(SCRIPT)!r})
s=importlib.util.spec_from_file_location('target_g2p',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
_passages,target=m.canonical_passages()
prepared,_=m.prepare_text(target['text'])
print(json.dumps(m.validate_prepared_g2p(prepared),sort_keys=True))
"""
        completed = subprocess.run(
            [str(PINNED_PYTHON), "-c", program],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["kokoro_lang_code"], "a")
        self.assertIs(report["british"], False)
        self.assertIsNone(report["fallback"])
        self.assertEqual(report["phoneme_sha256"], MODULE.PREPARED_PHONEME_SHA256)
        self.assertEqual(report["unresolved_tokens"], [])

    def test_prior_failure_and_every_retained_wav_are_bound(self) -> None:
        evidence, samples, reusable = MODULE.validate_prior(MODULE.DEFAULT_INPUT)
        self.assertEqual(evidence["status"], "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAILED_FINGERPRINT_CLOSED")
        self.assertEqual(len(samples), 4)
        for sample in samples:
            binding = MODULE.EXPECTED_SAMPLE_BINDINGS[sample["passage_id"]]
            self.assertEqual(sample["audio_sha256"], binding["audio_sha256"])
            self.assertEqual(sample["size_bytes"], binding["size_bytes"])
            self.assertTrue(Path(sample["audio_path"]).is_file())
        self.assertEqual(
            {item["passage_id"] for item in reusable},
            {"opening_india", "mary_colin_emotion", "ending_return"},
        )
        self.assertTrue(all(item["pass"] for item in reusable))

    def test_ending_projection_is_exact_context_bound_and_non_deleting(self) -> None:
        passages, _target = MODULE.canonical_passages()
        ending = next(item for item in passages if item["passage_id"] == "ending_return")
        evidence = MODULE.read_json(MODULE.DEFAULT_INPUT)
        prior = next(
            item for item in evidence["asr"]["reports"]
            if item["passage_id"] == "ending_return"
        )
        sample = next(
            item for item in evidence["samples"]
            if item["passage_id"] == "ending_return"
        )
        report = MODULE.evaluate(ending, sample, prior["raw_transcript"], "test")
        self.assertTrue(report["pass"])
        self.assertEqual(report["score"], 10.0)
        self.assertEqual(report["coverage"], 1.0)
        self.assertEqual(len(report["source_equivalences_applied"]), 1)
        unchanged, applications = MODULE.apply_equivalences(
            "opening_india", prior["raw_transcript"]
        )
        self.assertEqual(unchanged, prior["raw_transcript"])
        self.assertEqual(applications, [])
        trailing = MODULE.evaluate(
            ending, sample, prior["raw_transcript"] + " Thank you.", "test"
        )
        self.assertFalse(trailing["pass"])
        self.assertIn("thank", trailing["unexpected_tokens"])
        with self.assertRaises(MODULE.TargetedResynthesisError):
            MODULE.apply_equivalences(
                "ending_return", prior["raw_transcript"] + " Mizzlethwaite"
            )

    def test_yorkshire_rules_do_not_hide_substantive_failures(self) -> None:
        transcript = (
            "Was going to dress me. They dress thy son. Saying, being, and. "
            "Eye addressed me. Thank you."
        )
        evaluated, applications = MODULE.apply_equivalences(
            MODULE.TARGET_PASSAGE_ID, transcript
        )
        self.assertEqual(evaluated, transcript)
        self.assertEqual(applications, [])

    def test_attempt_fingerprint_is_exact_and_full_decoder_configs_are_bound(self) -> None:
        self.assertEqual(
            MODULE.attempt_fingerprint(), MODULE.EXPECTED_ATTEMPT_FINGERPRINT
        )
        original = MODULE.DECODING_ARMS
        try:
            MODULE.DECODING_ARMS = ({**original[0], "beam_size": 4}, *original[1:])
            self.assertNotEqual(
                MODULE.attempt_fingerprint(), MODULE.EXPECTED_ATTEMPT_FINGERPRINT
            )
        finally:
            MODULE.DECODING_ARMS = original

    def test_completed_output_rejects_before_artifact_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "completed.json"
            output.write_text(
                json.dumps(
                    {
                        "attempt_fingerprint": MODULE.EXPECTED_ATTEMPT_FINGERPRINT,
                        "safety": {"audio_generated": True},
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(
                MODULE, "validate_prepared_g2p", side_effect=AssertionError("too late")
            ):
                with self.assertRaisesRegex(
                    MODULE.TargetedResynthesisError,
                    "attempt fingerprint already exists|already generated audio",
                ):
                    MODULE.preflight(
                        input_path=MODULE.DEFAULT_INPUT,
                        output=output,
                        artifact_dir=Path("/missing/artifacts"),
                        whisper_cache=Path("/missing/whisper"),
                        private_dir=root / "private",
                        paid_lock=MODULE.DEFAULT_PAID_LOCK,
                    )

    def _mocked_execute(self, transform):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts: dict[str, Path] = {}
            for name in ("model", "config", "voice", "whisper"):
                path = root / name
                path.write_bytes(name.encode("utf-8"))
                artifacts[name] = path
            _all, target = MODULE.canonical_passages()
            prepared_text, _transformations = MODULE.prepare_text(target["text"])
            prepared = {
                **target,
                "canonical_text_sha256": target["text_sha256"],
                "text": prepared_text,
                "text_sha256": MODULE.PREPARED_TEXT_SHA256,
                "characters": len(prepared_text),
            }
            _evidence, _samples, reusable = MODULE.validate_prior(MODULE.DEFAULT_INPUT)
            payload = {
                "runtime_evidence": {"offline_local_artifacts_only": True},
                "next_stage_contract": {},
                "safety": {},
            }
            sample = {
                "passage_id": MODULE.TARGET_PASSAGE_ID,
                "audio_path": str(root / "target.wav"),
                "audio_sha256": "a" * 64,
                "objective_format_pass": True,
            }
            calls: list[list[dict[str, object]]] = []

            def synthesize(passages, _artifacts, _private):
                calls.append(passages)
                return [sample]

            with mock.patch.object(MODULE.BASE, "synthesize", side_effect=synthesize):
                code, result = MODULE.execute(
                    payload=payload,
                    prepared=prepared,
                    artifacts=artifacts,
                    reusable_reports=reusable,
                    private_dir=root / "private",
                    whisper_cache=root,
                    paid_lock=MODULE.DEFAULT_PAID_LOCK,
                    model_loader=lambda _cache: object(),
                    decoder=lambda _model, _arm, _sample: transform(target["text"]),
                )
        return code, result, calls

    def test_mocked_exact_target_advances_only_to_private_listening(self) -> None:
        code, result, calls = self._mocked_execute(lambda text: text)
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 1)
        self.assertEqual(result["go_no_go"], "GO_PRIVATE_LISTENING_QA_ONLY")
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], True)
        self.assertIs(result["next_stage_contract"]["full_title_generation_allowed"], False)
        self.assertIs(result["safety"]["upload_performed"], False)
        self.assertIs(result["safety"]["publication_performed"], False)
        self.assertIs(result["safety"]["paid_tts_lock_unchanged"], True)

    def test_mocked_missing_word_closes_the_fingerprint(self) -> None:
        code, result, _calls = self._mocked_execute(
            lambda text: text.replace("Who is", "Was", 1)
        )
        self.assertEqual(code, 4)
        self.assertEqual(
            result["go_no_go"], "NO_GO_TARGETED_RESYNTHESIS_OBJECTIVE_FAILED"
        )
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], False)

    def test_source_and_cli_have_no_publication_surface(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn('"/audio/', source)
        self.assertNotIn("speechSynthesis", source)
        self.assertNotIn("def upload", source)
        self.assertNotIn("def publish", source)
        completed = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--preflight", completed.stdout)
        self.assertIn("--execute", completed.stdout)
        self.assertNotIn("--upload", completed.stdout)
        self.assertNotIn("--publish", completed.stdout)


if __name__ == "__main__":
    unittest.main()
