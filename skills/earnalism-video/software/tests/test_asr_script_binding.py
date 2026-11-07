import unittest,pathlib,sys,json,tempfile
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from asr_review import require_script_match
import studio
class ScriptBindingTests(unittest.TestCase):
 def record(self,words):return {'recognized':words,'word_times':[{'word':w,'start':i*.2,'end':i*.2+.2} for i,w in enumerate(words.split())],'unresolved_asr_edits':[]}
 def test_actual_words_required_even_when_old_asr_has_no_edits(self):
  with self.assertRaisesRegex(ValueError,'script does not match'):require_script_match(self.record('The Moon reflects sunlight.'),'The Moon creates sunlight.')
 def test_existing_exact_orthographic_display_resolutions_remain_valid(self):
  r=self.record('Our view point changes in 29 days.');r['display_word_times']=self.record('Our viewpoint changes in twenty nine days.')['word_times']
  self.assertTrue(require_script_match(r,'Our viewpoint changes in twenty nine days.'))
 def test_invented_display_words_do_not_repair_missing_speech(self):
  r=self.record('The Moon creates sunlight.');r['display_word_times']=self.record('The Moon reflects sunlight.')['word_times']
  with self.assertRaises(ValueError):require_script_match(r,'The Moon reflects sunlight.')
 def test_assemble_rejects_text_edit_before_any_media_command(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'raw').mkdir();(p/'alignment').mkdir();wav=p/'raw/s1.wav';wav.write_bytes(b'test input')
   r=self.record('The Moon reflects sunlight.');r['audio_sha256']=studio.sha(wav)
   (p/'episode.json').write_text(json.dumps({'scenes':[{'id':'s1','text':'The Moon creates sunlight.'}]}));(p/'alignment/s1.json').write_text(json.dumps(r))
   with patch('audio_derivation.check_unit',return_value={}),patch.object(studio,'duration',return_value=1),patch.object(studio,'run') as run:
    with self.assertRaisesRegex(ValueError,'script does not match'):studio.assemble(p)
   run.assert_not_called()
 def test_frozen_render_rejects_current_script_drift(self):
  from frozen_edition import verify
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'raw').mkdir();(p/'alignment').mkdir();wav=p/'raw/s1.wav';wav.write_bytes(b'unchanged source')
   r=self.record('The Moon reflects sunlight.');r['audio_sha256']=studio.sha(wav)
   (p/'frozen-assets.json').write_text(json.dumps({'files':{'raw/s1.wav':studio.sha(wav)},'body_seconds':1}))
   (p/'alignment/s1.json').write_text(json.dumps(r));(p/'props.json').write_text(json.dumps({'duration':1,'reviewOverlay':False}))
   ep={'scenes':[{'id':'s1','text':'The Moon creates sunlight.'}]};(p/'episode.json').write_text(json.dumps(ep))
   with patch('frozen_edition.check_unit',return_value={}),patch.object(studio,'validate',side_effect=lambda x:x):
    with self.assertRaisesRegex(ValueError,'script does not match'):verify(p)
    ep['scenes'][0]['text']='The Moon reflects sunlight.';(p/'episode.json').write_text(json.dumps(ep))
    self.assertEqual(verify(p)['duration'],1)
