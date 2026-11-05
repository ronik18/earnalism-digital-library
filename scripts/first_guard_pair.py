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
BASELINE_KEYS={'schema','owner_scope_receipt_sha256','release_scope_id','intended_closed_source_sha','operations_journal_identity_sha256','historical_terminal_operations','historical_request_artifacts','initial_future_operation_count','limits'}
def validate_scope(scope,baseline,journal_identity):
    exact(scope,SCOPE_KEYS);exact(baseline,BASELINE_KEYS)
    need(scope['schema']=='earnalism.native_action_scope.v1' and baseline['schema']=='earnalism.actual_root_native_baseline.v2','Exact Root scope/baseline schema')
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
    requests=baseline['historical_request_artifacts']
    need(isinstance(requests,dict) and list(requests)==sorted(requests)
         and all(sha(k) and sha(v) and k in rows for k,v in requests.items()),
         'Exact historical request hashes must belong to terminal history')
    return scope

# Exact native owner answer, reviewed with this source. This grants only the
# second cumulative build, never a new baseline, scope, action or time window.
SREDNI_BUILD_OWNER_RECEIPT_SHA256 = 'b74103f4dd348abcd41f76da3eb870a76ed439edc12b5602024188d314ca9791'
BUILD_AMENDMENT_KEYS = {'schema', 'owner_receipt_sha256', 'original_scope_sha256',
    'original_baseline_sha256', 'title', 'additional_builds', 'cumulative_build_maximum'}
def validate_build_amendment(scope, amendment):
    exact(amendment, BUILD_AMENDMENT_KEYS)
    need(amendment['schema'] == 'earnalism.native_build_amendment.v1'
         and amendment['owner_receipt_sha256'] == SREDNI_BUILD_OWNER_RECEIPT_SHA256
         and scope.get('owner_scope_receipt_sha256') == 'be09149041167583000ec12183729c1622c1b74e5326d9aef2d96c8b2d768611'
         and amendment['original_scope_sha256'] == digest(scope)
         and amendment['original_baseline_sha256'] == scope['baseline_sha256']
         and amendment['title'] == 'sredni-vashtar'
         and type(amendment['additional_builds']) is int and amendment['additional_builds'] == 1
         and type(amendment['cumulative_build_maximum']) is int and amendment['cumulative_build_maximum'] == 2,
         'Exact owner-approved cumulative second-build amendment required')
    return amendment


def count_scoped_intents(scope,baseline,records,*,candidate=None):
    """Records include actual raw-byte hashes; count every nonbaseline intent once."""
    old=baseline['historical_terminal_operations']
    found=set();backend=frontend=builds=0;ids=set();build_maximum=1
    for record,raw_sha in records:
        op=record.get('operation_id');need(sha(op) and op not in ids,'Unique operation record required');ids.add(op)
        if op in old:
            need(record.get('state') in {'APPLIED_VERIFIED','NOT_APPLIED_VERIFIED'} and raw_sha==old[op],'Historical terminal baseline changed');found.add(op);continue
        need(record.get('binding',{}).get('native_action_scope')==scope,'Foreign/unscoped post-baseline operation blocks dispatch')
        if 'native_build_amendment' in record.get('binding',{}):
            need(record.get('action')=='stage_frontend','Build amendment applies only to exact stage operation')
            validate_build_amendment(scope,record['binding']['native_build_amendment']);build_maximum=2
        action=record.get('action');need(action in {'stage_frontend','promote_frontend','restore_frontend','release_backend','release_guarded_bootstrap','restore_guarded_bootstrap'},'Unknown scoped action')
        if action in {'release_backend','release_guarded_bootstrap','restore_guarded_bootstrap'}:backend+=1
        else:frontend+=1
        if action=='stage_frontend':builds+=1
    need(found==set(old),'Historical baseline record missing')
    if candidate is not None and candidate['operation_id'] not in ids:
        need(candidate['binding'].get('native_action_scope')==scope,'Candidate scope differs')
        if candidate['action']=='stage_frontend' and builds>=1:
            need('native_build_amendment' in candidate['binding'],'Second stage must itself bind exact build amendment')
        if 'native_build_amendment' in candidate['binding']:
            need(candidate['action']=='stage_frontend','Build amendment applies only to exact stage operation')
            validate_build_amendment(scope,candidate['binding']['native_build_amendment']);build_maximum=2
        action=candidate['action']
        if action in {'release_backend','release_guarded_bootstrap','restore_guarded_bootstrap'}:backend+=1
        elif action in {'stage_frontend','promote_frontend','restore_frontend'}:frontend+=1
        else:raise ValueError('Unknown candidate action')
        if action=='stage_frontend':builds+=1
    need(backend<=3 and frontend<=3 and builds<=build_maximum,'Original bounded native action allowance exhausted')
    return {'backend':backend,'frontend':frontend,'stage_builds':builds}


def _committed_reader_policy(binding):
    """Read exact deployed-role inputs, never the current disk policy or a URL."""
    from pathlib import Path
    from scripts.purchase_guard_source import _git_blob
    root = Path(binding['source_root']).resolve()
    source = binding['source_sha']
    need(re.fullmatch('[a-f0-9]{40}', source or ''), 'Exact Reader policy source required')
    raw = _git_blob(root, source, 'backend/data/controlled_launch.json')
    service = _git_blob(root, source, 'backend/reading_pass_service.py')
    return raw, service


def validate_reader_mode_preservation(binding, actual):
    """Require applicable native evidence; inactive pilots are N/A, never PASS.

    The native observer remains responsible for genuine observation receipts.
    Commercial preview evidence cannot substitute for protected Reader checks.
    """
    import ast
    raw, service = _committed_reader_policy(binding)
    config = json.loads(raw)
    candidates = []
    for node in ast.parse(service).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'FREE_INDIA_READER_SLUGS' for t in node.targets):
            value = node.value
            need(isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'frozenset'
                 and len(value.args) == 1 and not value.keywords, 'Explicit committed free Reader allowlist required')
            candidates.append(ast.literal_eval(value.args[0]))
    need(len(candidates) == 1 and isinstance(candidates[0], (set, list, tuple))
         and all(isinstance(x, str) and x for x in candidates[0]), 'Unambiguous free Reader allowlist required')
    pilots = set(candidates[0])
    default = config.get('text_access_mode', 'PILOT_FULL_FREE')
    overrides = config.get('title_access_modes', {})
    live = config.get('live_approved_slugs')
    modes = {'PILOT_FULL_FREE', 'COMMERCIAL_ENTITLEMENT'}
    need(default in modes and isinstance(overrides, dict)
         and all(isinstance(k, str) and k and v in modes for k, v in overrides.items())
         and isinstance(live, list) and live and len(set(live)) == len(live)
         and all(isinstance(x, str) and x for x in live), 'Invalid committed Reader mode policy')
    effective = {slug: overrides.get(slug, default if slug in pilots else None) for slug in sorted(live)}
    active = sorted(slug for slug, mode in effective.items() if mode == 'PILOT_FULL_FREE' and slug in pilots)
    proof = actual.get('reader_entitlement_mode_observation')
    keys = {'schema', 'source_sha', 'runtime_sha256', 'controlled_launch_sha256',
            'effective_mode_map_sha256', 'active_free_pilot_slugs', 'scenario', 'free_pilot_results', 'receipt_sha256'}
    exact(proof, keys)
    need(proof['schema'] == 'earnalism.reader_entitlement_mode_observation.v1'
         and proof['source_sha'] == binding['source_sha']
         and proof['runtime_sha256'] == actual.get('runtime_sha256') == binding['source_delivery_sha256']
         and actual.get('source_attestation_matches') is True
         and proof['controlled_launch_sha256'] == hashlib.sha256(raw).hexdigest()
         and proof['effective_mode_map_sha256'] == digest(effective)
         and proof['active_free_pilot_slugs'] == active and sha(proof['receipt_sha256']),
         'Actual source/runtime-bound Reader mode observation required')
    rows = proof['free_pilot_results']
    if not active:
        need(proof['scenario'] == 'NO_CONFIGURED_FULL_FREE_PILOT' and rows == []
             and actual.get('reader_free_pilot_entitlement_preserved') is None,
             'Inactive free pilot must be explicit N/A without a fabricated PASS')
    else:
        need(proof['scenario'] == 'ACTIVE_FREE_PILOTS_VERIFIED'
             and actual.get('reader_free_pilot_entitlement_preserved') is True
             and isinstance(rows, list) and len(rows) == len(active), 'Actual full-free pilot acceptance required')
        for slug, row in zip(active, rows):
            exact(row, {'slug', 'entitlement_kind', 'status', 'receipt_sha256'})
            need(row['slug'] == slug and row['entitlement_kind'] == 'india_pilot_free_text'
                 and row['status'] == 'VERIFIED' and sha(row['receipt_sha256']), 'Exact actual free pilot evidence required')
    return proof
