#!/usr/bin/env python3
"""Offline admission only. No credentials, network, provider writes or load."""
import argparse,json
from pathlib import Path

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
    return {'schema':'earnalism.offline-scaling-admission.v1','status':'HOLD' if any(x['state']=='HOLD' for x in findings) else 'UNQUALIFIED','findings':findings,'basePoolArithmeticOnly':arithmetic,'runtimeCapacity':'UNPROVEN','productionMutations':0,'note':'Configuration evidence alone cannot establish load, shared-state correctness, failover or capacity. No automatic flag changes.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--replicas',type=int,required=True);p.add_argument('--limits',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    config=json.loads(a.config.read_text());limits=json.loads(a.limits.read_text()) if a.limits else {}
    result=assess(config,a.replicas,limits);a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['status']);return 2 if result['status']=='HOLD' else 3
if __name__=='__main__':raise SystemExit(main())
