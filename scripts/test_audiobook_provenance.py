"""CPU-only contract tests for private audiobook provenance helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from audiobook_provenance import (
    build_generation_manifest,
    build_rights_workflow_bundle,
    capture_runtime,
    compatible_voice_inventory,
    deterministic_generation_job_id,
    normalize_gutenberg,
    normalize_gutenberg_story,
    normalized_manuscript_hash,
    require_full_generation,
    run_auditions,
    segment_provenance,
    sha256_bytes,
    storage_receipt_reference,
)


class ProvenanceTests(unittest.TestCase):
    def test_gutenberg_269_normalization_is_deterministic_and_strips_furniture(self):
        raw = ("Header\r\n*** START OF THE PROJECT GUTENBERG EBOOK 269 ***\r\n\r\n"
               "The Open Window.  \r\n\r\nA story.\r\n\r\n"
               "*** END OF THE PROJECT GUTENBERG EBOOK 269 ***\r\nLicense")
        result = normalize_gutenberg(raw)
        self.assertEqual(result, "The Open Window.\n\nA story.\n")
        self.assertEqual(normalized_manuscript_hash(result), normalized_manuscript_hash(normalize_gutenberg(raw)))
        self.assertNotIn("Project Gutenberg", result)

    def test_gutenberg_wrong_or_ambiguous_marker_fails_closed(self):
        with self.assertRaises(ValueError):
            normalize_gutenberg("*** START OF THE PROJECT GUTENBERG EBOOK 12 ***\nbody\n*** END OF THE PROJECT GUTENBERG EBOOK 12 ***", expected_id=12)

    def test_gutenberg_269_story_interval_removes_title_furniture_and_unwraps_lines(self):
        raw = ("*** START OF THE PROJECT GUTENBERG EBOOK BEASTS ***\n\n"
               "OTHER STORY\n\nOld text.\n\nTHE OPEN WINDOW\n\nFirst line\nsecond line.\n\nLast paragraph.\n\n"
               "THE TREASURE SHIP\n\nNext story.\n\n*** END OF THE PROJECT GUTENBERG EBOOK BEASTS ***")
        self.assertEqual(normalize_gutenberg_story(raw), "First line second line.\n\nLast paragraph.\n")

    def test_generation_job_identity_binds_inputs(self):
        base = dict(source_sha256="a" * 64, manuscript_sha256="b" * 64, model_repo="hexgrad/Kokoro-82M",
                    model_revision="c" * 40, voice="af_heart", settings={"speed": 0.92}, language="en")
        job = deterministic_generation_job_id(**base)
        self.assertEqual(job, deterministic_generation_job_id(**base))
        self.assertNotEqual(job, deterministic_generation_job_id(**{**base, "voice": "af_bella"}))

    def test_runtime_pin_requires_revision_and_artifact_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            model_file = Path(directory) / "weights.bin"
            model_file.write_bytes(b"fixture")
            runtime = capture_runtime(model_revision="deadbeef", model_path=directory)
        self.assertFalse(runtime["model"]["pinning_ready"])
        self.assertEqual(len(runtime["model"]["artifact_sha256"]), 64)

    def test_voice_inventory_is_explicit_and_language_aware(self):
        self.assertEqual([v["voice_id"] for v in compatible_voice_inventory("en", ["af_heart", "af_bella", "unknown"])],
                         ["af_heart", "af_bella"])
        self.assertEqual(compatible_voice_inventory("bn", ["af_heart", "af_bella"]), [])

    def test_auditions_write_audio_hashes_and_manifest_without_release_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            binding = {"source_sha256": "a" * 64, "manuscript_sha256": "b" * 64}
            manifest = run_auditions(text="A short sample.", voices=["af_heart", "af_bella"], language="en",
                                     output_dir=directory, source_binding_data=binding,
                                     model_revision="c" * 40, settings={"speed": 0.92},
                                     synthesize=lambda text, voice, settings: f"wav:{voice}".encode())
            self.assertEqual(len(manifest["voices"]), 2)
            self.assertTrue(all(len(row["audio_sha256"]) == 64 for row in manifest["voices"]))
            saved = json.loads((Path(directory) / "audition_manifest.json").read_text())
            self.assertFalse(saved["full_generation_authorized"])
            self.assertFalse(saved["public_release_ready"])

    def test_full_generation_requires_both_owner_approval_and_voice(self):
        with self.assertRaises(PermissionError):
            require_full_generation(False, "af_heart")
        with self.assertRaises(PermissionError):
            require_full_generation(True, None)
        require_full_generation(True, "af_heart")

    def test_segment_and_final_provenance_bind_hashes_and_qa_rights_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "segment.wav"
            audio.write_bytes(b"audio")
            segment = segment_provenance(job_id="egj_" + "a" * 64, segment_id="seg-001", text="hello",
                                         audio_path=audio, start_word=0, end_word=1, start_paragraph=0,
                                         end_paragraph=1, start_ms=0, end_ms=500, voice="af_heart",
                                         model_revision="b" * 40)
            manifest = build_generation_manifest(job_id="egj_" + "a" * 64,
                                                 binding={"source_sha256": "c" * 64},
                                                 runtime={"model": {"revision": "b" * 40}}, voice="af_heart",
                                                 settings={}, segments=[segment], qa_evidence=[{"path": "qa.json", "sha256": "d" * 64}],
                                                 license_evidence=[{"path": "rights.json", "sha256": "e" * 64}],
                                                 storage_receipts=[{"receipt": "receipt.json"}])
            self.assertEqual(manifest["segments"][0]["audio_sha256"], sha256_bytes(b"audio"))
            self.assertFalse(manifest["public_release_ready"])
            self.assertIn("license_evidence", manifest)
            self.assertIn("storage_receipts", manifest)

    def test_rights_bundle_references_absent_evidence_without_fabricating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = {name: Path(directory) / f"{name}.json" for name in
                     ("rights_decision", "publication_manifest", "audio_distribution_authority", "ownership_chain")}
            bundle = build_rights_workflow_bundle(source_sha256="a" * 64, manuscript_sha256="b" * 64,
                                                  evidence_paths=paths)
        self.assertEqual(bundle["status"], "BLOCKED_MISSING_EVIDENCE")
        self.assertFalse(bundle["release_eligible"])
        self.assertTrue(all(not row["present"] and row["decision"] == "UNREVIEWED" for row in bundle["evidence"].values()))

    def test_storage_handoff_receipt_is_referenced_and_asset_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text(json.dumps({"assets": {"audio": {"sha256": "a" * 64}}}), encoding="utf-8")
            good = storage_receipt_reference(path, {"audio": "a" * 64})
            bad = storage_receipt_reference(path, {"audio": "b" * 64})
            missing = storage_receipt_reference(Path(directory) / "missing.json", {"audio": "a" * 64})
        self.assertTrue(good["matched_assets"])
        self.assertFalse(bad["matched_assets"])
        self.assertFalse(good["release_eligible"])
        self.assertFalse(missing["present"])


if __name__ == "__main__":
    unittest.main()
