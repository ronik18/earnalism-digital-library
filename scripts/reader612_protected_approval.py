"""Resolve actual GitHub protected reviews. GET only; never approve or dispatch.

Trust source: existing authenticated gh API, exact main workflow source, required
owner reviewer, and an explicit backend action/binding/controller review comment.
Run creation bounds age conservatively; GitHub review history has no timestamp.
"""
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from scripts.india_release_provider_adapter import digest

REPO='ronik18/earnalism-digital-library'
REPOSITORY_ID=1232345982
ENVIRONMENT='reader-frontend-production'
ENVIRONMENT_ID=23963594893
OWNER_ID=19212527
WORKFLOW='.github/workflows/reader612-protected-approval.yml'
JOB='Record Backend612 approval only — NO EXECUTION'
ACTIONS={'release_guarded_bootstrap','restore_original_native_after_reader612_qualification'}
ROOT=Path(__file__).resolve().parents[1]


def local_git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True,timeout=15,
        env={**os.environ,'GIT_NO_LAZY_FETCH':'1'}).strip()


class GitHubProtectedApprovalResolver:
    def __init__(self, run_id, controller_sha, rollback_operator, *, run=subprocess.run, git=local_git,
                 clock=lambda:datetime.now(timezone.utc)):
        if (type(run_id) is not int or run_id<=0 or not re.fullmatch('[0-9a-f]{40}',controller_sha)
                or not re.fullmatch('[A-Za-z0-9_.-]{1,80}',rollback_operator)):
            raise ValueError('Exact run/controller/named operator required')
        self.run_id,self.controller_sha,self.operator=run_id,controller_sha,rollback_operator
        self.run,self.clock,self.git=run,clock,git

    def _get(self, suffix):
        # All suffixes originate in fixed code; no arbitrary URL or shell.
        result=self.run(['gh','api','--method','GET','repos/'+REPO+'/'+suffix],
            capture_output=True,text=True,timeout=30,check=False)
        if result.returncode or len(result.stdout)>1024*1024:
            raise ValueError('Authenticated approval read unavailable; no retry')
        return json.loads(result.stdout)

    def inspect(self, action, binding_sha256):
        if action not in ACTIONS or not re.fullmatch('[0-9a-f]{64}',binding_sha256):
            raise ValueError('Exact backend action/binding required')
        if self.git('rev-parse','HEAD')!=self.controller_sha or self.git('status','--porcelain','--untracked-files=all'):
            raise ValueError('Exact clean reviewed controller checkout required')
        run=self._get('actions/runs/'+str(self.run_id))
        title='APPROVAL ONLY Backend612 '+action+' binding='+binding_sha256+' controller='+self.controller_sha+' operator='+self.operator+' — NO EXECUTION'
        if (run.get('id')!=self.run_id or run.get('repository',{}).get('full_name')!=REPO
                or run.get('repository',{}).get('id')!=REPOSITORY_ID
                or run.get('head_repository',{}).get('id')!=REPOSITORY_ID
                or run.get('display_title')!=title
                or run.get('head_repository',{}).get('full_name')!=REPO
                or run.get('head_branch')!='main' or run.get('head_sha')!=self.controller_sha
                or run.get('event')!='workflow_dispatch' or run.get('run_attempt')!=1
                or run.get('path') not in {WORKFLOW,WORKFLOW+'@main'}
                or run.get('status')!='completed' or run.get('conclusion')!='success'):
            raise ValueError('Exact successful first-attempt backend approval workflow required')
        if (run.get('head_commit',{}).get('id')!=self.controller_sha
                or self.git('rev-parse','HEAD^{tree}')!=run.get('head_commit',{}).get('tree_id')):
            raise ValueError('Actual controller tree differs')
        created=datetime.fromisoformat(run['created_at'].replace('Z','+00:00'));now=self.clock()
        if created.tzinfo is None or not timedelta(0)<=now-created<timedelta(minutes=15):
            raise ValueError('Approval run age exceeds conservative15minute bound')
        source=self._get('contents/'+WORKFLOW+'?ref='+self.controller_sha)
        expected=(Path(__file__).resolve().parents[1]/WORKFLOW).read_bytes()
        if source.get('encoding')!='base64' or base64.b64decode(source['content'])!=expected:
            raise ValueError('Reviewed backend approval workflow source mismatch')
        env=self._get('environments/'+ENVIRONMENT)
        reviewers=[x.get('reviewer',{}).get('id') for r in env.get('protection_rules',[])
            if r.get('type')=='required_reviewers' for x in r.get('reviewers',[]) if x.get('type')=='User']
        if env.get('id')!=ENVIRONMENT_ID or env.get('name')!=ENVIRONMENT or OWNER_ID not in reviewers:
            raise ValueError('Existing owner-required protected environment changed')
        jobs=self._get('actions/runs/'+str(self.run_id)+'/attempts/1/jobs?per_page=100')
        if jobs.get('total_count')!=1 or len(jobs.get('jobs',[]))!=1:
            raise ValueError('Single protected approval-only job required')
        job=jobs['jobs'][0]
        if job.get('name')!=JOB or job.get('head_sha')!=self.controller_sha or job.get('conclusion')!='success':
            raise ValueError('Actual protected approval-only job did not complete')
        reviews=self._get('actions/runs/'+str(self.run_id)+'/approvals')
        scoped=[r for r in reviews if any(e.get('id')==ENVIRONMENT_ID and e.get('name')==ENVIRONMENT for e in r.get('environments',[]))]
        comment='APPROVE_BACKEND612 '+action+' '+binding_sha256+' '+self.controller_sha+' '+self.operator
        if (len(scoped)!=1 or scoped[0].get('state')!='approved'
                or scoped[0].get('user',{}).get('id')!=OWNER_ID or scoped[0].get('comment')!=comment):
            raise ValueError('Actual owner backend-scoped exact review missing/rejected/ambiguous')
        current=self._get('git/ref/heads/main')
        if current.get('object',{}).get('sha')!=self.controller_sha:
            raise ValueError('Main advanced; rebind exact controller before execution')
        receipt={'repository':REPO,'run_id':self.run_id,'attempt':1,'controller_sha':self.controller_sha,
            'environment_id':ENVIRONMENT_ID,'reviewer_id':OWNER_ID,'review_comment':comment,
            'action':action,'binding_sha256':binding_sha256,'created_at':run['created_at']}
        reference=digest(receipt)
        return {'issuer':'AUTHENTIC_NATIVE_OWNER_PROTECTED_GATE','receipt_sha256':reference,
            'binding_sha256':binding_sha256,'action':action,
            'native_turn_id':'github-protected-review:'+str(self.run_id)+':1',
            'scope':'BACKEND612_QUALIFICATION_PAUSE_AND_EXACT_BASELINE_RESTORE',
            'rollback_operator':self.operator,'issued_at':created.isoformat(),
            'expires_at':(created+timedelta(minutes=15)).isoformat(),
            'age_scope':'conservative workflow creation bound, not invented review timestamp',
            'trust_source':'authenticated GitHub workflow review history; not dispatcher/PR/frontend approval'}

    def __call__(self, reference, action, binding_sha256):
        proof=self.inspect(action,binding_sha256)
        if proof['receipt_sha256']!=reference:raise ValueError('Authentic review reference mismatch')
        return proof
