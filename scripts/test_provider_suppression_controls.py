import sys,importlib.util,json,tempfile,unittest,subprocess
from pathlib import Path
from scripts import india_release_observer as m
class Tests(unittest.TestCase):
 def collect(self,provider,repo):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'frontend').mkdir()
   if repo is not None:(p/'frontend/vercel.json').write_text(json.dumps(repo))
   project={'id':m.PROJECT,'accountId':m.TEAM,**provider,'env':[{'value':'SECRET_MUST_NOT_SURVIVE'}]};responses=[project,[]]
   def run(argv,**kw):
    if argv[1:]==['--version']:return subprocess.CompletedProcess(argv,0,m.CLI_VERSIONS[argv[0]],'')
    self.assertNotIn('--token',argv);self.assertNotIn('variables',argv);return subprocess.CompletedProcess(argv,0,json.dumps(responses.pop(0)),'')
   result=m.NativeMetadataObserver(p,run=run).collect();self.assertNotIn('SECRET_MUST_NOT_SURVIVE',json.dumps(result));return result
 def test_actual_shape_and_repo_false_required(self):
  r=self.collect({'gitProviderOptions':{'createDeployments':'disabled'}},{'git':{'deploymentEnabled':False}});self.assertTrue(r['frontend_auto_deploy_disabled']);self.assertTrue(r['frontend_provider_auto_deploy_disabled']);self.assertTrue(r['frontend_repository_auto_deploy_disabled'])
 def test_missing_enabled_malformed_provider_denies(self):
  for provider in [{},{'link':{'deploymentEnabled':False}},{'gitProviderOptions':{'createDeployments':'enabled'}},{'gitProviderOptions':{'createDeployments':False}},{'gitProviderOptions':[]},{'gitProviderOptions':{'createDeployments':{'main':'disabled'}}}]:
   with self.subTest(provider=provider):self.assertFalse(self.collect(provider,{'git':{'deploymentEnabled':False}})['frontend_auto_deploy_disabled'])
 def test_missing_enabled_malformed_repo_denies(self):
  for repo in [None,{}, {'git':{'deploymentEnabled':True}}, {'git':{'deploymentEnabled':'false'}}, {'git':{'deploymentEnabled':{'main':False}}}, {'git':[]},[]]:
   with self.subTest(repo=repo):self.assertFalse(self.collect({'gitProviderOptions':{'createDeployments':'disabled'}},repo)['frontend_auto_deploy_disabled'])
 def test_no_historical_prohibition_reinterpreted(self):
  src=Path(m.__file__).read_text();self.assertIn('CURRENT_OWNER_PROHIBITS_EXECUTION',src);self.assertIn('class ProtectedReleasePreflight',src)
if __name__=='__main__':unittest.main()
