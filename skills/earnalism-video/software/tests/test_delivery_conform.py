import pathlib,sys,tempfile,json,subprocess,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from delivery_conform import sentences,word_map,plan,render_scene
from audio_derivation import sha,check_unit
class DeliveryConformTests(unittest.TestCase):
 def test_speaking_plan_uses_complete_sentences_and_rejects_missing_words(self):
  ep={'scenes':[{'id':'s01','text':'The round Moon reflects the sunlight. We see its light.'}]}
  words=[{'word':w,'start':i*.43,'end':(i+1)*.43} for i,w in enumerate(ep['scenes'][0]['text'].split())]
  mapped=word_map(ep,[('block',{'word_times':words,'unresolved_asr_edits':[]})]);result=plan(ep,mapped,{'block':6})
  self.assertEqual(len(result[0]['phrases']),2);self.assertEqual(result[0]['phrases'][-1]['pad_after'],.65)
  self.assertTrue(.8<=result[0]['phrases'][0]['tempo']<=1.2)
  with self.assertRaisesRegex(ValueError,'complete canonical'):word_map(ep,[('block',{'word_times':words[:-1],'unresolved_asr_edits':[]})])
 def test_derivative_keeps_source_binding_and_rejects_tampering(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);src=root/'source';(src/'raw').mkdir(parents=True);wav=src/'raw/block.wav'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=140:duration=3','-ar','24000','-c:a','pcm_f32le',str(wav)],check=True)
   (src/'raw/block.wav.json').write_text(json.dumps({'status':'GENERATED_REQUIRES_REVIEW','wav_sha256':sha(wav),'settings':{'speaker':'Ryan','instruct':'fixture'},'audio':{'duration_seconds':3,'mechanical_checks':'PASS'},'provenance':{'model_id':'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice'}}))
   ph={'scene':'s01','text':'A fixture tests the source binding.','phrases':[{'text':'A fixture tests the source binding.','tempo':1.05,'parts':[{'source':'block','start':0,'end':2.8}],'pad_after':.45}]};dest=root/'dest'
   render_scene(dest,src,ph,{'block':0});self.assertEqual(check_unit(dest,'s01')['derivation']['passes_from_original'],1)
   self.assertFalse(check_unit(dest,'s01')['derivation']['pitch_shift'])
   (dest/'delivery-source/raw/block.wav').write_bytes(b'corrupted')
   with self.assertRaisesRegex(ValueError,'binding'):check_unit(dest,'s01')
 def test_gross_rushing_cannot_be_hidden_by_large_tempo_processing(self):
  ep={'scenes':[{'id':'s01','text':'The Moon reflects light from the Sun.'}]}
  words=[{'word':w,'start':i*.1,'end':(i+1)*.1} for i,w in enumerate(ep['scenes'][0]['text'].split())]
  mapped=word_map(ep,[('block',{'word_times':words,'unresolved_asr_edits':[]})])
  with self.assertRaisesRegex(ValueError,'consistent speech band'):plan(ep,mapped,{'block':1})
 def test_quiet_boundary_and_original_file_tail_are_retained(self):
  from delivery_conform import quiet_boundary
  samples=[.1]*24000+[0.]*24000+[.1]*24000
  self.assertTrue(1.1<=quiet_boundary(samples,1.1,1.8)<=1.8)
  ep={'scenes':[{'id':'s01','text':'A short phrase.'}]};words=[{'word':w,'start':i*.5,'end':(i+1)*.5} for i,w in enumerate(ep['scenes'][0]['text'].split())]
  result=plan(ep,word_map(ep,[('block',{'word_times':words,'unresolved_asr_edits':[]})]),{'block':3},source_words={'block':words},audio_samples={'block':samples})
  self.assertEqual(result[0]['phrases'][-1]['parts'][-1]['end'],3)
 def test_source_tone_matching_is_bounded(self):
  from delivery_conform import validate
  # Reject excessive tone adjustment even when there are no source entries to traverse.
  from unittest.mock import patch
  meta={'settings':{'instruct':'x'},'provenance':{},'derivation':{'pitch_shift':False,'passes_from_original':1,'sources':{'block':{'wav_sha256':'x','meta_sha256':'x','tone_eq_db':3}},'plan':{'phrases':[]}}}
  with patch('audio_derivation.check_unit',return_value={'settings':{'speaker':'Ryan','instruct':'x'},'provenance':{}}),patch('audio_derivation.sha',return_value='x'):
   with self.assertRaisesRegex(ValueError,'source-tone'):validate(pathlib.Path('/unused'),meta)
