"""Pure/private finishing regressions; no score, speech or video is generated."""
from pathlib import Path
import array
import tempfile
import unittest
from unittest.mock import patch

from . import finish as production


def timeline():
    # Explicit test-only ASR positions, never production narration/acceptance data.
    scenes = [
        {"scene": "question", "start": 0., "end": 12., "marks": {"equal": 9.}},
        {"scene": "flow", "start": 12., "end": 24., "marks": {"touch": 7.}},
        {"scene": "material", "start": 24., "end": 46.,
         "marks": {"metal": 2., "wood": 9., "cooling": 15.}},
        {"scene": "temperature", "start": 46., "end": 62.,
         "marks": {"stores": 4., "touch": 12.}},
        {"scene": "reverse", "start": 62., "end": 80.,
         "marks": {"warm": 2., "reverse": 6., "hotter": 10., "safety": 14.}},
        {"scene": "callback", "start": 80., "end": 100.,
         "marks": {"callback": 7., "next": 16.}},
    ]
    return {"duration": 100., "scenes": scenes}


class ThermalFinishingTests(unittest.TestCase):
    def test_plan_uses_current_explicit_audio_marks_not_earlier_episode_times(self):
        first = production.phrase_plan(timeline())
        changed = timeline()
        changed["scenes"][2]["marks"]["wood"] += 1.3
        changed["scenes"][4]["marks"]["reverse"] += .8
        second = production.phrase_plan(changed)
        for reason, delta in (("key wood/skin contrast", 1.3), ("reversal and safety", .8)):
            a = next(r for r in first["rests"] if r["reason"] == reason)
            b = next(r for r in second["rests"] if r["reason"] == reason)
            self.assertAlmostEqual(b["start"] - a["start"], delta)
        self.assertEqual(first["rests"][0]["end"], timeline()["scenes"][0]["end"])
        self.assertEqual(first["listening"], "PENDING")
        self.assertEqual(first["resemblance_review"], "PENDING")
        self.assertFalse(first["publication_approved"])
        self.assertNotIn("moon", str(first).lower())
        self.assertNotIn("spoon", str(first).lower())

    def test_missing_stale_or_wrong_scene_marks_fail_before_media_creation(self):
        for mutate in (lambda t: t["scenes"][2]["marks"].pop("wood"),
                       lambda t: t["scenes"][4]["marks"].update(safety=19.),
                       lambda t: t["scenes"][2]["marks"].update(cooling=1.),
                       lambda t: t.update(duration=101.),
                       lambda t: t["scenes"][1].update(start=12.8),
                       lambda t: t["scenes"][3].update(scene="cycle")):
            data = timeline()
            mutate(data)
            with self.assertRaises(production.QualificationError):
                production.phrase_plan(data)

    def test_new_motif_has_pinned_nearby_samples_and_sparse_valid_events(self):
        assets = production.acoustic_score.validate_assets()
        plan = production.phrase_plan(timeline())
        self.assertGreater(len(plan["events"]), 10)
        self.assertLess(len(plan["events"]), 35)
        self.assertTrue(any(e["phrase"].startswith("E A F sharp") for e in plan["events"]))
        for e in plan["events"]:
            self.assertLess(e["time"], plan["duration"])
            self.assertGreater(e["duration"], 0)
            self.assertTrue(0 < e["velocity"] < .5)
            closest = min(abs(r["root_midi"] - e["midi"]) for r in assets["samples"]
                          if r["instrument"] == e["instrument"])
            self.assertLessEqual(closest, 2)
            self.assertGreater(production.shoulder(e["time"], plan["quiet_intervals"]), .08)

    def test_phrase_fades_are_monotone_and_rest_and_boundaries_are_flat(self):
        rest = [(10., 14.)]
        g = lambda t: production.shoulder(t, rest)
        before = [g(6.8 + i * .1) for i in range(33)]
        after = [g(14. + i * .1) for i in range(46)]
        self.assertTrue(all(a >= b - 1e-12 for a, b in zip(before, before[1:])))
        self.assertTrue(all(a <= b + 1e-12 for a, b in zip(after, after[1:])))
        for t in (10., 10.1, 12., 13.9, 14.):
            self.assertEqual(g(t), 0.)
        self.assertAlmostEqual(g(6.8), 1.)
        self.assertAlmostEqual(g(18.5), 1.)
        # First/second derivatives tend to zero at both ends, avoiding abrupt re-entry.
        h = 1e-4
        for t in (6.8, 10., 14., 18.5):
            self.assertLess(abs((g(t + h) - g(t - h)) / (2 * h)), 1e-5)
            self.assertLess(abs((g(t + h) - 2 * g(t) + g(t - h)) / h ** 2), .001)

    def test_nearby_rests_cannot_raise_gain_or_break_true_silence(self):
        rests = [(8., 10.), (14., 17.)]
        for i in range(221):
            t = i * .1
            value = production.shoulder(t, rests)
            self.assertTrue(0 <= value <= 1)
            self.assertLessEqual(value, production.shoulder(t, rests[:1]))
            self.assertLessEqual(value, production.shoulder(t, rests[1:]))
        self.assertEqual(production.shoulder(14., rests), 0)

    def test_overlapping_shoulders_multiply_without_minimum_crossover_cusp(self):
        rests = [(8., 10.), (14., 17.)]
        for t in (10.9, 11.7, 12.4, 13.2):
            self.assertAlmostEqual(production.shoulder(t, rests),
                                   production.shoulder(t, rests[:1]) *
                                   production.shoulder(t, rests[1:]), places=12)
        # Smooth product also crosses its broad return peak without a derivative jump.
        h, t = 1e-4, 12.2
        g = lambda x: production.shoulder(x, rests)
        left = (g(t) - g(t-h)) / h
        right = (g(t+h) - g(t)) / h
        self.assertLess(abs(left-right), .001)

    def test_ident_tail_requires_every_decoded_sample_to_match(self):
        ident = array.array("f", [0., .1, -.2, .3])
        body = array.array("f", [.7, -.7, .8, -.8])
        with patch.object(production, "pcm", side_effect=[body + ident, ident]):
            check = production.verify_ident_tail("scored", "ident", 2)
        self.assertTrue(check["exact_decoded_pcm_match"])
        bad = array.array("f", ident)
        bad[-1] += .001
        with patch.object(production, "pcm", side_effect=[body + bad, ident]):
            with self.assertRaisesRegex(production.QualificationError, "sample equality"):
                production.verify_ident_tail("scored", "ident", 2)

    def test_existing_or_partial_outputs_are_never_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "score.wav"
            original.write_bytes(b"existing immutable candidate")
            with self.assertRaisesRegex(production.QualificationError, "preserved"):
                production.reserve_outputs(root)
            self.assertEqual(original.read_bytes(), b"existing immutable candidate")
            self.assertFalse((root / ".thermal-finish-lock.json").exists())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            production.reserve_outputs(root)
            self.assertFalse(production.load(root / ".thermal-finish-lock.json")["publication_approved"])
            with self.assertRaises(production.QualificationError):
                production.reserve_outputs(root)

    def test_exact_selected_standard_ident_and_original_sound_are_verified(self):
        manifest = production.validate_ident()
        self.assertEqual(manifest["seconds"], 3)
        self.assertEqual(manifest["version"], "earnalism-flowing-paired-v1")
        with patch.object(production, "sha", return_value="0" * 64):
            with self.assertRaisesRegex(production.QualificationError, "manifest changed"):
                production.validate_ident()

    def test_ident_append_and_mix_do_not_retime_pitch_or_reprocess_ident(self):
        command = production.append_ident_command("narration.wav", "source-sound.wav", "out.wav", 100.1)
        filters = command[command.index("-filter_complex") + 1]
        self.assertIn("apad=whole_dur=100.100000000", filters)
        self.assertIn("[a][b]concat=n=2", filters)
        self.assertIn("-n", command)
        for forbidden in ("atempo", "rubberband", "asetrate", "pitch", "sidechain", "silenceremove"):
            self.assertNotIn(forbidden, filters)
            self.assertNotIn(forbidden, production.MIX_FILTER)
        self.assertNotIn("loudnorm", filters)  # The ident bypasses body mastering.
        self.assertEqual(command[-1], "out.wav")

    def test_stale_assembly_binding_blocks_before_composition(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            production.write_new(root / "assembly-manifest.json", {
                "state": "ASSEMBLED_PRIVATE_REQUIRES_REVIEW", "output_files": {"timeline.json": "wrong"}})
            production.write_new(root / "voice-binding.json", {})
            production.write_new(root / "timeline.json", timeline())
            with patch.object(production, "render_score") as compose:
                with self.assertRaisesRegex(production.QualificationError, "Stale assembly"):
                    production.finish(root)
                compose.assert_not_called()
            self.assertFalse((root / ".thermal-finish-lock.json").exists())

    def test_source_level_score_does_not_monkeypatch_shared_composer(self):
        # Protect the existing acoustic engine against leakage from an episode plan.
        original = production.acoustic_score.plan
        production.phrase_plan(timeline())
        self.assertIs(production.acoustic_score.plan, original)


if __name__ == "__main__":
    unittest.main()
