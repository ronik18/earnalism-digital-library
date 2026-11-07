import pathlib,sys,tempfile,json,subprocess,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from audio_derivation import derive_scene,check_unit,sha
class DerivationTests(unittest.TestCase):
 def fixture(self,p):
  source=p/'source';dest=p/'dest';(source/'raw').mkdir(parents=True);dest.mkdir();wav=source/'raw/fixture.wav'
  subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1.2','-ar','24000','-c:a','pcm_f32le',str(wav)],check=True)
  pathlib.Path(str(wav)+'.json').write_text(json.dumps({'status':'GENERATED_REQUIRES_REVIEW','wav_sha256':sha(wav),'audio':{'mechanical_checks':'PASS'},'provenance':{'model_id':'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice','model_revision':'fixture'}}))
  return source,dest,{'id':'fixture','text':'Hello there.'}
 def test_actual_tempo_derivative_keeps_original_and_source_binding(self):
  with tempfile.TemporaryDirectory() as d:
   source,dest,scene=self.fixture(pathlib.Path(d));before=sha(source/'raw/fixture.wav');r=derive_scene(source,dest,scene);self.assertTrue(.85<=r['tempo_factor']<=1.1);self.assertEqual(sha(source/'raw/fixture.wav'),before);self.assertEqual(check_unit(dest,'fixture')['status'],'DERIVED_REQUIRES_REVIEW');self.assertTrue(r['fresh_alignment_required']);self.assertFalse(r['pitch_shift'])
 def test_changed_derivative_source_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   source,dest,scene=self.fixture(pathlib.Path(d));derive_scene(source,dest,scene);(dest/'source-raw/fixture.wav').write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'Changed derivative source'):check_unit(dest,'fixture')
 def test_existing_derivative_cannot_be_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   source,dest,scene=self.fixture(pathlib.Path(d));derive_scene(source,dest,scene)
   with self.assertRaises(FileExistsError):derive_scene(source,dest,scene)
