import pathlib,sys,tempfile,wave,array,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from score import compose,score_plan
class ScoreMotifTests(unittest.TestCase):
 def test_motif_varies_by_scene_and_stays_within_audio(self):
  scenes=[{'diagram':'orbit','start':0},{'diagram':'phases','start':10},{'diagram':'cycle','start':20}]
  events=score_plan(32,scenes);self.assertEqual(len(events),12);self.assertTrue(all(0<=v[0]<32 for v in events));self.assertNotEqual([v[1] for v in events[:4]],[v[1] for v in events[6:10]])
 def test_important_statement_has_real_silence_and_deterministic_recording(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);compose(p/'a.wav',6,[(2,3)]);compose(p/'b.wav',6,[(2,3)]);self.assertEqual((p/'a.wav').read_bytes(),(p/'b.wav').read_bytes())
   with wave.open(str(p/'a.wav')) as w:data=array.array('h',w.readframes(w.getnframes()));rate=w.getframerate()
   self.assertTrue(all(v==0 for v in data[int(2.2*rate):int(2.8*rate)]));self.assertGreater(max(abs(v) for v in data),0)
