import asyncio,threading,unittest
from types import SimpleNamespace
try:
 from . import test_scoped_motor_admission as helpers
except ImportError:
 import test_scoped_motor_admission as helpers
from backend.reading_pass_admission import ScopedAdmission,ScopedSession
from motor.motor_asyncio import AsyncIOMotorClient,AsyncIOMotorClientSession
class Hardened(unittest.IsolatedAsyncioTestCase):
 async def test_enter_failure_cleans_original_context_and_releases(self):
  d=helpers.Delegate();raw=AsyncIOMotorClientSession(d,None);error=ValueError('enter')
  class Entry:
   async def __aenter__(self):raise error
   async def __aexit__(self,*args):return await raw.__aexit__(*args)
  q=ScopedAdmission(helpers.Client(d),_inert_test_client=True);permit=await q._acquire();s=ScopedSession(q,Entry(),permit);q.sessions.add(s)
  with self.assertRaises(ValueError)as got:await s.__aenter__()
  self.assertIs(got.exception,error);await q.drain(timeout=1);self.assertEqual(d.exits,1);self.assertEqual(q.gate._value,8)
 async def test_enter_cancellation_defers_original_context_and_releases(self):
  d=helpers.Delegate();raw=AsyncIOMotorClientSession(d,None);started=asyncio.Event()
  class Entry:
   async def __aenter__(self):started.set();await asyncio.Event().wait()
   async def __aexit__(self,*args):return await raw.__aexit__(*args)
  q=ScopedAdmission(helpers.Client(d),_inert_test_client=True);permit=await q._acquire();s=ScopedSession(q,Entry(),permit);q.sessions.add(s);t=asyncio.create_task(s.__aenter__());await started.wait();t.cancel()
  with self.assertRaises(asyncio.CancelledError):await t
  await q.drain(timeout=1);self.assertEqual(d.exits,1);self.assertEqual(q.gate._value,8)
 async def test_drain_timeout_cancel_never_cancels_actual_operation(self):
  q=ScopedAdmission(helpers.Client(helpers.Delegate()),_inert_test_client=True);f=asyncio.get_running_loop().create_future()
  class Obj:
   def find_one(self):return f
  t=asyncio.create_task(q.call(Obj(),'find_one'));await asyncio.sleep(0)
  with self.assertRaises(asyncio.TimeoutError):await q.drain(timeout=.01)
  self.assertEqual(q.gate._value,7);self.assertFalse(f.cancelled());self.assertFalse(q.drain_task.cancelled())
  waiting=asyncio.create_task(q.drain(timeout=1));await asyncio.sleep(0);waiting.cancel()
  with self.assertRaises(asyncio.CancelledError):await waiting
  self.assertFalse(f.cancelled());self.assertFalse(q.drain_task.cancelled());f.set_result(3);self.assertEqual(await t,3);await q.drain(timeout=1);self.assertEqual(q.gate._value,8)
 async def test_open_unentered_session_drain_bounded_no_premature_release(self):
  q=ScopedAdmission(helpers.Client(helpers.Delegate()),_inert_test_client=True);s=await q.start_session()
  with self.assertRaises(asyncio.TimeoutError):await q.drain(timeout=.01)
  self.assertEqual(q.gate._value,7)
  async with s:pass
  await q.drain(timeout=1);self.assertEqual(q.gate._value,8)
 async def test_real_motor_future_identity_is_tracked_not_replaced(self):
  q=ScopedAdmission(helpers.Client(helpers.Delegate()),_inert_test_client=True);raw_future=asyncio.get_running_loop().create_future()
  class Obj:
   def find_one(self):return raw_future
  s=await q.start_session()
  async with s:
   # Run in owner task; observer checks before resolving the original Future.
   async def observer():
    await asyncio.sleep(0);self.assertIn(raw_future,s.pending);raw_future.set_result(4)
   observe=asyncio.create_task(observer());self.assertEqual(await q.call(Obj(),'find_one'),4);await observe
  await q.drain(timeout=1)
 async def test_actual_motor_client_database_binding_and_foreign_rejection(self):
  c=AsyncIOMotorClient('mongodb://127.0.0.1:1',connect=False,maxPoolSize=8);other=AsyncIOMotorClient('mongodb://127.0.0.1:1',connect=False,maxPoolSize=8)
  try:
   q=ScopedAdmission(c);db=q.database(c['dummy']);self.assertIs(db.client,q);self.assertEqual(db.name,'dummy')
   with self.assertRaises(RuntimeError):q.database(other['dummy'])
   with self.assertRaises(AttributeError):getattr(db.users,'delete_many')
   await q.drain(timeout=1)
  finally:c.close();other.close()
 async def test_unknown_commit_exhaustion_never_replays_callback(self):
  d=helpers.Delegate();commits=[];ops=[];error=helpers.LabelError()
  def commit():
   commits.append(1);f=asyncio.get_running_loop().create_future();f.set_exception(error);return f
  q=ScopedAdmission(helpers.Client(d,commit),_inert_test_client=True);service=object.__new__(helpers.ReadingPassService);service.client=q
  async def op(_):ops.append(1);return 1
  with self.assertRaises(helpers.LabelError)as got:await service._transaction(op)
  self.assertIs(got.exception,error);await q.drain(timeout=1);self.assertEqual(len(commits),3);self.assertEqual(len(ops),1);self.assertEqual(d.exits,1)
 async def test_start_session_cancel_finishes_original_future_then_cleanup(self):
  d=helpers.Delegate();f=asyncio.get_running_loop().create_future()
  class Client:
   def start_session(self):return f
  q=ScopedAdmission(Client(),_inert_test_client=True);t=asyncio.create_task(q.start_session());await asyncio.sleep(0);t.cancel()
  with self.assertRaises(asyncio.CancelledError):await t
  self.assertFalse(f.cancelled());self.assertEqual(q.gate._value,7);f.set_result(AsyncIOMotorClientSession(d,None));await q.drain(timeout=1);self.assertEqual(d.exits,1);self.assertEqual(q.gate._value,8)
if __name__=='__main__':unittest.main()

class Coverage(unittest.IsolatedAsyncioTestCase):
 async def test_eight_actual_motor_futures_hold_exact_capacity(self):
  q=ScopedAdmission(helpers.Client(helpers.Delegate()),_inert_test_client=True);started=[];release=threading.Event()
  class Obj:
   def find_one(self):
    f=helpers.framework.run_on_executor(asyncio.get_running_loop(),lambda:release.wait(3));started.append(f);return f
  tasks=[asyncio.create_task(q.call(Obj(),'find_one'))for _ in range(16)]
  try:
   for _ in range(100):
    if len(started)==8:break
    await asyncio.sleep(.001)
   self.assertEqual(len(started),8);self.assertEqual(q.snapshot()['held_permits'],8)
   release.set();await asyncio.gather(*tasks);await q.drain(timeout=1);self.assertEqual(q.snapshot()['held_permits'],0)
  finally:release.set()
 def test_current_service_collection_call_inventory_supported(self):
  import ast
  from pathlib import Path
  from backend.reading_pass_admission import ScopedCollection
  source=(Path(__file__).resolve().parents[1]/'reading_pass_service.py').read_text();tree=ast.parse(source);methods=set()
  for node in ast.walk(tree):
   if isinstance(node,ast.Call)and isinstance(node.func,ast.Attribute):
    base=node.func.value
    if isinstance(base,ast.Attribute)and isinstance(base.value,ast.Attribute)and isinstance(base.value.value,ast.Name)and base.value.value.id=='self'and base.value.attr=='db':methods.add(node.func.attr)
  self.assertTrue(methods);self.assertLessEqual(methods,ScopedCollection.ASYNC|{'find'})
