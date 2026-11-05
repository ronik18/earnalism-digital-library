import json,pathlib,sys,tempfile,unittest,hashlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from intro import shift_cues,install
class IntroTests(unittest.TestCase):
 def test_audio_captions_shift_without_mutating_body(self):
  body=[{'start':.24,'end':1.87,'text':'The Moon reflects sunlight.'}]
  export=shift_cues(body,3)
  self.assertEqual(export,[{'start':3.24,'end':4.87,'text':body[0]['text']}]);self.assertEqual(body[0]['start'],.24)
  with self.assertRaises(ValueError):shift_cues(body,-3)
 def test_intro_tamper_stops_install(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);a=p/'assets';a.mkdir();out=p/'run';out.mkdir()
   (a/'landscape.mp4').write_bytes(b'changed')
   (a/'manifest.json').write_text(json.dumps({'seconds':3,'version':'test','files':{'landscape.mp4':hashlib.sha256(b'original').hexdigest()}}))
   with self.assertRaisesRegex(ValueError,'hash mismatch'):install(out,a)
   self.assertFalse((out/'intro-landscape.mp4').exists())
 def test_install_preserves_existing_intro(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);a=p/'assets';a.mkdir();out=p/'run';out.mkdir()
   for fmt in ('landscape','portrait'):(a/(fmt+'.mp4')).write_bytes(fmt.encode())
   (a/'manifest.json').write_text(json.dumps({'seconds':3,'version':'test','files':{f+'.mp4':hashlib.sha256(f.encode()).hexdigest() for f in ('landscape','portrait')}}))
   (out/'intro-landscape.mp4').write_bytes(b'keep')
   with self.assertRaises(FileExistsError):install(out,a)
   self.assertEqual((out/'intro-landscape.mp4').read_bytes(),b'keep')

 def test_wrong_selected_version_fails_before_copy(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'manifest.json').write_text(json.dumps({'seconds':3,'version':'other'}))
   with self.assertRaisesRegex(ValueError,'version mismatch'):install(p,p,'selected')
 def test_portrait_corruption_leaves_no_partial_install(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);a=p/'assets';a.mkdir();out=p/'run';out.mkdir()
   (a/'landscape.mp4').write_bytes(b'good');(a/'portrait.mp4').write_bytes(b'bad')
   (a/'manifest.json').write_text(json.dumps({'seconds':3,'version':'test','files':{f+'.mp4':hashlib.sha256(b'good').hexdigest() for f in ('landscape','portrait')}}))
   with self.assertRaisesRegex(ValueError,'hash mismatch'):install(out,a)
   self.assertEqual(list(out.iterdir()),[])

 def test_publication_defaults_append_brand_without_spoken_name(self):
  import studio
  policy=studio.load(studio.BASE/'config/defaults.json')
  self.assertEqual(policy['intro']['placement'],'end')
  self.assertEqual(policy['intro']['caption_offset_seconds'],0)
  self.assertEqual(studio.speech_text({'text':'Earnalism. See differently.','tts_text':'Earn Al-ism. See differently.'},policy),'See differently.')
  self.assertEqual(studio.omit_spoken_brand('A round world. Earnalism. See differently.'),'A round world. See differently.')

 def test_brand_removal_is_idempotent_for_colab_resume(self):
  import studio
  original={'scenes':[{'text':'Earnalism. See differently.','tts_text':'Earn Al-ism. See differently.'}]}
  normalized=studio.normalize_episode(original,{'spoken_brand_name':False})
  self.assertEqual(normalized,studio.normalize_episode(normalized,{'spoken_brand_name':False}))
  self.assertEqual(original['scenes'][0]['text'],'Earnalism. See differently.')
  self.assertEqual(normalized['scenes'][0]['text'],'See differently.')
