"""Durable fail-closed operation budgets. No provider access or credentials."""
from contextvars import ContextVar
import fcntl,hashlib,json,os,stat
from pathlib import Path

ACTIVE=ContextVar('audiobook_upload_budget',default=None)
class BudgetError(RuntimeError):pass
class Budget:
    def __init__(self,path,identity,requests=2000,download_bytes=31713460,upload_bytes=15856730,versions=176,metadata_bytes=16777216):
        self.path=Path(path);self.identity=identity
        self.limits={'requests':requests,'download_bytes':download_bytes,'upload_bytes':upload_bytes,'versions':versions,'metadata_bytes':metadata_bytes}
        if any(type(v) is not int or v<0 for v in self.limits.values()):raise BudgetError('INVALID_BUDGET')
        self.fd=os.open(self.path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:
            st=os.fstat(self.fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077:raise BudgetError('LEDGER_NOT_PRIVATE')
            fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            raw=os.read(self.fd,1048577)
            if len(raw)>1048576:raise BudgetError('LEDGER_TOO_LARGE')
            self.state=json.loads(raw) if raw else {'identity':identity,'limits':self.limits,'used':dict.fromkeys(self.limits,0),'attempted_objects':[]}
            if self.state['identity']!=identity or self.state['limits']!=self.limits:raise BudgetError('LEDGER_IDENTITY_MISMATCH')
            if any(type(self.state['used'][k]) is not int or not 0<=self.state['used'][k]<=v for k,v in self.limits.items()):raise BudgetError('INVALID_LEDGER')
            attempted=self.state['attempted_objects']
            if (not isinstance(attempted,list) or len(attempted)!=len(set(attempted))
                    or any(not isinstance(x,str) or len(x)!=64 or any(c not in '0123456789abcdef' for c in x) for x in attempted)
                    or len(attempted)!=self.state['used']['versions']):raise BudgetError('INVALID_MUTATION_LEDGER')
            self._save()
            directory_fd=os.open(self.path.parent,os.O_RDONLY)
            try:os.fsync(directory_fd)
            finally:os.close(directory_fd)
        except Exception:os.close(self.fd);raise
    def _save(self):
        raw=json.dumps(self.state,sort_keys=True).encode()
        os.lseek(self.fd,0,os.SEEK_SET)
        view=memoryview(raw)
        while view:
            written=os.write(self.fd,view)
            if written<=0:raise BudgetError('LEDGER_WRITE_FAILED')
            view=view[written:]
        os.ftruncate(self.fd,len(raw));os.fsync(self.fd)
    def reserve(self,object_identity=None,**amounts):
        if any(k not in self.limits or type(v) is not int or v<0 for k,v in amounts.items()):raise BudgetError('INVALID_RESERVATION')
        key=hashlib.sha256(object_identity.encode()).hexdigest() if object_identity is not None else None
        if key in self.state['attempted_objects']:raise BudgetError('PRIOR_OBJECT_MUTATION_DO_NOT_RETRY')
        if any(self.state['used'][k]+v>self.limits[k] for k,v in amounts.items()):raise BudgetError('OPERATION_BUDGET_EXCEEDED')
        for k,v in amounts.items():self.state['used'][k]+=v
        if key:self.state['attempted_objects'].append(key)
        self._save() # Reserve durably BEFORE network/mutation; never refund uncertainty.
    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None
    def __enter__(self):self.token=ACTIVE.set(self);return self
    def __exit__(self,*args):ACTIVE.reset(self.token);self.close()

class LimitedBody:
    def __init__(self,body,size):self.body=body;self.remaining=size
    def read(self,size=-1):
        if self.remaining==0:return b''
        n=self.remaining if size is None or size<0 else min(size,self.remaining)
        data=self.body.read(n)
        if len(data)>n:raise BudgetError('BODY_EXCEEDS_DECLARED_LENGTH')
        self.remaining-=len(data);return data
    def close(self):self.body.close()

def before_call(operation,kwargs):
    budget=ACTIVE.get()
    if budget is None:
        if operation=='put_object':raise BudgetError('UPLOAD_BUDGET_REQUIRED')
        return
    if operation=='put_object':
        budget.reserve(requests=1,upload_bytes=kwargs['ContentLength'],versions=1,object_identity=kwargs['Bucket']+'\0'+kwargs['Key'])
    elif operation in {'create_multipart_upload','upload_part','complete_multipart_upload','delete_object','delete_objects'}:
        raise BudgetError('UNAPPROVED_MUTATION')
    elif operation in {'head_object','get_object','head_bucket','get_bucket_versioning','get_object_lock_configuration','get_public_access_block','get_bucket_policy_status','get_bucket_acl','list_object_versions','native_metadata_request'}:
        budget.reserve(requests=1)
    else:raise BudgetError('UNAPPROVED_OPERATION')

def after_call(operation,response):
    budget=ACTIVE.get()
    if budget is not None and operation=='get_object':
        try:
            length=response['ContentLength']
            budget.reserve(download_bytes=length)
            response['Body']=LimitedBody(response['Body'],length)
        except Exception:
            response['Body'].close();raise
    return response
