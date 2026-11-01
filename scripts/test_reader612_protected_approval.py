"""Synthetic GitHub review fixtures; these never create actual approval."""
import base64
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock
from scripts import reader612_protected_approval as m


class Tests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,1,12,tzinfo=timezone.utc);self.sha='a'*40;self.binding='b'*64
        self.action='release_guarded_bootstrap';self.operator='FIXTURE_OPERATOR';self.calls=[]
        comment='APPROVE_BACKEND612 '+self.action+' '+self.binding+' '+self.sha+' '+self.operator
        self.rows=[{'id':123,'repository':{'full_name':m.REPO},'head_repository':{'full_name':m.REPO},
            'head_branch':'main','head_sha':self.sha,'event':'workflow_dispatch','run_attempt':1,
            'path':m.WORKFLOW,'status':'completed','conclusion':'success','created_at':self.now.isoformat(),
            'head_commit':{'id':self.sha,'tree_id':'d'*40}},
            {'encoding':'base64','content':base64.b64encode((Path(m.__file__).resolve().parents[1]/m.WORKFLOW).read_bytes()).decode()},
            {'id':m.ENVIRONMENT_ID,'name':m.ENVIRONMENT,'protection_rules':[{'type':'required_reviewers','reviewers':[{'type':'User','reviewer':{'id':m.OWNER_ID}}]}]},
            {'total_count':1,'jobs':[{'name':m.JOB,'head_sha':self.sha,'conclusion':'success'}]},
            [{'state':'approved','comment':comment,'environments':[{'id':m.ENVIRONMENT_ID,'name':m.ENVIRONMENT}],'user':{'id':m.OWNER_ID}}],
            {'object':{'sha':self.sha}}]

    def resolver(self):
        queue=list(self.rows)
        def run(argv,**kw):
            self.calls.append(argv);return subprocess.CompletedProcess(argv,0,json.dumps(queue.pop(0)),'')
        git=lambda *a:self.sha if a==('rev-parse','HEAD') else 'd'*40 if a==('rev-parse','HEAD^{tree}') else ''
        return m.GitHubProtectedApprovalResolver(123,self.sha,self.operator,run=run,git=git,clock=lambda:self.now)

    def test_exact_owner_backend_review_resolves_with_no_write(self):
        resolver=self.resolver();proof=resolver.inspect(self.action,self.binding)
        self.assertEqual(proof['native_turn_id'],'github-protected-review:123:1')
        self.assertEqual(proof['issued_at'],self.now.isoformat())
        self.assertEqual(len(self.calls),6)
        self.assertTrue(all(x[:4]==['gh','api','--method','GET'] for x in self.calls))
        self.assertFalse(any('dispatches' in x[-1] or 'pending_deployments' in x[-1] for x in self.calls))
        self.assertEqual(self.resolver()(proof['receipt_sha256'],self.action,self.binding),proof)

    def test_other_workflow_head_repository_event_or_attempt_denied(self):
        for key,value in [('path','.github/workflows/india-protected-observation.yml'),('head_sha','c'*40),
            ('head_branch','feature'),('event','pull_request'),('run_attempt',2),('conclusion','failure'),
            ('repository',{'full_name':'other/repository'}),('head_repository',{'full_name':'other/repository'})]:
            old=self.rows[0][key];self.rows[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.resolver().inspect(self.action,self.binding)
            self.rows[0][key]=old

    def test_run_creation_bounds_age_not_observer_fetch_time(self):
        for delta in (timedelta(minutes=-1),timedelta(minutes=15),timedelta(days=1)):
            self.rows[0]['created_at']=(self.now-delta).isoformat()
            with self.subTest(delta=delta),self.assertRaises(ValueError):self.resolver().inspect(self.action,self.binding)

    def test_wrong_reviewer_environment_comment_rejection_and_ambiguity_denied(self):
        original=self.rows[4]
        for change in ({'user':{'id':1}},{'state':'rejected'},{'comment':'Approve frontend'},
            {'environments':[{'id':1,'name':m.ENVIRONMENT}]},{'comment':original[0]['comment'].replace(self.binding,'c'*64)}):
            self.rows[4]=[{**original[0],**change}]
            with self.subTest(change=change),self.assertRaises(ValueError):self.resolver().inspect(self.action,self.binding)
        self.rows[4]=original*2
        with self.assertRaises(ValueError):self.resolver().inspect(self.action,self.binding)

    def test_removed_protection_changed_source_job_or_reference_denied(self):
        for i,field,value in [(1,'content',base64.b64encode(b'old workflow').decode()),(2,'protection_rules',[]),(3,'jobs',[])]:
            old=self.rows[i][field];self.rows[i][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.resolver().inspect(self.action,self.binding)
            self.rows[i][field]=old
        with self.assertRaises(ValueError):self.resolver()('0'*64,self.action,self.binding)

    def test_local_approved_dictionary_or_arbitrary_inputs_cannot_authorize(self):
        for action,binding in [('frontend_promotion',self.binding),(self.action,'approved=true')]:
            with self.assertRaises(ValueError):self.resolver().inspect(action,binding)
        with self.assertRaises(ValueError):m.GitHubProtectedApprovalResolver('../api',self.sha,self.operator)

    def test_changed_local_controller_tree_dirty_checkout_or_remote_main_denied(self):
        for ref,value in [(('rev-parse','HEAD'),'0'*40),(('rev-parse','HEAD^{tree}'),'0'*40),(('status','--porcelain','--untracked-files=all'),'M scripts/anything')]:
            resolver=self.resolver();old=resolver.git
            resolver.git=lambda *a: value if a==ref else old(*a)
            with self.subTest(ref=ref),self.assertRaises(ValueError):resolver.inspect(self.action,self.binding)
        self.rows[5]={'object':{'sha':'e'*40}}
        with self.assertRaisesRegex(ValueError,'Main advanced'):self.resolver().inspect(self.action,self.binding)


if __name__=='__main__':unittest.main()
