"""Synthetic audio tests: no provider, network, production or release writes."""

from __future__ import annotations

from array import array
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave

from scripts.audiobook_score_renderer import ScoreRenderError, _graph_file_option, render_score


class FilterGraphCompatibilityTests(unittest.TestCase):
    def test_graph_file_option_supports_representative_old_and_new_help(self):
        cases = [
            ("-filter_complex graph\n-filter_complex_script filename  read complex filtergraph from a file", "-filter_complex_script"),
            ("-filter_complex graph\n-filter_threads  number of non-complex filter threads", "-/filter_complex"),
        ]
        for help_text, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(_graph_file_option(help_text), expected)


def fixture(path: Path, duration_ms: int, *, voice: bool = False, loop_middle: bool = False, gain_db: float = 0) -> dict:
    rate = 48_000
    frames = bytearray()
    for index in range(duration_ms * 48):
        seconds = index / rate
        if voice:
            amplitude = 0.35 if 2 <= seconds < 4 or 6 <= seconds < 8 else 0.0
            frequency = 220
        else:
            amplitude, frequency = 0.12, 660
            if loop_middle and not 1 <= seconds < 3:
                amplitude = 0.0
        frames.extend(struct.pack("<h", round(32767 * amplitude * 10 ** (gain_db / 20) * math.sin(2 * math.pi * frequency * seconds))))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "duration_ms": duration_ms}


def rms(path: Path, start: float, duration: float) -> float:
    result = subprocess.run([
        "ffmpeg", "-v", "error", "-nostdin", "-ss", str(start), "-i", str(path),
        "-t", str(duration), "-ac", "1", "-ar", "48000", "-f", "f32le", "-",
    ], capture_output=True, timeout=20, check=True)
    values = array("f")
    values.frombytes(result.stdout)
    return math.sqrt(sum(value * value for value in values) / len(values))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "local ffmpeg/ffprobe are required")
class ScoreRendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        narration = fixture(self.root / "voice.wav", 10_000, voice=True)
        asset = {"id": "bed", **fixture(self.root / "bed.wav", 10_000), "loop": None}
        self.plan = {
            "schema": "earnalism.audiobook_score.plan.v1", "release_approved": False,
            "fixture_mode": True, "narration": narration, "assets": [asset],
            "placements": [{
                "asset_id": "bed", "start_ms": 0, "end_ms": 10_000,
                "source_offset_ms": 0, "fade_in_ms": 100, "fade_out_ms": 100,
                "gain_db": 0, "anchor_cue_id": "measured-001",
            }],
            "policy": {
                "music_lufs": -34, "target_lufs": -18, "max_true_peak_dbfs": -1.5,
                "duck_threshold_db": -32, "duck_ratio": 6, "duck_attack_ms": 15,
                "duck_release_ms": 500,
            },
        }

    def test_actual_render_ducks_music_from_speech_and_preserves_timeline(self):
        output = self.root / "rendered"
        report = render_score(self.plan, output)
        music = output / "music_stem.wav"
        pause_level = rms(music, 0.6, 0.8)
        speech_level = rms(music, 2.5, 0.8)
        self.assertGreater(pause_level, speech_level * 2)
        self.assertLess(abs(report["duration_ms"] - 10_000), 2)
        self.assertLess(abs(report["outputs"]["music_stem"]["duration_ms"] - 10_000), 2)
        self.assertLessEqual(report["final_mix_measurements"]["input_tp"], -1.4)
        self.assertLess(abs(report["final_mix_measurements"]["input_i"] + 18), 1)
        self.assertFalse(report["release_approved"])
        self.assertEqual(report["subjective_emotional_appropriateness"], "UNPERFORMED")
        self.assertEqual(json.loads((output / "report.json").read_text()), report)
        self.assertEqual(hashlib.sha256((self.root / "voice.wav").read_bytes()).hexdigest(), self.plan["narration"]["sha256"])
        self.assertEqual(sorted(path.name for path in output.iterdir()),
                         ["effective-plan.json", "final_mix.wav", "music_stem.wav", "report.json"])

    def test_absolute_overlapping_placements_do_not_shorten_timeline(self):
        first = {**self.plan["placements"][0], "start_ms": 1000, "end_ms": 5500, "fade_out_ms": 1500}
        second = {**first, "start_ms": 4000, "end_ms": 9000, "fade_in_ms": 1500, "fade_out_ms": 100}
        self.plan["placements"] = [first, second]
        output = self.root / "overlap"
        report = render_score(self.plan, output)
        self.assertEqual(report["placement_count"], 2)
        self.assertLess(abs(report["duration_ms"] - 10_000), 2)
        self.assertLess(rms(output / "music_stem.wav", 0, 0.5), 0.000001)
        self.assertGreater(rms(output / "music_stem.wav", 8.5, 0.2), 0.0001)
        self.assertLess(rms(output / "music_stem.wav", 9.5, 0.4), 0.000001)

    def test_quiet_voice_is_normalized_before_it_drives_ducking(self):
        self.plan["narration"] = fixture(self.root / "quiet-voice.wav", 10_000, voice=True, gain_db=-24)
        output = self.root / "quiet-render"
        report = render_score(self.plan, output)
        self.assertLess(report["dry_narration_measurements"]["input_i"], -30)
        self.assertGreater(report["voice_gain_db"], 12)
        self.assertLessEqual(report["voice_gain_db"], 24)
        self.assertLess(abs(report["voice_reference_lufs"] + 18), 0.1)
        self.assertGreater(rms(output / "music_stem.wav", 0.6, 0.8), rms(output / "music_stem.wav", 2.5, 0.8) * 2)
        self.assertLess(abs(report["final_mix_measurements"]["input_i"] + 18), 1)

    def test_excessively_quiet_voice_is_rejected_without_outputs(self):
        self.plan["narration"] = fixture(self.root / "too-quiet.wav", 10_000, voice=True, gain_db=-40)
        with self.assertRaisesRegex(ScoreRenderError, "Narration normalization.*excessive boost"):
            render_score(self.plan, self.root / "too-quiet-render")
        self.assertFalse((self.root / "too-quiet-render").exists())
        self.assertEqual(list(self.root.glob(".too-quiet-render.render-*")), [])

    def test_only_authorized_loop_interval_is_repeated(self):
        asset = fixture(self.root / "loop.wav", 4000, loop_middle=True)
        self.plan["assets"] = [{"id": "bed", **asset, "loop": {"start_ms": 1000, "end_ms": 3000}}]
        output = self.root / "loop-render"
        render_score(self.plan, output)
        # The source is silent outside the authorized middle interval. If the
        # full file were repeated these two pause windows would be silent.
        self.assertGreater(rms(output / "music_stem.wav", 0.4, 0.4), 0.0001)
        self.assertGreater(rms(output / "music_stem.wav", 4.5, 0.4), 0.0001)

    def test_stale_checksum_is_rejected_before_output_is_created(self):
        (self.root / "bed.wav").write_bytes(b"changed")
        with self.assertRaisesRegex(ScoreRenderError, "checksum mismatch"):
            render_score(self.plan, self.root / "stale")
        self.assertFalse((self.root / "stale").exists())

    def test_measured_duration_mismatch_is_rejected(self):
        self.plan["narration"]["duration_ms"] = 10_500
        with self.assertRaisesRegex(ScoreRenderError, "measured duration differs"):
            render_score(self.plan, self.root / "duration")

    def test_local_playlist_is_rejected_as_nonphysical_media(self):
        playlist = self.root / "local.ffconcat"
        playlist.write_text("ffconcat version 1.0\nfile 'voice.wav'\n", encoding="utf-8")
        self.plan["narration"] = {
            "path": str(playlist), "sha256": hashlib.sha256(playlist.read_bytes()).hexdigest(),
            "duration_ms": 10_000,
        }
        with self.assertRaisesRegex(ScoreRenderError, "[Ww]hitelist"):
            render_score(self.plan, self.root / "playlist-render")
        self.assertFalse((self.root / "playlist-render").exists())

    def test_nonloop_media_cannot_be_repeated_implicitly(self):
        short = fixture(self.root / "short.wav", 2000)
        self.plan["assets"] = [{"id": "bed", **short, "loop": None}]
        with self.assertRaisesRegex(ScoreRenderError, "Nonloop asset is too short"):
            render_score(self.plan, self.root / "short-render")

    def test_existing_output_is_preserved(self):
        output = self.root / "existing"
        output.mkdir()
        marker = output / "keep.txt"
        marker.write_text("preserve concurrent work")
        with self.assertRaisesRegex(ScoreRenderError, "refusing to overwrite"):
            render_score(self.plan, output)
        self.assertEqual(marker.read_text(), "preserve concurrent work")

    def test_nonfinite_controls_and_out_of_bounds_loops_are_rejected(self):
        bad_policy = deepcopy(self.plan)
        bad_policy["policy"]["duck_ratio"] = float("nan")
        with self.assertRaisesRegex(ScoreRenderError, "finite"):
            render_score(bad_policy, self.root / "nan")
        self.plan["assets"][0]["loop"] = {"start_ms": 0, "end_ms": 10_001}
        with self.assertRaisesRegex(ScoreRenderError, "outside the measured media"):
            render_score(self.plan, self.root / "bad-loop")

    def test_music_policy_cannot_place_music_at_or_above_voice_reference(self):
        self.plan["policy"]["music_lufs"] = -20
        self.plan["policy"]["target_lufs"] = -25
        with self.assertRaisesRegex(ScoreRenderError, "at least 10 LU below"):
            render_score(self.plan, self.root / "loud-policy")

    def test_silent_asset_fails_without_leaving_partial_outputs(self):
        path = self.root / "silence.wav"
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(48_000)
            handle.writeframes(b"\x00\x00" * 48_000 * 10)
        self.plan["assets"] = [{
            "id": "bed", "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "duration_ms": 10_000, "loop": None,
        }]
        with self.assertRaisesRegex(ScoreRenderError, "Silent or nonfinite"):
            render_score(self.plan, self.root / "silent-render")
        self.assertFalse((self.root / "silent-render").exists())
        self.assertEqual(list(self.root.glob(".silent-render.render-*")), [])

    def test_voice_only_plan_produces_a_silent_music_stem(self):
        self.plan["assets"] = []
        self.plan["placements"] = []
        output = self.root / "voice-only"
        report = render_score(self.plan, output)
        self.assertEqual(report["placement_count"], 0)
        self.assertEqual(rms(output / "music_stem.wav", 0, 1), 0)


if __name__ == "__main__":
    unittest.main()
