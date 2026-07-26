#!/usr/bin/env python3

from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
from unittest import mock

import bengali_tts_provider_bakeoff as bakeoff


MANUSCRIPT = " ".join(
    [
        "প্রথম সকালে গ্রামের পথ দিয়ে শিক্ষক ধীরে ধীরে বিদ্যালয়ের দিকে চললেন।",
        "ছাত্রটি বলল, “মশাই, আজ কি আমাদের নতুন গল্পটি পড়াবেন?”",
        "শিক্ষক উত্তর দিলেন, “পড়াব, তবে মন দিয়ে শোনো এবং প্রশ্ন করতে ভয় পেয়ো না।”",
        "দীর্ঘ করিডরের একদিকে জানালা, অন্যদিকে পুরোনো ছবি, মাঝখানে স্তব্ধ আলো—সব মিলিয়ে অদ্ভুত পরিবেশ তৈরি করেছিল।",
        "কিছুক্ষণ পরে সবাই মাঠে গেল এবং দিনের কঠিন পাঠ নিয়ে আলোচনা করল।",
        "শেষ বিকেলে ঘণ্টা বাজলে তারা বই গুছিয়ে শান্ত মনে বাড়ির পথে ফিরল।",
        "রাত্রি নামার আগে শিক্ষক দরজা বন্ধ করে শেষবারের মতো খালি ঘরটির দিকে তাকালেন।",
    ]
)


class SingleTitlePassageTests(unittest.TestCase):
    def test_voice_filter_is_applied_before_sarvam_voice_limit(self) -> None:
        provider_env = {
            "sarvam": {"detected": True},
            "openai": {"detected": False},
            "google": {"detected": False},
            "azure": {"detected": False},
            "human_licensed_import": {"detected": False},
        }
        voices, unavailable, metadata = bakeoff.available_voices(
            provider_env,
            limit_per_provider=1,
            provider_order=["sarvam"],
            release_policy=bakeoff.BENGALI_AUDIOBOOK_92_POLICY,
            voice_filters={"ratan"},
        )
        filtered = [voice for voice in voices if bakeoff.voice_filter_match(voice, {"ratan"})]
        prioritized = bakeoff.prioritize_mvp_voices(
            filtered,
            bakeoff.BENGALI_AUDIOBOOK_92_POLICY,
            limit_per_provider=1,
        )
        self.assertEqual([voice.voice for voice in prioritized], ["ratan"])
        self.assertIn("ratan", metadata["sarvam"])
        self.assertEqual(unavailable, [])

    @mock.patch.object(bakeoff, "run_cmd")
    def test_quota_probe_reuses_preexisting_short_mp3_without_ffmpeg(self, run_cmd: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            probe = Path(temporary) / "openai_listening_qa_quota_probe_silence.mp3"
            probe.write_bytes(b"ID3-private-probe")
            selected, source = bakeoff._ensure_probe_mp3(Path(temporary))
        self.assertEqual(selected, probe)
        self.assertEqual(source, "preexisting_short_mp3_probe")
        run_cmd.assert_not_called()

    def test_nishkriti_uses_backend_canonical_chapters_when_root_copy_is_absent(self) -> None:
        manuscript = bakeoff.latest_clean_manuscript("nishkriti")
        self.assertGreater(len(manuscript), 10000)
        passages = bakeoff.build_passages(["nishkriti"], 4)
        self.assertEqual(
            [item["passage_id"] for item in passages],
            ["narrative_opening", "dialogue", "punctuation_heavy", "ending_style"],
        )
        self.assertTrue(all(item["text"] for item in passages))
        self.assertEqual(len({item["text_hash"] for item in passages}), 4)

    @mock.patch.object(bakeoff, "latest_clean_manuscript", return_value=MANUSCRIPT)
    def test_single_title_gets_four_representative_passage_categories(self, _manuscript: mock.Mock) -> None:
        passages = bakeoff.build_passages(["example"], 4)
        self.assertEqual(
            [item["passage_id"] for item in passages],
            ["narrative_opening", "dialogue", "punctuation_heavy", "ending_style"],
        )
        self.assertTrue(all(item["slug"] == "example" for item in passages))
        self.assertTrue(all(item["text"] for item in passages))
        self.assertEqual(len({item["text_hash"] for item in passages}), 4)

    @mock.patch.object(bakeoff, "latest_clean_manuscript", return_value=MANUSCRIPT)
    def test_single_title_respects_smaller_max_passage_limit(self, _manuscript: mock.Mock) -> None:
        passages = bakeoff.build_passages(["example"], 2)
        self.assertEqual([item["passage_id"] for item in passages], ["narrative_opening", "dialogue"])

    @mock.patch.object(bakeoff, "latest_clean_manuscript", return_value=MANUSCRIPT)
    def test_single_title_respects_character_cap(self, _manuscript: mock.Mock) -> None:
        passages = bakeoff.build_passages(["example"], 4, max_chars=150)
        self.assertTrue(all(len(item["text"]) <= 150 for item in passages))

    def test_google_text_prep_splits_long_sentences_without_losing_words(self) -> None:
        text = " ".join(["একটি" for _ in range(100)]) + "।"
        prepared = bakeoff.google_safe_tts_text(text, max_sentence_chars=80)
        self.assertEqual(prepared.replace("।", "").split(), text.replace("।", "").split())
        self.assertTrue(all(len(part.strip()) <= 80 for part in prepared.split("।") if part.strip()))

    def test_fail_closed_quality_limit_returns_nonzero(self) -> None:
        self.assertEqual(bakeoff.final_bakeoff_exit_code(passing=False, fail_closed=True), 2)
        self.assertEqual(bakeoff.final_bakeoff_exit_code(passing=False, fail_closed=False), 0)
        self.assertEqual(bakeoff.final_bakeoff_exit_code(passing=True, fail_closed=True), 0)

    @mock.patch.object(bakeoff, "latest_clean_manuscript", return_value=MANUSCRIPT)
    def test_passages_file_requires_unique_source_bound_text(self, _manuscript: mock.Mock) -> None:
        source_passages = bakeoff.build_passages(["example"], 4, max_chars=150)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "passages.json"
            path.write_text(json.dumps({"passages": source_passages}, ensure_ascii=False), encoding="utf-8")
            loaded, errors = bakeoff.load_passages_file(path, ["example"], 4, max_chars=150)
            self.assertEqual(errors, [])
            self.assertEqual([item["text_hash"] for item in loaded], [item["text_hash"] for item in source_passages])
            duplicate = list(source_passages)
            duplicate[-1] = dict(source_passages[0], passage_id="duplicate")
            path.write_text(json.dumps({"passages": duplicate}, ensure_ascii=False), encoding="utf-8")
            _loaded, errors = bakeoff.load_passages_file(path, ["example"], 4, max_chars=150)
            self.assertTrue(any("duplicates" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
