import sys,asyncio,threading,unittest
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClientSession
import motor.frameworks.asyncio as framework
from backend.reading_pass_service import ReadingPassService
from backend.reading_pass_admission import ScopedAdmission
class LabelError(Exception):
 def has_error_label(self,label):return label=='UnknownTransactionCommitResult'
class Delegate:
 def __init__(self,running=None,cleanup_error=None):self.running=running;self.overlap=[];self.exits=0;self.in_transaction=False;self.cleanup_error=cleanup_error
 def start_transaction(self,**k):self.in_transaction=True
 def __exit__(self,*a):
  self.overlap.append(self.running.is_set()if self.running else False);self.exits+=1;self.in_transaction=False
  if self.cleanup_error:raise self.cleanup_error
class Client:
 def __init__(self,delegate,commit=None):self.delegate=delegate;self.commit=commit;self.starts=0
 def start_session(self,**k):
  self.starts+=1;f=asyncio.get_running_loop().create_future();s=AsyncIOMotorClientSession(self.delegate,None)
  if self.commit:s.commit_transaction=self.commit
  f.set_result(s);return f
class Collection:
 def __init__(self,fn):self.fn=fn;self.calls=0
 def find_one(self,*a,**k):
  if 'session'in k:assert isinstance(k['session'],AsyncIOMotorClientSession)
  self.calls+=1;return framework.run_on_executor(asyncio.get_running_loop(),self.fn)
class Scoped(unittest.IsolatedAsyncioTestCase):
 async def wait_started(self,event):
  for _ in range(1000):
   if event.is_set():return
   await asyncio.sleep(.001)
  self.fail('worker not started')
 def service(self,q):s=object.__new__(ReadingPassService);s.client=q;return s
 async def test_query_cancel_original_motor_exit_after_real_worker_only(self):
  started=threading.Event();release=threading.Event();running=threading.Event();d=Delegate(running);q=ScopedAdmission(Client(d),_inert_test_client=True);s=self.service(q)
  def work():
   running.set();started.set()
   try:release.wait(3);return 7
   finally:running.clear()
  c=Collection(work)
  async def op(session):return await q.call(c,'find_one',{},session=session)
  t=asyncio.create_task(s._transaction(op));await self.wait_started(started);t.cancel()
  try:
   with self.assertRaises(asyncio.CancelledError):await asyncio.wait_for(t,.2)
   self.assertEqual(d.exits,0);self.assertEqual(q.gate._value,7);self.assertEqual(c.calls,1)
   release.set();await asyncio.wait_for(q.drain(timeout=1),1);self.assertEqual(d.overlap,[False]);self.assertEqual(d.exits,1);self.assertEqual(q.gate._value,8)
  finally:release.set()
 async def test_commit_cancel_no_callback_replay_no_overlap(self):
  started=threading.Event();release=threading.Event();running=threading.Event();calls=[]
  def commit_work():
   running.set();started.set()
   try:release.wait(3)
   finally:running.clear()
  def commit():return framework.run_on_executor(asyncio.get_running_loop(),commit_work)
  d=Delegate(running);q=ScopedAdmission(Client(d,commit),_inert_test_client=True);s=self.service(q)
  async def op(session):calls.append(1);return 'ok'
  t=asyncio.create_task(s._transaction(op));await self.wait_started(started);t.cancel()
  try:
   with self.assertRaises(asyncio.CancelledError):await asyncio.wait_for(t,.2)
   self.assertEqual(d.exits,0);release.set();await asyncio.wait_for(q.drain(timeout=1),1);self.assertEqual(calls,[1]);self.assertEqual(d.overlap,[False])
  finally:release.set()
 async def test_queued_cancel_does_not_dispatch(self):
  q=ScopedAdmission(Client(Delegate()),_inert_test_client=True);q._loop()
  for _ in range(8):await q.gate.acquire()
  c=Collection(lambda:1);t=asyncio.create_task(q.call(c,'find_one',{}));await asyncio.sleep(0);t.cancel()
  with self.assertRaises(asyncio.CancelledError):await t
  self.assertEqual(c.calls,0)
  for _ in range(8):q.gate.release()
  await q.drain(timeout=1)
 async def test_deferred_cleanup_error_visible_drain_cancel_preserved(self):
  started=threading.Event();release=threading.Event();error=RuntimeError('cleanup failure');d=Delegate(cleanup_error=error);q=ScopedAdmission(Client(d),_inert_test_client=True);s=self.service(q)
  def work():started.set();release.wait(3)
  c=Collection(work)
  async def op(session):return await q.call(c,'find_one',{},session=session)
  t=asyncio.create_task(s._transaction(op));await self.wait_started(started);t.cancel()
  try:
   with self.assertRaises(asyncio.CancelledError):await t
   release.set()
   with self.assertRaises(RuntimeError)as got:await asyncio.wait_for(q.drain(timeout=1),1)
   self.assertIs(got.exception.__cause__,error);self.assertEqual(q.gate._value,8);self.assertEqual(d.exits,1)
  finally:release.set()
 async def test_shutdown_drains_outside_operation_and_rejects_new(self):
  started=threading.Event();release=threading.Event();q=ScopedAdmission(Client(Delegate()),_inert_test_client=True)
  def work():started.set();release.wait(3);return 2
  c=Collection(work);t=asyncio.create_task(q.call(c,'find_one',{}));await self.wait_started(started);drain=asyncio.create_task(q.drain(timeout=1));await asyncio.sleep(.01);self.assertFalse(drain.done())
  try:
   with self.assertRaises(RuntimeError):await q.call(c,'find_one',{})
   release.set();self.assertEqual(await t,2);await asyncio.wait_for(drain,1);self.assertEqual(q.gate._value,8)
  finally:release.set()
 async def test_unknown_commit_retry_preserves_single_callback_and_original_exit(self):
  commits=[];ops=[];d=Delegate()
  def commit():
   f=asyncio.get_running_loop().create_future();commits.append(1)
   if len(commits)<3:f.set_exception(LabelError())
   else:f.set_result(None)
   return f
  q=ScopedAdmission(Client(d,commit),_inert_test_client=True);s=self.service(q)
  async def op(session):ops.append(1);return 9
  self.assertEqual(await s._transaction(op),9);await q.drain(timeout=1);self.assertEqual(len(commits),3);self.assertEqual(ops,[1]);self.assertEqual(d.exits,1)
 async def test_unrelated_client_and_driver_function_untouched(self):
  old=framework.run_on_executor;q=ScopedAdmission(Client(Delegate()),_inert_test_client=True);other=Collection(lambda:5)
  self.assertEqual(await other.find_one({}),5);self.assertIs(framework.run_on_executor,old);self.assertIsNone(q.loop)
 async def test_child_task_session_operation_fails_closed(self):
  q=ScopedAdmission(Client(Delegate()),_inert_test_client=True);raw=await q.start_session()
  async with raw:
   with self.assertRaises(RuntimeError):await asyncio.create_task(q.call(Collection(lambda:1),'find_one',{},session=raw))
  await q.drain(timeout=1)
if __name__=='__main__':unittest.main()
