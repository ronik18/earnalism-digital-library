"""Synthetic source-only timing fixtures; no voice/render/qualification occurs."""
from copy import deepcopy
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from . import finish as f


def fixture():
    # Do not include private narration text in public software/test fixtures.
    contract = deepcopy(f.CONTRACT)
    words = [{"word": "synthetic", "start": i * .4, "end": i * .4 + .3}
             for i in range(contract["word_count"])]
    contract["normalized_tokens_sha256"] = hashlib.sha256(" ".join(w["word"] for w in words).encode()).hexdigest()
    duration = words[-1]["end"] + .2
    scenes = []
    captions = []
    for row in contract["scenes"]:
        a, b = row["word_start"], row["word_end"]
        start = 0 if a == 0 else words[a]["start"]
        scenes.append({"scene": row["id"], "start": start,
                       "end": duration if b == len(words) else words[b]["start"],
                       "word_start": a, "word_end": b,
                       "marks": {k: words[i]["start"] - start for k, i in contract["anchors"][row["id"]].items()}})
        for first in range(a, b, 6):
            last = min(b, first + 6)
            captions.append({"text": " ".join(w["word"] for w in words[first:last]),
                             "word_start": first, "word_end": last,
                             "start": words[first]["start"], "end": words[last - 1]["end"]})
    return contract, {"schema": "earnalism.metal-rust.timeline.v1", "topic_id": f.TOPIC,
        "source_sha256": f.SOURCE_SHA, "audio_sha256": "a" * 64,
        "timing_status": "actual_audio_aligned", "method": "measured_word_alignment",
        "duration": duration, "words": words, "scenes": scenes, "captions": captions}


class ActualTimingTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.timeline = fixture()
        self.mock = patch.object(f, "CONTRACT", self.contract)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def test_actual_word_bound_scene_and_caption_contract(self):
        seconds, scenes = f.validate_timeline(self.timeline)
        self.assertEqual(seconds, self.timeline["duration"])
        self.assertEqual(tuple(s["scene"] for s in scenes), f.SCENE_KINDS)

    def test_unrelated_topic_renaming_and_wrong_script_are_rejected(self):
        for field, value in (("topic_id", "19-tides"), ("source_sha256", "b" * 64),
                             ("schema", "illustrative-18-second-study")):
            data = deepcopy(self.timeline); data[field] = value
            with self.assertRaisesRegex(ValueError, "source identity"):
                f.validate_timeline(data)

    def test_illustrative_and_fixture_clocks_are_not_actual_audio(self):
        for changes in ({"method": "synthetic_fixture"}, {"timing_status": "estimated"},
                        {"fixture_mode": True}, {"duration": 18}):
            data = deepcopy(self.timeline); data.update(changes)
            with self.assertRaises(ValueError): f.validate_timeline(data)

    def test_word_omission_substitution_and_bad_intervals_are_rejected(self):
        for change in (lambda d: d["words"].pop(),
                       lambda d: d["words"][2].update(word="moon"),
                       lambda d: d["words"][2].update(start=-1),
                       lambda d: d["words"][2].update(end=float("nan"))):
            data = deepcopy(self.timeline); change(data)
            with self.assertRaises(ValueError): f.validate_timeline(data)

    def test_actions_follow_current_words_not_fractional_old_scene_clock(self):
        data = deepcopy(self.timeline)
        data["scenes"][4]["marks"]["scratch"] += .15
        with self.assertRaisesRegex(ValueError, "current measured"):
            f.validate_timeline(data)
        data = deepcopy(self.timeline); data["scenes"][1]["word_start"] += 1
        with self.assertRaises(ValueError): f.validate_timeline(data)

    def test_editorial_preview_captions_cannot_replace_spoken_words(self):
        data = deepcopy(self.timeline); data["captions"][0]["text"] = "Follow a raindrop."
        with self.assertRaisesRegex(ValueError, "verbatim"):
            f.validate_timeline(data)

    def test_destination_props_preserve_audio_words_and_separate_caption_layers(self):
        props = {**self.timeline, "burnCaptions": True, "outro": True}
        f.validate_props(props, self.timeline, "shorts-props.json")
        props["audio_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "identity/timing"):
            f.validate_props(props, self.timeline, "shorts-props.json")

    def test_stock_voice_cannot_be_relabelled_as_branded_voice(self):
        binding = {"identity": "AcceptedVoiceB", "language": "en", "source_sha256": f.SOURCE_SHA,
                   "narration_sha256": "a" * 64, "no_tempo_or_pitch_change": True}
        with patch("scripts.earnalism_voice.inspect_profile") as inspect:
            with self.assertRaisesRegex(ValueError, "no stock B fallback"):
                f.validate_voice(binding, ".", "a" * 64)
        inspect.assert_not_called()

    def test_named_branded_profile_without_real_qualification_stays_held(self):
        binding = {"identity": "TheEarnalismVoice", "language": "en", "source_sha256": f.SOURCE_SHA,
                   "narration_sha256": "a" * 64, "no_tempo_or_pitch_change": True, "profile": {}}
        with patch.object(f, "bound", return_value="inert-profile.json"), \
             patch("scripts.earnalism_voice.inspect_profile", return_value={"status": "UNQUALIFIED", "production_accepted": False}):
            with self.assertRaisesRegex(ValueError, "qualification remains required"):
                f.validate_voice(binding, ".", "a" * 64)

    def test_native_pcm_clock_is_read_from_real_bytes_not_declared_seconds(self):
        # Inert silence fixture only; never narration or a qualification candidate.
        frames, rate = 441, 44100
        data = bytes(frames * 4)
        header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt "
        header += struct.pack("<IHHIIHH", 16, 3, 1, rate, rate * 4, 4, 32)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "INERT_TEST_NOT_NARRATION.wav"
            path.write_bytes(header + b"data" + struct.pack("<I", len(data)) + data)
            self.assertEqual(f.wave_info(path), {"duration": .01, "frames": frames, "sample_rate": rate, "channels": 1})
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, "Complete native"):
                f.wave_info(path)


if __name__ == "__main__": unittest.main()
