"""Exact scoped review metadata and usage, never a user-wide cap.

No automatic provisioning/startup, new ordinary-session writes or user-cap
mutation. Admission/provisioning is a separately gated private operator.
"""
from collections.abc import Mapping
from datetime import datetime,timedelta,timezone
try:
    from . import native_audiobook_replacement as native
    from . import native_audiobook_profiles as profiles
    from . import native_audio_review_authority as authority
    from .domain.reading_pass import ReadingPassError
except ImportError:
    import native_audiobook_replacement as native
    import native_audiobook_profiles as profiles
    import native_audio_review_authority as authority
    from domain.reading_pass import ReadingPassError

PACKAGE='sha256-288896c0fa472ce2a13c76d022b717805c21a8620b0bdb0662055685bd365fa2'
GRANT_SCHEMA='earnalism.native_audio_review_grant.v1'
WORKFLOW_SCHEMA='earnalism.native_audio_review_workflow.v1'
GRANTS='native_audio_review_grants'
WORKFLOWS='native_audio_review_workflows'
SCOPE_KEY='native_audio_review_grant_id'
TERMINAL={'ended','expired','exhausted','transferred','revoked'}

def need(value,message):
    if not value:raise ReadingPassError('NATIVE_REVIEW_SCOPE_UNAVAILABLE',403,message)

def utc(v):
    need(isinstance(v,datetime),'Review clock invalid')
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)

def validate_workflow(w):
    need(w and w.get('schema')==WORKFLOW_SCHEMA and w.get('original_ceiling_seconds')==120
        and w.get('lineage_status') in {'ACTUAL_SETTLED_RECONCILED','CONSERVATIVE_PROVEN_BOUND'}
        and all(isinstance(w.get(k),str) and native.SHA.fullmatch(w[k]) for k in ('owner_scope_sha256','legacy_lineage_sha256'))
        and type(w.get('reserved_legacy_microseconds')) is int and 0<=w['reserved_legacy_microseconds']<=120000000
        and type(w.get('reserved_legacy_debit_seconds')) is int and 0<=w['reserved_legacy_debit_seconds']<=120
        and type(w.get('used_microseconds')) is int and w['reserved_legacy_microseconds']<=w['used_microseconds']<=120000000
        and type(w.get('used_credit_seconds')) is int and w['reserved_legacy_debit_seconds']<=w['used_credit_seconds']<=120
        and type(w.get('native_billable_microseconds')) is int and w['native_billable_microseconds']>=0
        and type(w.get('native_wallet_debit_seconds')) is int and w['native_wallet_debit_seconds']>=0
        and w['used_microseconds']==w['reserved_legacy_microseconds']+w['native_billable_microseconds']
        and w['used_credit_seconds']==w['reserved_legacy_debit_seconds']+w['native_wallet_debit_seconds']
        and type(w.get('revision')) is int and w['revision']>=0,'Original native120 lineage unavailable')
    return w

class ScopedReviewBudget(Mapping):
    """Server-only typed object. JSON/lease input cannot instantiate this path."""
    def __init__(self,db,grant,workflow,scope):
        self.db,self.grant,self.workflow,self.scope=db,dict(grant),dict(workflow),dict(scope)
    def _view(self):
        return dict(schema=GRANT_SCHEMA,test_id=self.scope['acceptance_test_id'],maximum_seconds=120,
            consumed_seconds=max((self.workflow['used_microseconds']+999999)//1000000,self.workflow['used_credit_seconds']),
            expires_at=self.grant['expires_at'])
    def __getitem__(self,key):return self._view()[key]
    def __iter__(self):return iter(self._view())
    def __len__(self):return len(self._view())
    def wallet_remaining(self):return 120-self.workflow['used_credit_seconds']
    def remaining(self,now,pending_debit=0):
        if utc(self.grant['expires_at'])<=utc(now):return 0
        return max(0,min((120000000-self.workflow['used_microseconds'])//1000000,self.wallet_remaining()-pending_debit))
    async def claim(self,session):
        need(session is not None and getattr(session,'in_transaction',False),'Native review transaction required')
        g=self.grant
        result=await self.db[GRANTS].update_one({'_id':g['_id'],'user_id':g['user_id'],'state':'OPEN','epoch':g['epoch']},
            {'$inc':{'epoch':1}},session=session)
        need(result.modified_count==1,'Native review grant changed; no uncapped fallback')
        self.grant['epoch']+=1
    async def interval(self,microseconds,session):
        need(type(microseconds) is int and microseconds>=0,'Native usage interval invalid')
        value=min(microseconds,120000000-self.workflow['used_microseconds'])
        if value:
            await self.claim(session)
            w=self.workflow
            result=await self.db[WORKFLOWS].update_one({'_id':w['_id'],'user_id':w['user_id'],'revision':w['revision'],
                'used_microseconds':w['used_microseconds'],'used_credit_seconds':w['used_credit_seconds']},
                {'$inc':{'used_microseconds':value,'native_billable_microseconds':value,'revision':1}},session=session)
            need(result.modified_count==1,'Native time counter changed')
            self.workflow['used_microseconds']+=value;self.workflow['native_billable_microseconds']+=value;self.workflow['revision']+=1
        return value
    async def debit(self,seconds,session):
        need(session is not None and getattr(session,'in_transaction',False),'Native review transaction required')
        need(type(seconds) is int and 0<=seconds<=self.wallet_remaining(),'Native credit ceiling exceeded')
        if seconds:
            w=self.workflow
            result=await self.db[WORKFLOWS].update_one({'_id':w['_id'],'user_id':w['user_id'],'revision':w['revision'],
                'used_microseconds':w['used_microseconds'],'used_credit_seconds':w['used_credit_seconds']},
                {'$inc':{'used_credit_seconds':seconds,'native_wallet_debit_seconds':seconds,'revision':1}},session=session)
            need(result.modified_count==1,'Native credit counter changed')
            self.workflow['used_credit_seconds']+=seconds;self.workflow['native_wallet_debit_seconds']+=seconds;self.workflow['revision']+=1

async def resolve(db,document,now,session=None,*,starting=False,current_access=False):
    scope=document.get('scope') or {};gid=scope.get(SCOPE_KEY)
    profile=profiles.profile_for_slug(document.get('content_id'))
    need(profile is not None,'Exact native review title required')
    try:package_version=profiles.actual_package(profile)
    except native.ReplacementError:need(False,'Real finalized native review binding unavailable')
    if not starting:need(document.get('acceptance_test_id')==profile.TEST_ID,'Native review lease binding missing')
    need(isinstance(gid,str) and gid and document.get('content_type')=='audio'
        and document.get('content_id')==profile.SLUG,'Exact native review lease required')
    user=await db.users.find_one({'id':document['user_id'],'role':'user'},{'reader_acceptance_budget':1,'status':1},session=session)
    need(user and user.get('status')=='active' and 'reader_acceptance_budget' not in user,'Conflicting retained user cap or unavailable member')
    g=await db[GRANTS].find_one({'_id':gid,'user_id':document['user_id']},session=session)
    need(g and g.get('schema')==GRANT_SCHEMA and g.get('state')=='OPEN'
        and g.get('slug')==profile.SLUG and g.get('descriptor_sha256')==profile.DESCRIPTOR
        and g.get('package_version')==package_version and g.get('country')=='IN'
        and type(g.get('epoch')) is int and g['epoch']>=0,'Native scoped grant unavailable')
    w=await db[WORKFLOWS].find_one({'_id':g['workflow_id'],'user_id':document['user_id']},session=session)
    validate_workflow(w)
    need(utc(g['created_at'])<=utc(now) and timedelta(0)<utc(g['expires_at'])-utc(g['created_at'])<=timedelta(minutes=15),'Native grant clock invalid')
    need(g.get('owner_scope_sha256')==w['owner_scope_sha256'] and g.get('legacy_lineage_sha256')==w['legacy_lineage_sha256'],'Native review lineage binding changed')
    if profile.SLUG=='the-open-window':
        need(g.get('owner_scope_sha256')==authority.ORIGINAL_OWNER_RECEIPT_SHA256
             and g.get('continuation_sha256')==authority.BOTH_TITLES_RECEIPT_SHA256,
             'Open review must preserve original120 and exact continuation')
    expected={SCOPE_KEY:gid,'native_audio_review_workflow_id':w['_id'],
        'native_replacement_authorization_id':gid,'acceptance_test_id':profile.TEST_ID,
        'manifest_version':package_version,'segmentation_version':profile.DESCRIPTOR,
        'package_version':package_version,'release_descriptor_sha256':profile.DESCRIPTOR,'release_country':'IN'}
    need(all(scope.get(k)==v for k,v in expected.items()),'Server native review scope changed')
    result=ScopedReviewBudget(db,g,w,expected)
    if current_access or starting:need(result.remaining(now)>0,'Native review expired or exhausted')
    return result

async def member_scope(db,book,user_id,*,country,now,session_scope=None):
    """Book-specific access metadata; ordinary users/books get no added writes."""
    profile=profiles.review_profile(book)
    if profile is None:return None
    try:package_version=profiles.actual_package(profile)
    except native.ReplacementError:need(False,'Real finalized native review binding unavailable')
    gid=(session_scope or {}).get(SCOPE_KEY)
    query={'user_id':user_id,'slug':profile.SLUG,'descriptor_sha256':profile.DESCRIPTOR,'package_version':package_version}
    if gid:query['_id']=gid
    else:query['state']='OPEN'
    rows=await db[GRANTS].find(query).max_time_ms(5000).limit(2).to_list(2)
    if not rows:
        need(not gid,'Native scoped lease grant removed');return None
    need(len(rows)==1,'Ambiguous native review grants')
    g=rows[0];package,_=profile.rights_for_review_phase(book,country=country,now=now)
    need(package['package_version']==package_version,'Actual finalized native package changed')
    scope={SCOPE_KEY:g['_id'],'native_audio_review_workflow_id':g['workflow_id'],
        'native_replacement_authorization_id':g['_id'],'acceptance_test_id':profile.TEST_ID,
        'manifest_version':package_version,'segmentation_version':profile.DESCRIPTOR,
        'package_version':package_version,'release_descriptor_sha256':profile.DESCRIPTOR,'release_country':'IN'}
    if session_scope is not None:need(all(session_scope.get(k)==v for k,v in scope.items()),'Native review session changed')
    await resolve(db,{'user_id':user_id,'content_type':'audio','content_id':profile.SLUG,'scope':scope},now,starting=True,current_access=True)
    return scope
