import ast
import copy
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch
from backend.startup_data_guard import StartupDataGuardError, verify_startup_data, parse_policy

POLICY = {'database':'earnalism', 'principal':'replacement_fixture', 'authentication_database':'admin', 'markers':[
 {'uuid':'599f3ccb-4111-4fa7-8596-32d9ffc3dc0a','slug':'dsires-baby','version':'124f8b020c4fa88eba42a6d4','segmentation_version':'canonical-html-blocks-v1','generation':0},
 {'uuid':'32a20edc-5097-4d64-98d0-fb3d29487a9d','slug':'the-call-of-the-wild','version':'606ed98e2f0dc802ba2e014f','segmentation_version':'canonical-html-blocks-v1','generation':0}]}

class Cursor:
 def __init__(self, rows): self.rows=rows
 def max_time_ms(self, value): assert value==1000; return self
 async def to_list(self, n): assert n==2; return self.rows[:n]

class Collection:
 def __init__(self, rows): self.rows=rows
 def find(self, query, projection):
  assert projection.get('_id')==0
  return Cursor([{k:v for k,v in r.items() if projection.get(k)} for r in self.rows if all(r.get(k)==v for k,v in query.items())])

class GuardTests(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  self.auth={'ok':1,'authInfo':{'authenticatedUsers':[{'user':'replacement_fixture','db':'admin'}], 'authenticatedUserRoles':[{'role':'readWrite','db':'earnalism'}]}}
  async def command(value):
   self.assertEqual(value,{'connectionStatus':1,'showPrivileges':False}); return self.auth
  self.client=types.SimpleNamespace(admin=types.SimpleNamespace(command=command))
  self.db=types.SimpleNamespace(name='earnalism',books=Collection([{'id':m['uuid'],'slug':m['slug']} for m in POLICY['markers']]),reader_segment_manifests=Collection([dict(book_slug=m['slug'],status='active',version=m['version'],segmentation_version=m['segmentation_version']) for m in POLICY['markers']]),reader_segment_activation_state=Collection([]))
 async def check(self): await verify_startup_data(self.client,self.db,json.dumps(POLICY))
 async def test_matching_metadata_passes(self): await self.check()
 async def test_explicit_generation_passes(self):
  self.db.reader_segment_activation_state.rows=[{'book_slug':m['slug'],'active_segmentation_version':m['segmentation_version'],'generation':0} for m in POLICY['markers']]; await self.check()
 async def test_wrong_database_stops_before_auth(self):
  self.db.name='other'
  with self.assertRaisesRegex(StartupDataGuardError,'DATABASE'): await self.check()
 async def test_principal_mismatch(self):
  self.auth['authInfo']['authenticatedUsers'][0]['user']='old_user'
  with self.assertRaisesRegex(StartupDataGuardError,'PRINCIPAL'): await self.check()
 async def test_extra_or_admin_roles_fail(self):
  for roles in [[{'role':'atlasAdmin','db':'admin'}],self.auth['authInfo']['authenticatedUserRoles']+[{'role':'read','db':'other'}]]:
   self.auth['authInfo']['authenticatedUserRoles']=roles
   with self.assertRaisesRegex(StartupDataGuardError,'ROLES'): await self.check()
 async def test_malformed_auth_fails(self):
  for response in [{}, {'ok':1}, {'ok':1,'authInfo':{'authenticatedUsers':[]}}]:
   self.auth=response
   with self.assertRaises(StartupDataGuardError): await self.check()
 async def test_missing_or_duplicate_catalogue_fails(self):
  original=copy.deepcopy(self.db.books.rows)
  for rows in [[],original+[original[0]], [dict(original[0],slug='wrong'),original[1]]]:
   self.db.books.rows=rows
   with self.assertRaisesRegex(StartupDataGuardError,'CATALOGUE'): await self.check()
 async def test_wrong_or_duplicate_publication_fails(self):
  original=copy.deepcopy(self.db.reader_segment_manifests.rows)
  for rows in [[],original+[original[0]],[dict(original[0],version='wrong'),original[1]]]:
   self.db.reader_segment_manifests.rows=rows
   with self.assertRaisesRegex(StartupDataGuardError,'PUBLICATION'): await self.check()
 async def test_state_mismatch_and_duplicate_fail(self):
  m=POLICY['markers'][0]
  good={'book_slug':m['slug'],'active_segmentation_version':m['segmentation_version'],'generation':0}
  for rows in [[dict(good,generation=1)],[dict(good,generation=False)],[dict(good,active_segmentation_version='wrong')],[good,good]]:
   self.db.reader_segment_activation_state.rows=rows
   with self.assertRaisesRegex(StartupDataGuardError,'ACTIVATION'): await self.check()
 async def test_driver_error_is_sanitized(self):
  async def command(_): raise ValueError('SECRET_CONNECTION_STRING')
  self.client.admin.command=command
  with self.assertRaisesRegex(StartupDataGuardError,'^STARTUP_DATA_GUARD_READ_UNAVAILABLE$') as e: await self.check()
  self.assertTrue(e.exception.__suppress_context__)
 async def test_timeout_is_sanitized(self):
  async def timed_out(coro,timeout): coro.close(); self.assertEqual(timeout,10); raise __import__('asyncio').TimeoutError('SECRET')
  with patch('backend.startup_data_guard.asyncio.wait_for',timed_out):
   with self.assertRaisesRegex(StartupDataGuardError,'TIMEOUT'): await self.check()
 def test_invalid_policy_fails_without_io(self):
  for raw in [None,'{}','{"database":"x","database":"y"}',json.dumps(dict(POLICY,markers=[])),json.dumps(dict(POLICY,extra=True))]:
   with self.assertRaisesRegex(StartupDataGuardError,'POLICY'): parse_policy(raw)
 async def test_first_lifespan_guard_failure_prevents_all_startup_work(self):
  source=Path(__file__).with_name('server.py').read_text()
  tree=ast.parse(source)
  fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='lifespan')
  # Compile only the lifespan body, never import server or its real client.
  fn.decorator_list=[]
  events=[]
  async def guard(): events.append('guard'); raise StartupDataGuardError('STOP')
  def forbidden(*a,**k): self.fail('startup activity before guard: '+str(events))
  ns={'_verify_startup_data_before_writes':guard,'FastAPI':object}
  for node in ast.walk(fn):
   if isinstance(node,ast.Name) and isinstance(node.ctx,ast.Load): ns.setdefault(node.id,forbidden)
  exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'lifespan-only','exec'),ns)
  with self.assertRaisesRegex(StartupDataGuardError,'STOP'): await ns['lifespan'](None).__anext__()
  self.assertEqual(events,['guard'])

if __name__=='__main__': unittest.main()
