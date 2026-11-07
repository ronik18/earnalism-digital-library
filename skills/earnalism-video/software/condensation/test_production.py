"""Mechanism/production safeguards, not fabricated narration or listening results."""
import copy,json,tempfile,unittest
from pathlib import Path
from . import build_colab,finish
from ..thermal_touch.assemble import published_b_reference,validate_units
class CondensationTests(unittest.TestCase):
 def test_original_b_worker_and_recipe_still_pinned(self):
  baseline,metadata=published_b_reference();self.assertEqual(baseline['speaker'],'Ryan') if 'speaker' in baseline else self.assertTrue(metadata['settings'])
 def timeline(self):
  units=json.loads((build_colab.PROJECT/'output/episodes/05-condensation/preproduction/script-units.json').read_text());validate_units(units)
  return {'duration':120,'scenes':[{**u,'start':i*20.,'end':(i+1)*20.,'marks':{k:1.+j*3 for j,k in enumerate(u['anchors'])}} for i,u in enumerate(units)]}
 def test_score_uses_actual_marks_and_rest_interiors(self):
  t=self.timeline();p=finish.phrase_plan(t);self.assertTrue(p['events']);self.assertEqual(p['listening'],'PENDING');self.assertFalse(p['publication_approved'])
  for r in p['rests']:self.assertEqual(finish.shoulder((r['start']+r['end'])/2,p['quiet_intervals']),0.)
 def test_missing_narration_anchor_blocks_score(self):
  t=self.timeline();del t['scenes'][3]['marks']['liquid']
  with self.assertRaises(ValueError):finish.phrase_plan(t)
 def test_discontinuous_scene_blocks_score(self):
  t=self.timeline();t['scenes'][1]['start']+=.2
  with self.assertRaises(ValueError):finish.phrase_plan(t)
 def test_notebook_is_disabled_and_isolated(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);(d/'units.json').write_text(json.dumps(self.timeline()['scenes']))
   # Use original untimed units; estimated proof times never become final timing.
   (d/'units.json').write_bytes((build_colab.PROJECT/'output/episodes/05-condensation/preproduction/script-units.json').read_bytes())
   build_colab.build(d);s=(d/'colab-launch.py').read_text();self.assertIn('RUN_CONDENSATION = False',s);self.assertIn('EXISTING_COMPUTE_ALLOWED = False',s);self.assertIn('/content/earnalism-condensation-v1',s)
   self.assertNotIn('/content/earnalism-thermal-touch-v1',s)
if __name__=='__main__':unittest.main()
