import unittest,sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from improvement import assess
class ImprovementTests(unittest.TestCase):
 def test_smooth_transitions_do_not_clear_bad_mix_or_fixture(self):
  r=assess({'private_test':True},{'issues':['quiet']},{'transition_check':{'issues':[],'maximum_phrase_gain_rate_db_per_second':1}}, {},True)
  self.assertEqual(r['status'],'RED_HOLD');self.assertGreaterEqual(len(r['holds']),3);self.assertFalse(r['autopublish'])
 def test_stale_manifest_blocks_even_complete_human_review(self):
  review={'reviewer':'owner',**{k:True for k in ['factual','rights','voice','audiovisual','technical','delivery']}}
  r=assess({'private_test':False},{'issues':[]},{'transition_check':{'issues':[],'maximum_phrase_gain_rate_db_per_second':1}},review,False)
  self.assertIn('Stale or incomplete delivery manifest',r['holds'])

 def test_pending_human_review_does_not_suggest_release_handoff(self):
  r=assess({'private_test':False},{'issues':[]},{'transition_check':{'issues':[],'maximum_phrase_gain_rate_db_per_second':1}}, {},True)
  self.assertIn('human review',r['next_action']);self.assertNotIn('handoff',r['next_action'])
