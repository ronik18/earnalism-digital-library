import pathlib,sys,tempfile,shutil,json,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from rights_audit import audit
from score import compose
ROOT=pathlib.Path(__file__).resolve().parents[1]
class RightsAuditTests(unittest.TestCase):
 def fixture(self,p):
  for sub in ('rights','assets/standard-intro/v1'):shutil.copytree(ROOT/sub,p/sub)
  (p/'config').mkdir();shutil.copy2(ROOT/'score.py',p/'score.py');folder=p/'run';folder.mkdir();compose(folder/'score.wav',.2)
  return folder
 def test_missing_owner_attestation_never_claims_complete_or_publication_approval(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=audit(self.fixture(p),p);self.assertEqual(r['status'],'OWNER_EVIDENCE_PENDING');self.assertFalse(r['publication_authorized'])
 def test_tampered_license_evidence_stops_audit(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);f=self.fixture(p);(p/'rights/qwen-model-card.md').write_text('changed')
   with self.assertRaisesRegex(ValueError,'evidence changed'):audit(f,p)

 def test_unknown_model_is_not_covered_by_qwen_license(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);f=self.fixture(p);(f/'raw').mkdir();(f/'raw/scene.wav.json').write_text(json.dumps({'provenance':{'model_id':'different-model'}}))
   with self.assertRaisesRegex(ValueError,'model not covered'):audit(f,p)
 def test_owner_approval_does_not_transfer_to_a_different_logo(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);f=self.fixture(p);(p/'config/rights-owner.json').write_text(json.dumps({'brand_commercial_rights':True,'brand_logo_sha256':'different-logo'}))
   with self.assertRaisesRegex(ValueError,'does not cover this logo'):audit(f,p)
