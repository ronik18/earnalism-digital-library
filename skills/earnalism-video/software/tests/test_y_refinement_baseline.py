"""Owner baseline choices stay separate from unheard candidates and approval."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import studio
from expectations import audit, ROOT


class YRefinementBaselineTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        for name in ["config/defaults.json", "config/editorial-contract.json",
                     "src/branding.mjs", "src/social-safe-area.mjs", "src/opening-visibility.mjs", "src/readability.mjs",
                     "assets/standard-intro/v1/production-lockup.png",
                     "public/brand-sting/production-lockup.png", "watch-template.html"]:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        return root

    def test_new_default_job_uses_exact_selected_y_without_sampling_changes(self):
        policy = studio.load(ROOT / "config/defaults.json")
        profile = studio.load(ROOT / "config/b-meaning-first-v1.json")
        scene = {"id": "test", "text": "The Moon reflects sunlight.", "narration_seed": 20261028}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            studio.write(folder / "episode.json", {"id": "private-fixture", "private_test": True,
                                                  "scenes": [scene]})
            job = studio.make_job(folder, {})
        self.assertEqual(policy["default_voice_profile"], profile["id"])
        self.assertEqual(job["segments"][0]["instruct"], profile["instruction"])
        self.assertEqual(job["segments"][0]["speaker"], "Ryan")
        self.assertEqual(job["segments"][0]["seed"], 20261028)
        self.assertEqual(job["generation"], {"temperature": .85})
        self.assertEqual(job["max_attempts"], 3)
        self.assertFalse(policy["voice_profiles"][profile["id"]]["recording_acceptance"])
        self.assertFalse(policy["voice_profiles"][profile["id"]]["publication_approval"])

    def test_explicit_historical_scene_direction_is_not_silently_rewritten(self):
        policy = studio.load(ROOT / "config/defaults.json")
        scene = {"text": "The Moon reflects sunlight.", "voice_profile": "original_warm_baritone_v2"}
        before = copy.deepcopy(scene)
        result = studio.narration_instruction(scene, policy)
        self.assertEqual(result, policy["voice_profiles"][scene["voice_profile"]]["instruction"])
        self.assertEqual(scene, before)
        self.assertNotEqual(result, policy["instruction"])

    def test_exact_selected_binding_and_historical_instruction_are_retained(self):
        policy = studio.load(ROOT / "config/defaults.json")
        selected = policy["voice_profiles"][policy["default_voice_profile"]]
        self.assertEqual(selected["selected_audition_sha256"],
            "cdfdbb6cdd23a0436e4c15b3566a0ba3e451793ba06adbfc9bcfc3b44b5672e2")
        self.assertEqual(hashlib.sha256(selected["instruction"].encode()).hexdigest(),
            "92e2b6b1e725b3900399f542d756ca638381479fd2c399f37ef65e87247549f3")
        old = policy["voice_profiles"]["original_warm_baritone_v2"]
        self.assertEqual(hashlib.sha256(old["instruction"].encode()).hexdigest(),
            "fe1aec4c7c85f6abb50cb2e150fafcd1aad4fb00ff8a1fdd108c0404ecd067bf")

    def test_unheard_candidate_cannot_silently_become_the_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            policy = json.loads((root / "config/defaults.json").read_text())
            policy["default_voice_profile"] = "unheard_candidate"
            policy["instruction"] = "A new unheard performance."
            policy["voice_profiles"]["unheard_candidate"] = {"instruction": policy["instruction"]}
            (root / "config/defaults.json").write_text(json.dumps(policy))
            with self.assertRaisesRegex(ValueError, "Default drift"):
                audit(root)

    def test_matching_profile_name_cannot_hide_changed_instruction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            policy = json.loads((root / "config/defaults.json").read_text())
            profile = policy["voice_profiles"][policy["default_voice_profile"]]
            profile["instruction"] += " Make this a different performance."
            policy["instruction"] = profile["instruction"]
            (root / "config/defaults.json").write_text(json.dumps(policy))
            with self.assertRaisesRegex(ValueError, "baseline instruction changed"):
                audit(root)

    def test_baseline_selection_never_implicitly_approves_a_repaired_take_or_publication(self):
        for key in ["recording_acceptance", "publication_approval"]:
            for container in ["policy", "contract"]:
                with self.subTest(key=key, container=container), tempfile.TemporaryDirectory() as directory:
                    root = self.fixture(directory)
                    path = root / "config" / ("defaults.json" if container == "policy" else "editorial-contract.json")
                    data = json.loads(path.read_text())
                    value = data["voice_profiles"][data["default_voice_profile"]] if container == "policy" else data["voice_selection"]
                    value[key] = True
                    path.write_text(json.dumps(data))
                    with self.assertRaisesRegex(ValueError, "cannot imply"):
                        audit(root)


if __name__ == "__main__":
    unittest.main()
