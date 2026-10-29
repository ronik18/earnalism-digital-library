from scripts import india_release_provider_adapter as a
import json,os,tempfile,unittest,stat
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
class DurableTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.r=Path(self.t.name);self.calls=[];self.now=datetime.now(timezone.utc);self.b={'source_sha':'a'*40,'source_root':str(self.r)}
 def approval(self,b=None):
  return {'schema':'earnalism-india-protected-operation.v1','action':'stage_frontend','binding_sha256':a.digest(b or self.b),'project':a.PROJECT,'team':a.TEAM,'railway_project':a.RAILWAY_PROJECT,'service':a.SERVICE,'environment':a.ENVIRONMENT,'territories':['IN'],'auto_deploy':False,'approved':True,'provider_identity_sha256':'b'*64,'config_sha256':'c'*64,'guarded_rollback_sha256':'d'*64,'rollback_operator':'SYNTHETIC_INERT_OPERATOR','approved_at':(self.now-timedelta(seconds=10)).isoformat(),'expires_at':(self.now+timedelta(minutes=5)).isoformat(),'provider_observed_at':self.now.isoformat()}
 def observe(self,action,b):
  if action=='reconcile':return {'scope':'ACTUAL_PROVIDER_AND_SOURCE','operation_id':b['operation_id'],'action':b['action'],'source_sha':b['binding']['source_sha'],'outcome':'APPLIED','receipt_sha256':'e'*64,'deployment_id':'dpl_SYNTHETIC'}
  return {k:v for k,v in {**self.approval(),'scope':'ACTUAL_PROVIDER_AND_SOURCE','qualified':True,'guarded_rollback_available':True,'authenticated_provider_account':True,'cli_version':a.CLI_VERSIONS['vercel']}.items()}
 def provider_run(self,*args,**kw):self.calls.append(args);return SimpleNamespace(returncode=0,stdout='{"id":"dpl_SYNTHETIC"}')
 def adapter(self):return a.ProviderAdapter(self.r/'operations',owner_authorized=True,observe=self.observe,run=self.provider_run,clock=lambda:self.now)
 def perform(self,b=None):return self.adapter().perform('stage_frontend',b or self.b,self.approval(b))
 def test_fsync_and_request_precede_provider(self):
  events=[];real=a._sync_directory
  def sync(p):events.append('dir');return real(p)
  def run(*x,**k):
   rows=[json.loads(p.read_text()) for p in (self.r/'operations').glob('*.json')];self.assertTrue(any(x.get('gitSource') for x in rows));self.assertGreaterEqual(events.count('dir'),5);return self.provider_run(*x,**k)
  x=self.adapter();x.run=run
  with patch.object(a,'_sync_directory',side_effect=sync):x.perform('stage_frontend',self.b,self.approval())
  self.assertEqual(len(self.calls),1)
 def test_directory_fsync_failure_means_no_provider(self):
  with patch.object(a,'_sync_directory',side_effect=OSError('synthetic')):
   with self.assertRaises(OSError):self.perform()
  self.assertFalse(self.calls)
 def test_intent_file_fsync_failure_means_no_provider(self):
  real=os.fsync
  def fail(fd):
   if stat.S_ISREG(os.fstat(fd).st_mode):raise OSError('synthetic file fsync')
   real(fd)
  with patch.object(a.os,'fsync',side_effect=fail):
   with self.assertRaises(OSError):self.perform()
  self.assertFalse(self.calls)
 def test_result_replace_failure_keeps_unknown_barrier(self):
  with patch.object(a.os,'replace',side_effect=OSError('synthetic partial state write')):
   with self.assertRaises(OSError):self.perform()
  self.assertEqual(len(self.calls),1);self.assertTrue((self.r/'operations/_write-barrier.json').exists());self.assertTrue(list((self.r/'operations').glob('*.pending')))
  with self.assertRaises(FileExistsError):self.perform()
  self.assertEqual(len(self.calls),1)
 def test_malformed_or_other_barrier_cannot_clear(self):
  result=self.perform();barrier=self.r/'operations/_write-barrier.json';original=barrier.read_text()
  for value in ['{broken',json.dumps({'operation_id':'f'*64,'state':'INTENT_RECONCILE_BEFORE_RETRY'}),json.dumps({'operation_id':result['operation_id'],'state':'WRONG'})]:
   barrier.write_text(value)
   with self.assertRaises((ValueError,json.JSONDecodeError)):self.adapter().reconcile(result['operation_id'])
   self.assertTrue(barrier.exists())
  barrier.write_text(original)
 def test_receipt_directory_failure_prevents_barrier_clear(self):
  result=self.perform()
  real=a._sync_directory
  def fail_receipt(p):
   record=json.loads((self.r/'operations'/f"{result['operation_id']}.json").read_text())
   if record['state']=='APPLIED_VERIFIED':raise OSError('synthetic receipt directory sync')
   return real(p)
  with patch.object(a,'_sync_directory',side_effect=fail_receipt):
   with self.assertRaises(OSError):self.adapter().reconcile(result['operation_id'])
  self.assertTrue((self.r/'operations/_write-barrier.json').exists())
 def test_receipt_before_unlink_and_directory_synced_after(self):
  result=self.perform();events=[];real=a._sync_directory
  def sync(p):
   permanent=json.loads((self.r/'operations'/f"{result['operation_id']}.json").read_text());events.append(('dir',permanent['state'],(self.r/'operations/_write-barrier.json').exists()));return real(p)
  with patch.object(a,'_sync_directory',side_effect=sync):self.adapter().reconcile(result['operation_id'])
  self.assertEqual(events[-2:],[('dir','APPLIED_VERIFIED',True),('dir','APPLIED_VERIFIED',False)])
  with self.assertRaises(FileExistsError):self.perform()
  self.assertEqual(len(self.calls),1)
 def test_concurrent_different_operation_at_most_one_call(self):
  def execute(n):
   try:return self.perform({**self.b,'source_sha':str(n)*40})
   except (ValueError,FileExistsError):return 'HELD'
  with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(execute,[1,2]))
  self.assertEqual(len(self.calls),1)
 def test_concurrent_reconcile_lock_fails_closed(self):
  import fcntl
  result=self.perform();p=self.r/'operations/.reconciliation.lock';fd=os.open(p,os.O_RDWR|os.O_CREAT,0o600)
  try:
   fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaises(BlockingIOError):self.adapter().reconcile(result['operation_id'])
   self.assertTrue((self.r/'operations/_write-barrier.json').exists())
  finally:os.close(fd)
 def test_missing_nested_parent_fails_before_provider(self):
  adapter=self.adapter();adapter.journal=self.r/'missing-parent'/'operations'
  with self.assertRaises(FileNotFoundError):adapter.perform('stage_frontend',self.b,self.approval())
  self.assertFalse(self.calls);self.assertFalse((self.r/'missing-parent').exists())
 def test_nested_existing_parent_fsync_failure_prevents_provider(self):
  parent=self.r/'admitted-parent';parent.mkdir(mode=0o700);adapter=self.adapter();adapter.journal=parent/'operations';real=a._sync_directory
  def fail(p):
   if p==parent:raise OSError('synthetic nested admitted parent fsync failure')
   real(p)
  with patch.object(a,'_sync_directory',side_effect=fail):
   with self.assertRaises(OSError):adapter.perform('stage_frontend',self.b,self.approval())
  self.assertFalse(self.calls)
 def test_symlink_or_world_writable_parent_rejected(self):
  for mode in ['symlink','writable']:
   parent=self.r/mode
   if mode=='symlink':parent.symlink_to(self.r,target_is_directory=True)
   else:parent.mkdir(mode=0o777);parent.chmod(0o777)
   adapter=self.adapter();adapter.journal=parent/'operations'
   with self.assertRaises(ValueError):adapter.perform('stage_frontend',self.b,self.approval())
  self.assertFalse(self.calls)
if __name__=='__main__':unittest.main()
