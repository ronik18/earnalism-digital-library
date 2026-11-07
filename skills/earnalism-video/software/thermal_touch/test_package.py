"""Local packaging/qualification regressions; no speech, render, upload or real approval."""
from pathlib import Path
import json
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from . import package as production


def save(path, value):
    Path(path).write_text(json.dumps(value))


def fixture(root):
    """Deliberately synthetic file bytes test binding logic, not media decoding."""
    root = Path(root)
    for name in production.SOURCE_FILES:
        (root / name).write_bytes(b"SYNTHETIC TEST ONLY; NOT MEDIA OR APPROVAL")
    (root / "source").mkdir()
    (root / "source" / "raw.wav").write_bytes(b"SYNTHETIC RAW FIXTURE")
    cues = [{"start": 0., "end": 2., "text": "Same starting temperature."}]
    scenes = [{"id": f"s{i+1:02}", "scene": kind, "start": float(i*3), "end": float((i+1)*3),
               "text": "Test-only sentence.", "marks": {}} for i, kind in
              enumerate(("question", "flow", "material", "temperature", "reverse", "callback"))]
    save(root / "timeline.json", {"duration": 18., "scenes": scenes})
    props = {"duration": 18., "scenes": scenes, "captions": cues, "burnCaptions": False}
    save(root / "props.json", props)
    save(root / "clean-shorts-props.json", props)
    save(root / "shorts-props.json", {**props, "burnCaptions": True})
    save(root / "voice-binding.json", {"narration_sha256": production.sha(root / "narration.wav"),
                                       "no_tempo_or_pitch_change": True})
    save(root / "asr-review.json", [{"source_validation": "PASS", "differences": []} for _ in range(6)])
    save(root / "caption-quality.json", {"issues": []})
    save(root / "sources.json", [{"title": "Original primary source", "url": "https://example.edu/science"}])
    for name, size in (("thumbnail-landscape.png", (1920, 1080)), ("thumbnail-shorts.png", (1080, 1920))):
        (root / name).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + struct.pack(">II", *size))
    bound = ["timeline.json", "narration.wav", "voice-binding.json", "asr-review.json", "caption-quality.json",
             "props.json", "shorts-props.json", "clean-shorts-props.json", "captions.srt", "captions.vtt", "transcript.txt"]
    save(root / "assembly-manifest.json", {"state": "ASSEMBLED_PRIVATE_REQUIRES_REVIEW",
         "source_root": str(root / "source"), "input_files": {"raw.wav": production.sha(root / "source/raw.wav")},
         "output_files": {name: production.sha(root / name) for name in bound},
         "publication_approved": True})  # Must never transfer this synthetic stale approval.
    save(root / "mix-provenance.json", {"narration_sha256": production.sha(root / "narration.wav"),
         "narration_source_unchanged": True, "pitch_or_tempo_changed": False, "final_duration": 21.,
         "inputs": {name: production.sha(root / name) for name in
                    ("assembly-manifest.json", "timeline.json", "voice-binding.json", "narration.wav")},
         "output_files": {name: production.sha(root / name) for name in
                          ("soundtrack.m4a", "dry-soundtrack.m4a", "score.provenance.json")},
         "human_listening": "ACCEPTED_BUT_NOT_TRANSFERABLE"})
    for fmt in production.FORMATS:
        (root / fmt).mkdir()
        outputs = {}
        for name in ("video.mp4", "narration-only.mp4"):
            (root / fmt / name).write_bytes((fmt + name + " SYNTHETIC FIXTURE").encode())
            outputs[name] = {"decode": "PASS", "soundtrack_stream_copy": True,
                             "sha256": production.sha(root / fmt / name), "audio_video_duration_gap": .01,
                             "common_audio_packet_hash": "TEST-ONLY-SCORED" if name == "video.mp4" else "TEST-ONLY-DRY"}
        save(root / fmt / "technical.json", {"format": fmt, "width": 1920 if fmt == "landscape" else 1080,
             "height": 1080 if fmt == "landscape" else 1920, "duration": 21., "narration_source_unchanged": True,
             "outputs": outputs, "listening_av": "STALE_ACCEPTANCE_NOT_TRANSFERABLE"})


class PrivatePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture(self.root)

    def test_fresh_package_binds_media_and_never_copies_acceptance(self):
        before = {p: production.sha(p) for p in self.root.rglob("*") if p.is_file()}
        result = production.package(self.root)
        manifest = production.load(self.root / "delivery-manifest.json")
        self.assertEqual(result["listening_av"], "PENDING")
        self.assertFalse(result["publication_approved"])
        self.assertEqual(manifest["listening_av"], "PENDING")
        self.assertFalse(manifest["uploads"])
        self.assertIsNone(manifest["schedule"])
        for name, digest in manifest["files"].items():
            self.assertEqual(digest, production.sha(self.root / name))
        for path, digest in before.items():
            self.assertEqual(digest, production.sha(path))
        review = production.load(self.root / "private-review.json")
        self.assertEqual(review["factual"], "PENDING_FINAL_REVIEW")
        self.assertNotIn("ACCEPTED", review["listening_av"])
        self.assertNotIn("moon", (self.root / "watch.html").read_text().lower())

    def test_existing_or_partial_package_is_never_overwritten(self):
        (self.root / "watch.html").write_text("KEEP")
        with self.assertRaisesRegex(production.QualificationError, "Existing or partial"):
            production.package(self.root)
        self.assertEqual((self.root / "watch.html").read_text(), "KEEP")
        self.assertFalse((self.root / ".thermal-package-lock.json").exists())

    def test_stale_mux_rejected_before_any_package_record(self):
        (self.root / "landscape/video.mp4").write_bytes(b"CHANGED")
        with self.assertRaisesRegex(production.QualificationError, "Stale mux/decode"):
            production.package(self.root)
        self.assertFalse((self.root / ".thermal-package-lock.json").exists())

    def test_different_audio_between_formats_is_rejected(self):
        path = self.root / "clean-shorts/technical.json"
        value = production.load(path)
        value["outputs"]["video.mp4"]["common_audio_packet_hash"] = "WRONG"
        save(path, value)
        with self.assertRaisesRegex(production.QualificationError, "identical encoded soundtrack"):
            production.package(self.root)

    def test_changed_original_source_and_wrong_cover_fail_without_creation(self):
        (self.root / "source/raw.wav").write_bytes(b"CHANGED")
        with self.assertRaisesRegex(production.QualificationError, "original narration source"):
            production.package(self.root)
        fixture_root = self.root / "another"
        fixture_root.mkdir()
        fixture(fixture_root)
        (fixture_root / "thumbnail-shorts.png").write_bytes((fixture_root / "thumbnail-landscape.png").read_bytes())
        with self.assertRaisesRegex(production.QualificationError, "aspect ratio"):
            production.package(fixture_root)

    def test_players_reuse_caption_safe_seek_replay_recovery_and_fit(self):
        landscape, portrait = production.page(self.root, False), production.page(self.root, True)
        for page in (landscape, portrait):
            for text in ("Replay from beginning", "Reload preview", "old.replaceWith(fresh)",
                         "shell.requestFullscreen()", "node.addEventListener('seeked',showCaption)"):
                self.assertIn(text, page)
            self.assertNotIn("{{", page)
            self.assertNotIn("landscape-preview", page)
        self.assertIn("reviewCues.filter(c=>video.currentTime>=c.start&&video.currentTime<c.end)", landscape)
        self.assertIn("track.mode='hidden'", landscape)
        self.assertIn('<track kind="captions" src="captions.vtt"', landscape)
        self.assertNotIn('<track kind="captions"', portrait)
        self.assertIn("Captions: burned in", portrait)
        self.assertIn("calc((100dvh - 260px)*9/16)", portrait)
        self.assertIn("video.getBoundingClientRect().top+(window.scrollY||0)", portrait)
        self.assertIn("portraitRoom(window.innerHeight,documentTop,controls.getBoundingClientRect().height", portrait)
        self.assertIn("node.addEventListener('loadedmetadata',fitPortrait)", portrait)
        self.assertIn('src="shorts/video.mp4"', portrait)
        self.assertIn("event.target.matches?.('video,audio')", landscape)

    def test_no_webm_does_not_create_broken_codec_source(self):
        page = production.page(self.root, False)
        self.assertNotIn('type="video/webm"', page)
        self.assertIn('disabled title="No alternate codec generated"', page)
        with patch.object(production, "preview_check", side_effect=AssertionError("No preview should be checked")):
            production.package(self.root)

    def test_present_webm_is_checked_and_bound_as_compatibility_not_identical_audio(self):
        path = self.root / "shorts/preview.webm"
        path.write_bytes(b"SYNTHETIC WEBM")
        with patch.object(production, "preview_check", return_value={"decode": "PASS", "kind": "compatibility"}) as check:
            production.package(self.root)
        check.assert_called_once_with(path.resolve(), (1080, 1920), 21.)
        page = (self.root / "shorts.html").read_text()
        self.assertLess(page.index('src="shorts/preview.webm"'), page.index('src="shorts/video.mp4"'))
        manifest = production.load(self.root / "delivery-manifest.json")
        self.assertEqual(manifest["files"]["shorts/preview.webm"], production.sha(path))

    def test_private_metadata_has_clean_master_reviewed_captions_and_paired_brand_tags(self):
        production.package(self.root)
        for name in ("youtube-landscape.json", "youtube-shorts.json"):
            data = production.load(self.root / name)
            self.assertEqual(data["privacyStatus"], "private")
            self.assertFalse(data["upload_automatically"])
            self.assertFalse(data["publication_approved"])
            self.assertIn("#earnalism #learnalism", data["description"])
            self.assertIn("PENDING", data["audience_classification"])
            self.assertIn("https://example.edu/science", data["description"])
        self.assertEqual(production.load(self.root / "youtube-shorts.json")["video"], "clean-shorts/video.mp4")
        self.assertIn("#earnalism #learnalism", (self.root / "instagram-caption.txt").read_text())

    def test_inline_caption_json_cannot_close_script_element(self):
        encoded = production.script_json([{"text": "</script><script>untrusted</script>"}])
        self.assertNotIn("</script>", encoded)
        self.assertIn("\\u003c", encoded)

    def test_optional_listening_targets_are_bound_escaped_and_never_approval(self):
        targets = {"targets": [{"start": 3.25, "end": 6.5,
                                "reason": '<script>alert("bad")</script> & compare the transition',
                                "approval": "SHOULD_NOT_TRANSFER"}],
                   "publication_approved": True}
        save(self.root / "listening-targets.json", targets)
        production.package(self.root)
        for name in ("watch.html", "shorts.html"):
            page = (self.root / name).read_text()
            self.assertIn('data-role="listening-targets"', page)
            self.assertIn("3.25–6.5 seconds", page)
            self.assertIn("not confirmed audible defects", page)
            self.assertIn("&lt;script&gt;", page)
            self.assertIn("&amp; compare", page)
            self.assertNotIn('<script>alert("bad")</script>', page)
            self.assertNotIn("SHOULD_NOT_TRANSFER", page)
        manifest = production.load(self.root / "delivery-manifest.json")
        self.assertEqual(manifest["files"]["listening-targets.json"], production.sha(self.root / "listening-targets.json"))
        self.assertFalse(manifest["publication_approved"])
        self.assertEqual(production.load(self.root / "private-review.json")["listening_av"], "PENDING")

    def test_absent_listening_targets_leave_the_review_unchanged(self):
        for portrait in (False, True):
            self.assertNotIn('data-role="listening-targets"', production.page(self.root, portrait))
        production.package(self.root)
        self.assertNotIn("listening-targets.json", production.load(self.root / "delivery-manifest.json")["files"])

    def test_listening_target_bounds_and_reasons_fail_before_packaging(self):
        for target in ({"start": -1, "end": 2, "reason": "question"},
                       {"start": 1, "end": 22, "reason": "question"},
                       {"start": 3, "end": 3, "reason": "question"},
                       {"start": float("nan"), "end": 3, "reason": "question"},
                       {"start": 1, "end": float("inf"), "reason": "question"},
                       {"start": False, "end": 3, "reason": "question"},
                       {"start": "1", "end": 3, "reason": "question"},
                       {"start": 1, "end": 3, "reason": " "}):
            save(self.root / "listening-targets.json", [target])
            with self.subTest(target=target), self.assertRaises(production.QualificationError):
                production.package(self.root)
            self.assertFalse((self.root / ".thermal-package-lock.json").exists())

    @unittest.skipUnless(shutil.which("node"), "Node is unavailable for player syntax validation")
    def test_generated_player_javascript_parses_in_both_formats_and_codec_states(self):
        for portrait in (False, True):
            for webm in (False, True):
                script = production.page(self.root, portrait, webm).rsplit("<script>", 1)[1].split("</script>", 1)[0]
                result = subprocess.run(["node", "--check"], input=script, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node is unavailable for evaluated player-layout regression")
    def test_portrait_fit_is_scroll_independent_and_reserves_wrapped_mobile_controls(self):
        # Execute the same function emitted into the actual review page. The
        # mobile fixture reproduces a negative viewport top after resizing a
        # scrolled desktop page; document position remains 163.5 px.
        script = r"""
const assert=require('node:assert/strict');
let documentVideoTop=163.5,controlsHeight=45,statusHeight=27;
const window={innerHeight:720,scrollY:0};
const video={style:{},getBoundingClientRect:()=>({top:documentVideoTop-window.scrollY})};
const document={fullscreenElement:null,querySelector:selector=>({getBoundingClientRect:()=>({height:selector==='.player-controls'?controlsHeight:statusHeight})})};
""" + production.PORTRAIT_FIT_JS + r"""
fitPortrait();const desktop=video.style.maxHeight;
assert.equal(desktop,'419.5px');
window.innerHeight=844;controlsHeight=174;
fitPortrait();const mobile=video.style.maxHeight,mobileWidth=video.style.width;
assert.equal(mobile,'414.5px');
for(const scroll of [309.5,700,0]){
 window.scrollY=scroll;fitPortrait();
 assert.equal(video.style.maxHeight,mobile);assert.equal(video.style.width,mobileWidth);
}
assert.equal(video.getBoundingClientRect().top,163.5);
controlsHeight=45;fitPortrait();assert.equal(video.style.maxHeight,'543.5px');
controlsHeight=174;fitPortrait();assert.equal(video.style.maxHeight,mobile);
window.innerHeight=720;controlsHeight=45;window.scrollY=309.5;fitPortrait();
assert.equal(video.style.maxHeight,desktop);
document.fullscreenElement={};fitPortrait();
assert.equal(video.style.maxHeight,'');assert.equal(video.style.width,'');
"""
        result = subprocess.run(["node"], input=script, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
