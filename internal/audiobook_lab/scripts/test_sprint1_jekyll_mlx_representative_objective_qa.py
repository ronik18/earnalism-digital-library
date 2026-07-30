from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import sprint1_jekyll_mlx_representative_objective_qa as qa


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class JekyllMLXRepresentativeObjectiveQATests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run_dir = self.root / "private-candidate"
        self.run_dir.mkdir()
        self.records: list[dict[str, object]] = []
        for unit_id in qa.EXPECTED_UNIT_IDS:
            audio = self.run_dir / f"{unit_id}.mp3"
            audio.write_bytes(b"ID3" + unit_id.encode("ascii"))
            source = f"Exact source for {unit_id}."
            self.records.append(
                {
                    "unit_id": unit_id,
                    "audio_path": str(audio),
                    "audio_sha256": file_sha256(audio),
                    "text_sha256": hashlib.sha256(source.encode()).hexdigest(),
                    "source_text": source,
                    "measured_duration_seconds": 3.0,
                }
            )
        self.manifest = self.run_dir / "full_generation_manifest.json"
        self.manifest.write_text("{}\n", encoding="utf-8")
        self.evidence = qa.candidate_qa.CandidateEvidence(
            manifest={"slug": qa.EXPECTED_SLUG},
            manifest_path=self.manifest,
            manifest_sha256="a" * 64,
            source_path=self.run_dir / "sanitized_source.txt",
            source_sha256="b" * 64,
            input_manifest_path=self.run_dir / "input_manifest.json",
            input_manifest_sha256="c" * 64,
            records=self.records,
            measured_sync={},
            construction={},
            candidate_audio_sequence_sha256="d" * 64,
            candidate_binding_sha256="e" * 64,
        )
        reports = []
        for record in self.records:
            reports.append(
                {
                    "unit_id": record["unit_id"],
                    "audio_sha256": record["audio_sha256"],
                    "source_text_sha256": record["text_sha256"],
                    "transcript_sha256": "f" * 64,
                    "score": (
                        9.4
                        if record["unit_id"] in qa.EXPECTED_TARGET_UNIT_IDS
                        else 10.0
                    ),
                    "coverage": (
                        0.91
                        if record["unit_id"] in qa.EXPECTED_TARGET_UNIT_IDS
                        else 1.0
                    ),
                    "first_words_match": True,
                    "last_words_match": (
                        record["unit_id"] not in qa.EXPECTED_TARGET_UNIT_IDS
                    ),
                    "pass": (
                        record["unit_id"] not in qa.EXPECTED_TARGET_UNIT_IDS
                    ),
                }
            )
        self.prior = {
            "schema_version": qa.EXPECTED_PRIOR_SCHEMA,
            "slug": qa.EXPECTED_SLUG,
            "status": "FULL_AUDIO_DERIVED_ASR_SYNC_BLOCKED",
            "source_sha256": self.evidence.source_sha256,
            "input_manifest_sha256": self.evidence.input_manifest_sha256,
            "full_manifest_sha256": self.evidence.manifest_sha256,
            "audio_derived_asr": {
                "model": qa.EXPECTED_PRIOR_MODEL,
                "chunk_count": len(self.records),
                "local_asr_run_count": len(self.records),
                "reports": reports,
            },
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "paid_lock_read_or_written": False,
        }
        self.prior_path = self.run_dir / "prior.json"
        self.prior_path.write_text(
            json.dumps(self.prior, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.prior_sha = file_sha256(self.prior_path)

    def passing_report(self, unit_id: str) -> dict[str, object]:
        return {
            "unit_id": unit_id,
            "strict_objective_pass": True,
            "word_timestamp_evidence_valid": True,
            "metrics": {"last_words_match": True},
        }

    def test_validate_prior_report_requires_exact_hash_and_unit_bindings(
        self,
    ) -> None:
        report, by_id = qa.validate_prior_report(
            self.prior_path,
            self.prior_sha,
            self.evidence,
        )
        self.assertEqual(report["slug"], qa.EXPECTED_SLUG)
        self.assertEqual(set(by_id), set(qa.EXPECTED_UNIT_IDS))

        with self.assertRaisesRegex(
            qa.JekyllMLXDiagnosticError,
            "report hash changed",
        ):
            qa.validate_prior_report(
                self.prior_path,
                "0" * 64,
                self.evidence,
            )

        changed = json.loads(self.prior_path.read_text(encoding="utf-8"))
        changed["audio_derived_asr"]["reports"][0]["audio_sha256"] = "0" * 64
        self.prior_path.write_text(json.dumps(changed) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(
            qa.JekyllMLXDiagnosticError,
            "binding changed",
        ):
            qa.validate_prior_report(
                self.prior_path,
                file_sha256(self.prior_path),
                self.evidence,
            )

    def test_classification_requires_targets_controls_and_timestamps(self) -> None:
        reports = [
            self.passing_report(unit_id)
            for unit_id in qa.EXPECTED_UNIT_IDS
        ]
        decision = qa.classify(reports)
        self.assertTrue(decision["full_92_unit_mlx_run_eligible"])
        self.assertFalse(decision["release_authorized"])

        reports[2]["strict_objective_pass"] = False
        decision = qa.classify(reports)
        self.assertEqual(
            decision["status"],
            "MLX_MODEL_NOT_VALIDATED_ON_STRONG_CONTROLS",
        )
        self.assertFalse(decision["full_92_unit_mlx_run_eligible"])

        reports = [
            self.passing_report(unit_id)
            for unit_id in qa.EXPECTED_UNIT_IDS
        ]
        reports[0]["word_timestamp_evidence_valid"] = False
        decision = qa.classify(reports)
        self.assertFalse(decision["full_92_unit_mlx_run_eligible"])

    def test_output_must_remain_private_and_immutable(self) -> None:
        allowed = (
            self.run_dir
            / "mlx_large_v3_turbo_diagnostic"
            / "report.json"
        )
        self.assertEqual(
            qa.validate_output_path(allowed, self.run_dir),
            allowed.resolve(),
        )
        with self.assertRaisesRegex(
            qa.JekyllMLXDiagnosticError,
            "private MLX diagnostic",
        ):
            qa.validate_output_path(self.root / "public.json", self.run_dir)
        allowed.parent.mkdir()
        allowed.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(
            qa.JekyllMLXDiagnosticError,
            "already exists",
        ):
            qa.validate_output_path(allowed, self.run_dir)

    def test_model_hashes_fail_closed(self) -> None:
        model = self.root / "model"
        model.mkdir()
        weights = model / "weights.safetensors"
        config = model / "config.json"
        weights.write_bytes(b"weights")
        config.write_bytes(b"config")
        profile = dict(qa.MODEL_PROFILES[qa.DEFAULT_MODEL_PROFILE])
        profile["weights_sha256"] = file_sha256(weights)
        profile["config_sha256"] = file_sha256(config)
        profile["weights_filename"] = weights.name
        with (
            mock.patch.dict(
                qa.MODEL_PROFILES,
                {qa.DEFAULT_MODEL_PROFILE: profile},
            ),
        ):
            validated = qa.validate_model(model, qa.DEFAULT_MODEL_PROFILE)
            self.assertEqual(
                validated["weights_sha256"],
                file_sha256(weights),
            )
        weights.write_bytes(b"tampered")
        with self.assertRaisesRegex(
            qa.JekyllMLXDiagnosticError,
            "weights hash changed",
        ):
            qa.validate_model(model, qa.DEFAULT_MODEL_PROFILE)

    def test_full_large_v3_profile_is_distinct_and_pinned(self) -> None:
        turbo = qa.MODEL_PROFILES["large-v3-turbo"]
        full = qa.MODEL_PROFILES["large-v3"]
        self.assertNotEqual(turbo["repository"], full["repository"])
        self.assertNotEqual(turbo["revision"], full["revision"])
        self.assertNotEqual(turbo["weights_sha256"], full["weights_sha256"])
        self.assertEqual(full["license"], "MIT")
        self.assertEqual(full["weights_filename"], "weights.npz")
        self.assertEqual(len(str(full["revision"])), 40)
        self.assertEqual(len(str(full["weights_sha256"])), 64)

    def test_run_is_exactly_five_units_and_cannot_authorize_release(self) -> None:
        output = (
            self.run_dir
            / "mlx_large_v3_turbo_diagnostic"
            / "report.json"
        )
        prior_by_id = {
            item["unit_id"]: item
            for item in self.prior["audio_derived_asr"]["reports"]
        }
        metrics = {
            "score": 10.0,
            "coverage": 1.0,
            "precision": 1.0,
            "source_token_count": 5,
            "transcript_token_count": 5,
            "equal_token_count": 5,
            "first_words_match": True,
            "last_words_match": True,
            "ordered_content_integrity_pass": True,
            "no_missing_content": True,
            "no_duplicate_content": True,
            "no_reordered_content": True,
            "no_unexpected_content": True,
            "pass": True,
        }
        calls: list[str] = []

        def transcriber(audio_path: str, **_kwargs: object) -> dict[str, object]:
            calls.append(Path(audio_path).stem)
            return {
                "text": f"transcript for {Path(audio_path).stem}",
                "segments": [
                    {
                        "words": [
                            {
                                "word": "word",
                                "start": 0.1,
                                "end": 0.5,
                                "probability": 0.99,
                            }
                        ]
                    }
                ],
            }

        with (
            mock.patch.object(
                qa.full_qa,
                "validate_contract",
                return_value=self.evidence,
            ),
            mock.patch.object(
                qa,
                "validate_model",
                return_value={
                    "profile": qa.DEFAULT_MODEL_PROFILE,
                    "repository": qa.MODEL_PROFILES[
                        qa.DEFAULT_MODEL_PROFILE
                    ]["repository"],
                    "revision": qa.MODEL_PROFILES[
                        qa.DEFAULT_MODEL_PROFILE
                    ]["revision"],
                    "license": "MIT",
                    "path": str(self.root / "model"),
                    "weights_filename": "weights.safetensors",
                    "weights_sha256": qa.MODEL_PROFILES[
                        qa.DEFAULT_MODEL_PROFILE
                    ]["weights_sha256"],
                    "config_sha256": qa.MODEL_PROFILES[
                        qa.DEFAULT_MODEL_PROFILE
                    ]["config_sha256"],
                    "diagnostic_directory": (
                        "mlx_large_v3_turbo_diagnostic"
                    ),
                },
            ),
            mock.patch.object(
                qa,
                "validate_prior_report",
                return_value=(self.prior, prior_by_id),
            ),
            mock.patch.object(
                qa.full_qa,
                "_evaluated_metrics",
                return_value=metrics,
            ),
            mock.patch.object(
                qa.importlib.metadata,
                "version",
                return_value="0.4.3",
            ),
        ):
            result = qa.run_diagnostic(
                full_manifest=self.manifest,
                prior_report=self.prior_path,
                prior_report_sha256=self.prior_sha,
                model_path=self.root / "model",
                output=output,
                transcriber=transcriber,
            )

        self.assertEqual(tuple(calls), qa.EXPECTED_UNIT_IDS)
        self.assertTrue(result["decision"]["full_92_unit_mlx_run_eligible"])
        self.assertFalse(result["decision"]["release_authorized"])
        self.assertFalse(result["upload_performed"])
        self.assertFalse(result["paid_lock_read_or_written"])
        self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
