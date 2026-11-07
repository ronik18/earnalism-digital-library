import unittest,tempfile,pathlib,sys,json
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio
class PublicationGates(unittest.TestCase):
 def fixture(self,p,edits=None,flags=None):
  def save(name,obj): (p/name).write_text(json.dumps(obj))
  save('episode.json',{'private_test':False,'scenes':[]})
  save('props.json',{'captions':[{'start':0,'end':2,'text':'A round world.'}],'intro':{'placement':'end'}})
  save('asr-review.json',[{'edits':edits or []}]);save('pace-review.json',{'scenes':[{'flags':flags or []}],'consistency':{'consistent':True}})
  save('rights-audit.json',{'status':'COMPLETE'})
  for name in ('landscape.mp4','portrait.mp4','portrait-captioned.mp4','captions.srt','captions.vtt','transcript.txt','sources.json','youtube.json','landscape.png','portrait.png'):(p/name).write_bytes(b'test artifact')
  save('technical.json',[{'file':n,'sha256':studio.sha(p/n),'decode':'PASS'} for n in ('landscape.mp4','portrait.mp4','portrait-captioned.mp4')])
  self.bind(p)
 def bind(self,p):
  (p/'delivery-manifest.json').write_text(json.dumps({f.name:studio.sha(f) for f in p.iterdir() if f.name not in ('delivery-manifest.json','review.json')}))
  (p/'review.json').write_text(json.dumps({**{k:True for k in ('factual','rights','voice','audiovisual','technical','delivery')},'reviewer':'test-only','delivery_manifest_sha256':studio.sha(p/'delivery-manifest.json')}))
 def test_unresolved_edit_cannot_hide_behind_similarity(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p,edits=[{'wrong':'word'}])
   with self.assertRaisesRegex(ValueError,'Unresolved ASR'):studio.release_check(p)
 def test_pacing_flags_need_explicit_bound_review(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p,flags=['Listen'])
   with self.assertRaisesRegex(ValueError,'pacing'):studio.release_check(p)
 def test_stale_technical_evidence_cannot_pass_rebound_manifest(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);(p/'landscape.mp4').write_bytes(b'changed');self.bind(p)
   with self.assertRaisesRegex(ValueError,'Stale technical'):studio.release_check(p)
 def test_caption_fragment_blocks_release(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);props=studio.load(p/'props.json');props['captions'][0]['end']=.3;(p/'props.json').write_text(json.dumps(props));self.bind(p)
   with self.assertRaisesRegex(ValueError,'Caption readability'):studio.release_check(p)
 def test_clean_production_marking_does_not_bypass_explicit_study_mode(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);ep=studio.load(p/'episode.json');ep['requires_independent_learning_study']=True;(p/'episode.json').write_text(json.dumps(ep));self.bind(p)
   with self.assertRaisesRegex(ValueError,'Explicitly required independent'):studio.release_check(p)
 def test_legacy_pending_research_does_not_replace_primary_strict_review(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);ep=studio.load(p/'episode.json');ep['requires_learning_acceptance']=True;(p/'episode.json').write_text(json.dumps(ep));self.bind(p)
   with self.assertRaisesRegex(ValueError,'Mandatory strict factual/graphical'):studio.release_check(p)

 def test_legacy_booleans_cannot_bypass_mandatory_strict_review(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);self.fixture(p);ep=studio.load(p/'episode.json');ep['strict_quality_required']=False;(p/'episode.json').write_text(json.dumps(ep));self.bind(p)
   with self.assertRaisesRegex(ValueError,'Mandatory strict factual/graphical'):studio.release_check(p)
