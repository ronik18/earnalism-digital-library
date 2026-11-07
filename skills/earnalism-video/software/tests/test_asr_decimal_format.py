"""Exact decimal ASR display equivalence retains real word evidence."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from asr_review import require_script_match, resolve_numeric, tokens


class DecimalASRTests(unittest.TestCase):
    expected='about twenty nine and a half days.'

    def record(self,audio,split=False):
        number=([{'word':'29','start':2.28,'end':3.10},
                 {'word':'.5','start':3.10,'end':3.60}] if split else
                [{'word':'29.5','start':2.28,'end':3.60}])
        return {'recognized':'about 29.5 days.',
                'word_times':[{'word':'about','start':1.9,'end':2.28},*number,
                              {'word':'days.','start':3.60,'end':4.0}],
                'audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),
                'unresolved_asr_edits':[{'tag':'replace',
                    'reference':['twenty','nine','and','a','half'],'recognized':['29','5']}]}

    def test_only_literal_decimal_and_exact_split_spelling_have_the_equivalence(self):
        for spelling in ('29.5','29 .5','29.5.'):
            with self.subTest(spelling=spelling):
                self.assertEqual(tokens(spelling),tokens('twenty nine and a half'))
        for spelling in ('29.4','29.50','29 .50','29 5','129.5','29 . 5','29.5.0',
                         '29.5x','.29.5','-29.5','- 29.5','29.5%','29.5 %'):
            with self.subTest(spelling=spelling):
                self.assertNotEqual(tokens(spelling),tokens('twenty nine and a half'))

    def test_single_decimal_resolves_without_rewriting_raw_recognition_or_times(self):
        with tempfile.TemporaryDirectory() as directory:
            audio=Path(directory)/'fixture';audio.write_bytes(b'ASR binding fixture, not speech')
            record=self.record(audio);before=copy.deepcopy(record)
            result=resolve_numeric(record,self.expected,audio)
            self.assertEqual(record,before)
            self.assertEqual(result['recognized'],before['recognized'])
            self.assertEqual(result['word_times'],before['word_times'])
            self.assertNotIn('display_word_times',result)
            self.assertTrue(result['human_listening_required'])
            self.assertTrue(require_script_match(result,self.expected))

    def test_actual_adjacent_29_and_point5_merge_only_their_original_outer_span(self):
        with tempfile.TemporaryDirectory() as directory:
            audio=Path(directory)/'fixture';audio.write_bytes(b'ASR binding fixture, not speech')
            record=self.record(audio,split=True);before=copy.deepcopy(record)
            result=resolve_numeric(record,self.expected,audio)
            self.assertEqual(record,before)
            self.assertEqual(result['word_times'],before['word_times'])
            self.assertEqual(result['display_word_times'],[
                before['word_times'][0],{'word':'29.5','start':2.28,'end':3.60},before['word_times'][-1]])
            self.assertFalse(any(w['word'] in ('twenty','nine','and','a','half')
                                 for w in result['display_word_times']))
            self.assertTrue(require_script_match(result,self.expected))

    def test_invalid_decimals_and_other_words_cannot_clear_a_semantic_difference(self):
        with tempfile.TemporaryDirectory() as directory:
            audio=Path(directory)/'fixture';audio.write_bytes(b'ASR binding fixture, not speech')
            for wrong in ('about 29.4 days.','about 29.50 days.','about 29 5 days.',
                          'about 129.5 days.','about 29 . 5 days.','about 29.5 hours.',
                          'about 29.5 Earth days.'):
                with self.subTest(wrong=wrong):
                    record=self.record(audio);record['recognized']=wrong
                    with self.assertRaisesRegex(ValueError,'Not a number-format-only'):
                        resolve_numeric(record,self.expected,audio)

    def test_recognized_decimal_cannot_mask_different_or_missing_raw_words(self):
        with tempfile.TemporaryDirectory() as directory:
            audio=Path(directory)/'fixture';audio.write_bytes(b'ASR binding fixture, not speech')
            for wrong in ('29.4','29.50','29 5'):
                with self.subTest(wrong=wrong):
                    record=self.record(audio);record['word_times'][1]['word']=wrong
                    with self.assertRaisesRegex(ValueError,'raw word evidence'):
                        resolve_numeric(record,self.expected,audio)
            record=self.record(audio);record['word_times'].pop()
            with self.assertRaisesRegex(ValueError,'raw word evidence'):
                resolve_numeric(record,self.expected,audio)

    def test_stale_binding_still_fails_and_29_integer_equivalence_remains(self):
        with tempfile.TemporaryDirectory() as directory:
            audio=Path(directory)/'fixture';audio.write_bytes(b'ASR binding fixture, not speech')
            record=self.record(audio);audio.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'Stale ASR'):
                resolve_numeric(record,self.expected,audio)
            self.assertEqual(tokens('29 and a half'),tokens('twenty nine and a half'))


if __name__=='__main__':
    unittest.main()
