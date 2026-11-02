"""Private fake-only current-adapter counter model. No credentials/providers or active ledger."""
from pathlib import Path
import copy,hashlib,json,os,sys
P=Path(__file__).resolve().parent
CAN=Path('/tmp/earnalism-main-approved-integration')
REC=P.parents[2]
sys.path[:0]=[str(CAN/'backend'),str(CAN/'internal/audiobook_lab/scripts')]
import audiobook_package_storage_v2 as storage
from test_audiobook_package_storage_v2 import FakeS3,FakeNativeLifecycleReader,config
from audiobook_upload_budget import Budget,before_call,ACTIVE
LIMITS={'requests':2000,'upload_bytes':40*1024**2,'download_bytes':80*1024**2,'versions':176,'metadata_bytes':44*1024**2}
OLD=REC/'continuous-private-staging-20261101/the-open-window/storage-budget.json'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':')).encode()
def write(path,o):
 with path.open('x') as f:json.dump(o,f,indent=2);f.write('\n')
class CountedNative(FakeNativeLifecycleReader):
 def read(self):
  for _ in range(2):
   before_call('native_metadata_request',{})
   ACTIVE.get().reserve(metadata_bytes=storage.NATIVE_API_MAX_RESPONSE_BYTES+1)
  return super().read()
def main():
 manifest=json.loads((P/'MANIFEST.PROPOSED.json').read_text());d=manifest['descriptor_canonical_sha256'];planpath=P/'upload-plan.PROPOSED-NOT-AUTHORIZED.json'
 plan=storage.load_storage_plan(planpath)
 for row in manifest['assets']:assert h(row['local_path'])==row['sha256'] and Path(row['local_path']).stat().st_size==row['size_bytes']
 oldsha=h(OLD);assert oldsha=='68770ec864527cf14925e733e71ae239b166dbfe2c0fc436c9e7ec99cc037e4a';old=json.loads(OLD.read_text())
 assert len(old['attempted_objects'])==old['used']['versions']==10
 out=P/'offline-storage-rehearsal';out.mkdir()
 state=copy.deepcopy(old);state.update(identity=d,limits=LIMITS)
 ledger=out/'SYNTHETIC-NOT-ACTIVE-carried-budget.json';write(ledger,state);ledger.chmod(0o600)
 prefix=plan.immutable_prefix
 payload=b'{"SYNTHETIC_ONLY_NOT_REAL_FINAL_MANIFEST":true}';mf=out/'SYNTHETIC-64KiB-final-manifest-reserve.json';mf.write_bytes(payload+b' '*(65536-len(payload)))
 mp={'schema_version':storage.PLAN_SCHEMA,'slug':'the-open-window','release_descriptor_sha256':d,'immutable_prefix':prefix,'release_status':'RELEASE_CANDIDATE','assets':[{'asset_id':'release-manifest','local_path':str(mf),'key':prefix+'release-manifest.json','sha256':h(mf),'size_bytes':65536,'mime_type':'application/json'}]}
 mpp=out/'SYNTHETIC-manifest-plan.json';write(mpp,mp);manifestplan=storage.load_storage_plan(mpp)
 prod=FakeS3();dr=FakeS3();dr.counter=100;pc=config('prod');dc=config('dr');pn=CountedNative();dn=CountedNative()
 with Budget(ledger,d,**LIMITS) as budget:
  for client,cfg,n in [(prod,pc,pn),(dr,dc,dn)]:assert storage.preflight_store(client,cfg,client,n)['passed']
  for i,model in enumerate([plan,manifestplan]):
   receipt=storage.upload_plan(prod,pc,model,retention_admin_client=prod,native_lifecycle_reader=pn)
   rp=out/f'SYNTHETIC-phase{i}-primary.json';write(rp,receipt)
   parsed=storage.load_storage_receipt(rp,model,'primary',pc)
   replica=storage.replicate_plan(prod,pc,dr,dc,model,parsed,prod_retention_admin_client=prod,dr_retention_admin_client=dr,prod_native_lifecycle_reader=pn,dr_native_lifecycle_reader=dn)
   write(out/f'SYNTHETIC-phase{i}-replica.json',replica)
  final=copy.deepcopy(budget.state)
 total=manifest['total_four_asset_bytes_per_store']+65536
 expected={'requests':119,'upload_bytes':2*total,'download_bytes':4*total,'versions':10,'metadata_bytes':16*(storage.NATIVE_API_MAX_RESPONSE_BYTES+1)}
 delta={k:final['used'][k]-old['used'][k] for k in old['used']};assert delta==expected,(delta,expected)
 assert final['attempted_objects'][:10]==old['attempted_objects'] and h(OLD)==oldsha
 result={'schema':'earnalism.open_window_scored_offline_carried_storage_rehearsal.v1','status':'OFFLINE_ACTUAL_ADAPTER_WITH_FAKE_STORES_ONLY_NOT_STORAGE_QUALIFICATION','descriptor_sha256':d,'source_packet_status':'PROPOSED_NOT_ADOPTED','payload_assets_per_store_bytes':manifest['total_four_asset_bytes_per_store'],'reserved_final_manifest_bytes_per_store':65536,'payload_plus_manifest_per_store':total,'predecessor_path':str(OLD),'predecessor_sha256':oldsha,'predecessor_identity':old['identity'],'old_used_carried':old['used'],'old_ten_ordered_attempted_hashes':old['attempted_objects'],'predecessor_unchanged':True,'new_operation_delta':delta,'projected_cumulative_used':final['used'],'proposed_total_limits_NOT_APPROVED':LIMITS,'remaining_if_approved':{k:LIMITS[k]-final['used'][k] for k in LIMITS},'actual_native_read_model':{'preflight_runs':pn.read_calls+dn.read_calls,'metadata_requests_per_run':2,'bounded_bytes_per_response':storage.NATIVE_API_MAX_RESPONSE_BYTES+1},'actual_upload_readback_adapter_sha256':h(CAN/'internal/audiobook_lab/scripts/audiobook_package_storage_v2.py'),'actual_budget_module_sha256':h(CAN/'internal/audiobook_lab/scripts/audiobook_upload_budget.py'),'real_provider_calls':0,'active_budget_or_original_file_writes':0,'not_proven':['Actual provider endpoints/account/bucket/privacy/retention/versioning/expiry/destination absence','Real versionIDs/final manifest actualsize/sourceQA native admission','Storage receipt or public readiness'],'scope':'Model one bounded four-asset PROD upload/fullverify, full DR replication/fullverify, finalmanifest PROD+DR similarly. No second full-master read/replay margin is available; partial/uncertain phases must reconcile receipts before continuing. Protected customer traffic has separate original120 authority and actual measured provider bytes, not an operator-budget escape route.'}
 write(P/'OWN-STORAGE-REHEARSAL-RESULT.json',result)
 candidate=copy.deepcopy(old);candidate.update(identity=d,limits=LIMITS);candidate['lineage']={'predecessor_state_sha256':oldsha,'predecessor_identity':old['identity'],'predecessor_limits':old['limits'],'owner_amendment_receipt_sha256':None,'owner_amendment_status':'NOT_REQUESTED_OR_APPROVED','exact_proposed_descriptor_sha256':d,'no_counter_or_attempt_reset':True}
 proposal={'schema':'earnalism.open_window_scored_carried_budget_proposal.v1','status':'PROPOSED_NOT_AUTHORIZED_NOT_ACTIVE','predecessor_path':str(OLD),'required_predecessor_sha256':oldsha,'candidate_state':candidate,'candidate_state_canonical_sha256':hashlib.sha256(canonical(candidate)).hexdigest(),'native_constructor':{'identity':d,'explicit_kwargs':LIMITS},'future_destination_path':str(REC/'continuous-scored-staging-20261102/the-open-window'/d/'storage-budget.json'),'no_active_budget_change':True,'all_prior_counters_and_ten_attempts_carried':True,'model_result_sha256':h(P/'OWN-STORAGE-REHEARSAL-RESULT.json'),'owner_decision_needed':'One exact carried total-cap amendment for Open Window plus own four restricted expiring keys, after actual sourceQA/profile/rights and complete upload preparation. Selfish approval/keys/caps are not applicable.'}
 assert not Path(proposal['future_destination_path']).exists();write(P/'OWN-CARRIED-BUDGET.CONSTRUCTOR-PROPOSAL.json',proposal)
 # Public metadata only; no private auth values/files are inspected.
 selfish_plan=REC/'selfish-fresh-production-20261101/native-full-draft-20261101/release-preparation-20261102/four-key-carried-storage-preparation-20261102/FOUR-EXACT-REQUESTS.PRIVATE-PREPARED.json'
 baseline=json.loads(selfish_plan.read_text());requests=[]
 for i,row in enumerate(baseline['requests'],1):
  body=copy.deepcopy(row['request']);body['keyName']=f"ear-openwindow-scored-{row['store']}-{'upload' if row['role']=='upload' else 'config'}-20261102"
  if row['role']=='upload':body['namePrefix']=prefix
  else:assert 'namePrefix' not in body
  requests.append({'sequence':i,'store':row['store'],'role':row['role'],'expected_bucket_name':row['expected_bucket_name'],'request':body,'request_sha256':hashlib.sha256(canonical(body)).hexdigest(),'status':'PROPOSED_NOT_AUTHORIZED_NOT_SENT'})
 keys={'schema':'earnalism.open_window_four_scoped_key_request_proposal.v1','status':'PROPOSED_NOT_AUTHORIZED','maximum_additional_keys_requested':4,'actual_new_keys_created':0,'ttl_seconds':7200,'descriptor_sha256':d,'requests':requests,'owner_receipt_sha256':None,'no_borrowed_selfish_keys_or_cap':True,'authority_preconditions':['Supported scored-retained sourceQA/rights/profile integrated and actual exact-headCI/review passes','Actual relevant merged source inputs and clean canonical handoff qualified','Current final descriptor/fourasset bytes unchanged or proposal superseded before approval','Own originalbudget/tenattempt history preserved and explicit owner carriedcap/keycount decision retained','Provider/admin auth remains available without new keys/master reset/broader permissions; freshness, durable intents and uncertainty safety reviewed before any create']}
 write(P/'OWN-FOUR-RESTRICTED-KEYS.PROPOSED-NOT-AUTHORIZED.json',keys)
 print(json.dumps({'delta':delta,'projected_cumulative':final['used'],'proposed_total_limits_NOT_APPROVED':LIMITS,'manifest_sha256':manifest['descriptor_canonical_sha256'],'rehearsal_sha256':h(P/'OWN-STORAGE-REHEARSAL-RESULT.json'),'budget_proposal_sha256':h(P/'OWN-CARRIED-BUDGET.CONSTRUCTOR-PROPOSAL.json'),'key_proposal_sha256':h(P/'OWN-FOUR-RESTRICTED-KEYS.PROPOSED-NOT-AUTHORIZED.json'),'real_provider_calls':0}))
if __name__=='__main__':main()
