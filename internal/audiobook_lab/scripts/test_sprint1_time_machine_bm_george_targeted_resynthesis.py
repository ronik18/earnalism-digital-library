#!/usr/bin/env python3
"""Focused tests for The Time Machine two-passage targeted repair."""

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
    "sprint1_time_machine_bm_george_targeted_resynthesis.py"
)
SPEC = importlib.util.spec_from_file_location("time_machine_targeted", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class TimeMachineTargetedResynthesisTests(unittest.TestCase):
    def test_prior_failure_is_bound_and_only_two_targets_failed(self) -> None:
        _evidence, reports, samples = MODULE.validate_prior(MODULE.DEFAULT_INPUT)
        self.assertEqual(len(reports), 4)
        self.assertEqual(len(samples), 4)
        self.assertEqual(
            {
                item["passage_id"]
                for item in reports
                if item["pass"] is not True
            },
            set(MODULE.TARGET_PASSAGE_IDS),
        )
        self.assertEqual(
            {item["passage_id"] for item in reports if item["pass"] is True},
            set(MODULE.REUSED_PASSAGE_IDS),
        )

    def test_preparations_change_only_punctuation(self) -> None:
        _passages, indexed = MODULE.canonical_passages()
        for passage_id in MODULE.TARGET_PASSAGE_IDS:
            source = indexed[passage_id]["text"]
            prepared, transformations = MODULE.prepare_text(passage_id, source)
            binding = MODULE.PREPARED_TEXT_BINDINGS[passage_id]
            self.assertEqual(MODULE.sha256_text(prepared), binding["sha256"])
            self.assertTrue(transformations)
            self.assertEqual(
                MODULE.PROFILE.lexical_tokens(source),
                MODULE.PROFILE.lexical_tokens(prepared),
            )
        eloi, _ = MODULE.prepare_text(
            "eloi_first_contact", indexed["eloi_first_contact"]["text"]
        )
        ending, _ = MODULE.prepare_text(
            "epilogue_tenderness", indexed["epilogue_tenderness"]["text"]
        )
        self.assertIn("face to face. I—and this", eloi)
        self.assertIn("plesiosaurus ... haunted Oolitic", ending)
        self.assertIn("brown, and flat, and brittle", ending)

    def test_prepared_g2p_is_british_fallback_free_and_pinned(self) -> None:
        program = f"""
import importlib.util,json
from pathlib import Path
p=Path({str(SCRIPT)!r})
s=importlib.util.spec_from_file_location('target_g2p',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
_passages,indexed=m.canonical_passages()
reports=[]
for passage_id in m.TARGET_PASSAGE_IDS:
    prepared,_=m.prepare_text(passage_id,indexed[passage_id]['text'])
    reports.append(m.validate_prepared_g2p(passage_id,prepared))
print(json.dumps(reports,sort_keys=True))
"""
        completed = subprocess.run(
            [str(PINNED_PYTHON), "-c", program],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        reports = json.loads(completed.stdout)
        self.assertEqual(len(reports), 2)
        for report in reports:
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["kokoro_lang_code"], "b")
            self.assertIs(report["british"], True)
            self.assertIsNone(report["fallback"])
            self.assertEqual(
                report["phoneme_sha256"],
                MODULE.PREPARED_TEXT_BINDINGS[report["passage_id"]][
                    "phoneme_sha256"
                ],
            )
            self.assertEqual(report["unresolved_tokens"], [])

    def test_attempt_fingerprint_is_exact(self) -> None:
        self.assertEqual(
            MODULE.attempt_fingerprint(), MODULE.EXPECTED_ATTEMPT_FINGERPRINT
        )

    def test_completed_fingerprint_is_durably_recorded_and_cannot_repeat(self) -> None:
        fingerprint = MODULE.EXPECTED_ATTEMPT_FINGERPRINT
        recorded_paths = [
            path
            for path in MODULE.NO_REPEAT_FILES
            if path.is_file()
            and fingerprint in path.read_text(encoding="utf-8", errors="strict")
        ]
        self.assertGreaterEqual(len(recorded_paths), 3)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed = subprocess.run(
                [
                    str(PINNED_PYTHON),
                    str(SCRIPT),
                    "--preflight",
                    "--output",
                    str(root / "evidence.json"),
                    "--private-output-dir",
                    str(root / "private"),
                ],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 2, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout or completed.stderr)
        self.assertEqual(payload["status"], "BLOCKED_FAIL_CLOSED")
        self.assertIn("attempt fingerprint already exists", payload["error"])

    def test_actual_result_is_fail_closed_without_downstream_actions(self) -> None:
        result = MODULE.read_json(MODULE.DEFAULT_OUTPUT)
        self.assertEqual(
            result["status"],
            "PRIVATE_TARGETED_RESYNTHESIS_FAILED_FINGERPRINT_CLOSED",
        )
        self.assertEqual(
            [item["score"] for item in result["combined_representative_reports"]],
            [10.0, 9.964, 10.0, 10.0],
        )
        self.assertEqual(
            [
                item["passage_id"]
                for item in result["combined_representative_reports"]
                if item["pass"] is not True
            ],
            ["eloi_first_contact"],
        )
        safety = result["safety"]
        self.assertIs(safety["paid_tts_lock_unchanged"], True)
        self.assertIs(safety["listening_qa_run"], False)
        self.assertIs(safety["upload_performed"], False)
        self.assertIs(safety["publication_performed"], False)
        self.assertIs(safety["release_gate_mutated"], False)

    def mocked_execute(self, transcript_transform):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = {}
            for name in ("model", "config", "voice", "whisper"):
                path = root / name
                path.write_bytes(name.encode("utf-8"))
                artifacts[name] = path
            all_passages, indexed = MODULE.canonical_passages()
            prepared_passages = []
            samples = []
            for passage_id in MODULE.TARGET_PASSAGE_IDS:
                target = indexed[passage_id]
                prepared_text, _ = MODULE.prepare_text(passage_id, target["text"])
                prepared_passages.append(
                    {
                        **target,
                        "canonical_text_sha256": target["text_sha256"],
                        "text": prepared_text,
                        "text_sha256": MODULE.PREPARED_TEXT_BINDINGS[passage_id][
                            "sha256"
                        ],
                        "characters": len(prepared_text),
                    }
                )
                samples.append(
                    {
                        "passage_id": passage_id,
                        "source_text_sha256": MODULE.PREPARED_TEXT_BINDINGS[passage_id][
                            "sha256"
                        ],
                        "audio_path": str(root / f"{passage_id}.wav"),
                        "audio_sha256": passage_id.encode().hex().ljust(64, "0")[:64],
                        "objective_format_pass": True,
                    }
                )
            _prior, prior_reports, _prior_samples = MODULE.validate_prior(
                MODULE.DEFAULT_INPUT
            )
            lock = {
                "path": str(root / "paid_tts.lock"),
                "sha256": MODULE.EXPECTED_PAID_LOCK_SHA256,
                "size_bytes": 1,
                "status": "active",
                "current_holder": "none",
                "allowed_next_holders": [],
                "read_only": True,
            }
            payload = {
                "runtime_evidence": {
                    "offline_local_artifacts_only": True,
                    "deterministic_algorithms_required": True,
                    "torch_thread_count": 1,
                },
                "next_stage_contract": {},
                "safety": {"paid_tts_lock": lock},
            }
            with mock.patch.object(
                MODULE.PROFILE, "synthesize", return_value=samples
            ), mock.patch.object(
                MODULE.PROFILE, "lock_snapshot", return_value=lock
            ):
                code, result = MODULE.execute(
                    payload=payload,
                    all_passages=all_passages,
                    prepared_passages=prepared_passages,
                    artifacts=artifacts,
                    prior_reports=prior_reports,
                    private_dir=root / "private",
                    whisper_cache=root,
                    paid_lock=root / "paid_tts.lock",
                    model_loader=lambda _cache: object(),
                    decoder=lambda _model, _arm, sample: transcript_transform(
                        sample["passage_id"], indexed[sample["passage_id"]]["text"]
                    ),
                )
        return code, result

    def test_mocked_exact_targets_advance_only_to_listening(self) -> None:
        code, result = self.mocked_execute(lambda _passage_id, text: text)
        self.assertEqual(code, 0)
        self.assertEqual(result["go_no_go"], "GO_PRIVATE_LISTENING_QA_ONLY")
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], True)
        self.assertIs(
            result["next_stage_contract"]["full_title_generation_allowed"], False
        )
        self.assertIs(result["safety"]["paid_tts_lock_unchanged"], True)
        self.assertIs(result["safety"]["upload_performed"], False)
        self.assertIs(result["safety"]["publication_performed"], False)

    def test_mocked_missing_word_closes_fingerprint(self) -> None:
        def remove_flat(passage_id: str, text: str) -> str:
            return text.replace(" flat", "", 1) if passage_id == "epilogue_tenderness" else text

        code, result = self.mocked_execute(remove_flat)
        self.assertEqual(code, 4)
        self.assertEqual(
            result["go_no_go"], "NO_GO_TARGETED_RESYNTHESIS_OBJECTIVE_FAILED"
        )
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], False)

    def test_source_has_no_publication_or_browser_speech_path(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn('"/audio/', source)
        self.assertNotIn("speechSynthesis", source)
        self.assertNotIn("def upload", source)
        self.assertNotIn("def publish", source)

    def test_cli_is_bounded(self) -> None:
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--execute", result.stdout)
        self.assertIn("--preflight", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertNotIn("--publish", result.stdout)


if __name__ == "__main__":
    unittest.main()
