import importlib.util,json,pathlib,sys,tempfile,unittest,os
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio
class StudioTests(unittest.TestCase):
 def test_original_checksum(self):
  base=pathlib.Path(os.environ['EARNALISM_TEST_PROJECT'])/'video_studio' if os.environ.get('EARNALISM_TEST_PROJECT') else studio.BASE
  with patch.object(studio,'BASE',base):self.assertEqual(studio.verify_original(),studio.ORIGINAL_SHA)
 def test_topic_needs_actual_diagram(self):
  e=studio.load(studio.BASE/'episodes/moon-phases.json');e['topic']='Economics'
  with self.assertRaises(ValueError):studio.validate(e)
 def test_claim_source_binding(self):
  e=studio.load(studio.BASE/'episodes/moon-phases.json');e['scenes'][0]['source_ids']=['invented']
  with self.assertRaises(ValueError):studio.validate(e)
 def test_audio_timing_subtitles(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);studio.captions([{'start':1.125,'end':2.75,'text':'Moon'}],p)
   self.assertIn('00:00:01,125 --> 00:00:02,750',(p/'captions.srt').read_text())
   self.assertIn('00:00:01.125 --> 00:00:02.750',(p/'captions.vtt').read_text())
 def test_overlapping_captions_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):studio.captions([{'start':0,'end':2,'text':'a'},{'start':1,'end':3,'text':'b'}],pathlib.Path(d))
 def test_no_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'x';studio.write(p,{'a':1})
   with self.assertRaises(FileExistsError):studio.write(p,{'a':2})
 def test_fixture_never_publish(self):
  with tempfile.TemporaryDirectory() as d:
   studio.write(pathlib.Path(d)/'episode.json',{'private_test':True})
   with self.assertRaisesRegex(ValueError,'never publish'):studio.release_check(d)
 def test_review_does_not_transfer(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);studio.write(p/'episode.json',{'private_test':False});studio.write(p/'review.json',{});studio.write(p/'delivery-manifest.json',{})
   with self.assertRaisesRegex(ValueError,'human review'):studio.release_check(p)
 def test_changed_watch_page_invalidates_review(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);studio.write(p/'episode.json',{'private_test':False,'scenes':[{'text':'A round world.'}]});studio.write(p/'props.json',{'intro':{'placement':'end'}});(p/'watch.html').write_text('original')
   studio.write(p/'rights-audit.json',{'status':'COMPLETE'});studio.write(p/'delivery-manifest.json',{'watch.html':studio.sha(p/'watch.html'),'rights-audit.json':studio.sha(p/'rights-audit.json')})
   review={k:True for k in ('factual','rights','voice','audiovisual','technical','delivery')};review.update({'reviewer':'test reviewer','delivery_manifest_sha256':studio.sha(p/'delivery-manifest.json')});studio.write(p/'review.json',review)
   with self.assertRaises((ValueError,FileNotFoundError)):studio.release_check(p) # Sparse manifests can no longer qualify
   (p/'watch.html').write_text('changed')
   with self.assertRaisesRegex(ValueError,'Delivery changed'):studio.release_check(p)
 def test_exact_worker_retry_journal(self):
  sys.path.insert(0,str(studio.BASE/'vendor'));import qwen_worker as q
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'journal';q.journal(p,{'event':'attempt_started','attempt':1});self.assertEqual(q.read_journal(p)[0]['attempt'],1)
   with p.open('a') as f:f.write('{broken')
   with self.assertRaisesRegex(RuntimeError,'Journal damaged'):q.read_journal(p)
if __name__=='__main__':unittest.main()

class PreservedNarrationTests(unittest.TestCase):
 def test_presentation_render_stops_before_video_if_voice_changes(self):
  import tempfile
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'narration.wav').write_bytes(b'changed')
   (p/'episode.json').write_text(json.dumps({'topic':'Moon fixture','private_test':True,'scenes':[],'sources':[]}))
   with patch.object(studio,'assemble',return_value={}),patch.object(studio,'run') as run:
    with self.assertRaisesRegex(ValueError,'Narration changed'):studio.render(p,expected_narration_sha256='0'*64)
   run.assert_not_called()
