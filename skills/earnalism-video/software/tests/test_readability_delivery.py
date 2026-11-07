import unittest,pathlib,sys,tempfile,json,subprocess
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio
class ReadabilityDelivery(unittest.TestCase):
 def test_landscape_caption_default_and_explicit_toggle(self):
  text=(studio.BASE/'watch-template.html').read_text()
  self.assertIn('label="English" default',text)
  self.assertIn('id="toggle-captions"',text)
  self.assertIn('captionsEnabled=on;',text)
  self.assertIn("sessionStorage.setItem(key+'-captions'",text)
 def test_no_duplicate_native_captions_in_shorts(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'landscape.mp4').touch();(p/'episode.json').write_text(json.dumps({'topic':'test','scenes':[],'sources':[]}));studio.draft_watch(p)
   self.assertNotIn('<track ',(p/'portrait-short.html').read_text())
   self.assertIn('Captions: burned in',(p/'portrait-short.html').read_text())
   from participant_preview import make
   make(p);self.assertNotIn('<track ',(p/'participant-shorts.html').read_text())
 def test_full_moon_qualified_and_landscape_labels_larger(self):
  text=(studio.BASE/'src/OrbitScene.tsx').read_text()
  self.assertIn("nearFull(phase)?'Almost fully lit'",text)
  actual=json.loads(subprocess.check_output(['node','--input-type=module','-e',"import {orbitLabel} from './src/readability.mjs';console.log(JSON.stringify(orbitLabel(false,'Earth',32).size))"],cwd=studio.BASE,text=True))
  self.assertGreaterEqual(actual,46)
