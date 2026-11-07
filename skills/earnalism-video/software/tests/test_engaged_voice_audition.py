import json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio
class EngagedVoiceAuditionTests(unittest.TestCase):
 def test_audition_keeps_worker_speaker_and_retry_safeguards(self):
  ep=studio.load(studio.BASE/'episodes/moon-engaged-60-audition-v1.json')
  self.assertTrue(ep['private_test']);studio.validate(ep)
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'episode.json').write_text(json.dumps(ep));job=studio.make_job(p,{})
   self.assertEqual(job['max_attempts'],3)
   self.assertEqual({s['speaker'] for s in job['segments']},{'Ryan'})
   self.assertEqual(len({s['output_path'] for s in job['segments']}),2)
   self.assertEqual(job['segments'][0]['text'],job['segments'][1]['text'])
   self.assertNotEqual(job['segments'][0]['instruct'],job['segments'][1]['instruct'])
   self.assertTrue(all(len(s['text'].split())<=65 and len(s['text'])<=520 for s in job['segments']))
