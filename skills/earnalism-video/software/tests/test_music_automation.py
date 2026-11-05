import unittest,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from music_automation import gain_plan,gain_at,transition_check,reentries
from audio_balance import analyze
class MusicAutomationTests(unittest.TestCase):
 def test_phrase_plan_is_bounded_and_slew_limited_under_extreme_alternation(self):
  rows=[{'start':i,'voice_dbfs':-16,'music_dbfs':-60 if (i//6)%2 else -25,'active_overlap':True} for i in range(36)]
  plan=gain_plan({'windows':rows});self.assertTrue(all(-12<=k['gain_db']<=8 for k in plan));self.assertFalse(transition_check(plan,[])['issues'])
  steps=[gain_at(i/100,plan) for i in range(3600)];self.assertLessEqual(max(abs(b-a)*100 for a,b in zip(steps,steps[1:])),1.001)
 def test_median_cannot_hide_individual_bad_passage(self):
  r=analyze([.1]*50,[.006]*40+[.001]*10,10);self.assertTrue(r['passage_issues']);self.assertTrue(r['issues'])
 def test_reentry_detects_long_rest_but_not_short_note_gap(self):
  self.assertEqual(reentries([0.]*100+[.1]*100+[0.]*20+[.1]*100,100),[1.0])

 def test_written_phrase_trims_preserve_bounds_and_slew(self):
  from music_automation import apply_scene_trims
  plan=[{'time':3+6*i,'gain_db':-4*i} for i in range(3)]
  output=apply_scene_trims(plan,[{'start':8,'end':17,'diagram':'cycle'}],{'cycle':-.5})
  self.assertFalse(transition_check(output,[])['issues']);self.assertTrue(all(-12<=k['gain_db']<=8 for k in output));self.assertEqual(plan[0]['gain_db'],0)
  with self.assertRaises(ValueError):apply_scene_trims(plan,[],{'cycle':-4})

 def test_short_reentry_is_bounded_monotonic_and_has_soft_endpoints(self):
  from music_automation import entry_gain
  values=[entry_gain(i/100,True) for i in range(101)]
  self.assertEqual(values[0],0);self.assertEqual(values[-1],1);self.assertTrue(all(a<=b for a,b in zip(values,values[1:])))
  self.assertLess(entry_gain(.001,True)/.001,.0001);self.assertLess((1-entry_gain(.999,True))/.001,.0001)
