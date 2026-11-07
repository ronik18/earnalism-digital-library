"""Strict assembly regressions using existing, immutable published audio evidence.

No speech is synthesized; test assemblies cannot produce narration. Temporary
records are explicit test fixtures and confer no episode or listening approval.
"""

from pathlib import Path
import copy
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import assemble as production
except ImportError:
    import assemble as production


class AssemblyQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = production.PUBLISHED_B_ROOT
        cls.baseline = production.load(cls.source / "baseline-job.json")
        cls.units = production.load(cls.source / "units.json")
        cls.unit = cls.units[0]
        cls.wav = cls.source / "imported/raw/s01.wav"
        cls.metadata = production.load(str(cls.wav) + ".json")
        cls.alignment = production.load(cls.source / "imported/alignment/s01.json")

    def audit(self, alignment=None):
        return production.alignment_audit(self.unit, alignment or self.alignment,
                                          production.sha(self.wav), 12.4)

    def test_real_published_recipe_and_wav_validate_without_new_acceptance(self):
        production.validate_baseline(self.baseline)
        result = production.validate_source(self.unit, self.wav, self.metadata, self.baseline)
        self.assertEqual(result["duration"], 12.4)
        self.assertEqual(result["stream"]["sample_rate"], 24000)
        self.assertEqual(result["new_recording_listening"], "PENDING")
        audit, words = self.audit()
        self.assertEqual(audit["differences"], [])
        self.assertEqual(audit["listening"], "PENDING")
        self.assertEqual(words[16]["start"], 7.0)
        self.assertEqual(production.actual_anchor(words, "What changes"), 7.0)

    def test_stale_wav_hash_is_rejected_without_modifying_source(self):
        before = production.sha(self.wav)
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "s01.wav"
            shutil.copy2(self.wav, copied)
            with copied.open("ab") as handle:
                handle.write(b"stale")
            with self.assertRaisesRegex(production.QualificationError, "WAV hash is stale"):
                production.validate_source(self.unit, copied, self.metadata, self.baseline)
        self.assertEqual(production.sha(self.wav), before)

    def test_stale_alignment_cannot_borrow_current_script(self):
        stale = copy.deepcopy(self.alignment)
        stale["audio_sha256"] = "0" * 64
        with self.assertRaisesRegex(production.QualificationError, "Alignment is stale"):
            self.audit(stale)

    def test_small_asr_difference_remains_unresolved(self):
        bad = copy.deepcopy(self.alignment)
        bad["recognized"] = "How" + bad["recognized"][3:]
        bad["word_times"][0]["word"] = "How"
        audit, _ = self.audit(bad)
        self.assertEqual(audit["differences"][0]["expected"], ["why"])
        self.assertEqual(audit["differences"][0]["recognized"], ["how"])
        self.assertIsNone(audit["resolution"])
        self.assertFalse(audit["automatic_equivalence_applied"])

    def test_word_times_must_contain_the_same_words_as_recognized_text(self):
        bad = copy.deepcopy(self.alignment)
        bad["word_times"][0]["word"] = "How"
        audit, _ = self.audit(bad)
        self.assertEqual(audit["raw_differences"], [])
        self.assertTrue(audit["word_time_differences"])
        self.assertTrue(audit["differences"])

    def test_time_outside_actual_wav_or_overlapping_is_rejected(self):
        for change in ((0, "start", -0.1), (0, "end", 13), (1, "start", 0.1),
                       (0, "end", 0), (0, "end", float("nan"))):
            bad = copy.deepcopy(self.alignment)
            index, key, value = change
            bad["word_times"][index][key] = value
            with self.subTest(change=change), self.assertRaises(production.QualificationError):
                self.audit(bad)

    def test_missing_or_ambiguous_anchors_are_never_estimated(self):
        words = self.alignment["word_times"]
        with self.assertRaisesRegex(production.QualificationError, "Missing actual-audio anchor"):
            production.actual_anchor(words, "A phrase that is absent")
        with self.assertRaisesRegex(production.QualificationError, "Ambiguous actual-audio anchor"):
            production.actual_anchor(words, "the")
        compound = [{"word": "twenty-two", "start": 3.2, "end": 3.8}]
        with self.assertRaisesRegex(production.QualificationError, "inside an unsplit"):
            production.actual_anchor(compound, "two")

    def test_changed_baseline_or_generation_settings_rejected(self):
        bad_baseline = copy.deepcopy(self.baseline)
        bad_baseline["generation"]["temperature"] = 0.8
        with self.assertRaisesRegex(production.QualificationError, "exact published Spoon B baseline"):
            production.validate_baseline(bad_baseline)
        for section, key, value in (("generation", "temperature", 0.8),
                                     ("validation", "max_peak", 1.1)):
            bad_metadata = copy.deepcopy(self.metadata)
            bad_metadata["settings"][section][key] = value
            with self.subTest(setting=(section, key)), self.assertRaisesRegex(
                    production.QualificationError, "settings changed"):
                production.validate_source(self.unit, self.wav, bad_metadata, self.baseline)

    def test_worker_seed_and_effective_key_must_be_bound(self):
        mutations = (
            (lambda m: m["provenance"].update(worker_sha256="0" * 64), "worker_sha256"),
            (lambda m: m.update(selected_seed=1), "retry seed"),
            (lambda m: m.update(effective_key="0" * 64), "settings hash"),
        )
        for mutate, expected in mutations:
            bad = copy.deepcopy(self.metadata)
            mutate(bad)
            with self.subTest(expected=expected), self.assertRaisesRegex(production.QualificationError, expected):
                production.validate_source(self.unit, self.wav, bad, self.baseline)

    def test_existing_or_partial_outputs_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "props.json").write_text("KEEP")
            with self.assertRaisesRegex(production.QualificationError, "Existing or partial"):
                production.reserve_outputs(root)
            self.assertEqual((root / "props.json").read_text(), "KEEP")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            production.reserve_outputs(root)
            before = (root / production.RESERVED[0]).read_bytes()
            with self.assertRaises(production.QualificationError):
                production.reserve_outputs(root)
            self.assertEqual((root / production.RESERVED[0]).read_bytes(), before)

    def test_real_fixture_with_one_spelling_difference_blocks_before_audio_assembly(self):
        # The old Spoon source has travelling/traveling in s04. This new
        # assembler must NOT inherit the older automatic spelling exception.
        source_hashes = {p.name: production.sha(p) for p in (self.source / "imported/raw").glob("*.wav")}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "imported").symlink_to(self.source / "imported", target_is_directory=True)
            shutil.copy2(self.source / "units.json", root / "units.json")
            shutil.copy2(self.source / "baseline-job.json", root / "baseline-job.json")
            with patch.object(production, "normalize_narration", side_effect=AssertionError("No narration may run")):
                with self.assertRaisesRegex(production.QualificationError, "Unresolved source/ASR/anchor"):
                    production.assemble(root)
            audits = json.loads((root / "asr-review.json").read_text())
            self.assertEqual(len(audits), 6)
            flagged = next(a for a in audits if a["unit"] == "s04")
            self.assertTrue(flagged["raw_differences"])
            self.assertIsNone(flagged["resolution"])
            self.assertFalse((root / "narration.wav").exists())
            self.assertFalse((root / "timeline.json").exists())
        self.assertEqual(source_hashes, {p.name: production.sha(p)
                                         for p in (self.source / "imported/raw").glob("*.wav")})


if __name__ == "__main__":
    unittest.main()
