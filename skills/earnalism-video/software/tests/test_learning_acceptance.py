import sys,pathlib,unittest,tempfile,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from learning_acceptance import pending,validate,CASES
class LearningAcceptanceTests(unittest.TestCase):
 def test_prepared_records_and_empty_responses_never_count_as_acceptance(self):
  r=pending()
  with self.assertRaisesRegex(ValueError,'bound'):validate(r,'new-manifest')
  r['delivery_manifest_sha256']='m';r['learning'].update(decision='PASS',reviewer='fixture-reviewer')
  with self.assertRaisesRegex(ValueError,'Actual first-time'):validate(r,'m')
 def test_real_response_fields_cannot_clear_unrun_device_cases_or_new_edition(self):
  r=pending();r['delivery_manifest_sha256']='m';r['learning'].update(decision='PASS',reviewer='fixture-reviewer',participants=[{'id':'test-only','first_time':True,'single_uninterrupted_view':True,'responses':{'q1':'fixture1','q2':'fixture2','q3':'fixture3'}}])
  with self.assertRaisesRegex(ValueError,'device/listening'):validate(r,'m')
  r['acceptance']={'reviewer':'fixture-reviewer','cases':{k:{'status':'PASS','evidence':'TEST DATA ONLY','device':'TEST DEVICE ONLY'} for k in CASES}}
  self.assertTrue(validate(r,'m'))
  r['acceptance']['cases']['physical_speakers']['device']=''
  with self.assertRaisesRegex(ValueError,'device/listening'):validate(r,'m')
  r['acceptance']['cases']['physical_speakers']['device']='TEST DEVICE ONLY'
  with self.assertRaisesRegex(ValueError,'bound'):validate(r,'changed-manifest')
 def test_frozen_audio_edit_is_rejected(self):
  from frozen_edition import verify
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'mix.wav').write_bytes(b'changed');(p/'frozen-assets.json').write_text(json.dumps({'files':{'mix.wav':'original-hash'}}))
   with self.assertRaisesRegex(ValueError,'Frozen audio'):verify(p)
 def test_clean_video_keeps_exact_reference_audio_without_changing_picture(self):
  import subprocess
  from unittest.mock import patch
  import studio
  from frozen_edition import copy_frozen_soundtrack,encoded_audio_hash
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);src=root/'outputs/ref';dst=root/'outputs/clean';src.mkdir(parents=True);dst.mkdir()
   for folder,color,tone in [(src,'blue','440'),(dst,'green','880')]:
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color={color}:s=160x90:r=30:d=1','-f','lavfi','-i',f'sine=frequency={tone}:duration=1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(folder/'landscape.mp4')],check=True)
   (src/'delivery-manifest.json').write_text(json.dumps({'landscape.mp4':studio.sha(src/'landscape.mp4')}));(dst/'frozen-assets.json').write_text(json.dumps({'source_private_edition':'ref','source_manifest_sha256':studio.sha(src/'delivery-manifest.json')}))
   stream=lambda p:subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-'])
   picture=stream(dst/'landscape.mp4');expected=encoded_audio_hash(src/'landscape.mp4')
   self.assertNotEqual(encoded_audio_hash(dst/'landscape.mp4'),expected)
   with patch('studio.BASE',root):copy_frozen_soundtrack(dst,dst/'landscape.mp4')
   self.assertEqual(stream(dst/'landscape.mp4'),picture);self.assertEqual(encoded_audio_hash(dst/'landscape.mp4'),expected)
