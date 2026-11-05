import unittest,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phrase_music_repair import adjust_plan,feasibility,source_bindings,require_source_bindings,compose

class PhraseRepairTests(unittest.TestCase):
 def test_reports_infeasible_slow_gain_instead_of_hiding_flag(self):
  r={'windows':[{'start':16,'active_overlap':True,'music_below_voice_db':8.23},{'start':17,'active_overlap':True,'music_below_voice_db':28.53}]}
  result=feasibility(r);self.assertFalse(result['adjacent_constraints_feasible']);self.assertEqual(result['conflicts'][0]['required_gain_change_db'],4.3)
 def test_moves_existing_chord_to_nearby_phrase_without_changing_notes(self):
  voice=[.001]*1000+[.1]*1000
  source=[{'time':.5,'midi':50,'instrument':'piano','phrase':'chord'},{'time':.565,'midi':57,'instrument':'piano','phrase':'chord'}]
  result,changes=adjust_plan(source,[],voice,1000,3)
  self.assertEqual(len(changes),1);self.assertEqual([e['midi'] for e in result],[50,57]);self.assertAlmostEqual(result[1]['time']-result[0]['time'],.065);self.assertEqual(source[0]['time'],.5)
 def test_does_not_cross_an_authored_rest_or_another_note(self):
  voice=[.001]*1000+[.1]*2000
  source=[{'time':.5,'midi':50,'instrument':'piano','phrase':'a'},{'time':.9,'midi':57,'instrument':'piano','phrase':'b'}]
  result,changes=adjust_plan(source,[(.8,1.3)],voice,1000,4)
  self.assertLess(result[0]['time'],.8);self.assertEqual(result[1]['time'],source[1]['time']);self.assertEqual([e['midi'] for e in result],[50,57])
 def test_source_change_during_render_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'composer.py';p.write_text('first')
   bound=source_bindings([p]);self.assertTrue(require_source_bindings(bound));p.write_text('changed')
   with self.assertRaises(ValueError):require_source_bindings(bound)
 def test_unrelated_palette_is_rejected_before_outputs(self):
  with self.assertRaises(ValueError):compose('/no/output.wav',5,palette='unrelated')
 def test_clear_phrase_is_not_chased(self):
  voice=[.1]*4000
  source=[{'time':.5,'midi':50,'instrument':'piano','phrase':'a'}]
  self.assertEqual(adjust_plan(source,[],voice,1000,4),(source,[]))
if __name__=='__main__':unittest.main()
