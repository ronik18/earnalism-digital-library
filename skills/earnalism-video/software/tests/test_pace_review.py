import pathlib,sys,tempfile,hashlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from pace_review import review,compare_scene_rates
class PaceTests(unittest.TestCase):
 def test_decimal_pause_at_exact_limit_does_not_create_a_roundoff_flag(self):
  with tempfile.TemporaryDirectory() as d:
   wav=pathlib.Path(d)/'audio';wav.write_bytes(b'fixture')
   words=[{'word':'grows,','start':11.12,'end':11.66},{'word':'then','start':12.56,'end':12.82},{'word':'shrinks.','start':12.82,'end':13.4}]
   r=review({'audio_sha256':hashlib.sha256(b'fixture').hexdigest(),'word_times':words},wav,'grows, then shrinks.',{'max_between_words_pause_seconds':.9})
   self.assertEqual(r['long_pauses'],[]);self.assertNotIn('Long pause inside a sentence: listen and inspect',r['flags'])
 def test_real_pause_above_limit_is_still_flagged(self):
  with tempfile.TemporaryDirectory() as d:
   wav=pathlib.Path(d)/'audio';wav.write_bytes(b'fixture')
   words=[{'word':'grows,','start':11.12,'end':11.66},{'word':'then','start':12.561,'end':12.82},{'word':'shrinks.','start':12.82,'end':13.4}]
   r=review({'audio_sha256':hashlib.sha256(b'fixture').hexdigest(),'word_times':words},wav,'grows, then shrinks.',{'max_between_words_pause_seconds':.9})
   self.assertEqual(len(r['long_pauses']),1);self.assertIn('Long pause inside a sentence: listen and inspect',r['flags'])
 def test_mid_sentence_gap_is_flagged_but_sentence_pause_is_retained(self):
  with tempfile.TemporaryDirectory() as d:
   wav=pathlib.Path(d)/'audio';wav.write_bytes(b'fixture')
   r={'audio_sha256':hashlib.sha256(b'fixture').hexdigest(),'word_times':[{'word':'The','start':0,'end':.3},{'word':'Moon.','start':1.5,'end':2},{'word':'Watch.','start':3.3,'end':3.8}]}
   report=review(r,wav,'The Moon. Watch.',{});self.assertEqual([v['sentence_boundary'] for v in report['long_pauses']],[False,True]);self.assertIn('Long pause inside a sentence: listen and inspect',report['flags'])
 def test_stale_audio_cannot_receive_pacing_approval(self):
  with tempfile.TemporaryDirectory() as d:
   wav=pathlib.Path(d)/'audio';wav.write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'Stale'):review({'audio_sha256':'old'},wav,'The Moon.',{})
 def test_inconsistent_scene_rates_are_detected(self):
  self.assertFalse(compare_scene_rates([{'spoken_wpm':95},{'spoken_wpm':130}])['consistent'])
  self.assertTrue(compare_scene_rates([{'spoken_wpm':121},{'spoken_wpm':126}])['consistent'])
 def test_selected_teacher_profile_is_used_without_brand_pronunciation(self):
  import studio
  policy=studio.load(studio.BASE/'config/defaults.json')
  self.assertEqual(studio.narration_instruction({'text':'The Moon stays round.','voice_profile':'teacher_gravity'},policy),policy['voice_profiles']['teacher_gravity']['instruction'])
  with self.assertRaisesRegex(ValueError,'Unknown voice profile'):studio.narration_instruction({'text':'The Moon.','voice_profile':'missing'},policy)

class CanonicalPacingTests(unittest.TestCase):
 def test_asr_missing_punctuation_does_not_hide_fast_second_sentence(self):
  from pace_review import canonical_sentence_rates
  words=[{'word':w,'start':i*.5,'end':(i+1)*.5} for i,w in enumerate('The Moon reflects light from the Sun'.split())]+[{'word':w,'start':4+i*.2,'end':4+(i+1)*.2} for i,w in enumerate('We see its surface clearly from Earth'.split())]
  # Correct sentence boundaries come from the canonical script; raw recognition has none.
  result=canonical_sentence_rates(words,'The Moon reflects light from the Sun. We see its surface clearly from Earth.')
  self.assertEqual(len(result),2);self.assertEqual(result[0]['words'],7);self.assertGreater(result[1]['wpm'],2*result[0]['wpm'])

 def test_new_default_does_not_change_frozen_B_generation_profile(self):
  import studio,json
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   for profile,temp in [('teacher_patient',.85),('teacher_mature_55',.7)]:
    (p/'episode.json').write_text(json.dumps({'id':'fixture','private_test':True,'scenes':[{'id':'one','text':'The Moon stays round.','voice_profile':profile}]}))
    job=studio.make_job(p,{})
    self.assertEqual(job['generation']['temperature'],temp)

class ShortSentencePacingTests(unittest.TestCase):
 def test_short_phrase_cannot_disappear_from_pacing_review(self):
  with tempfile.TemporaryDirectory() as d:
   wav=pathlib.Path(d)/'audio';wav.write_bytes(b'fixture')
   words=[{'word':w,'start':i*.1,'end':(i+1)*.1} for i,w in enumerate('Watch the light.'.split())]
   r=review({'audio_sha256':hashlib.sha256(b'fixture').hexdigest(),'word_times':words},wav,'Watch the light.',{})
   self.assertEqual(len(r['short_sentence_review_items']),1);self.assertIn('Short-sentence pace needs explicit listening review',r['flags'])
