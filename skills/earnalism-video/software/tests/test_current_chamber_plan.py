"""Exercise the registered production score planner with changed narration lengths."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from final_chamber_score import plan
class CurrentChamberPlanTests(unittest.TestCase):
 def test_short_sunlight_motif_fits_actual_scene_and_keeps_identity(self):
  start,end=4.8,11.04
  events,_=plan(70.16,[{'diagram':'sunlight','start':start,'end':end}])
  motif=[e for e in events if e['phrase']=='question: D A E F']
  self.assertEqual([e['midi'] for e in motif],[62,69,64,65])
  self.assertTrue(all(start<=e['time']<=end-.649 for e in motif))
  self.assertTrue(any(8<=e['time']<10 for e in motif))
 def test_long_sunlight_phrase_preserves_existing_placement(self):
  events,_=plan(90,[{'diagram':'sunlight','start':8,'end':22}])
  motif=[e for e in events if e['phrase']=='question: D A E F']
  self.assertEqual([e['time'] for e in motif],[14.2,15.85,17.25,19.15])
 def test_quarter_reasoning_silence_tracks_new_actual_anchors(self):
  _,quiet=plan(70.16,[{'diagram':'phases','start':20.48,'end':37.28,'anchors':[{'phrase':'At first quarter','time':24.6},{'phrase':'First quarter means','time':28.1},{'phrase':'Near full Moon','time':33.0}]}])
  self.assertIn((24.35,32.65),quiet)
