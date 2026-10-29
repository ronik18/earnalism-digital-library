import importlib.util,unittest,copy,tempfile,json
from pathlib import Path
from scripts import india_release_provider_adapter as a
class Tests(unittest.TestCase):
 def bootstrap(self):
  b={'source_sha':'a'*40,'native_pause_acceptance_sha256':'b'*64,'closed_server_sha256':'c'*64,'source_delivery_sha256':'d'*64,'purchase_mode':'CLOSED','current_backend_deployment_id':'actual-id-required','current_backend_source_sha':'e'*40,'config_sha256':'f'*64}
  return b,{**b,'current_backend_healthy':True,'native_healthcheck_traffic_gating':True,'new_resources_or_config_changes':False}
 def test_closed_bootstrap_does_not_circularly_require_existing_guarded_artifact(self):
  b,o=self.bootstrap();a.validate_action_recovery('release_guarded_bootstrap',b,o)
 def test_bootstrap_preflight_each_missing_or_changed_field_denies(self):
  for k in ['native_pause_acceptance_sha256','closed_server_sha256','source_delivery_sha256','purchase_mode','current_backend_deployment_id','current_backend_source_sha','current_backend_healthy','native_healthcheck_traffic_gating','new_resources_or_config_changes']:
   b,o=self.bootstrap();o.pop(k)
   with self.subTest(k=k),self.assertRaises(ValueError):a.validate_action_recovery('release_guarded_bootstrap',b,o)
 def front(self,phase):
  b={'frontend_phase':phase,'backend_source_sha':'a'*40,'rollback_frontend_source_sha':'b'*40,'rollback_frontend_deployment_id':'dpl_SYNTHETIC'}
  return b,{**b,'frontend_rollback_available':True,'frontend_backend_compatible':True,'backend_unchanged':True}
 def test_frontend_only_eligible_with_unchanged_backend_and_existing_front(self):
  b,o=self.front('BACKEND_UNCHANGED');a.validate_action_recovery('stage_frontend',b,o);a.validate_action_recovery('promote_frontend',b,o)
 def test_frontend_old_rollback_blocked_after_backend_changes(self):
  b,o=self.front('BACKEND_UNCHANGED');o['backend_unchanged']=False
  with self.assertRaises(ValueError):a.validate_action_recovery('stage_frontend',b,o)
 def test_guard_active_unsigned_rollback_denied_signed_accepted(self):
  b,o=self.front('GUARD_ACTIVE')
  with self.assertRaises(ValueError):a.validate_action_recovery('stage_frontend',b,o)
  o['rollback_frontend_signed_purchase_ready']=True;a.validate_action_recovery('promote_frontend',b,o)
 def test_final_normal_backend_still_requires_guarded_recovery(self):
  with self.assertRaises(ValueError):a.validate_action_recovery('release_backend',{}, {})
 def post(self):
  b,o=self.bootstrap();o.update(scope='ACTUAL_PROVIDER_AND_SOURCE',action='release_guarded_bootstrap',source_sha=b['source_sha'],deployment_id='observed-bootstrap',retained_image_id='observed-retained-image',recovery_receipt_sha256='1'*64,guarded_backend_deployment_id='observed-bootstrap',closed_guest_status=503,purchase_pause_proof='MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503')
  for k in ['startup_complete','database_healthy','source_attestation_matches','native_can_rollback','config_compatible','existing_reader_listener_preserved','verify_refund_webhook_code_preserved']:o[k]=True
  return b,o
 def test_post_receipt_requires_every_actual_evidence_field(self):
  b,o=self.post();self.assertEqual(a.qualify_bootstrap_recovery(b,o),'1'*64)
  for k in ['retained_image_id','config_sha256','source_attestation_matches','native_can_rollback','config_compatible','closed_guest_status','purchase_pause_proof','source_delivery_sha256','startup_complete','guarded_backend_deployment_id']:
   x=copy.deepcopy(o);x.pop(k)
   with self.subTest(k=k),self.assertRaises(ValueError):a.qualify_bootstrap_recovery(b,x)
 def test_no_fake_provider_outcome_from_preflight(self):
  b,o=self.bootstrap()
  with self.assertRaises(ValueError):a.qualify_bootstrap_recovery(b,o)
 def test_default_adapter_owner_prohibition_precedes_observer(self):
  from datetime import datetime,timezone
  calls=[]
  with tempfile.TemporaryDirectory() as d:
   adapter=a.ProviderAdapter(Path(d)/'j',observe=lambda *x:calls.append(x))
   with self.assertRaises(ValueError):adapter.perform('release_guarded_bootstrap',{}, {})
   self.assertFalse(calls)
 def test_bootstrap_is_existing_backend_command_not_new_service(self):
  adapter=a.ProviderAdapter(Path('/private/tmp/inert-journal'))
  c=adapter._command('release_guarded_bootstrap',{'source_root':'/private/tmp/inert-source'},Path('/private/tmp/inert-request'));self.assertEqual(c[:3],['railway','up','--ci']);self.assertIn(a.SERVICE,c)
  self.assertEqual(c[-1],'/private/tmp/inert-source/backend');self.assertNotIn('--path-as-root',c)
 def test_final_backend_controller_rejects_absent_bootstrap(self):
  class Inert:
   def __init__(self,p):self.journal=p
   def perform(self,*x):raise AssertionError('must not reach adapter')
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):a.ReleaseController(Inert(Path(d))).perform('release_backend',{}, {})
if __name__=='__main__':unittest.main()
