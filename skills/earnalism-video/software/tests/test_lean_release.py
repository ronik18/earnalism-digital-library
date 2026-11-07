"""Lean gates keep primary defects and approval real; research is optional."""
import copy,json,pathlib,subprocess,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio,audience_plan as a
from learning_acceptance import pending,primary_findings,validate_release_findings
from test_viewer_experience import generic_fixture
class LeanReleaseTests(unittest.TestCase):
 def test_missing_pending_and_unrun_studies_remain_optional_not_pass(self):
  self.assertEqual(validate_release_findings(None,'current')['study'],'NOT_RUN_OPTIONAL')
  r=pending();r['delivery_manifest_sha256']='old'
  self.assertEqual(validate_release_findings(r,'current')['open_primary_findings'],[])
  self.assertNotEqual(validate_release_findings(r,'current')['study'],'PASS')
 def test_known_failure_survives_stale_manifest_and_pending_reset(self):
  r=pending();r['delivery_manifest_sha256']='old';r['learning']['unresolved_confusions']=['Critical mechanism is unclear'];r['acceptance']['cases']['landscape_complete']['status']='FAIL'
  fresh=pending(previous=r);fresh['delivery_manifest_sha256']='new'
  self.assertEqual(len(primary_findings(fresh)),2)
  with self.assertRaisesRegex(ValueError,'Known primary'):validate_release_findings(fresh,'new')
 def test_aggregate_failed_verdict_cannot_disappear_without_a_listed_detail(self):
  r=pending();r['learning']['decision']='FAIL';r['acceptance']['decision']='FAILED'
  fresh=pending(previous=r);self.assertEqual(len(primary_findings(fresh)),2)
  with self.assertRaisesRegex(ValueError,'Known primary'):validate_release_findings(fresh,'new')
 def test_one_current_final_review_can_resolve_named_findings_with_real_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);r=pending();r['learning']['unresolved_confusions']=['Unreadable explanation'];finding=primary_findings(r)[0];(p/'fix.txt').write_text('Test evidence: actual fix, no human approval inferred');ref={'path':'fix.txt','sha256':studio.sha(p/'fix.txt')}
   review={'reviewer':'test fixture only','delivery_manifest_sha256':'current','audiovisual':True,'resolved_findings':[{'id':finding['id'],'resolution':'Verified explanation staging and reading time','evidence':[ref]}]}
   self.assertEqual(validate_release_findings(r,'current',review,p)['open_primary_findings'],[])
   with self.assertRaises(ValueError):validate_release_findings(r,'different',review,p)
   (p/'fix.txt').write_text('tampered')
   with self.assertRaises(ValueError):validate_release_findings(r,'current',review,p)
 def test_final_human_review_is_still_required_with_pending_optional_research(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'episode.json').write_text(json.dumps({'private_test':False,'requires_learning_acceptance':True}));(p/'review.json').write_text('{}');(p/'acceptance-review.json').write_text(json.dumps(pending()));(p/'delivery-manifest.json').write_text(json.dumps({'episode.json':studio.sha(p/'episode.json')}))
   with self.assertRaisesRegex(ValueError,'human review'):studio.release_check(p)
 def test_explicit_independent_study_mode_remains_strict(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'episode.json').write_text(json.dumps({'private_test':False,'requires_independent_learning_study':True}));(p/'review.json').write_text('{}');(p/'delivery-manifest.json').write_text(json.dumps({'episode.json':studio.sha(p/'episode.json')}))
   with self.assertRaisesRegex(ValueError,'Explicitly required'):studio.release_check(p)
   (p/'acceptance-review.json').write_text(json.dumps(pending()))
   with self.assertRaisesRegex(ValueError,'topic-bound v2'):studio.release_check(p)
 def test_growth_administration_is_not_a_paid_generation_prerequisite(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);ep=generic_fixture('Planning test');plan=ep['audience_plan'];plan['audience'].pop('discovery_context');plan['audience'].pop('why_choose_this_explanation');plan.pop('series');plan.pop('study')
   for f in plan['formats'].values():f['titles']=f['titles'][:1];f.pop('cover_brief')
   (p/'episode.json').write_text(json.dumps(ep));a.initialize(p);self.assertEqual(a.validate_generation(p)['status'],'GENERATION_BRIEF_COMPLETE')
   plan=studio.load(p/a.PLAN);plan['story']['scenes'].pop();(p/a.PLAN).write_text(json.dumps(plan))
   with self.assertRaisesRegex(ValueError,'Every actual scene'):a.validate_generation(p)
 def test_media_validation_performs_one_full_audiovisual_decode(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'fixture.mp4';subprocess.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','color=c=navy:s=160x90:r=30:d=1','-f','lavfi','-i','sine=frequency=440:duration=1','-af','volume=0.1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(p)],check=True)
   real=subprocess.run
   with patch('studio.subprocess.run',wraps=real) as calls:r=studio.verify_media(p)
   decodes=[c.args[0] for c in calls.call_args_list if c.args[0][0]=='ffmpeg']
   self.assertEqual(len(decodes),1);self.assertIn('0:v:0',decodes[0]);self.assertIn('0:a:0',decodes[0]);self.assertIn('-xerror',decodes[0]);self.assertEqual(r['decode'],'PASS')
if __name__=='__main__':unittest.main()
