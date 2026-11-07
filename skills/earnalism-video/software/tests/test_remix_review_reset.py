import pathlib,sys,tempfile,json,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio
from remix import remix
class ReviewResetTests(unittest.TestCase):
 def test_source_approvals_and_provenance_do_not_leak_into_new_edition(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);src=p/'source';src.mkdir();dst=p/'new';files=['landscape.mp4','portrait.mp4','portrait-captioned.mp4']
   for n in files:(src/n).write_bytes(b'private fixture')
   (src/'episode.json').write_text('{"private_test": true, "music": {}}')
   prior={'reviewer':'old reviewer','voice':True,'audiovisual':True};(src/'review.json').write_text(json.dumps(prior));(src/'remix-provenance.json').write_text('{"source":"old"}')
   (src/'strict-quality-review.json').write_text('{"factual":{"decision":"PASS","reviewer":"old"}}')
   (src/'acceptance-review.json').write_text('{"learning":{"decision":"PASS","reviewer":"old"}}')
   names=files+['strict-quality-review.json','acceptance-review.json','episode.json','review.json','remix-provenance.json'];(src/'delivery-manifest.json').write_text(json.dumps({n:studio.sha(src/n) for n in names}))
   with patch('studio.mix_score',side_effect=RuntimeError('stop after cloning')):
    with self.assertRaisesRegex(RuntimeError,'stop after cloning'):remix(src,dst)
   self.assertEqual(json.loads((dst/'strict-quality-review.json').read_text())['factual']['decision'],'PENDING');self.assertFalse(json.loads((dst/'review.json').read_text())['voice']);self.assertEqual(json.loads((src/'review.json').read_text()),prior);self.assertFalse((dst/'remix-provenance.json').exists());self.assertEqual(json.loads((dst/'acceptance-review.json').read_text())['learning']['decision'],'PENDING')

