"""Synthetic local composer tests; no production media or acceptance evidence."""

from array import array
from copy import deepcopy
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave
import zlib

from scripts.book_av_render import _decode_end_pcm, _decode_pcm, digest, display_caption_text, render, validate
from scripts import book_av_render


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return {"path": str(path), "sha256": digest(path)}


def png(path, width, height, *, transparent=False):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    row = b"".join(bytes((40 + x % 80, 120, 170, 0 if transparent and x < 4 else 255)) for x in range(width))
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress((b"\0" + row) * height)) + chunk(b"IEND", b"")
    path.write_bytes(data)
    return {"path": str(path), "sha256": digest(path)}


def sine(path, duration_ms, frequency=440):
    frames = b"".join(struct.pack("<h", round(math.sin(2 * math.pi * frequency * i / 48000) * 5000))
                      for i in range(duration_ms * 48))
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(48000)
        target.writeframes(frames)
    return {"path": str(path), "sha256": digest(path), "duration_ms": duration_ms}


def media(args):
    return subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-n", *args],
                          capture_output=True, check=True, timeout=30).stdout


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "local FFmpeg required")
class BookAVRenderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="book-av-fixtures-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        text = self.root / "story.txt"
        text.write_text("Hello.", encoding="utf-8")
        manuscript = {"path": str(text), "sha256": digest(text), "language": "en"}
        voice = sine(self.root / "voice.wav", 1000)
        timing = write_json(self.root / "timing.json", {
            "schema": "earnalism.audiobook_score.timing.v1", "manuscript_sha256": manuscript["sha256"],
            "narration_sha256": voice["sha256"], "duration_ms": 1000,
            "method": "synthetic_fixture", "provenance": {"tool": "test fixture", "version": "1",
            "boundary_validation": "synthetic_fixture"}, "cues": [{"id": "c1", "start_ms": 0,
            "end_ms": 1000, "text_start": 0, "text_end": 6, "text": "Hello."}]})
        picture = png(self.root / "scene.png", 320, 160)
        rights = write_json(self.root / "rights.json", {
            "schema": "earnalism.book_av_visual_rights.v1", "asset_sha256": picture["sha256"],
            "scope": "commercial_audiovisual", "territories": ["IN"], "approval_status": "SYNTHETIC_FIXTURE",
            "commercial_use": True, "distribution": True, "derivative_use": True,
            "rights_holder": "Synthetic fixture", "license_id": "synthetic_fixture",
            "attribution": "Synthetic test only", "approval_ref": "synthetic_fixture"})
        brand = {**png(self.root / "brand.png", 64, 16, transparent=True), "approval_ref": "synthetic_fixture"}
        self.job = {"schema": "earnalism.book_av_render.v1", "title": "Synthetic fixture",
                    "territory": "IN", "fixture_mode": True, "manuscript": manuscript,
                    "narration": voice, "scored_audio": voice, "timing": timing,
                    "assets": [{"id": "art", "kind": "image", **picture, "rights": rights}],
                    "scenes": [{"id": "s1", "cue_id": "c1", "start_ms": 0, "end_ms": 1000}],
                    "branding": brand, "outputs": [], "captions": True}
        for name, width, height in [("landscape", 320, 180), ("portrait", 180, 320)]:
            end = self.root / f"END-{name}.mp4"
            media(["-f", "lavfi", "-i", f"color=c=0x132635:s={width}x{height}:r=30:d=3",
                   "-f", "lavfi", "-i", "sine=frequency=660:sample_rate=48000:duration=3",
                   "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-ac", "2", "-t", "3", str(end)])
            self.job["outputs"].append({"name": name, "width": width, "height": height, "fps": 30,
                "watermark": {"box": [width - 72, 8, 64, 16], "halo_px": 2},
                "scenes": [{"scene_id": "s1", "asset_id": "art", "box": [0, 32, width, height - 32],
                            "zoom_start": 1, "zoom_end": 1.03, "source_offset_ms": 0}],
                "end_clip": {"path": str(end), "sha256": digest(end), "duration_ms": 3000,
                             "approval_ref": "synthetic_fixture"}})
        self.path = self.root / "job.json"
        write_json(self.path, self.job)

    def save(self, job=None):
        write_json(self.path, job if job is not None else self.job)

    def test_actual_two_format_render_preserves_soundtrack_and_rejects_reuse(self):
        report = render(self.path, self.root / "candidate")
        self.assertEqual(report["schema"], "earnalism.book_av_render_report.v1")
        self.assertTrue(report["fixture_mode"])
        self.assertFalse(report["release_approved"])
        self.assertEqual(report["full_listening_av_review"], "UNPERFORMED")
        self.assertEqual(report["motion_treatment"], ["illustration-camera-motion"])
        self.assertEqual(len(report["outputs"]), 2)
        self.assertEqual([v["format"] for v in report["caption_files"]], ["srt", "vtt"])
        with wave.open(report["soundtrack"]["path"], "rb") as soundtrack:
            self.assertEqual(soundtrack.getnframes(), 4 * 48000)
            body = soundtrack.readframes(48000)
        expected = subprocess.run(["ffmpeg", "-v", "error", "-i", self.job["scored_audio"]["path"],
            "-ac", "2", "-ar", "48000", "-f", "s24le", "pipe:1"], capture_output=True, check=True).stdout
        self.assertEqual(body, expected)
        for output in report["outputs"]:
            self.assertEqual(output["decode"], "PASS")
            self.assertEqual(output["audio_payload_sha256"], report["encoded_soundtrack"]["audio_payload_sha256"])
            self.assertAlmostEqual(output["duration_ms"], 4000, delta=34)
            # Inspect actual encoded sound, independent of metadata/receipts:
            # scored body is 440 Hz; approved END is 660 Hz, never a silent track.
            for start, wanted, other in [(0.2, 440, 660), (1.4, 660, 440)]:
                pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-i", output["path"],
                    "-t", "0.4", "-ac", "1", "-ar", "48000", "-f", "f32le", "pipe:1"],
                    capture_output=True, check=True).stdout
                samples = array("f", pcm)
                def amplitude(frequency):
                    return abs(sum(x * complex(math.cos(2 * math.pi * frequency * i / 48000),
                                               math.sin(2 * math.pi * frequency * i / 48000))
                                   for i, x in enumerate(samples))) / len(samples)
                self.assertGreater(amplitude(wanted), .02)
                self.assertGreater(amplitude(wanted), amplitude(other) * 10)
        self.assertIn("Hello.", (self.root / "candidate" / "captions.vtt").read_text())
        with self.assertRaisesRegex(ValueError, "already exists"):
            render(self.path, self.root / "candidate")

    def test_production_rejects_fixture_timing(self):
        self.job["fixture_mode"] = False
        self.save()
        with self.assertRaisesRegex(ValueError, "timing method"):
            validate(self.path)

    def test_stale_asset_and_unapproved_visual_rights_fail_before_output(self):
        original = deepcopy(self.job)
        self.job["assets"][0]["sha256"] = "0" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "checksum"):
            render(self.path, self.root / "uncreated")
        self.assertFalse((self.root / "uncreated").exists())
        self.job = original
        rights_path = Path(self.job["assets"][0]["rights"]["path"])
        rights = json.loads(rights_path.read_text())
        rights["scope"] = "commercial_audiobook"
        self.job["assets"][0]["rights"] = write_json(rights_path, rights)
        self.save()
        with self.assertRaisesRegex(ValueError, "Visual rights"):
            validate(self.path)

    def test_measured_anchors_and_independent_composition_are_required(self):
        original = deepcopy(self.job)
        self.job["scenes"][0]["start_ms"] = 1
        self.save()
        with self.assertRaisesRegex(ValueError, "anchors"):
            validate(self.path)
        self.job = original
        self.job["outputs"][1]["scenes"] = []
        self.save()
        with self.assertRaisesRegex(ValueError, "output scenes"):
            validate(self.path)

    def test_brand_halo_collision_and_opaque_brand_are_rejected(self):
        original = deepcopy(self.job)
        self.job["outputs"][0]["scenes"][0]["box"] = [0, 0, 320, 180]
        self.save()
        with self.assertRaisesRegex(ValueError, "halo"):
            validate(self.path)
        self.job = original
        self.job["branding"] = {**png(self.root / "opaque.png", 64, 16), "approval_ref": "fixture"}
        self.save()
        with self.assertRaisesRegex(ValueError, "transparency"):
            validate(self.path)

    def test_private_output_cannot_follow_symlink_into_git(self):
        checkout = self.root / "pretend-checkout"
        checkout.mkdir()
        (checkout / ".git").write_text("gitdir: fixture")
        nested = checkout / "nested"
        nested.mkdir()
        link = self.root / "outside-link"
        link.symlink_to(nested, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "outside git"):
            render(self.path, link / "private")
        self.assertFalse((nested / "private").exists())

    def test_unqualified_paragraphs_are_not_estimated_as_readable_captions(self):
        timing = json.loads(Path(self.job["timing"]["path"]).read_text())
        timing["cues"][0]["end_ms"] = 500
        self.job["timing"] = write_json(Path(self.job["timing"]["path"]), timing)
        self.save()
        with self.assertRaisesRegex(ValueError, "coarse/fast"):
            validate(self.path)

    def test_caption_display_whitespace_preserves_source_and_bound_cue_bytes(self):
        original = "  A question?\n\nA  quiet reply.\t"
        self.assertEqual(display_caption_text(original), "A question? A quiet reply.")
        self.assertEqual(original, "  A question?\n\nA  quiet reply.\t")
        text_path = Path(self.job["manuscript"]["path"])
        text_path.write_text("Hello.\n\nAgain.", encoding="utf-8")
        self.job["manuscript"]["sha256"] = digest(text_path)
        timing_path = Path(self.job["timing"]["path"])
        timing = json.loads(timing_path.read_text())
        timing["manuscript_sha256"] = digest(text_path)
        timing["cues"][0].update({"text": text_path.read_text(), "text_end": len(text_path.read_text())})
        self.job["timing"] = write_json(timing_path, timing)
        self.save()
        before_source, before_timing = text_path.read_bytes(), timing_path.read_bytes()
        job = validate(self.path)
        self.assertEqual(job["timing_data"]["cues"][0]["text"], "Hello.\n\nAgain.")
        report = render(self.path, self.root / "multiline-display")
        vtt = Path(next(ref["path"] for ref in report["caption_files"] if ref["format"] == "vtt")).read_text()
        self.assertIn("Hello. Again.", vtt)
        self.assertNotIn("Hello.\n\nAgain.", vtt)
        self.assertEqual(text_path.read_bytes(), before_source)
        self.assertEqual(timing_path.read_bytes(), before_timing)

    def test_short_motion_clip_cannot_loop_silently(self):
        clip = self.root / "short.mp4"
        media(["-f", "lavfi", "-i", "testsrc2=s=320x160:r=30:d=0.2",
               "-c:v", "libx264", str(clip)])
        self.job["assets"][0].update({"kind": "video", "path": str(clip), "sha256": digest(clip)})
        rights_path = Path(self.job["assets"][0]["rights"]["path"])
        rights = json.loads(rights_path.read_text())
        rights["asset_sha256"] = digest(clip)
        self.job["assets"][0]["rights"] = write_json(rights_path, rights)
        for output in self.job["outputs"]:
            output["scenes"][0]["zoom_end"] = 1
        self.save()
        with self.assertRaisesRegex(ValueError, "finite source capacity"):
            validate(self.path)

    def test_actual_native_motion_clip_is_reported_without_character_animation_claim(self):
        clip = self.root / "motion.mp4"
        media(["-f", "lavfi", "-i", "testsrc2=s=320x160:r=30:d=1",
               "-c:v", "libx264", str(clip)])
        self.job["assets"][0].update({"kind": "video", "path": str(clip), "sha256": digest(clip)})
        rights_path = Path(self.job["assets"][0]["rights"]["path"])
        rights = json.loads(rights_path.read_text())
        rights["asset_sha256"] = digest(clip)
        self.job["assets"][0]["rights"] = write_json(rights_path, rights)
        self.job["outputs"] = self.job["outputs"][:1]
        self.job["outputs"][0]["scenes"][0]["zoom_end"] = 1
        self.job["captions"] = False
        self.save()
        report = render(self.path, self.root / "motion-candidate")
        self.assertEqual(report["motion_treatment"], ["supplied-motion-clip-unassessed-character-naturalness"])
        self.assertEqual(report["caption_files"], [])
        hashes = []
        for seconds in (0.2, 0.7):
            frame = media(["-ss", str(seconds), "-i", report["outputs"][0]["path"],
                           "-frames:v", "1", "-f", "md5", "pipe:1"])
            hashes.append(frame)
        self.assertNotEqual(*hashes)

    def test_inconsistent_decoded_score_clock_leaves_honest_private_failure(self):
        wrong = sine(self.root / "wrong-duration.wav", 1003)
        self.job["scored_audio"] = {**wrong, "duration_ms": 1000}
        self.save()
        output = self.root / "failed-clock"
        with self.assertRaisesRegex(ValueError, "more than 1ms"):
            render(self.path, output)
        self.assertFalse((output / "render-report.json").exists())
        self.assertEqual(json.loads((output / "FAILED.json").read_text())["state"], "FAILED_PRIVATE_RENDER")

    def test_submillisecond_score_tail_is_preserved_sample_for_sample(self):
        scored = self.root / "score-with-original-tail.wav"
        with wave.open(self.job["scored_audio"]["path"], "rb") as original:
            samples = original.readframes(original.getnframes())
        # A distinctive nonzero half-ms tail must survive in its entirety,
        # independently of the rounded 1000ms manuscript/narration clock.
        tail = b"".join(struct.pack("<h", 3700 + index * 7) for index in range(24))
        with wave.open(str(scored), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(48000)
            target.writeframes(samples + tail)
        self.job["scored_audio"] = {"path": str(scored), "sha256": digest(scored), "duration_ms": 1000}
        self.job["outputs"] = self.job["outputs"][:1]
        self.save()
        report = render(self.path, self.root / "complete-score-tail")
        soundtrack_ref = report["soundtrack"]
        self.assertEqual(soundtrack_ref["scored_source_frames"], 48024)
        self.assertEqual(soundtrack_ref["body_frames"], 48024)
        self.assertEqual(soundtrack_ref["measured_body_frames"], 48000)
        self.assertEqual(soundtrack_ref["source_vs_measured_clock_delta_ms"], .5)
        self.assertTrue(soundtrack_ref["decoded_scored_audio_preserved_complete"])
        with wave.open(soundtrack_ref["path"], "rb") as soundtrack:
            self.assertEqual(soundtrack.getnframes(), 48024 + 144000)
            actual_body = soundtrack.readframes(48024)
        expected_body = subprocess.run(["ffmpeg", "-v", "error", "-i", str(scored),
            "-ac", "2", "-ar", "48000", "-f", "s24le", "pipe:1"],
            capture_output=True, check=True).stdout
        self.assertEqual(actual_body, expected_body)
        self.assertNotEqual(actual_body[-24 * 6:], bytes(24 * 6))

    def test_end_presentation_gap_preserves_its_position_and_every_physical_sample(self):
        clip = self.root / "END-existing-gap.mp4"
        media(["-f", "lavfi", "-i", "color=c=0x132635:s=320x180:r=30:d=3",
               "-f", "lavfi", "-i", "sine=frequency=660:sample_rate=48000:duration=3",
               "-map", "0:v:0", "-map", "1:a:0", "-af", "aselect='not(between(t,0.5,0.6))'",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "2",
               "-t", "3", str(clip)])
        output = self.root / "END-presentation.pcm"
        result = _decode_end_pcm(clip, output)
        self.assertEqual(result["playable_frames"], 144000)
        self.assertGreater(result["gap_frames"], 0)
        self.assertEqual(result["physical_frames"] + result["gap_frames"], 144000)
        self.assertEqual(len(result["gaps"]), 1)
        gap = result["gaps"][0]
        # The fixture drops the 1024-sample packets whose original starts fall
        # inside 0.5..0.6s. This expected interval is independent of the helper.
        self.assertEqual(gap, {"start_frame": 24576, "end_frame": 29696})
        actual = output.read_bytes()
        self.assertEqual(actual[24576 * 6:29696 * 6], bytes((29696 - 24576) * 6))
        physical_path = self.root / "END-physical.pcm"
        _decode_pcm(clip, physical_path)
        # All non-gap audio bytes survive in order, and the silent gap stays
        # at its original presentation location rather than shifting the sting.
        physical = physical_path.read_bytes()
        padding = result["decoder_padding_frames"]
        if padding:
            physical = physical[:-padding * 6]
        self.assertEqual(actual[:24576 * 6] + actual[29696 * 6:], physical)
        self.assertNotEqual(actual[29696 * 6:30720 * 6], bytes(1024 * 6))
        self.assertEqual(result["timeline_pcm_sha256"], digest(output))

    def test_end_timeline_rejects_resampling(self):
        clip = self.root / "unsupported-END.mov"
        media(["-f", "lavfi", "-i", "sine=frequency=660:sample_rate=44100:duration=3",
               "-ac", "2", "-c:a", "pcm_s24le", str(clip)])
        output = self.root / "unsupported.pcm"
        with self.assertRaisesRegex(ValueError, "native 48k stereo"):
            _decode_end_pcm(clip, output)
        self.assertFalse(output.exists())

    def test_legacy_aac_padding_preserves_every_presented_sample(self):
        clip = self.root / "END-landscape.mp4"
        # Export real unskipped AAC decoder output. Remove only its separately
        # certified initial priming frame to emulate FFmpeg 6's default decode:
        # that decoder applies initial skip but exposes the final whole frame.
        manual = json.loads(subprocess.run(["ffprobe", "-v", "error", "-flags2", "+skip_manual",
            "-select_streams", "a:0", "-show_streams", "-show_frames", "-of", "json", str(clip)],
            capture_output=True, check=True).stdout)
        self.assertEqual(manual["frames"][0]["pts"], -1024)
        self.assertEqual(manual["frames"][0]["nb_samples"], 1024)
        manual["frames"] = manual["frames"][1:]
        self.assertEqual(manual["frames"][-1]["nb_samples"], 1024)
        manual["frames"][-1].pop("side_data_list", None)
        packets = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_packets", "-of", "json", str(clip)], capture_output=True, check=True).stdout)
        first_skip = packets["packets"][0]["side_data_list"][0]
        self.assertEqual(first_skip["skip_samples"], 1024)
        self.assertEqual(packets["packets"][-1]["pts"], 143360)
        self.assertEqual(packets["packets"][-1]["duration"], 640)
        # FFmpeg 6 has the exact packet duration, without terminal skip data.
        packets["packets"][-1].pop("side_data_list", None)
        raw = media(["-flags2", "+skip_manual", "-i", str(clip), "-map", "0:a:0",
                     "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le", "-f", "s24le", "pipe:1"])[1024 * 6:]
        self.assertEqual(len(raw), (144000 + 384) * 6)
        original_run = book_av_render._run

        def legacy_probe(args, **kwargs):
            if "-show_frames" in args:
                return json.dumps(manual)
            if "-show_packets" in args:
                return json.dumps(packets)
            return original_run(args, **kwargs)

        def legacy_decode(path, output):
            Path(output).write_bytes(raw)
            return len(raw)

        output = self.root / "legacy-presented.pcm"
        with patch.object(book_av_render, "_run", side_effect=legacy_probe), patch.object(
                book_av_render, "_decode_pcm", side_effect=legacy_decode):
            result = _decode_end_pcm(clip, output)
        self.assertEqual(result["decoder_padding_frames"], 384)
        self.assertEqual(result["decoded_physical_frames"], 144384)
        self.assertEqual(result["physical_frames"], 144000)
        self.assertEqual(output.read_bytes(), raw[:-384 * 6])
        # Current decoders already apply terminal discard; these bytes must be
        # identical rather than a replacement fade, time stretch or silence.
        expected = self.root / "current-presented.pcm"
        current = _decode_end_pcm(clip, expected)
        self.assertEqual(current["playable_frames"], 144000)
        self.assertEqual(output.read_bytes(), expected.read_bytes())

        cases = {
            "missing_packet_duration": lambda p: p["packets"][-1].pop("duration"),
            "wrong_packet_pts": lambda p: p["packets"][-1].update(pts=143359),
            "wrong_packet_end": lambda p: p["packets"][-1].update(duration=639),
            "contradictory_discard": lambda p: p["packets"][-1].update(side_data_list=[
                {"side_data_type": "Skip Samples", "skip_samples": 0, "discard_padding": 383}]),
        }
        original_packets = deepcopy(packets)
        for name, change in cases.items():
            with self.subTest(name=name):
                packets = deepcopy(original_packets)
                change(packets)
                rejected = self.root / f"reject-{name}.pcm"
                with patch.object(book_av_render, "_run", side_effect=legacy_probe), patch.object(
                        book_av_render, "_decode_pcm", side_effect=legacy_decode) as decode:
                    with self.assertRaisesRegex(ValueError, "exceed the approved timeline"):
                        _decode_end_pcm(clip, rejected)
                    decode.assert_not_called()
                self.assertFalse(rejected.exists())

        packets = deepcopy(original_packets)
        manual["frames"][-1]["side_data_list"] = [
            {"side_data_type": "Skip samples", "skip_samples": 0, "discard_padding": 383}]
        with patch.object(book_av_render, "_run", side_effect=legacy_probe), patch.object(
                book_av_render, "_decode_pcm", side_effect=legacy_decode) as decode:
            with self.assertRaisesRegex(ValueError, "exceed the approved timeline"):
                _decode_end_pcm(clip, self.root / "reject-frame-discard.pcm")
            decode.assert_not_called()

    def test_light_canvas_changes_actual_header_pixels_without_logo_backing(self):
        self.job["outputs"] = self.job["outputs"][:1]
        self.job["outputs"][0]["canvas_color"] = "#F4EAD5"
        self.save()
        report = render(self.path, self.root / "light-canvas")
        # Inspect a decoded body-header pixel away from artwork and branding.
        # YUV420/H.264 roundtrips can differ by a few RGB values.
        pixel = media(["-ss", "0.2", "-i", report["outputs"][0]["path"],
                       "-vf", "crop=2:2:20:8,format=rgb24", "-frames:v", "1", "-f", "rawvideo", "pipe:1"])
        self.assertEqual(len(pixel), 12)
        for actual, expected in zip(pixel[:3], (244, 234, 213)):
            self.assertLessEqual(abs(actual - expected), 4)
        self.assertGreater(min(pixel[:3]), 200)
        self.assertEqual(report["scored_audio_sha256"], self.job["scored_audio"]["sha256"])

    def test_canvas_color_rejects_malformed_or_filter_injection_values(self):
        for color in ("cream", "#FFF", "#F4EAD5;null", "071724", 123, None):
            with self.subTest(color=color):
                self.job["outputs"][0]["canvas_color"] = color
                self.save()
                with self.assertRaisesRegex(ValueError, "#RRGGBB"):
                    validate(self.path)


if __name__ == "__main__":
    unittest.main()
