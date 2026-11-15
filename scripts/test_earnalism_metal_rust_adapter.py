"""Fixed dispatcher source tests only; no renderer, model or approval is run."""
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
from scripts import earnalism_media_adapters as media


class MetalRustDispatchTests(unittest.TestCase):
    def test_exact_fixed_topic_is_registered_without_arbitrary_module_selection(self):
        self.assertEqual(media._science_name({"science": "metal-rust"}), ("metal_rust", "MetalRust"))
        for name in ("20-metal-rust", "moon-renamed-rust", "metal_rust.finish"):
            with self.assertRaises(ValueError): media._science_name({"science": name})

    def test_missing_real_project_never_reaches_runtime_or_model(self):
        with tempfile.TemporaryDirectory() as d, patch.object(media, "_render_runtime") as runtime, \
             patch.object(media, "_run") as render:
            result = media.run_stage("visuals", {"kind": "science-animation", "science": "metal-rust", "project": {}},
                                     {"workspace": str(Path(d).resolve()), "language": "en"})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["acceptance"]["release_approved"])
        runtime.assert_not_called(); render.assert_not_called()

    def test_current_source_and_timing_are_consumed_before_any_render_setup(self):
        for mismatch in ("manuscript", "timing"):
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory() as d:
                root = Path(d).resolve()
                def put(name, value):
                    p = root / name; p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(json.dumps(value) if not isinstance(value, str) else value)
                    return media._bound(p)
                source = put("private-script.txt", "Synthetic source fixture only.")
                narration = put("narration.wav", "INERT: NOT AUDIO")
                timing = put("shared-timing.json", {"fixture": "INERT TEST ONLY"})
                timeline = put("timeline.json", {"duration": 1, "scenes": [{"scene": "gate"}]})
                assembly = put("assembly-manifest.json", {"source_root": ".", "input_files": {"private-script.txt": source["sha256"]}})
                refs = [source, narration, timing, timeline, assembly]
                for name in ("voice-binding.json", "asr-review.json", "caption-quality.json", "units.json"):
                    refs.append(put(name, {}))
                manifest = put("project.json", {"schema": "earnalism.media-project.v1", "root": ".", "files": refs,
                                              "narration": narration, "public_assets": "public"})
                bindings = {"manuscript": source, "timing": timing, "voice_profile": {"sha256": "f" * 64}}
                upstream = {"source": {"details": {"bindings": {"manuscript": source}}},
                            "timing": {"details": {"bindings": {"timing": timing}}},
                            "narration": {"details": {"bindings": {"narration": narration}}}}
                stage = "source" if mismatch == "manuscript" else "timing"
                upstream[stage]["details"]["bindings"][mismatch] = {"sha256": "b" * 64}
                validator = types.SimpleNamespace(validate_inputs=lambda p: ({}, bindings))
                with patch.object(media.importlib, "import_module", return_value=validator), \
                     patch.object(media, "_render_runtime") as runtime, patch.object(media, "_run") as render:
                    result = media.run_stage("visuals", {"kind": "science-animation", "science": "metal-rust", "project": manifest},
                                             {"workspace": str(root), "language": "en", "upstream": upstream})
                self.assertEqual(result["status"], "BLOCKED", result)
                self.assertIn("Stale handoff", result["blockers"][0])
                runtime.assert_not_called(); render.assert_not_called()


if __name__ == "__main__": unittest.main()
