import json,pathlib,sys,unittest,tempfile,shutil
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from expectations import audit,ROOT
class ExpectationTests(unittest.TestCase):
 def fixture(self,d):
  p=pathlib.Path(d)
  for name in ['config/defaults.json','config/editorial-contract.json','src/branding.mjs','src/BrandWatermark.tsx','src/social-safe-area.mjs','src/opening-visibility.mjs','src/readability.mjs','assets/standard-intro/v1/production-lockup.png','public/brand-sting/production-lockup.png','watch-template.html']:
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

 def test_new_top_right_blur_contract_and_real_component_application_are_enforced(self):
  for mutation in ('radius','anchor','component'):
   with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as d:
    p=self.fixture(d)
    if mutation=='component':
     f=p/'src/BrandWatermark.tsx';f.write_text(f.read_text().replace('filter:q.blurPx>0?','filter:false?'))
     reason='blur is not applied'
    else:
     f=p/'config/editorial-contract.json';r=json.loads(f.read_text());r['brand']['watermark_style']['blur_px_at_1080p' if mutation=='radius' else 'anchor']=1.5 if mutation=='radius' else 'raw-frame-edge';f.write_text(json.dumps(r));reason='styling/anchor drift'
    with self.assertRaisesRegex(ValueError,reason):audit(p)

 def test_future_music_and_end_keys_reject_policy_or_contract_drift(self):
  for target,field,value in [('policy','coverage','callback-excluded'),('contract','intentional_silent_body_sections',True),
    ('policy','commercially_cleared_open_license',False),('contract','efficacy_claims',True),
    ('policy','narration_waveform_unchanged',False),('contract','qualified_by_configuration_alone',True)]:
   with self.subTest(target=target,field=field),tempfile.TemporaryDirectory() as d:
    p=self.fixture(d);f=p/('config/defaults.json' if target=='policy' else 'config/editorial-contract.json')
    r=json.loads(f.read_text());r['music']['future_profile'][field]=value;f.write_text(json.dumps(r))
    with self.assertRaisesRegex(ValueError,'future music profile drift'):audit(p)
  for target in ('policy','contract'):
   with self.subTest(ending=target),tempfile.TemporaryDirectory() as d:
    p=self.fixture(d);f=p/('config/defaults.json' if target=='policy' else 'config/editorial-contract.json');r=json.loads(f.read_text())
    ending=r['intro'] if target=='policy' else r['brand']['outro'];ending['body_music_bleed']=True;f.write_text(json.dumps(r))
    with self.assertRaisesRegex(ValueError,'END treatment drift|Brand ending drift'):audit(p)

 def test_matching_weakened_profiles_cannot_relabel_historical_treatment(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.fixture(d)
   for name in ('config/defaults.json','config/editorial-contract.json'):
    f=p/name;r=json.loads(f.read_text());r['music']['future_profile']['intentional_silent_body_sections']=True
    r['music']['legacy_palette_scope']='future-qualified';f.write_text(json.dumps(r))
   with self.assertRaisesRegex(ValueError,'future music profile drift|historical palette scope drift'):audit(p)
