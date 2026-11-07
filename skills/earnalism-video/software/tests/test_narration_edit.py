"""Synthetic tones test edit integrity only; they are never narration integration."""
import pathlib,sys,tempfile,json,subprocess,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from audio_derivation import check_unit,sha
from narration_edit import edit
class NarrationEditTests(unittest.TestCase):
 def source(self,p):
  src=p/'source';(src/'raw').mkdir(parents=True);wav=src/'raw/take.wav'
  subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=330:duration=2','-ar','24000','-c:a','pcm_f32le',str(wav)],check=True)
  pathlib.Path(str(wav)+'.json').write_text(json.dumps({'status':'GENERATED_REQUIRES_REVIEW','wav_sha256':sha(wav),'settings':{'speaker':'Ryan','instruct':'teacher fixture'},'audio':{'duration_seconds':2,'mechanical_checks':'PASS'},'provenance':{'model_id':'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice','model_revision':'fixture','worker_sha256':'fixture'}}))
  return src
 def test_edit_preserves_source_and_exact_pcm_slices(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);src=self.source(p);before=sha(src/'raw/take.wav');dest=p/'dest'
   result=edit({'id':'edited','text':'Three test words.'},dest,[dict(folder=src,scene='take',start=0,end=1),dict(folder=src,scene='take',start=1,end=2)])
   self.assertEqual(sha(src/'raw/take.wav'),before);self.assertEqual(check_unit(dest,'edited')['derivation']['kind'],'sentence_content_edit');self.assertFalse(result['derivation']['pitch_shift']);self.assertFalse(result['derivation']['retry_budgets_reset'])
   pcm=lambda f:subprocess.check_output(['ffmpeg','-v','error','-i',str(f),'-f','f32le','-'])
   self.assertEqual(pcm(src/'raw/take.wav'),pcm(dest/'raw/edited.wav'))
   retained=dest/'edit-sources/input-1/raw/take.wav';retained.write_bytes(b'tampered')
   with self.assertRaisesRegex(ValueError,'binding'):check_unit(dest,'edited')
 def test_out_of_source_range_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);src=self.source(p)
   with self.assertRaisesRegex(ValueError,'range'):edit({'id':'edited','text':'Three test words.'},p/'dest',[dict(folder=src,scene='take',start=0,end=3)])
