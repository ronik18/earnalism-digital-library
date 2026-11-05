import pathlib,sys,tempfile,unittest,wave,array,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from score import compose,anchors
class Refinements(unittest.TestCase):
 def test_anchor_uses_recorded_word_time(self):
  result=anchors({'anchors':[{'phrase':'first quarter','phase':.25}]},[{'word':'First','start':2.31},{'word':'quarter,','start':2.7}],10)
  self.assertEqual(result[0]['time'],12.31)
 def test_missing_anchor_fails(self):
  with self.assertRaises(ValueError):anchors({'anchors':[{'phrase':'full moon'}]},[],0)
 def test_score_is_quiet_and_fades(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'score.wav';compose(p,8,[(3,4)])
   with wave.open(str(p)) as w:a=array.array('h',w.readframes(w.getnframes()));rate=w.getframerate()
   rms=lambda lo,hi:math.sqrt(sum(x*x for x in a[int(lo*rate):int(hi*rate)])/((hi-lo)*rate))
   self.assertLess(max(abs(x) for x in a),2000)
   self.assertLess(rms(3.2,3.8),rms(4.2,4.8)*.3)
   self.assertLess(rms(0,.1),rms(2,2.5)*.1)

 def test_quiet_shoulders_are_continuous(self):
  from score import quiet_gain
  for boundary in (2,3,4,5):self.assertLess(abs(quiet_gain(boundary-1e-5,[(3,4)])-quiet_gain(boundary+1e-5,[(3,4)])),.0001)
 def test_score_records_scene_cues_and_no_imported_assets(self):
  import json
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'score.wav';compose(p,8,scenes=[{'diagram':'orbit','start':0}]);r=json.loads(p.with_suffix('.provenance.json').read_text());self.assertEqual(r['third_party_samples'],[]);self.assertEqual(len(r['events']),6)
