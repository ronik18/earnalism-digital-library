"""Pure first-guard pair contract. No execution, receipt creation or authority factory."""
import hashlib
import json
import re
PENDING = 'APPLIED_COMPONENT_VERIFIED_READER_PENDING'
BLOCKED = 'CONTAIN_BLOCKED'
SCHEMA = 'earnalism.first_guard_pair_contain_blocked.v1'
P_KEYS = {'schema','action','source_sha','source_delivery_sha256','closed_server_sha256','runtime_manifest_sha256','config_expected_sha256','frontend_source_sha','frontend_deployment_id','operations_journal_identity_sha256'}
K_KEYS = {'schema','phase','parent_source_projection_sha256','containment_scope','no_compatible_frontend_return','limits_sha256'}
F_KEYS = {'schema','phase','parent_source_projection_sha256','policy_core_sha256','staged_operation_id','staged_record_sha256','staged_source_sha','staged_deployment_id','component_expected_identity_sha256','reader_migration_owner_acceptance_sha256','containment_operator_reference_sha256','containment_scope','no_compatible_frontend_return','limits_sha256'}
LIMITS = {'backend_maximum':3,'frontend_maximum':3,'frontend_build_maximum':1,'policy_write_maximum':1,'policy_writes_consumed':1}
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def sha(v):return isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v) and v!='0'*64
def exact(v,keys):need(isinstance(v,dict) and set(v)==keys,'Exact first-guard contract keys required')
def validate(binding, actual=None):
    c=binding.get('first_guard_pair');exact(c,{'projection','core','policy','owner_acceptance','operator_context','limits'})
    p,k,f,o,t,l=(c[x] for x in ('projection','core','policy','owner_acceptance','operator_context','limits'))
    exact(p,P_KEYS);exact(k,K_KEYS);exact(f,F_KEYS)
    need(p['schema']=='earnalism.first_guard_parent_source_projection.v1' and p['action']=='release_guarded_bootstrap','Parent projection schema/action')
    for field in ('source_sha','frontend_source_sha'):need(re.fullmatch('[a-f0-9]{40}',p[field] or ''),'Exact source')
    for field in P_KEYS-{'schema','action','source_sha','frontend_source_sha','frontend_deployment_id'}:need(sha(p[field]),'Projection digest')
    expected={'source_sha':binding.get('source_sha'),'source_delivery_sha256':binding.get('source_delivery_sha256'),'closed_server_sha256':binding.get('closed_server_sha256'),'config_expected_sha256':binding.get('config_sha256'),'frontend_source_sha':binding.get('frontend_source_sha'),'frontend_deployment_id':binding.get('frontend_deployment_id')}
    if 'first_guard_parent_operation_id' not in binding:
        need(all(p[x]==v for x,v in expected.items()),'Projection differs from parent binding')
    need(l==LIMITS and all(type(v)is int for v in l.values()),'Original bounded limits required')
    for x in (k,f):need(x['phase']=='FIRST_GUARD_PAIR' and x['containment_scope']=='KEEP_PURCHASES_CLOSED_BLOCK_ALL_WRITES_RECONCILE_ONLY' and x['no_compatible_frontend_return'] is True and x['parent_source_projection_sha256']==digest(p) and x['limits_sha256']==digest(l),'Exact first-guard phase/limits')
    need(k['schema']=='earnalism.first_guard_policy_core.v1' and f['schema']==SCHEMA and f['policy_core_sha256']==digest(k),'Acyclic policy core')
    exact(o,{'schema','source','approved','scope','parent_source_projection_sha256','policy_core_sha256','receipt_sha256'})
    need(o['schema']=='earnalism.reader_migration_owner_acceptance.v1' and o['source']=='DIRECT_USER_EXPLICIT_ACCEPTANCE' and o['approved'] is True and o['scope']=='FIRST_GUARD_READER_MIGRATION_AND_CONTAINMENT' and o['parent_source_projection_sha256']==digest(p) and o['policy_core_sha256']==digest(k) and sha(o['receipt_sha256']),'Actual scope-specific Reader owner acceptance required')
    exact(t,{'schema','scope','reference_sha256'})
    need(t['schema']=='earnalism.existing_containment_operator_reference.v1' and t['scope']=='EXISTING_AUTHORIZED_OPERATOR' and sha(t['reference_sha256']),'Existing operator context required')
    need(f['reader_migration_owner_acceptance_sha256']==digest(o) and f['containment_operator_reference_sha256']==digest(t),'Owner/operator reference mismatch')
    need(all(sha(f[x]) for x in ('staged_operation_id','staged_record_sha256','component_expected_identity_sha256')) and re.fullmatch('[a-f0-9]{40}',f['staged_source_sha'] or '') and re.fullmatch('dpl_[A-Za-z0-9]+',f['staged_deployment_id'] or ''),'Exact staged child identity')
    need(f['component_expected_identity_sha256']==digest(p),'Exact expected component identity')
    if actual is not None:
        need(actual.get('reader_migration_owner_acceptance')==o and actual.get('containment_operator_reference')==t and actual.get('first_guard_policy_sha256')==digest(f),'Trusted current Reader authority observation required')
    return c

# Immutable actual-Root baseline admission, not a mutable counter/authority factory.
ACTION_LIMITS={'backend':3,'frontend':3,'stage':1}
SCOPE_KEYS={'schema','owner_scope_receipt_sha256','release_scope_id','baseline_sha256','intended_closed_source_sha','operations_journal_identity_sha256'}
BASELINE_KEYS={'schema','owner_scope_receipt_sha256','release_scope_id','intended_closed_source_sha','operations_journal_identity_sha256','historical_terminal_operations','initial_future_operation_count','limits'}
def validate_scope(scope,baseline,journal_identity):
    exact(scope,SCOPE_KEYS);exact(baseline,BASELINE_KEYS)
    need(scope['schema']=='earnalism.native_action_scope.v1' and baseline['schema']=='earnalism.actual_root_native_baseline.v1','Exact Root scope/baseline schema')
    need(scope['baseline_sha256']==digest(baseline),'Immutable original baseline digest')
    for k in SCOPE_KEYS-{'schema','baseline_sha256'}:need(scope[k]==baseline[k],'Original Root scope changed: '+k)
    need(scope['operations_journal_identity_sha256']==journal_identity and sha(journal_identity),'Original physical journal custody required')
    need(sha(scope['owner_scope_receipt_sha256']),'Actual owner scope receipt required')
    need(re.fullmatch('[a-f0-9]{40}',scope['intended_closed_source_sha'] or ''),'Exact intended B source required')
    identity={'domain':'earnalism.native_action_scope.v1','owner_scope_receipt_sha256':scope['owner_scope_receipt_sha256'],'intended_closed_source_sha':scope['intended_closed_source_sha'],'operations_journal_identity_sha256':journal_identity}
    need(scope['release_scope_id']==digest(identity),'Stable domain-separated owner/source/custody scope required')
    need(type(baseline['initial_future_operation_count'])is int and baseline['initial_future_operation_count']==0,'Actual Root initial zero-action admission required')
    need(baseline['limits']==ACTION_LIMITS and all(type(v)is int for v in baseline['limits'].values()),'Exact typed native action limits required')
    rows=baseline['historical_terminal_operations'];need(isinstance(rows,dict) and list(rows)==sorted(rows),'Complete sorted historical baseline map required')
    need(all(sha(k) and sha(v) for k,v in rows.items()),'Immutable original historical hashes required')
    return scope

def count_scoped_intents(scope,baseline,records,*,candidate=None):
    """Records include actual raw-byte hashes; count every nonbaseline intent once."""
    old=baseline['historical_terminal_operations']
    found=set();backend=frontend=builds=0;ids=set()
    for record,raw_sha in records:
        op=record.get('operation_id');need(sha(op) and op not in ids,'Unique operation record required');ids.add(op)
        if op in old:
            need(record.get('state') in {'APPLIED_VERIFIED','NOT_APPLIED_VERIFIED'} and raw_sha==old[op],'Historical terminal baseline changed');found.add(op);continue
        need(record.get('binding',{}).get('native_action_scope')==scope,'Foreign/unscoped post-baseline operation blocks dispatch')
        action=record.get('action');need(action in {'stage_frontend','promote_frontend','restore_frontend','release_backend','release_guarded_bootstrap','restore_guarded_bootstrap'},'Unknown scoped action')
        if action in {'release_backend','release_guarded_bootstrap','restore_guarded_bootstrap'}:backend+=1
        else:frontend+=1
        if action=='stage_frontend':builds+=1
    need(found==set(old),'Historical baseline record missing')
    if candidate is not None and candidate['operation_id'] not in ids:
        need(candidate['binding'].get('native_action_scope')==scope,'Candidate scope differs')
        action=candidate['action']
        if action in {'release_backend','release_guarded_bootstrap','restore_guarded_bootstrap'}:backend+=1
        elif action in {'stage_frontend','promote_frontend','restore_frontend'}:frontend+=1
        else:raise ValueError('Unknown candidate action')
        if action=='stage_frontend':builds+=1
    need(backend<=3 and frontend<=3 and builds<=1,'Original bounded native action allowance exhausted')
    return {'backend':backend,'frontend':frontend,'stage_builds':builds}
