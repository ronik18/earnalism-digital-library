import pathlib,sys,tempfile,json,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import strict_quality as q
import test_strict_quality as fixtures
class MotionCheckpointTests(unittest.TestCase):
 def test_observed_defect_is_sampled_in_both_final_formats(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);fixtures.StrictQualityTests().fixture(p);props=q.load(p/'props.json');scene=props['scenes'][0];scene['review_checkpoints']=[{'id':'connector-crossing','offset_seconds':1,'reason':'Check label glyphs above all connector paths'}];(p/'props.json').write_text(json.dumps(props));rows=[x for x in q.plan(p)['frames'] if x['id'].endswith('regression-connector-crossing')]
   self.assertEqual({r['format'] for r in rows},{'Landscape','Portrait'});self.assertTrue(all(r['seconds']==scene['start']+1 for r in rows))
 def test_invalid_or_ambiguous_checkpoints_do_not_silently_pass(self):
  for points in [[{'id':'x','offset_seconds':99,'reason':'outside'}],[{'id':'x','offset_seconds':True,'reason':'invalid'}],[{'id':'x','offset_seconds':1,'reason':''}],[{'id':'x','offset_seconds':1,'reason':'a'}]*2]:
   with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d);fixtures.StrictQualityTests().fixture(p);props=q.load(p/'props.json');props['scenes'][0]['review_checkpoints']=points;(p/'props.json').write_text(json.dumps(props))
    with self.assertRaises(ValueError):q.plan(p)
if __name__=='__main__':unittest.main()
