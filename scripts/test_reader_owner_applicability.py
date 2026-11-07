"""Offline exact-source approval applicability; no provider/receipt creation."""
import ast,copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import first_guard_pair as p
from scripts import india_release_provider_adapter as adapter
from scripts.test_first_guard_pair import fixture
FROZEN = {'p': {'schema': 'earnalism.first_guard_parent_source_projection.v1', 'action': 'release_guarded_bootstrap', 'source_sha': '65ca071ebebba3edb73ab44fd13c7e00f95b54e6', 'source_delivery_sha256': 'd19698a7f59042b01b0d24d36750cad83eab030d279263f8fc4202814042064e', 'closed_server_sha256': 'aff2fc165310a3e102f55cffbcef1659f87688967f8c72726af69a9f2e2a249b', 'runtime_manifest_sha256': '9fd188b06300958fb09114c06c8bb34065c913ebf69966006354ce559b96af93', 'config_expected_sha256': 'fde0f12d7a423104f210d2a2de4441ae0089e9b4548d5661869ab96c56ce1579', 'frontend_source_sha': 'b3d3293f006a7f2ae8c24a4ee973240082716dd3', 'frontend_deployment_id': 'dpl_EJBoeSDJLvnt5dkGFHX3LmVemzZu', 'operations_journal_identity_sha256': 'eddf1a6a0ad3d11383d5d41f8dc5a0752142651affcf38a405f874ffe1db8ddf'}, 'k': {'schema': 'earnalism.first_guard_policy_core.v1', 'phase': 'FIRST_GUARD_PAIR', 'parent_source_projection_sha256': '54eee0a6097289c588d53efbd763917e8818e3ab9974f9d08b85cce7a59cbf21', 'containment_scope': 'KEEP_PURCHASES_CLOSED_BLOCK_ALL_WRITES_RECONCILE_ONLY', 'no_compatible_frontend_return': True, 'limits_sha256': 'bd5b20626ff749ce72f496f0617d1cba703c0a624e735341e93c1c7c9b833cf8'}, 'o': {'schema': 'earnalism.reader_migration_owner_acceptance.v1', 'source': 'DIRECT_USER_EXPLICIT_ACCEPTANCE', 'approved': True, 'scope': 'FIRST_GUARD_READER_MIGRATION_AND_CONTAINMENT', 'parent_source_projection_sha256': '54eee0a6097289c588d53efbd763917e8818e3ab9974f9d08b85cce7a59cbf21', 'policy_core_sha256': '3531b8180439a8ee743470a503ed5fc124d7059cfed8fc7218ffe6d493a6a498', 'receipt_sha256': '13ed4e1d8caf9586d19129ef5572c50ab844455f2b8d7f7e6a09fdf8dcb52176'}}

class ReaderOwnerApplicabilityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  journal=Path(self.tmp.name)/'journal';journal.mkdir(mode=0o700)
  self.b,_,_=fixture(journal);c=self.b['first_guard_pair']
  pr={**FROZEN['p'],'source_sha':p.CURRENT_CLOSED,'source_delivery_sha256':'b'*64,'closed_server_sha256':'c'*64,'runtime_manifest_sha256':'d'*64}
  core={**FROZEN['k'],'parent_source_projection_sha256':p.digest(pr)}
  c.update(projection=pr,core=core,owner_acceptance=copy.deepcopy(FROZEN['o']))
  c['policy'].update(parent_source_projection_sha256=p.digest(pr),policy_core_sha256=p.digest(core),component_expected_identity_sha256=p.digest(pr),reader_migration_owner_acceptance_sha256=p.digest(FROZEN['o']))
  self.b.update(source_sha=pr['source_sha'],source_delivery_sha256=pr['source_delivery_sha256'],closed_server_sha256=pr['closed_server_sha256'],config_sha256=pr['config_expected_sha256'],frontend_source_sha=pr['frontend_source_sha'],frontend_deployment_id=pr['frontend_deployment_id'],source_root='/dummy/offline',controller_source_sha='e'*40)
  successor={'original_closed_source_sha':p.HISTORICAL_CLOSED,'source_pair':{'controller_source_sha':'e'*40}}
  self.b['native_source_successor']=successor
  c['owner_acceptance_applicability']={'schema':'earnalism.reader-owner-source-applicability.v1','historical_projection':copy.deepcopy(FROZEN['p']),'historical_core':copy.deepcopy(FROZEN['k']),'historical_owner_raw_sha256':p.HISTORICAL_READER_OWNER_RAW,'continuation_owner_receipt_sha256':p.SREDNI_BUILD_OWNER_RECEIPT_SHA256,'retirement_owner_receipt_sha256':p.RETIREMENT_OWNER_RAW,'source_successor':copy.deepcopy(successor),'native_source_successor_sha256':p.digest(successor),'current_projection_sha256':p.digest(pr),'current_core_sha256':p.digest(core),'source_equivalence_sha256':'f'*64}
 def validate(self,b=None,actual=None):
  b=b or self.b
  with patch.object(p,'validate_source_successor',return_value=b['first_guard_pair']['owner_acceptance_applicability']['source_successor']),patch.object(p,'reader_source_equivalence',return_value='f'*64):return p.validate(b,actual)
 def actual(self):
  c=self.b['first_guard_pair'];return {'reader_migration_owner_acceptance':c['owner_acceptance'],'containment_operator_reference':c['operator_context'],'first_guard_policy_sha256':p.digest(c['policy']),'reader_owner_applicability_sha256':p.digest(c['owner_acceptance_applicability'])}
 def test_preserved_owner_and_current_projection(self):
  before=copy.deepcopy(self.b);self.validate(actual=self.actual());self.assertEqual(before,self.b)
  self.assertEqual(self.b['first_guard_pair']['owner_acceptance'],FROZEN['o'])
 def test_shared_parent_still_rejected(self):
  parent=Path(self.tmp.name)/'shared';parent.mkdir(mode=0o777);parent.chmod(0o777)
  journal=parent/'journal';journal.mkdir(mode=0o700)
  with self.assertRaisesRegex(ValueError,'Private owner-matched journal custody'):fixture(journal)
 def test_child_uses_same_backend_role_without_relabeled_frontend(self):
  self.b['first_guard_parent_operation_id']='1'*64;self.b['source_sha']='2'*40;self.b.pop('native_source_successor');self.validate()
 def test_bridge_does_not_supply_reader_or_runtime_acceptance(self):
  c=self.validate();self.assertNotIn('reader_public_preview_verified',c);self.assertNotIn('startup_complete',c)
 def test_unbound_original_owner_cannot_be_reused(self):
  self.b['first_guard_pair'].pop('owner_acceptance_applicability')
  with self.assertRaises(ValueError):p.validate(self.b)
 def test_tampered_bridge_fields_rejected(self):
  value=self.b['first_guard_pair']['owner_acceptance_applicability']
  for key in value:
   b=copy.deepcopy(self.b);b['first_guard_pair']['owner_acceptance_applicability'][key]='0'*64
   with self.subTest(key=key),self.assertRaises((ValueError,TypeError,AttributeError)):self.validate(b)
 def test_changed_original_owner_projection_core_rejected(self):
  for part,key in [('owner_acceptance','receipt_sha256'),('projection','config_expected_sha256'),('core','containment_scope')]:
   b=copy.deepcopy(self.b);b['first_guard_pair'][part][key]='0'*64
   with self.subTest(part=part),self.assertRaises(ValueError):self.validate(b)
 def test_observation_must_bind_applicability(self):
  for value in (None,'0'*64):
   actual=self.actual();actual['reader_owner_applicability_sha256']=value
   with self.subTest(value=value),self.assertRaisesRegex(ValueError,'applicability observation'):self.validate(actual=actual)
 def test_protected_approval_must_bind_applicability(self):
  b=copy.deepcopy(self.b);b.pop('native_source_successor')
  with patch.object(p,'validate',return_value=b['first_guard_pair']),self.assertRaisesRegex(ValueError,'Protected approval must bind exact Reader owner applicability'):
   adapter.validate_approval('promote_frontend',b,{},True,None)

class CommittedSourceEquivalenceTests(unittest.TestCase):
 def blobs(self):
  from scripts.purchase_guard_source import _git_blob
  root=Path(__file__).resolve().parents[1]
  # Actual fixed committed server blobs; operator consumer files are inspected
  # from the candidate checkout so this test also works before its first commit.
  def blob(_,ref,path):
   if ref in (p.HISTORICAL_CLOSED,p.CURRENT_CLOSED):return _git_blob(root,ref,path)
   return (root/path).read_bytes()
  return blob
 def run_equivalence(self,blob=None):
  b={'source_root':str(Path(__file__).resolve().parents[1]),'controller_source_sha':'a'*40,'source_sha':p.CURRENT_CLOSED}
  with patch('scripts.purchase_guard_source._git_blob',side_effect=blob or self.blobs()):return p.reader_source_equivalence(b)
 def test_actual_fixed_committed_module_and_current_consumer(self):
  self.assertRegex(self.run_equivalence(),r'^[a-f0-9]{64}$')
 def test_protected_handler_or_global_change_rejected(self):
  original=self.blobs()
  def changed(root,ref,path):
   raw=original(root,ref,path)
   return raw+b'\nUNAUTHORIZED_ACCESS_OVERRIDE=True\n' if ref==p.CURRENT_CLOSED and path=='backend/server.py' else raw
  with self.assertRaisesRegex(ValueError,'beyond exact authorized retirement'):self.run_equivalence(changed)
 def test_consumer_or_owner_receipt_change_rejected(self):
  for target in ('frontend/src/pages/Reader.jsx','internal/legal/sredni_reader_retirement_owner_instruction.json','internal/legal/sredni_native_build_amendment_owner_acceptance.json'):
   original=self.blobs()
   def changed(root,ref,path):return original(root,ref,path)+(b' ' if path==target else b'')
   with self.subTest(target=target),self.assertRaises(ValueError):self.run_equivalence(changed)

if __name__=='__main__':unittest.main()
