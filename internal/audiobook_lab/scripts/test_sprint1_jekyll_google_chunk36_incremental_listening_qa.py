#!/usr/bin/env python3
"""Tests for one-call Jekyll incremental listening QA."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sprint1_google_english_full_candidate_qa as candidate_qa
import sprint1_jekyll_google_chunk36_bounded_repair as repair
import sprint1_jekyll_google_chunk36_incremental_listening_qa as listening


def scores(value: float = 9.4) -> dict[str, float]:
    return {
        field: (0.95 if field == "confidence_score" else value)
        for field in candidate_qa.LISTENING_THRESHOLDS
    }


def flags() -> dict[str, bool]:
    return {
        field: False for field in candidate_qa.BINARY_LISTENING_FLAGS
    }


class IncrementalListeningQATests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run_dir = self.root / "private" / "jekyll" / "repaired"
        self.run_dir.mkdir(parents=True)
        self.manifest_path = self.run_dir / "full_generation_manifest.json"
        self.manifest_path.write_text("{}\n", encoding="utf-8")
        self.records: list[dict] = []
        for index in range(92):
            self.records.append(
                {
                    "unit_id": f"chunk_{index:04d}",
                    "text_sha256": f"{index:064x}",
                    "audio_sha256": f"{index + 1000:064x}",
                    "audio_path": str(
                        self.run_dir / "audio" / f"chunk_{index:04d}.mp3"
                    ),
                    "source_text": f"section {index}",
                    "measured_duration_seconds": 1.0,
                }
            )
        self.evidence = candidate_qa.CandidateEvidence(
            manifest={
                "slug": repair.SLUG,
                "title": repair.TITLE,
                "author": repair.AUTHOR,
                "provider": "google",
                "voice": repair.BASE_VOICE,
                "bounded_chunk_repair": {
                    "slug": repair.SLUG,
                    "chunk_index": repair.TARGET_INDEX,
                    "unit_id": repair.TARGET_UNIT_ID,
                    "failed_listening_evidence_sha256": (
                        listening.EXPECTED_PRIOR_LISTENING_SHA256
                    ),
                    "repair_attempt_fingerprint": "a" * 64,
                },
            },
            manifest_path=self.manifest_path,
            manifest_sha256="b" * 64,
            source_path=self.run_dir / "sanitized_source.txt",
            source_sha256="c" * 64,
            input_manifest_path=self.run_dir / "input_manifest.json",
            input_manifest_sha256="d" * 64,
            records=self.records,
            measured_sync={"status": "PASS"},
            construction={"status": "PASS"},
            candidate_audio_sequence_sha256="e" * 64,
            candidate_binding_sha256="f" * 64,
        )
        self.selected = [
            {
                "sample_label": f"sample_{unit_id}",
                "section_index": int(unit_id[-4:]),
                "unit_id": unit_id,
                "start_time": float(position),
                "duration": 1.0,
                "sample_audio_path": self.records[int(unit_id[-4:])][
                    "audio_path"
                ],
                "sample_audio_hash": self.records[int(unit_id[-4:])][
                    "audio_sha256"
                ],
                "source_text_sha256": self.records[int(unit_id[-4:])][
                    "text_sha256"
                ],
                "selection_method": (
                    "deterministic_source_bound_full_candidate_section"
                ),
            }
            for position, unit_id in enumerate(
                listening.EXPECTED_PRIOR_UNIT_IDS
            )
        ]
        self.prior_by_unit: dict[str, dict] = {}
        for sample in self.selected:
            old_hash = sample["sample_audio_hash"]
            if sample["unit_id"] == repair.TARGET_UNIT_ID:
                old_hash = repair.TARGET_PRIOR_AUDIO_SHA256
            self.prior_by_unit[sample["unit_id"]] = {
                **sample,
                "sample_audio_hash": old_hash,
                "scores": scores(),
                "judge_flags": flags(),
                "frontmatter_present": False,
                "notes": "retained",
                "blocker_reason": "",
            }
        self.prior = {
            "candidate_binding_sha256": (
                repair.EXPECTED_BASE_CANDIDATE_BINDING_SHA256
            )
        }
        self.prior_path = self.root / "prior.json"
        self.prior_path.write_text("{}\n", encoding="utf-8")
        self.objective_path = self.run_dir / "audio_derived.json"
        self.objective_path.write_text("{}\n", encoding="utf-8")
        self.lock = self.root / "paid_tts.lock"
        self.lock.write_text(
            json.dumps(
                {
                    "status": "active",
                    "current_holder": "none",
                    "allowed_next_holders": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.env = {
            "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "OPENAI_API_KEY": "test",
            "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
            "EARNALISM_LISTENING_POLICY_VERSION": listening.ACTIVE_POLICY,
            "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "0.10",
            "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
            "MAX_TTS_BUDGET_USD": "75",
            "EARNALISM_PRIOR_ESTIMATED_SPEND_USD": "18.7",
            listening.APPROVAL_ENV: "true",
        }

    def test_reuses_only_five_exact_unchanged_hashes(self) -> None:
        with mock.patch.object(
            candidate_qa,
            "select_listening_samples",
            return_value=self.selected,
        ):
            reused, target = listening.bind_reused_samples(
                self.evidence,
                self.prior_path,
                self.prior,
                self.prior_by_unit,
            )
        self.assertEqual(len(reused), 5)
        self.assertEqual(target["unit_id"], repair.TARGET_UNIT_ID)
        self.assertTrue(all(sample["judgment_reused"] for sample in reused))

    def test_changed_non_target_hash_blocks_reuse(self) -> None:
        changed = dict(self.prior_by_unit["chunk_0018"])
        changed["sample_audio_hash"] = "9" * 64
        prior = {**self.prior_by_unit, "chunk_0018": changed}
        with mock.patch.object(
            candidate_qa,
            "select_listening_samples",
            return_value=self.selected,
        ):
            with self.assertRaisesRegex(
                listening.IncrementalListeningError,
                "audio hash changed",
            ):
                listening.bind_reused_samples(
                    self.evidence,
                    self.prior_path,
                    self.prior,
                    prior,
                )

    def run_incremental(self, target_score: float, output_name: str):
        reused = []
        target = {}
        for sample in self.selected:
            if sample["unit_id"] == repair.TARGET_UNIT_ID:
                target = dict(sample)
            else:
                reused.append(
                    {
                        **sample,
                        "scores": scores(),
                        "confidence": 0.95,
                        "judge_flags": flags(),
                        "frontmatter_present": False,
                        "notes": "retained",
                        "blocker_reason": "",
                        "judgment_reused": True,
                    }
                )
        judge_calls: list[dict] = []

        def judge(_client, _args, sample):
            judge_calls.append(sample)
            return {
                "scores": scores(target_score),
                "judge_flags": flags(),
                "frontmatter_present": False,
                "notes": "new repaired judgment",
                "blocker_reason": "",
            }

        output = self.run_dir / output_name
        lock_before = self.lock.read_bytes()
        patches = (
            mock.patch.object(
                listening.audio_derived_qa,
                "validate_contract",
                return_value=self.evidence,
            ),
            mock.patch.object(
                listening,
                "validate_objective_report",
                return_value={"qa_binding_sha256": "1" * 64},
            ),
            mock.patch.object(
                listening,
                "prior_samples",
                return_value=(self.prior, self.prior_by_unit),
            ),
            mock.patch.object(
                listening,
                "bind_reused_samples",
                return_value=(reused, target),
            ),
        )
        with patches[0], patches[1], patches[2], patches[3]:
            code, result = listening.evaluate(
                self.manifest_path,
                self.objective_path,
                self.prior_path,
                self.lock,
                output,
                env=self.env,
                judge=judge,
                client=object(),
                duration_probe=lambda _path: 1.0,
            )
        return code, result, judge_calls, lock_before

    def test_judges_only_replacement_under_active_89_policy(self) -> None:
        code, result, calls, lock_before = self.run_incremental(
            9.1,
            "incremental-pass.json",
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            result["status"],
            "FULL_CANDIDATE_QA_PASS_PRIVATE_ONLY",
        )
        self.assertEqual(result["active_release_policy"], listening.ACTIVE_POLICY)
        self.assertEqual(result["reused_judgment_count"], 5)
        self.assertEqual(result["new_judgment_count"], 1)
        self.assertEqual(result["new_judgment_unit_ids"], [repair.TARGET_UNIT_ID])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["unit_id"], repair.TARGET_UNIT_ID)
        self.assertEqual(self.lock.read_bytes(), lock_before)
        self.assertTrue(result["paid_lock_read_or_written"])
        self.assertTrue(result["paid_lock_restored_byte_for_byte"])
        self.assertFalse(result["upload_performed"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["release_mutation_performed"])

    def test_repaired_chunk_below_89_remains_blocked(self) -> None:
        code, result, calls, lock_before = self.run_incremental(
            8.8,
            "incremental-fail.json",
        )
        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "BLOCKED_LISTENING_QA")
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.lock.read_bytes(), lock_before)
        self.assertTrue(
            any(
                "overall_listening_score" in blocker
                for blocker in result["blockers"]
            )
        )


if __name__ == "__main__":
    unittest.main()
