"""Synthetic integration boundaries only; never install, resolve drivers or import ML."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

import scripts
from scripts import build_earnalism_orchestrator_colab as builder
from scripts import earnalism_foundation_diagnostic as diagnostic
from scripts import earnalism_foundation_qualification as qualification
from scripts import earnalism_orchestrator as engine
from scripts import test_build_earnalism_orchestrator_colab as notebook_tests


class QualificationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="qualification-integration-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.workspace = self.root / "private"
        self.workspace.mkdir()
        self.plan = {"frozen": {"proposal": {"id": "synthetic-qualification-only"}}}

    def test_disabled_controller_does_not_admit_or_dispatch(self):
        before = list(self.workspace.rglob("*"))
        report = {"state": "SYNTHETIC_PLAN_ONLY", "production_ready": False}
        with patch.object(qualification, "validate", return_value=self.plan), \
             patch.object(qualification, "summary", return_value=report), \
             patch.object(qualification, "qualify") as native, \
             patch.object(engine, "_runtime") as authority, \
             patch.object(engine, "_reserve_model") as reserve:
            self.assertEqual(engine.qualify_foundation(self.root / "request.json", self.workspace), report)
        native.assert_not_called()
        authority.assert_not_called()
        reserve.assert_not_called()
        self.assertEqual(before, list(self.workspace.rglob("*")))

    def test_missing_authority_cannot_reach_qualification(self):
        with patch.object(qualification, "validate", return_value=self.plan), \
             patch.object(qualification, "result_directory", return_value=self.workspace / "synthetic-qualification"), \
             patch.object(qualification, "qualify") as native:
            with self.assertRaisesRegex(ValueError, "guarded environment"):
                engine.qualify_foundation(self.root / "request.json", self.workspace, execute=True)
        native.assert_not_called()
        self.assertFalse((self.workspace / ".orchestrator/authorities").exists())

    def test_controller_preserves_model_allowance_and_no_auto_diagnostic(self):
        runtime = {"synthetic_fixture_only": True}
        context = {"synthetic_fixture_only": True}
        with patch.object(qualification, "validate", return_value=self.plan), \
             patch.object(qualification, "result_directory", return_value=self.workspace / "synthetic-qualification"), \
             patch.object(qualification, "qualify", return_value={"production_ready": False}) as native, \
             patch.object(engine, "_runtime", return_value=runtime), \
             patch.object(engine, "_reserve_model") as reserve, \
             patch.object(engine, "diagnose_foundation") as diagnostic_run:
            engine.qualify_foundation(self.root / "request.json", self.workspace, execute=True,
                                      authority_path=self.root / "fake-authority", runtime_context=context)
        native.assert_called_once_with(self.plan, self.workspace, runtime, context)
        reserve.assert_not_called()
        diagnostic_run.assert_not_called()
        self.assertFalse((self.workspace / ".orchestrator/authorities").exists())

    def test_completed_qualification_is_status_only_without_fresh_authority(self):
        output = self.workspace / "synthetic-qualification"
        output.mkdir()
        (output / "COMPLETED.json").write_text("SYNTHETIC_NOT_EVIDENCE")
        result = {"status_only": True, "current_runtime_admitted": False, "production_ready": False}
        with patch.object(qualification, "validate", return_value=self.plan), \
             patch.object(qualification, "result_directory", return_value=output), \
             patch.object(qualification, "verify_result", return_value=result) as verify, \
             patch.object(engine, "_runtime") as authority, \
             patch.object(qualification, "qualify") as native:
            self.assertEqual(engine.qualify_foundation(self.root / "request.json", self.workspace, execute=True), result)
        verify.assert_called_once_with(self.plan, output)
        authority.assert_not_called()
        native.assert_not_called()

    def test_qualification_marker_presence_cannot_spend_any_model_allowance(self):
        original = {"scope_ref": "SYNTHETIC_NOT_AUTHORITY", "sha256": "a" * 64,
                    "original_deadline_epoch": time.time() + 10,
                    "max_model_stage_starts": 1, "stage_attempt_limits": {"foundation-diagnostic": 1}}
        for marker in [None, {}, {"operation": "foundation-qualification"}]:
            for stage in engine.MODEL_OPERATIONS:
                with self.subTest(marker=marker, stage=stage):
                    runtime = {**original, "foundation_qualification": marker}
                    if stage == "foundation-diagnostic":
                        runtime["foundation_diagnostic"] = {}
                    with self.assertRaisesRegex(ValueError, "qualification"):
                        engine._reserve_model(runtime, stage, "b" * 64, self.workspace)
        with self.assertRaisesRegex(ValueError, "qualification"):
            engine._reserve_model(original, "arbitrary-stage", "c" * 64, self.workspace)
        self.assertFalse((self.workspace / ".orchestrator/authorities").exists())

    def test_direct_diagnostic_authority_rejects_qualification_marker(self):
        for marker in [None, {}, {"operation": "foundation-qualification"}]:
            with self.assertRaisesRegex(ValueError, "qualification authority"):
                diagnostic._authority({"foundation_qualification": marker}, {}, self.workspace)

    def notebook(self):
        source = self.root / "source"
        source.mkdir()
        notebook_tests.NotebookSourceTests().fixture(source)
        notebook = source / "fixture.ipynb"
        builder.build(notebook, root=source, base_revision="a" * 40)
        return json.loads(notebook.read_text())

    def test_notebook_guard_rejects_mixed_modes_before_any_execution(self):
        notebook = self.notebook()
        # Locate by behavior so adding markdown cells cannot weaken this test.
        guard = next("".join(cell["source"]) for cell in notebook["cells"]
                     if cell["cell_type"] == "code" and "runtime_guard = None" in "".join(cell["source"]))
        for other in ["FOUNDATION_DIAGNOSTIC_PATH", "BATCH_PATH", "FEEDBACK_PATH", "QUALIFY_PRE_STORAGE_DRIVER"]:
            namespace = {"EXECUTE": True, "FOUNDATION_QUALIFICATION_PATH": "synthetic-request", other: True}
            with self.subTest(other=other), self.assertRaises(ValueError):
                exec(compile(guard, "qualification-guard-fixture", "exec"), namespace)

    def test_notebook_lookup_precedes_drive_and_has_no_auto_model_dispatch(self):
        notebook = self.notebook()
        code = "".join(notebook["cells"][-1]["source"])
        order = []
        fake_engine = types.ModuleType("scripts.earnalism_orchestrator")
        fake_engine.run = Mock(side_effect=AssertionError("No production call"))
        fake_engine.feedback = Mock(side_effect=AssertionError("No feedback call"))
        fake_engine.diagnose_foundation = Mock(side_effect=AssertionError("No diagnostic call"))
        fake_engine._runtime = Mock(side_effect=lambda *a: order.append("authority") or {"fixture_only": True})
        fake_engine.qualify_foundation = Mock(side_effect=lambda *a, **kw: order.append("qualification") or
                                               {"state": "SYNTHETIC_QUALIFICATION_RESULT", "production_ready": False})
        fake_qualification = types.ModuleType("scripts.earnalism_foundation_qualification")
        receipt = self.root / "SYNTHETIC-PROVIDER-RESULT.json"
        receipt.write_text(json.dumps({"synthetic_fixture_only": True}))
        descriptor = {"path": str(receipt), "bytes": receipt.stat().st_size, "sha256": engine._sha(receipt)}
        fake_qualification.pre_storage = Mock(side_effect=lambda *a: order.append("provider") or descriptor)
        authority = self.root / "SYNTHETIC-AUTHORITY.json"
        authority.write_text(json.dumps({"project_id": "synthetic-qualification-only"}))
        namespace = {"pathlib": __import__("pathlib"), "json": json, "time": __import__("time"),
                     "PRIVATE_WORKSPACE": str(self.workspace), "EXECUTE": True,
                     "FOUNDATION_QUALIFICATION_PATH": "synthetic-request", "FEEDBACK_PATH": "",
                     "RUNTIME_AUTHORITY_PATH": str(authority), "runtime_authority_raw": authority.read_bytes(),
                     "runtime_authority": json.loads(authority.read_text()), "runtime_context": {},
                     "AUTO_DISCONNECT_OWN_RUNTIME": False,
                     "prepare_reviewed_software": lambda: order.append("software") or self.root,
                     "connect_private_workspace": lambda: (order.append("Drive") or self.workspace, self.workspace / "projects.json")}
        with patch.dict("sys.modules", {"scripts.earnalism_orchestrator": fake_engine,
                                        "scripts.earnalism_foundation_qualification": fake_qualification}), \
             patch.object(scripts, "earnalism_orchestrator", fake_engine), \
             patch.object(scripts, "earnalism_foundation_qualification", fake_qualification), \
             redirect_stdout(io.StringIO()):
            exec(compile(code, "qualification-notebook-fixture", "exec"), namespace)
        self.assertEqual(order, ["software", "authority", "provider", "Drive", "qualification"])
        self.assertEqual(namespace["runtime_context"]["foundation_qualification_pre_storage"], descriptor)
        self.assertEqual(fake_engine.qualify_foundation.call_args.kwargs["authority_path"].read_bytes(), authority.read_bytes())
        fake_engine.run.assert_not_called()
        fake_engine.diagnose_foundation.assert_not_called()
        self.assertFalse((self.workspace / ".orchestrator/authorities").exists())


if __name__ == "__main__":
    unittest.main()
