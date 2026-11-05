import sys,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from audio_balance import analyze
class AudioBalanceTests(unittest.TestCase):
 def test_quiet_music_fails_and_scoped_boost_passes_without_silence_penalty(self):
  voice=[.1]*40;bed=[0.]*10+[.002]*30
  self.assertTrue(analyze(voice,bed,10)['issues'])
  fixed=[v*10**(9/20) for v in bed];r=analyze(voice,fixed,10)
  self.assertFalse(r['issues']);self.assertEqual(r['active_overlap_windows'],3);self.assertEqual(fixed[:10],[0.]*10)
 def test_music_masking_voice_and_missing_music_are_flagged(self):
  self.assertTrue(analyze([.1]*20,[.08]*20,10)['issues'])
  self.assertTrue(analyze([.1]*20,[0.]*20,10)['issues'])
 def test_stem_mismatch_rejected(self):
  with self.assertRaises(ValueError):analyze([.1],[.001,.002])

 def test_final_authored_fade_requires_actual_zero_music_tail(self):
  rate=100;voice=[.1]*300
  bed=[.004]*200+[.004*(1-i/60) if i<60 else 0 for i in range(100)]
  result=analyze(voice,bed,rate)
  self.assertTrue(result['windows'][-1]['terminal_music_silence'])
  self.assertTrue(result['windows'][-1]['fade_boundary'])
  self.assertFalse(result['passage_issues'])
  constant_weak=[.004]*200+[.001]*100
  bad=analyze(voice,constant_weak,rate)
  self.assertFalse(bad['windows'][-1]['terminal_music_silence'])
  self.assertTrue(any(v['start']==2 for v in bad['passage_issues']))
