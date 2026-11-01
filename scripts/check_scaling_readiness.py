#!/usr/bin/env python3
"""Offline admission only. No credentials, network, provider writes or load."""
import argparse,json
from pathlib import Path

def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def connection_envelope(config, limits, observed_replicas=None):
    """Conditional arithmetic, never provider inventory/admission proof.

    Every cohort must describe its own actual or maximum overlapping process
    bound; pools are per node and monitoring sockets are additional per client.
    Missing inputs never become zero. No current-connection snapshot is added.
    """
    budget = limits.get('database_connection_budget')
    result = {'status': 'UNKNOWN', 'applicationPerNodeUpperBound': None,
              'allNodeApplicationUpperBound': None, 'totalPerNodeWithReserve': None,
              'headroomPerNodeAfterReserve': None, 'metadataEnvelopeWithinQuota': None,
              'maxAdditionalReplicas': None, 'unknownFields': [], 'runtimeAdmission': False}
    if not isinstance(budget, dict):
        result['unknownFields'] = ['database_connection_budget']
        return result
    required = {'nodes': 1, 'other_connections_per_node': 0,
                'reserve_connections_per_node': 1, 'observed_running_replicas': 1,
                'max_replacement_replicas': 0, 'max_current_web_replicas': 1}
    for key, minimum in required.items():
        if not _integer(budget.get(key), minimum):
            result['unknownFields'].append(key)
    observed = budget.get('observed_running_replicas')
    current_max = budget.get('max_current_web_replicas')
    autoscale_max = limits.get('autoscaler_max_replicas')
    if not _integer(autoscale_max, 1):
        result['unknownFields'].append('autoscaler_max_replicas')
    if (_integer(current_max, 1) and
            ((_integer(observed, 1) and current_max < observed) or
             (_integer(autoscale_max, 1) and current_max < autoscale_max))):
        result['unknownFields'].append('max_current_web_replicas.below_live_or_autoscaler_max')
    if observed_replicas is not None and (not _integer(observed_replicas, 1) or observed_replicas != observed):
        result['unknownFields'].append('observed_running_replicas.actual_mismatch')
    quota = limits.get('database_connection_quota')
    if not _integer(quota, 1):
        result['unknownFields'].append('database_connection_quota')
    cohorts = budget.get('cohorts')
    app = 0
    role_counts = {'current_web': 0, 'replacement_web': 0}
    roles_seen = set()
    if not isinstance(cohorts, list) or not cohorts:
        result['unknownFields'].append('cohorts')
    else:
        for index, cohort in enumerate(cohorts):
            keys = {'replicas': 0, 'workers_per_replica': 1, 'clients_per_worker': 1,
                    'pool_per_client_per_node': 1, 'monitoring_sockets_per_client_per_node': 2}
            if not isinstance(cohort, dict) or any(not _integer(cohort.get(k), n) for k, n in keys.items()):
                result['unknownFields'].append('cohorts.' + str(index))
                continue
            role = cohort.get('role')
            if role not in {'current_web', 'replacement_web', 'background'}:
                result['unknownFields'].append('cohorts.' + str(index) + '.role')
                continue
            roles_seen.add(role)
            if role in role_counts:role_counts[role] += cohort['replicas']
            if role in role_counts:
                for source, field in [('WEB_CONCURRENCY', 'workers_per_replica'), ('MONGODB_MAX_POOL_SIZE', 'pool_per_client_per_node')]:
                    expected = config.get(source)
                    if expected is not None and (not _integer(expected, 1) or cohort[field] != expected):
                        result['unknownFields'].append('cohorts.' + str(index) + '.config_drift.' + source)
            app += (cohort['replicas'] * cohort['workers_per_replica'] * cohort['clients_per_worker'] *
                    (cohort['pool_per_client_per_node'] + cohort['monitoring_sockets_per_client_per_node']))
    for role, bound in [('current_web', 'max_current_web_replicas'), ('replacement_web', 'max_replacement_replicas')]:
        if role not in roles_seen or role_counts[role] != budget.get(bound):
            result['unknownFields'].append('cohorts.' + role + '.inventory_mismatch')
    if not any(x == 'cohorts' or x.startswith('cohorts.') for x in result['unknownFields']):
        result['applicationPerNodeUpperBound'] = app
        if _integer(budget.get('nodes'), 1):
            result['allNodeApplicationUpperBound'] = app * budget['nodes']
    if result['unknownFields']:
        return result
    total = app + budget['other_connections_per_node'] + budget['reserve_connections_per_node']
    headroom = quota - total
    result.update(status='CONDITIONAL_BOUND' if headroom >= 0 else 'OVER_QUOTA',
                  totalPerNodeWithReserve=total, headroomPerNodeAfterReserve=headroom,
                  metadataEnvelopeWithinQuota=headroom >= 0)
    proposed = budget.get('additional_replica')
    keys = {'workers_per_replica': 1, 'clients_per_worker': 1,
            'pool_per_client_per_node': 1, 'monitoring_sockets_per_client_per_node': 2}
    proposed_valid = isinstance(proposed, dict) and all(_integer(proposed.get(k), n) for k, n in keys.items())
    if proposed_valid:
        for source, field in [('WEB_CONCURRENCY', 'workers_per_replica'), ('MONGODB_MAX_POOL_SIZE', 'pool_per_client_per_node')]:
            if source in config and (not _integer(config[source], 1) or proposed[field] != config[source]):
                proposed_valid = False
    if proposed_valid:
        cost = (proposed['workers_per_replica'] * proposed['clients_per_worker'] *
                (proposed['pool_per_client_per_node'] + proposed['monitoring_sockets_per_client_per_node']))
        result['maxAdditionalReplicas'] = max(0, headroom // cost)
    return result


def controller_evidence(limits):
    """Diagnose a supplied target binding, not attest a remote write path.

    No input field can set enforcementVerified true. Native Judoscale writes
    bypass this offline tool. A supported Custom API integration would need a
    separately reviewed guarded implementation and later provider configuration.
    """
    import re
    evidence = limits.get('controller')
    result = {'targetBinding': 'UNKNOWN', 'enforcementVerified': False,
              'status': 'UNQUALIFIED', 'mode': None}
    if not isinstance(evidence, dict):
        return result
    result['mode'] = evidence.get('mode')
    target_keys = {'project_id', 'environment_id', 'service_id'}
    def valid(target):
        return (isinstance(target, dict) and set(target) == target_keys and
                all(isinstance(v, str) and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', v)
                    for v in target.values()))
    expected, observed = evidence.get('expected_target'), evidence.get('observed_target')
    if valid(expected) and valid(observed):
        result['targetBinding'] = 'MATCH' if expected == observed else 'MISMATCH'
    if result['targetBinding'] == 'MISMATCH':
        result['status'] = 'TARGET_MISMATCH'
    elif result['mode'] == 'native_judoscale':
        result['status'] = 'UNMEDIATED_NATIVE_CONTROLLER'
    elif result['mode'] == 'guarded_custom_api':
        result['status'] = 'GUARDED_IMPLEMENTATION_AND_RUNTIME_BINDING_REQUIRED'
    return result


def assess(config,replicas,limits=None):
    limits=limits or {};findings=[]
    def flag(name):
        value=config.get(name)
        if type(value) is bool:return value
        if isinstance(value,str) and value.lower() in {'true','false'}:return value.lower()=='true'
        return None
    if type(replicas) is not int or replicas<1:
        findings.append({'code':'REPLICA_COUNT_UNKNOWN','state':'UNKNOWN'})
    elif replicas>1:
        shared,cache=flag('MULTI_REPLICA_ENABLED'),flag('REDIS_CACHE_ENABLED')
        if shared is False and cache is False:
            findings.append({'code':'MULTI_REPLICA_SHARED_STATE_NOT_ADMITTED','state':'HOLD','replicas':replicas,'multiReplicaEnabled':shared,'redisCacheEnabled':cache})
        elif shared is not True and cache is not True:
            findings.append({'code':'SHARED_STATE_FLAGS_UNKNOWN','state':'UNKNOWN'})
        else:
            findings.append({'code':'SHARED_STATE_CONFIGURED_NOT_RUNTIME_PROVEN','state':'UNKNOWN'})
    required=('autoscaler_min_replicas','autoscaler_max_replicas','autoscaler_cooldown_seconds','database_connection_quota','redis_maxmemory_bytes','redis_maxclients','redis_eviction_policy')
    for key in required:
        v=limits.get(key)
        valid=bool(v.strip()) if key=='redis_eviction_policy' and isinstance(v,str) else (type(v) is int and v>=0 if key=='autoscaler_cooldown_seconds' else type(v) is int and v>0)
        if not valid:findings.append({'code':'LIMIT_UNKNOWN','state':'UNKNOWN','field':key})
    lo,hi=limits.get('autoscaler_min_replicas'),limits.get('autoscaler_max_replicas')
    if type(lo) is int and type(hi) is int and lo>hi:findings.append({'code':'AUTOSCALER_RANGE_INVALID','state':'HOLD'})
    workers,pool=config.get('WEB_CONCURRENCY'),config.get('MONGODB_MAX_POOL_SIZE')
    # A bare arithmetic pool envelope is not topology, monitor, surge or quota proof.
    arithmetic=replicas*workers*pool if all(type(x) is int and x>0 for x in (replicas,workers,pool)) else None
    envelope=connection_envelope(config,limits,replicas);controller=controller_evidence(limits)
    if envelope['status']=='OVER_QUOTA':findings.append({'code':'DATABASE_CONNECTION_ENVELOPE_EXCEEDED','state':'HOLD'})
    if controller['status'] in {'TARGET_MISMATCH','UNMEDIATED_NATIVE_CONTROLLER'}:findings.append({'code':controller['status'],'state':'HOLD'})
    if envelope['status']=='UNKNOWN':findings.append({'code':'DATABASE_PROCESS_ENVELOPE_UNKNOWN','state':'UNKNOWN','fields':envelope['unknownFields']})
    if controller['enforcementVerified'] is not True:findings.append({'code':'CONTROLLER_WRITE_ENFORCEMENT_UNQUALIFIED','state':'UNKNOWN'})
    return {'connectionEnvelope':envelope,'controller':controller,'schema':'earnalism.offline-scaling-admission.v1','status':'HOLD' if any(x['state']=='HOLD' for x in findings) else 'UNQUALIFIED','findings':findings,'basePoolArithmeticOnly':arithmetic,'runtimeCapacity':'UNPROVEN','productionMutations':0,'note':'Configuration evidence alone cannot establish load, shared-state correctness, failover or capacity. No automatic flag changes.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--replicas',type=int,required=True);p.add_argument('--limits',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    config=json.loads(a.config.read_text());limits=json.loads(a.limits.read_text()) if a.limits else {}
    result=assess(config,a.replicas,limits);a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['status']);return 2 if result['status']=='HOLD' else 3
if __name__=='__main__':raise SystemExit(main())
