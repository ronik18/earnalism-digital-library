import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retime_score import timeline_map,map_time,preserve_events,map_intervals,covered

class RetimeTests(unittest.TestCase):
 def scenes(self,end=10,anchor=4):return [{'id':'a','text':'Same spoken explanation.','start':0,'end':end,'anchors':[{'phrase':'Same','time':anchor}]}]
 def test_actual_anchor_maps_exactly_and_other_points_interpolate(self):
  points=timeline_map(self.scenes(),self.scenes(12,5));self.assertEqual(map_time(4,points),5);self.assertAlmostEqual(map_time(7,points),8.5)
 def test_identity_preserves_content_and_chord_strum(self):
  events=[{'time':2,'midi':50,'instrument':'piano','phrase':'chord','velocity':.31,'duration':4,'pan':0,'arrangement_gain_db':-2},{'time':2.065,'midi':57,'instrument':'piano','phrase':'chord','velocity':.27,'duration':4,'pan':0,'arrangement_gain_db':-2}]
  old=copy.deepcopy(events);out,_=preserve_events(events,timeline_map(self.scenes(),self.scenes(12,5)),12)
  self.assertAlmostEqual(out[1]['time']-out[0]['time'],.065);self.assertEqual(events,old)
  self.assertEqual([{k:v for k,v in x.items() if k!='time'} for x in out],[{k:v for k,v in x.items() if k!='time'} for x in events])
 def test_rests_follow_same_semantic_map(self):
  p=timeline_map(self.scenes(),self.scenes(12,5));rests=map_intervals([[3,4],[4,6]],p);self.assertEqual(rests,[[3.75,5.0],[5.0,7.333333]]);self.assertTrue(covered([4,7],rests));self.assertFalse(covered([3,7],rests))
 def test_conflicts_reversed_anchors_text_or_unbounded_scales_fail(self):
  for new in [self.scenes(12,11),self.scenes(30,4)]:
   with self.assertRaises(ValueError):timeline_map(self.scenes(),new)
  new=self.scenes();new[0]['text']='Different content.'
  with self.assertRaises(ValueError):timeline_map(self.scenes(),new)
  with self.assertRaises(ValueError):timeline_map(self.scenes(),self.scenes(),[{'old':4,'new':5,'label':'conflict'}])
 def test_fixed_strum_cannot_silently_reorder_notes(self):
  p=[{'old':0,'new':0},{'old':10,'new':5}]
  ev=[{'time':1,'midi':50,'instrument':'piano','phrase':'a'},{'time':1.2,'midi':57,'instrument':'piano','phrase':'a'},{'time':1.3,'midi':62,'instrument':'piano','phrase':'b'}]
  with self.assertRaises(ValueError):preserve_events(ev,p,5)

if __name__=='__main__':unittest.main()
