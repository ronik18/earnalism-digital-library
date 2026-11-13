"""Behavioral tests of private scoring decisions and candidate/evidence binding."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.audiobook_score import (DIRECTION_SCHEMA, EDIT_SCHEMA, INPUT_SCHEMA, TIMING_SCHEMA,
                                     apply_editorial_edits,
                                     load_json, plan_score, prepare_director, sha256_file,
                                     validate_input)


class ScoreFixture:
    """Explicit synthetic assertions, never a real timing/rights acceptance."""
    def __init__(self, root):
        self.root = Path(root)
        self.input_path = self.root / "input.json"
        self.direction_path = self.root / "direction.json"
        phrases = ["They laughed together.", "Then the doctor became serious.",
                   "She wept for her friend.", "Why did you leave?", "Was that a joke?",
                   "She was not happy; her laughter was bitter."]
        text = "\n\n".join(phrases)
        (self.root / "manuscript.txt").write_text(text, encoding="utf-8")
        (self.root / "voice.wav").write_bytes(b"SYNTHETIC planner fixture, not audio")
        self.manuscript_hash = sha256_file(self.root / "manuscript.txt")
        self.narration_hash = sha256_file(self.root / "voice.wav")
        cues, offset = [], 0
        for i, phrase in enumerate(phrases):
            cues.append({"id": f"c{i}", "start_ms": i * 4000, "end_ms": i * 4000 + 3000,
                         "text_start": offset, "text_end": offset + len(phrase), "text": phrase})
            offset += len(phrase) + 2
        self.timing = {"schema": TIMING_SCHEMA, "manuscript_sha256": self.manuscript_hash,
            "narration_sha256": self.narration_hash, "duration_ms": 24000,
            "method": "synthetic_fixture", "provenance": {"tool": "synthetic test fixture",
            "version": "1", "boundary_validation": "synthetic_fixture"}, "cues": cues}
        self.write("timing.json", self.timing)
        self.input = {"schema": INPUT_SCHEMA, "fixture_mode": True, "territory": "IN",
            "manuscript": {"path": "manuscript.txt", "sha256": self.manuscript_hash, "language": "en"},
            "narration": {"path": "voice.wav", "sha256": self.narration_hash, "duration_ms": 24000},
            "timing": self.ref("timing.json"), "assets": []}
        for mood in ("amusement", "serious", "sadness", "joy", "reflective"):
            media = f"{mood}.wav"
            (self.root / media).write_bytes(f"synthetic {mood} stem".encode())
            digest = sha256_file(self.root / media)
            rights = {"schema": "earnalism.audiobook_music_rights.v1", "asset_sha256": digest,
                "rights_holder": "synthetic test fixture", "license_id": "test-only",
                "scope": "commercial_audiobook", "territories": ["IN"], "commercial_use": True,
                "distribution": True, "derivative_mixing": True, "instrumental": True,
                "approval_status": "APPROVED", "approved_by": "synthetic fixture only",
                "approval_ref": "synthetic fixture only; no actual license acceptance"}
            self.write(f"{mood}-rights.json", rights)
            self.input["assets"].append({"id": mood, **self.ref(media), "duration_ms": 30000,
                "moods": [mood], "energy": 0.5, "transition_group": "family-A",
                "rights": self.ref(f"{mood}-rights.json")})
        moods = [("amusement", "playful", "statement"), ("neutral", "serious", "narration"),
                 ("sadness", "reflective", "statement"), ("sadness", "serious", "question"),
                 ("amusement", "playful", "question"), ("unknown", "serious", "statement")]
        self.direction = {"schema": DIRECTION_SCHEMA, "manuscript_sha256": self.manuscript_hash,
            "narration_sha256": self.narration_hash, "timing_sha256": self.ref("timing.json")["sha256"],
            "provenance": {"method": "editor", "agent_or_model": "synthetic fixture",
                           "assessment_basis": "text_only", "version": "1"}, "annotations": []}
        for i, (emotion, tone, act) in enumerate(moods):
            self.direction["annotations"].append({"cue_id": f"c{i}", "emotion": emotion,
                "narrative_tone": tone, "speech_act": act, "intensity": 0.6,
                "confidence": 0.95 if emotion != "unknown" else 0.4,
                "uncertain": emotion == "unknown", "score": "music", "transition": "auto",
                "context_cue_ids": [f"c{i}"], "rationale": phrases[i]})
        self.save()

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def ref(self, name):
        return {"path": name, "sha256": sha256_file(self.root / name)}

    def save(self):
        self.write("input.json", self.input)
        self.write("direction.json", self.direction)

    def save_timing(self):
        self.write("timing.json", self.timing)
        self.input["timing"] = self.ref("timing.json")
        self.direction["timing_sha256"] = self.input["timing"]["sha256"]
        self.save()

    def plan(self):
        self.save()
        return plan_score(self.input_path, self.direction_path)


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = ScoreFixture(self.temp.name)

    def test_laughter_seriousness_sadness_and_questions_follow_measured_anchors(self):
        p = self.f.plan()
        d = p["decisions"]
        self.assertEqual([x["asset_id"] for x in d],
                         ["amusement", "serious", "sadness", "sadness", "amusement", None])
        self.assertEqual([x["anchor_ms"] for x in d], [0, 4000, 8000, 12000, 16000, 20000])
        self.assertEqual(d[3]["action"], "KEEP")  # Sad questioning stays sad, not automatic suspense.
        self.assertEqual(d[4]["mood"], "amusement")
        self.assertTrue(d[1]["hard_turn"])
        self.assertFalse(d[1]["dwell_suppressed"])
        self.assertFalse(p["release_approved"])
        self.assertTrue(p["fixture_mode"])
        self.assertEqual(p["acceptance"]["listening"], "UNPERFORMED")

    def test_no_cheerful_tail_after_abrupt_serious_revelation(self):
        p = self.f.plan()
        cheerful, serious = p["placements"][:2]
        self.assertEqual(cheerful["end_ms"], 4000)
        self.assertLessEqual(cheerful["fade_out_ms"], 240)
        self.assertEqual(serious["start_ms"], 4000)
        self.assertLessEqual(serious["fade_in_ms"], 240)

    def test_same_mood_continues_without_restart_and_unknown_fades_to_silence(self):
        p = self.f.plan()
        sad = [x for x in p["placements"] if x["asset_id"] == "sadness"]
        self.assertEqual(len(sad), 1)
        self.assertEqual(sad[0]["start_ms"], 8000)
        self.assertEqual(max(x["end_ms"] for x in p["placements"]), 20000)
        self.assertEqual(p["review_items"][-1]["reason"], "UNCERTAIN_INTERPRETATION")

    def test_minimum_dwell_prevents_minor_sentence_by_sentence_switches(self):
        self.f.direction["annotations"][1].update(emotion="neutral", narrative_tone="reflective")
        d = self.f.plan()["decisions"][1]
        self.assertEqual(d["asset_id"], "amusement")
        self.assertTrue(d["dwell_suppressed"])

    def test_explicit_strong_turn_overrides_dwell(self):
        self.f.direction["annotations"][1].update(emotion="neutral", narrative_tone="reflective", transition="strong")
        d = self.f.plan()["decisions"][1]
        self.assertEqual(d["asset_id"], "reflective")
        self.assertFalse(d["dwell_suppressed"])

    def test_low_confidence_or_uncertainty_never_reuses_old_cheerful_music(self):
        for patch in ({"confidence": 0.6}, {"uncertain": True}, {"emotion": "unknown"}):
            with self.subTest(patch=patch):
                original = copy.deepcopy(self.f.direction["annotations"][1])
                self.f.direction["annotations"][1].update(patch)
                self.assertIsNone(self.f.plan()["decisions"][1]["asset_id"])
                self.f.direction["annotations"][1] = original

    def test_short_scene_stem_does_not_need_whole_audiobook_length(self):
        self.f.input["assets"][0]["duration_ms"] = 4000
        p = self.f.plan()
        self.assertEqual(p["decisions"][0]["asset_id"], "amusement")
        self.assertEqual(p["placements"][0]["end_ms"], 4000)

    def test_measured_entry_offset_is_placed_and_reduces_finite_capacity(self):
        asset = self.f.input["assets"][0]
        asset.update(duration_ms=5000, entry_offset_ms=1000)
        p = self.f.plan()
        self.assertEqual(p["placements"][0]["source_offset_ms"], 1000)
        self.assertEqual(p["placements"][0]["end_ms"], 4000)
        asset["duration_ms"] = 4000
        p = self.f.plan()
        self.assertIsNone(p["decisions"][0]["asset_id"])
        self.assertEqual(p["review_items"][0]["reason"], "NO_SUITABLE_LICENSED_STEM")

    def test_offset_capacity_cannot_be_extended_by_minimum_dwell(self):
        self.f.input["assets"][0].update(duration_ms=9000, entry_offset_ms=5000)
        self.f.direction["annotations"][1].update(emotion="neutral", narrative_tone="reflective")
        p = self.f.plan()
        self.assertEqual(p["decisions"][0]["asset_id"], "amusement")
        self.assertEqual(p["decisions"][1]["asset_id"], "reflective")
        self.assertFalse(p["decisions"][1]["dwell_suppressed"])

    def test_offset_limits_outgoing_tail_and_actual_overlap_controls_entry_fade(self):
        self.f.input["policy"] = {"min_dwell_ms": 0}
        self.f.input["assets"][0].update(duration_ms=9000, entry_offset_ms=4500)
        self.f.input["assets"][4]["entry_fade_ms"] = 1400
        self.f.direction["annotations"][1].update(emotion="neutral", narrative_tone="reflective")
        first, second = self.f.plan()["placements"][:2]
        self.assertEqual(first["end_ms"], 4500)
        self.assertEqual(first["source_offset_ms"] + first["end_ms"] - first["start_ms"], 9000)
        self.assertEqual(first["fade_out_ms"], 500)
        self.assertEqual(second["fade_in_ms"], 500)

    def test_explicit_entry_fade_softens_new_attack_without_extending_abrupt_old_mood(self):
        self.f.input["policy"] = {"hard_turn_fade_ms": 350}
        self.f.input["assets"][1].update(entry_offset_ms=1360, entry_fade_ms=1400)
        first, second = self.f.plan()["placements"][:2]
        self.assertEqual(first["end_ms"], second["start_ms"])
        self.assertEqual(first["fade_out_ms"], 350)
        self.assertEqual(second["fade_in_ms"], 1400)
        self.assertEqual(second["source_offset_ms"], 1360)
        self.f.input["assets"][1]["entry_fade_ms"] = 5000
        second = self.f.plan()["placements"][1]
        self.assertEqual(second["fade_in_ms"], 2000)  # Half the nominal four-second run.

    def test_invalid_entry_controls_and_offsets_outside_authorized_loop_are_rejected(self):
        asset = self.f.input["assets"][0]
        for key, values in (("entry_offset_ms", [-1, 30000, True, 1.5]),
                            ("entry_fade_ms", [0, 19, 5001, True, 20.5])):
            for value in values:
                with self.subTest(key=key, value=value):
                    asset[key] = value
                    with self.assertRaisesRegex(ValueError, key):
                        self.f.plan()
            asset.pop(key)
        proof = {"schema": "earnalism.audiobook_music_loop.v1", "asset_sha256": asset["sha256"],
                 "start_ms": 1000, "end_ms": 2000, "seam_verified": True,
                 "provenance": "synthetic fixture only"}
        self.f.write("entry-loop.json", proof)
        asset["loop"] = {"start_ms": 1000, "end_ms": 2000, "evidence": self.f.ref("entry-loop.json")}
        asset["entry_offset_ms"] = 1000
        with self.assertRaisesRegex(ValueError, "entry_offset_ms"):
            self.f.plan()
        asset["entry_offset_ms"] = 500
        p = self.f.plan()
        self.assertEqual(p["placements"][0]["source_offset_ms"], 500)
        self.assertEqual(p["placements"][0]["start_ms"], 0)

    def test_missing_stem_yields_silence_and_useful_composition_brief(self):
        self.f.input["assets"] = []
        p = self.f.plan()
        self.assertEqual(p["placements"], [])
        self.assertEqual(p["review_items"][0]["reason"], "NO_SUITABLE_LICENSED_STEM")
        self.assertEqual(p["review_items"][0]["composition_brief"]["mood"], "amusement")

    def test_short_nonloop_cannot_be_held_past_capacity_by_dwell(self):
        self.f.input["assets"][0]["duration_ms"] = 4000
        self.f.direction["annotations"][1].update(emotion="neutral", narrative_tone="reflective")
        p = self.f.plan()
        self.assertEqual(p["decisions"][1]["asset_id"], "reflective")
        self.assertFalse(p["decisions"][1]["dwell_suppressed"])

    def test_compatible_crossfade_envelopes_have_identical_overlap_length(self):
        p = self.f.plan()
        serious = next(x for x in p["placements"] if x["asset_id"] == "serious")
        sad = next(x for x in p["placements"] if x["asset_id"] == "sadness")
        overlap = serious["end_ms"] - sad["start_ms"]
        # Emotional pivots use a bounded fast fade through the exact anchor.
        self.assertEqual(overlap, 0)
        self.f.input["policy"] = {"min_dwell_ms": 0}
        self.f.direction["annotations"][1].update(emotion="neutral", narrative_tone="reflective")
        p = self.f.plan()
        first, second = p["placements"][:2]
        overlap = first["end_ms"] - second["start_ms"]
        self.assertGreater(overlap, 0)
        self.assertEqual(first["fade_out_ms"], overlap)
        self.assertEqual(second["fade_in_ms"], overlap)

    def test_loop_requires_bound_verified_seam_evidence(self):
        asset = self.f.input["assets"][0]
        proof = {"schema": "earnalism.audiobook_music_loop.v1", "asset_sha256": asset["sha256"],
                 "start_ms": 1000, "end_ms": 2000, "seam_verified": True,
                 "provenance": "synthetic fixture only"}
        self.f.write("loop.json", proof)
        asset["loop"] = {"start_ms": 1000, "end_ms": 2000, "evidence": self.f.ref("loop.json")}
        asset["duration_ms"] = 2000
        self.assertEqual(self.f.plan()["decisions"][0]["asset_id"], "amusement")
        for patch in ({"seam_verified": False}, {"asset_sha256": "0" * 64}, {"end_ms": 1500}):
            with self.subTest(patch=patch):
                self.f.write("loop.json", {**proof, **patch})
                asset["loop"]["evidence"] = self.f.ref("loop.json")
                with self.assertRaisesRegex(ValueError, "loop evidence"):
                    self.f.plan()

    def test_dense_cues_do_not_create_triple_overlap_or_timeline_drift(self):
        self.f.input["policy"] = {"min_dwell_ms": 0}
        for i, cue in enumerate(self.f.timing["cues"]):
            cue.update(start_ms=i * 100, end_ms=i * 100 + 90)
        self.f.save_timing()
        p = self.f.plan()
        for t in range(0, 700):
            active = [x for x in p["placements"] if x["start_ms"] <= t < x["end_ms"]]
            self.assertLessEqual(len(active), 2)
        self.assertEqual(p["decisions"][4]["anchor_ms"], 400)

    def test_incompatible_families_do_not_overlap(self):
        self.f.input["assets"][2]["transition_group"] = "incompatible-key-tempo"
        p = self.f.plan()
        serious = next(x for x in p["placements"] if x["asset_id"] == "serious")
        sad = next(x for x in p["placements"] if x["asset_id"] == "sadness")
        self.assertEqual(serious["end_ms"], sad["start_ms"])

    def test_stale_audio_manuscript_direction_and_rights_fail_closed(self):
        for name in ("voice.wav", "manuscript.txt", "timing.json", "amusement-rights.json"):
            with self.subTest(name=name):
                path = self.f.root / name
                original = path.read_bytes()
                path.write_bytes(original + b"changed")
                with self.assertRaises(ValueError):
                    self.f.plan()
                path.write_bytes(original)
        self.f.direction["narration_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "bindings"):
            self.f.plan()

    def test_production_rejects_synthetic_and_estimated_timing(self):
        self.f.input["fixture_mode"] = False
        with self.assertRaisesRegex(ValueError, "timing method"):
            self.f.plan()
        for method in ("estimated", "deterministic_estimated_sync"):
            self.f.timing["method"] = method
            self.f.save_timing()
            with self.assertRaisesRegex(ValueError, "timing method"):
                self.f.plan()

    def test_source_omissions_reordering_bad_ranges_and_duplicate_ids_rejected(self):
        original = copy.deepcopy(self.f.timing)
        patches = [lambda cs: cs.pop(2),
                   lambda cs: cs[1].update(start_ms=0),
                   lambda cs: cs[1].update(id="c0"),
                   lambda cs: cs[1].update(text="paraphrase"),
                   lambda cs: cs[-1].update(end_ms=25000),
                   lambda cs: cs[0].update(start_ms=True)]
        for patch in patches:
            with self.subTest(patch=patch):
                self.f.timing = copy.deepcopy(original)
                patch(self.f.timing["cues"])
                self.f.save_timing()
                with self.assertRaises(ValueError):
                    self.f.plan()

    def test_rights_fail_without_distribution_mixing_instrumental_or_territory(self):
        name = "amusement-rights.json"
        original = load_json(self.f.root / name)
        for key, value in (("distribution", False), ("derivative_mixing", False),
                           ("instrumental", False), ("commercial_use", "true"),
                           ("territories", ["US"]), ("approval_status", "PENDING")):
            with self.subTest(key=key):
                rights = {**original, key: value}
                self.f.write(name, rights)
                self.f.input["assets"][0]["rights"] = self.f.ref(name)
                with self.assertRaisesRegex(ValueError, "rights"):
                    self.f.plan()

    def test_invalid_direction_and_policy_types_rejected(self):
        for patch in ({"confidence": True}, {"intensity": float("inf")},
                      {"speech_act": "interrogation_as_emotion"},
                      {"context_cue_ids": ["nonexistent"]}, {"unexpected": 1}):
            with self.subTest(patch=patch):
                original = copy.deepcopy(self.f.direction["annotations"][0])
                self.f.direction["annotations"][0].update(patch)
                with self.assertRaises(ValueError):
                    self.f.plan()
                self.f.direction["annotations"][0] = original
        self.f.input["policy"] = {"crossfade_ms": True}
        with self.assertRaises(ValueError):
            self.f.plan()

    def test_duplicate_or_missing_annotation_rejected(self):
        self.f.direction["annotations"].append(self.f.direction["annotations"][0])
        with self.assertRaisesRegex(ValueError, "duplicate annotation"):
            self.f.plan()
        self.f.direction["annotations"] = self.f.direction["annotations"][:-2]
        with self.assertRaisesRegex(ValueError, "every cue"):
            self.f.plan()

    def test_duplicate_json_keys_and_nonfinite_numbers_rejected(self):
        for text in ('{"a":1,"a":2}', '{"a": NaN}', '{"a": 1e999}'):
            self.f.input_path.write_text(text)
            if "1e999" in text:
                with self.assertRaises(ValueError):
                    validate_input(self.f.input_path)
            else:
                with self.assertRaises(ValueError):
                    load_json(self.f.input_path)

    def test_director_packet_retains_complete_context_and_does_not_approve_template(self):
        packet = prepare_director(self.f.input_path)
        self.assertIn("not happy", packet["complete_manuscript"])
        self.assertIn("sarcasm", packet["instructions"])
        self.f.write("direction.json", packet["direction_template"])
        with self.assertRaisesRegex(ValueError, "template provenance"):
            plan_score(self.f.input_path, self.f.direction_path)

    def test_cli_plan_refuses_overwrite_and_render_rejects_tampered_plan(self):
        script = Path(__file__).with_name("audiobook_score.py")
        output = self.f.root / "plan.json"
        args = [sys.executable, str(script), "plan", "--input", str(self.f.input_path),
                "--direction", str(self.f.direction_path), "--output", str(output)]
        r = subprocess.run(args, capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run(args, capture_output=True, text=True, timeout=15)
        self.assertNotEqual(r.returncode, 0)
        plan = load_json(output)
        plan["placements"][0]["start_ms"] = 42
        self.f.write("plan.json", plan)
        r = subprocess.run([sys.executable, str(script), "render", "--input", str(self.f.input_path),
            "--direction", str(self.f.direction_path), "--plan", str(output), "--output-dir", str(self.f.root / "mix")],
            capture_output=True, text=True, timeout=15)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("stale", r.stderr)
        self.assertFalse((self.f.root / "mix").exists())

    def test_editorial_feedback_can_use_an_unused_cleared_asset_without_rewriting_baseline(self):
        baseline = self.f.plan()
        self.f.write("plan.json", baseline)
        placements = copy.deepcopy(baseline["placements"])
        placements[0].update(asset_id="joy", fade_out_ms=2000)
        edit = {"schema": EDIT_SCHEMA, "base_plan_sha256": sha256_file(self.f.root / "plan.json"),
                "feedback": "Keep the opening warmer and soften the exit.", "placements": placements}
        self.f.write("edits.json", edit)
        revised = apply_editorial_edits(self.f.input_path, self.f.root / "plan.json", baseline, self.f.root / "edits.json")
        self.assertEqual(revised["placements"], placements)
        self.assertEqual(revised["baseline_decisions"], baseline["decisions"])
        self.assertNotIn("decisions", revised)
        self.assertEqual(baseline["placements"][0]["asset_id"], "amusement")
        self.assertEqual(revised["narration"], baseline["narration"])
        self.assertEqual(revised["timing"], baseline["timing"])
        self.assertIn("joy", {asset["id"] for asset in revised["assets"]})
        self.assertFalse(revised["release_approved"])
        self.assertEqual(revised["acceptance"]["listening"], "UNPERFORMED")

    def test_editorial_edit_rejects_stale_baseline_unknown_asset_and_invented_cue(self):
        baseline = self.f.plan()
        self.f.write("plan.json", baseline)
        original = {"schema": EDIT_SCHEMA, "base_plan_sha256": sha256_file(self.f.root / "plan.json"),
                    "feedback": "Repair a confirmed dropout.", "placements": baseline["placements"]}
        for patch in (lambda e: e.update(base_plan_sha256="0" * 64),
                      lambda e: e["placements"][0].update(asset_id="uncleared"),
                      lambda e: e["placements"][0].update(anchor_cue_id="invented")):
            edit = copy.deepcopy(original)
            patch(edit)
            self.f.write("edits.json", edit)
            with self.assertRaises(ValueError):
                apply_editorial_edits(self.f.input_path, self.f.root / "plan.json", baseline, self.f.root / "edits.json")

    def test_editorial_edit_rechecks_current_music_rights(self):
        baseline = self.f.plan()
        self.f.write("plan.json", baseline)
        self.f.write("edits.json", {"schema": EDIT_SCHEMA,
            "base_plan_sha256": sha256_file(self.f.root / "plan.json"),
            "feedback": "Extend the licensed bed.", "placements": baseline["placements"]})
        rights = load_json(self.f.root / "amusement-rights.json")
        rights["distribution"] = False
        self.f.write("amusement-rights.json", rights)
        self.f.input["assets"][0]["rights"] = self.f.ref("amusement-rights.json")
        self.f.save()
        with self.assertRaisesRegex(ValueError, "rights"):
            apply_editorial_edits(self.f.input_path, self.f.root / "plan.json", baseline, self.f.root / "edits.json")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "local ffmpeg/ffprobe required")
    def test_complete_cli_director_plan_render_with_real_synthetic_media(self):
        # These tones test the complete contract, never narrative interpretation
        # or rights/fidelity acceptance of a real book.
        for filename, hz, duration in (("voice.wav", 220, 24), ("music.wav", 660, 30)):
            subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i",
                            f"sine=frequency={hz}:sample_rate=48000:duration={duration}",
                            "-c:a", "pcm_s16le", str(self.f.root / filename)],
                           check=True, capture_output=True, timeout=15)
        self.f.input["narration"]["sha256"] = sha256_file(self.f.root / "voice.wav")
        self.f.timing["narration_sha256"] = self.f.input["narration"]["sha256"]
        self.f.direction["narration_sha256"] = self.f.input["narration"]["sha256"]
        for asset in self.f.input["assets"]:
            asset.update(self.f.ref("music.wav"))
            rights_name = asset["rights"]["path"]
            rights = load_json(self.f.root / rights_name)
            rights["asset_sha256"] = asset["sha256"]
            self.f.write(rights_name, rights)
            asset["rights"] = self.f.ref(rights_name)
        self.f.save_timing()
        script = Path(__file__).with_name("audiobook_score.py")
        shared = ["--input", str(self.f.input_path)]
        for command in (["prepare-director", *shared, "--output", str(self.f.root / "packet.json")],
                        ["plan", *shared, "--direction", str(self.f.direction_path), "--output", str(self.f.root / "plan.json")],
                        ["render", *shared, "--direction", str(self.f.direction_path), "--plan", str(self.f.root / "plan.json"),
                         "--output-dir", str(self.f.root / "render")]):
            r = subprocess.run([sys.executable, str(script), *command], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
        report = load_json(self.f.root / "render/report.json")
        self.assertTrue(report["fixture_mode"])
        self.assertFalse(report["release_approved"])
        self.assertAlmostEqual(report["duration_ms"], 24000, delta=2)
        self.assertEqual(report["dry_narration"]["sha256"], self.f.input["narration"]["sha256"])
        baseline = load_json(self.f.root / "plan.json")
        placements = copy.deepcopy(baseline["placements"])
        placements[0]["end_ms"] = 5000
        self.f.write("edits.json", {"schema": EDIT_SCHEMA,
            "base_plan_sha256": sha256_file(self.f.root / "plan.json"),
            "feedback": "Replace the abrupt opening exit with an overlapping tail.",
            "placements": placements})
        r = subprocess.run([sys.executable, str(script), "render", *shared,
            "--direction", str(self.f.direction_path), "--plan", str(self.f.root / "plan.json"),
            "--edits", str(self.f.root / "edits.json"), "--output-dir", str(self.f.root / "edited")],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        effective = load_json(self.f.root / "edited/effective-plan.json")
        edited_report = load_json(self.f.root / "edited/report.json")
        self.assertEqual(effective["placements"], placements)
        self.assertEqual(effective["narration"], baseline["narration"])
        self.assertEqual(effective["baseline_decisions"], baseline["decisions"])
        self.assertEqual(edited_report["outputs"]["effective_plan"]["sha256"],
                         sha256_file(self.f.root / "edited/effective-plan.json"))
        self.assertAlmostEqual(edited_report["duration_ms"], 24000, delta=2)


if __name__ == "__main__":
    unittest.main()
