"""Source-distribution checks; no Colab, model or provider is exercised."""
import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
import subprocess

from scripts import build_earnalism_orchestrator_colab as builder


class NotebookSourceTests(unittest.TestCase):
    def fixture(self, root):
        for name in builder.FILES:
            path = root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# public source fixture\n")
        runtime = root/"scripts/earnalism_voice_runtime/inference.py"
        runtime.parent.mkdir(parents=True)
        runtime.write_text("# inference fixture\n")
        (root/"private-voice-weights.bin").write_bytes(b"PRIVATE_MUST_NOT_EMBED")

    def test_deterministic_capsule_and_no_private_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            one, two = root/"one.ipynb", root/"two.ipynb"
            first = builder.build(one, root=root, base_revision="a"*40)
            second = builder.build(two, root=root, base_revision="a"*40)
            self.assertEqual(one.read_bytes(), two.read_bytes())
            self.assertEqual(first["capsule_sha256"], second["capsule_sha256"])
            self.assertNotIn("private-voice-weights.bin", first["files"])
            self.assertEqual(builder.verify_notebook(one, root=root), first)
            for cell in json.loads(one.read_text())["cells"]:
                if cell["cell_type"] == "code":
                    ast.parse("".join(cell["source"]))
                    self.assertEqual(cell["outputs"], [])

    def test_modified_runtime_is_rejected_without_rebuilding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="b"*40)
            (root/"scripts/earnalism_voice_runtime/inference.py").write_text("# changed\n")
            with self.assertRaisesRegex(ValueError, "stale"):
                builder.verify_notebook(notebook, root=root)

    def test_expired_scope_stops_before_colab_or_source_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="c"*40)
            cells = json.loads(notebook.read_text())["cells"]
            scope = root/"expired.json"
            scope.write_text(json.dumps({"schema":"earnalism.orchestrator_runtime.v1",
                                         "owner_authorized":True,"allocation_started_at":1,
                                         "original_deadline_epoch":2}))
            namespace = {"EXECUTE":True,"RUNTIME_AUTHORITY_PATH":str(scope)}
            guard = "".join(cells[3]["source"])
            with self.assertRaisesRegex(RuntimeError, "exhausted"):
                exec(compile(guard, "guard-fixture", "exec"), namespace)
            self.assertNotIn("google.colab", namespace)

    def test_invalid_source_base_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            with self.assertRaises(ValueError):
                builder.build(root/"bad.ipynb", root=root, base_revision="main")
            path = root/builder.FILES[0]
            path.unlink()
            path.symlink_to(root/builder.FILES[1])
            with self.assertRaisesRegex(ValueError, "regular source"):
                builder.build(root/"bad.ipynb", root=root, base_revision="d"*40)

    def test_existing_authority_bytes_are_admitted_inside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="e"*40)
            workspace = root/"private"
            workspace.mkdir()
            raw = b'{"schema":"existing-owner-authority","fixed-clock":123}\n'
            calls = []
            def run(instruction, selected_workspace, **kwargs):
                admission = kwargs["authority_path"]
                self.assertTrue(admission.is_relative_to(workspace))
                self.assertEqual(admission.read_bytes(), raw)
                calls.append(instruction)
                return {"state":"SOURCE_FIXTURE_ONLY", "production_ready":False}
            engine = types.ModuleType("scripts.earnalism_orchestrator")
            engine.run, engine.feedback = run, lambda *args: None
            namespace = {"pathlib":__import__("pathlib"),"json":json,"time":__import__("time"),
                         "PRIVATE_WORKSPACE":str(workspace), "EXECUTE":True,
                         "runtime_authority_raw":raw, "runtime_context":{"original_deadline_epoch":123},
                         "INSTRUCTION":"book - Fixture", "FEEDBACK_PATH":"",
                         "AUTO_DISCONNECT_OWN_RUNTIME":False,
                         "connect_private_workspace":lambda:(workspace, workspace/"projects.json"),
                         "prepare_reviewed_software":lambda:root}
            source = "".join(json.loads(notebook.read_text())["cells"][-1]["source"])
            with mock.patch.dict("sys.modules", {"scripts.earnalism_orchestrator":engine}), redirect_stdout(io.StringIO()):
                exec(compile(source, "notebook-wiring-fixture", "exec"), namespace)
            self.assertEqual(calls, ["book - Fixture"])

    def test_setup_failure_requests_owned_shutdown_and_keeps_failure_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            notebook = root/"production.ipynb"
            builder.build(notebook, root=root, base_revision="f"*40)
            workspace = root/"private"
            workspace.mkdir()
            stopped = []
            colab = types.ModuleType("google.colab")
            colab.runtime = types.SimpleNamespace(unassign=lambda:stopped.append(True))
            namespace = {"pathlib":__import__("pathlib"),"json":json,"time":__import__("time"),
                         "PRIVATE_WORKSPACE":str(workspace),"EXECUTE":True,
                         "runtime_authority_raw":b"{}", "runtime_context":{"original_deadline_epoch":123},
                         "AUTO_DISCONNECT_OWN_RUNTIME":True,
                         "connect_private_workspace":lambda:(workspace, workspace/"projects.json"),
                         "prepare_reviewed_software":mock.Mock(side_effect=RuntimeError("source setup failed"))}
            source = "".join(json.loads(notebook.read_text())["cells"][-1]["source"])
            with mock.patch.dict("sys.modules", {"google.colab":colab}), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "setup failed"):
                    exec(compile(source, "notebook-failure-fixture", "exec"), namespace)
            self.assertEqual(stopped, [True])
            self.assertEqual(json.loads((workspace/"last-orchestrator-error.json").read_text())["state"], "FAILED_OR_UNKNOWN")
            self.assertFalse(json.loads((workspace/"last-shutdown-request.json").read_text())["provider_closure_observed"])
            first_events = set((workspace/".orchestrator/notebook-events").glob("*.json"))
            self.assertEqual(len(first_events), 2)
            with mock.patch.dict("sys.modules", {"google.colab":colab}), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, "setup failed"):
                    exec(compile(source, "notebook-repeated-failure-fixture", "exec"), namespace)
            later_events = set((workspace/".orchestrator/notebook-events").glob("*.json"))
            self.assertEqual(len(later_events), 4)
            self.assertTrue(first_events.issubset(later_events))

    def test_changed_base_dependency_and_unknown_source_are_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/"base.py").write_text("# fixed base\n")
            (root/"overlay.py").write_text("# old overlay\n")
            subprocess.run(["git","init","-q",str(root)], check=True)
            subprocess.run(["git","-C",str(root),"add","."], check=True)
            subprocess.run(["git","-C",str(root),"-c","user.name=Fixture","-c","user.email=fixture@example.invalid",
                            "commit","-qm","source fixture"], check=True)
            (root/"overlay.py").write_text("# reviewed overlay\n")
            builder.check_base_source(root, {"overlay.py":"unused"})
            (root/"base.py").write_text("# preserve this modified base\n")
            with self.assertRaisesRegex(RuntimeError, "base.py"):
                builder.check_base_source(root, {"overlay.py":"unused"})
            self.assertEqual((root/"base.py").read_text(), "# preserve this modified base\n")
            (root/"base.py").write_text("# fixed base\n")
            (root/"foreign.py").write_text("# unowned\n")
            with self.assertRaisesRegex(RuntimeError, "foreign.py"):
                builder.check_base_source(root, {"overlay.py":"unused"})

    def test_foreign_import_cache_is_refused_without_resetting_it(self):
        builder.check_import_namespace(builder.ROOT)
        old = types.ModuleType("scripts.old_capsule")
        old.__file__ = "/content/earnalism-orchestrator-old/scripts/old_capsule.py"
        with mock.patch.dict("sys.modules", {"scripts.old_capsule":old}):
            with self.assertRaisesRegex(RuntimeError, "scripts.old_capsule"):
                builder.check_import_namespace(builder.ROOT)
            import sys
            self.assertIs(sys.modules["scripts.old_capsule"], old)


if __name__ == "__main__":
    unittest.main()
