import copy
import unittest
from scripts import verify_reader_alias_bindings as g

class ReadOnlyAccessTests(unittest.TestCase):
    def setUp(self):
        self.env={'GITHUB_REPOSITORY':'ronik18/earnalism-digital-library','GITHUB_REF':'refs/heads/main',
                  'GITHUB_EVENT_NAME':'workflow_dispatch','CONFIRM_PRODUCTION':'READ_ONLY_VERCEL_ACCESS',
                  'VERCEL_PROJECT_ID':g.PROJECT,'VERCEL_ORG_ID':g.TEAM}
        self.project={'id':g.PROJECT,'accountId':g.TEAM,'targets':{'production':{'id':g.RETAINED_READY}}}
        self.target={'id':g.RETAINED_READY,'projectId':g.PROJECT,'ownerId':g.TEAM,'target':'production',
                     'readyState':'READY','meta':{'githubCommitSha':'229df7f8b2cfb49a7f46215be3979608c39f7c33'}}
        self.calls=[]
    def request(self,path,method,timeout,env):
        self.assertEqual(method,'GET');self.assertLessEqual(timeout,5);self.calls.append(path)
        if path=='/v9/projects/'+g.PROJECT:return self.project
        if path=='/v13/deployments/'+g.RETAINED_READY:return self.target
        host=path.removeprefix('/v4/aliases/')
        self.assertIn(host,g.HOSTS)
        return {'alias':host,'projectId':g.PROJECT,'deploymentId':g.RETAINED_READY}
    def test_exact_six_gets_without_mutation(self):
        result=g.readonly_access_check(self.env,self.request)
        self.assertEqual(len(self.calls),6);self.assertEqual(result['mutations'],0)
        self.assertEqual(result['backend_compatibility'],'SEPARATE_GATE_NOT_RUN')
    def test_context_mismatch_makes_no_request(self):
        for key in self.env:
            with self.subTest(key=key),self.assertRaises(ValueError):
                g.readonly_access_check({**self.env,key:'wrong'},self.request)
        self.assertEqual(self.calls,[])
    def test_project_source_and_alias_drift_stop(self):
        good=copy.deepcopy(self.target)
        for key in ('id','projectId','ownerId','target','readyState'):
            self.target=copy.deepcopy(good);self.target[key]='wrong'
            with self.subTest(key=key),self.assertRaises(ValueError):g.readonly_access_check(self.env,self.request)
        self.target=copy.deepcopy(good);self.target['meta']['githubCommitSha']='a'*40
        with self.assertRaises(ValueError):g.readonly_access_check(self.env,self.request)
        self.target=good
        def wrong_alias(path,*args):
            result=self.request(path,*args)
            if path.startswith('/v4/aliases/'):result['deploymentId']='foreign'
            return result
        with self.assertRaises(ValueError):g.readonly_access_check(self.env,wrong_alias)
    def test_provider_denial_not_retried(self):
        calls=[]
        def denied(*args):calls.append(args);raise ValueError('denied')
        with self.assertRaises(ValueError):g.readonly_access_check(self.env,denied)
        self.assertEqual(len(calls),1)
if __name__=='__main__':unittest.main()
