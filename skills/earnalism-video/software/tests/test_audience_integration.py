import ast,json,os,pathlib,subprocess,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio
ROOT=pathlib.Path(__file__).resolve().parents[1]
class AudienceIntegrationTests(unittest.TestCase):
 def test_generated_notebook_has_narration_import_closure_without_project_modules(self):
  root=pathlib.Path(os.environ.get('EARNALISM_TEST_PROJECT',ROOT.parent))
  notebook=json.loads((root/'Earnalism_Video_Narration_Pipeline.ipynb').read_text());embedded=None
  for cell in notebook['cells']:
   if cell['cell_type']!='code':continue
   tree=ast.parse(''.join(cell['source']))
   for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FILES' for t in node.targets):embedded=ast.literal_eval(node.value)
  self.assertIsNotNone(embedded)
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   for name,content in embedded.items():
    f=p/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(content)
   script="import sys,pathlib;sys.path.insert(0,sys.argv[1]);import audience_plan,production_journal,studio,colab_runner;assert all(pathlib.Path(m.__file__).is_relative_to(sys.argv[1]) for m in (audience_plan,production_journal,studio,colab_runner));print('EMBEDDED_IMPORT_PASS')"
   output=subprocess.check_output([sys.executable,'-I','-c',script,str(p)],cwd=p,text=True)
   self.assertIn('EMBEDDED_IMPORT_PASS',output)
 def test_frozen_candidate_does_not_inherit_platform_or_operations_records(self):
  import frozen_edition
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);source=root/'source';source.mkdir();dest=root/'fresh'
   ep=json.loads((ROOT/'examples/moon-audience-episode.json').read_text());(source/'episode.json').write_text(json.dumps(ep));(source/'props.json').write_text(json.dumps({'duration':1,'reviewOverlay':True}));(source/'publication-handoff.json').write_text('{"publication_authorized":true}');(source/'production-journal.jsonl').write_text('history must remain at its source\n')
   for name in frozen_edition.FROZEN:(source/name).write_bytes(name.encode())
   (source/'compare.html').write_text('old candidate links')
   (source/'quality-evidence').mkdir();(source/'quality-evidence/old-frame.png').write_bytes(b'previous candidate frame')
   # Real hash-bound selected artwork must survive even though video posters reset.
   from test_audience_plan import png
   png(source/'selected-cover.png',1280,720);png(source/'landscape.png',1280,720)
   (source/'packaging.json').write_text(json.dumps({'formats':{'landscape':{'master':{'path':'selected-cover.png','sha256':studio.sha(source/'selected-cover.png')},'small_previews':[]}}}))
   (source/'delivery-manifest.json').write_text(json.dumps({'episode.json':studio.sha(source/'episode.json')}))
   with patch.object(studio,'BASE',root),patch.object(studio,'verify_original'),patch('frozen_edition.verify',return_value={}),patch('intro.install',return_value=({'seconds':3,'placement':'end'},{})):
    frozen_edition.prepare(source,dest)
   self.assertFalse((dest/'publication-handoff.json').exists());self.assertFalse((dest/'production-journal.jsonl').exists());self.assertFalse(json.loads((dest/'review.json').read_text())['voice']);self.assertTrue((dest/'audience-plan.json').exists())
   self.assertFalse((dest/'quality-evidence').exists());self.assertFalse((dest/'compare.html').exists())
   self.assertEqual((dest/'selected-cover.png').read_bytes(),(source/'selected-cover.png').read_bytes());self.assertFalse((dest/'landscape.png').exists())
 def test_remix_resets_approvals_and_does_not_copy_platform_or_operations_records(self):
  from remix import remix
  class StopBeforeMix(Exception):pass
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);source=root/'source';source.mkdir();dest=root/'fresh';ep=json.loads((ROOT/'examples/moon-audience-episode.json').read_text());(source/'episode.json').write_text(json.dumps(ep));(source/'publication-handoff.json').write_text('{"publication_authorized":true}');(source/'production-journal.jsonl').write_text('source work only\n');(source/'delivery-manifest.json').write_text(json.dumps({'episode.json':studio.sha(source/'episode.json')}))
   for name in ['landscape.mp4','portrait.mp4','portrait-captioned.mp4','narration.wav','score.wav','props.json','captions.srt','captions.vtt']:(source/name).write_bytes(b'fixture')
   with patch.object(studio,'mix_score',side_effect=StopBeforeMix):
    with self.assertRaises(StopBeforeMix):remix(source,dest)
   self.assertFalse((dest/'publication-handoff.json').exists());self.assertFalse((dest/'production-journal.jsonl').exists());self.assertEqual(json.loads((dest/'review.json').read_text())['reviewer'],'')
if __name__=='__main__':unittest.main()
