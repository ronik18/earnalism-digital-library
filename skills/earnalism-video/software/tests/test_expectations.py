import json,pathlib,sys,unittest,tempfile,shutil
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from expectations import audit,ROOT
class ExpectationTests(unittest.TestCase):
 def fixture(self,d):
  p=pathlib.Path(d)
  for name in ['config/defaults.json','config/editorial-contract.json','src/branding.mjs','src/social-safe-area.mjs','src/opening-visibility.mjs','src/readability.mjs','assets/standard-intro/v1/production-lockup.png','public/brand-sting/production-lockup.png','watch-template.html']:
   out=p/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,out)
  return p
 def test_current_contract_passes_without_approving_media(self):
  r=audit();self.assertEqual(r['status'],'PASS');self.assertFalse(r['human_approvals_supplied'])
 def test_voice_and_outro_and_paid_default_drift_fail(self):
  for key,value in [('speaker','AnotherProvider'),('spoken_brand_name',True),('paid_compute_allowed',True)]:
   with self.subTest(key=key),tempfile.TemporaryDirectory() as d:
    p=self.fixture(d);r=json.loads((p/'config/defaults.json').read_text());r[key]=value;(p/'config/defaults.json').write_text(json.dumps(r))
    with self.assertRaisesRegex(ValueError,'Default drift'):audit(p)
  with tempfile.TemporaryDirectory() as d:
   p=self.fixture(d);r=json.loads((p/'config/defaults.json').read_text());r['intro']['placement']='start';(p/'config/defaults.json').write_text(json.dumps(r))
   with self.assertRaisesRegex(ValueError,'Brand ending'):audit(p)
 def test_asset_substitution_and_download_ui_drift_fail(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.fixture(d);(p/'public/brand-sting/production-lockup.png').write_bytes(b'substitute')
   with self.assertRaisesRegex(ValueError,'brand asset'):audit(p)
  with tempfile.TemporaryDirectory() as d:
   p=self.fixture(d);f=p/'watch-template.html';f.write_text(f.read_text()+'<a download href="movie.mp4">Download</a>')
   with self.assertRaisesRegex(ValueError,'download link'):audit(p)

 def test_opening_visibility_and_creator_question_cannot_silently_regress(self):
  for filename,content,reason in [('opening-visibility.mjs','export const subjectOpacity=()=>0;','visibility drift'),('readability.mjs',"export const questionHeading=()=> 'Fixed Moon headline';",'question replaced')]:
   with self.subTest(filename=filename),tempfile.TemporaryDirectory() as d:
    p=self.fixture(d);(p/'src'/filename).write_text(content)
    with self.assertRaisesRegex(ValueError,reason):audit(p)

 def test_legacy_corner_watermark_cannot_pass_preflight(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.fixture(d);f=p/'src/branding.mjs';text=f.read_text();start=text.index('export function watermarkLayout(');end=text.index('export function schematicContext(')
   f.write_text(text[:start]+"export function watermarkLayout(width,height){const size=height>width?72:82,right=height>width?65:70,top=height>width?44:48;return {size,right,top,left:width-right-size,opacity:.48};}\n"+text[end:])
   with self.assertRaisesRegex(ValueError,'Full watermark identity/clearance drift'):audit(p)
