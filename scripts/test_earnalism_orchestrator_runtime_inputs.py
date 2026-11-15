"""Runtime receipts are sealed metadata; corpus paths remain private.

These are synthetic file/clock tests. No interpreter, driver, model or provider
is started, and no execution authority is created.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import earnalism_orchestrator as orchestrator


REQUEST = "en-svarah2-caption-comparison-20261116-v1"


class RuntimeInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.workspace = self.root / "private"
        self.workspace.mkdir()
        self.external = self.root / "synthetic-provider-file.bin"
        self.external.write_bytes(b"TEST RUNTIME BYTES, NEVER A LIBRARY")
        self.external_ref = {"path": str(self.external), "sha256": hashlib.sha256(self.external.read_bytes()).hexdigest()}

    def reference(self, value):
        path = self.workspace / "receipt.json"
        path.write_text(json.dumps(value))
        return {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def test_native_execution_metadata_does_not_read_provider_files_for_cache(self):
        value = {"schema": "earnalism.voice_execution.v1", "request_id": REQUEST,
                 "runtime_interpreter": self.external_ref,
                 "runtime_bootstrap": {"python_executable": self.external_ref},
                 "runtime_setup_authority": self.external_ref,
                 "runtime_setup_receipt": self.external_ref,
                 "provider_driver_preload": self.external_ref}
        ref = self.reference(value)
        with patch.object(orchestrator, "_sha", wraps=orchestrator._sha) as digest:
            found = orchestrator._refs(ref, self.workspace, self.workspace)
        self.assertEqual(set(found), {str(self.workspace / "receipt.json")})
        self.assertEqual([call.args[0] for call in digest.call_args_list], [self.workspace / "receipt.json"])

    def test_other_receipts_and_direct_corpus_paths_still_reject_escape(self):
        for value in [self.external_ref,
                      self.reference({"schema": "earnalism.voice_execution.v1", "request_id": "another-request",
                                      "runtime_interpreter": self.external_ref})]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "escapes"):
                orchestrator._refs(value, self.workspace, self.workspace)

    def test_english_receipt_does_not_hide_source_or_rights_bindings(self):
        ref = self.reference({"schema": "earnalism.voice_execution.v1", "request_id": REQUEST,
                              "runtime_interpreter": self.external_ref,
                              "rights": {"evidence": self.external_ref}})
        with self.assertRaisesRegex(ValueError, "escapes"):
            orchestrator._refs(ref, self.workspace, self.workspace)

    def test_earlier_native_cutoff_preserves_original_allocation_clock(self):
        child = {"schema": "earnalism.voice_execution.v1", "request_id": REQUEST,
                 "allocation_started_at": 1000, "absolute_deadline_epoch": 3695,
                 "allocation_shutdown_deadline_epoch": 3700}
        self.assertEqual(orchestrator._worker_original_clock(child), (1000, 3700))
        for changes in [{"absolute_deadline_epoch": 3696}, {"allocation_shutdown_deadline_epoch": 3701},
                        {"absolute_deadline_epoch": 999}, {"allocation_started_at": True},
                        {"allocation_shutdown_deadline_epoch": None}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                orchestrator._worker_original_clock({**child, **changes})

    def test_old_workers_keep_their_exact_clock_contract(self):
        child = {"allocation_started_at": 1000, "absolute_deadline_epoch": 3695,
                 "allocation_shutdown_deadline_epoch": 3700}
        self.assertEqual(orchestrator._worker_original_clock(child), (1000, 3695))
        self.assertEqual(orchestrator._worker_original_clock({**child, "original_deadline_epoch": 3600}),
                         (1000, 3600))


if __name__ == "__main__":
    unittest.main()
