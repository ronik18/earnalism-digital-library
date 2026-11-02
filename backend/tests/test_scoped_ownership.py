"""Regression for independent reviewer ownership counterexamples; no DB/services."""
import asyncio,unittest
try:
 from . import test_scoped_motor_admission as h
except ImportError:
 import test_scoped_motor_admission as h
from backend.reading_pass_admission import ScopedAdmission
class Client(h.Client):
 def __init__(self):self.calls=[];super().__init__(h.Delegate())
 def start_session(self,**kwargs):
  f=super().start_session(**kwargs);session=f.result()
  for name in ('commit_transaction','abort_transaction'):
   def operation(name=name):
    self.calls.append(name);future=asyncio.get_running_loop().create_future();future.set_result(None);return future
   setattr(session,name,operation)
  return f
class Ownership(unittest.IsolatedAsyncioTestCase):
 def client(self):
  raw=Client();return ScopedAdmission(raw,_inert_test_client=True),raw
 async def test_closed_session_commit_and_abort_no_dispatch(self):
  q,raw=self.client();s=await q.start_session()
  async with s:pass
  for method in ('commit_transaction','abort_transaction'):
   with self.assertRaises(RuntimeError):await getattr(s,method)()
  self.assertEqual(raw.calls,[]);await q.drain(timeout=1)
 async def test_unentered_session_cannot_borrow_another_owner(self):
  q,raw=self.client();s1=await q.start_session();s2=await q.start_session()
  async with s2:
   for method in ('commit_transaction','abort_transaction'):
    with self.assertRaises(RuntimeError):await getattr(s1,method)()
   self.assertEqual(raw.calls,[])
  async with s1:pass
  await q.drain(timeout=1)
 async def test_unentered_session_commit_and_abort_no_dispatch(self):
  q,raw=self.client();s=await q.start_session()
  for method in ('commit_transaction','abort_transaction'):
   with self.assertRaises(RuntimeError):await getattr(s,method)()
  self.assertEqual(raw.calls,[])
  async with s:pass
  await q.drain(timeout=1)
 async def test_child_session_commit_and_abort_no_dispatch(self):
  q,raw=self.client();s=await q.start_session()
  async with s:
   for method in ('commit_transaction','abort_transaction'):
    with self.assertRaises(RuntimeError):await asyncio.create_task(getattr(s,method)())
   self.assertEqual(raw.calls,[])
  await q.drain(timeout=1)
 async def test_foreign_admission_session_abort_rejected(self):
  q,raw=self.client();other,other_raw=self.client();s=await q.start_session()
  async with s:
   with self.assertRaises(RuntimeError):await other.call(s.raw,'abort_transaction',session=s)
   self.assertEqual(raw.calls,[]);self.assertEqual(other_raw.calls,[])
  await q.drain(timeout=1);await other.drain(timeout=1)
 async def test_valid_owner_commit_and_abort_still_dispatch(self):
  q,raw=self.client();s=await q.start_session()
  async with s:await s.commit_transaction();await s.abort_transaction()
  self.assertEqual(raw.calls,['commit_transaction','abort_transaction']);await q.drain(timeout=1)
