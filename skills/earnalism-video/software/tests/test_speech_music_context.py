import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from speech_music_context import interval_gap,flag_context
class Context(unittest.TestCase):
 def test_word_union_excludes_pause_and_double_count(self):
  r=interval_gap([1.,1.,0.,0.],[.1,.1,1.,1.],[(0,1),(0,2)],1)
  self.assertEqual(r['word_samples'],2);self.assertAlmostEqual(r['gap_db'],20)
 def test_rest_not_fake_infinite_gap(self):
  self.assertIsNone(interval_gap([1.],[0.],[(0,1)],1)['gap_db'])
 def test_outside_or_reversed_interval_rejected(self):
  for x in [[],[(0,2)],[(1,0)]]:
   with self.assertRaises(ValueError):interval_gap([1.],[.1],x,1)
class FlagContext(unittest.TestCase):
 def test_original_flag_not_overwritten_or_resolved(self):
  flags=[{'start':0,'gap_db':1}]
  r=flag_context([1.]*10,[.1]*10,flags,[{'start':0,'end':1,'word':'test'}],10)[0]
  self.assertEqual(r['original_flag']['gap_db'],1);self.assertEqual(flags[0]['gap_db'],1)
  self.assertEqual(r['word_context']['gap_db'],20);self.assertEqual(r['listening_status'],'UNRESOLVED')
 def test_window_clips_words_and_reports_coverage(self):
  r=flag_context([1.]*20,[.1]*20,[{'start':0}], [{'start':.5,'end':1.5,'word':'word'}],10)[0]
  self.assertEqual(r['word_context']['coverage_fraction'],.5)
 def test_no_words_is_unknown_not_pass(self):
  r=flag_context([1.]*10,[.1]*10,[{'start':0}],[],10)[0]
  self.assertIsNone(r['word_context']['gap_db']);self.assertEqual(r['listening_status'],'UNRESOLVED')

if __name__=='__main__':unittest.main()
