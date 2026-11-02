"""Unwired admission; not an external process/credential authority.

Only an injected no-I/O verifier may vouch for an actually enforced client
budget. JSON booleans/semaphores do not prove custody. The shipped verifier is
disabled. Redis observations come only from the trusted provider adapter.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,json,math
from typing import Protocol

class ResourceHeld(Exception):
    def __init__(self, code):self.code=code


def integer(value, minimum):return type(value) is int and value>=minimum


def budget_digest(budget):
    try:return hashlib.sha256(json.dumps(budget,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    except (TypeError,ValueError):raise ResourceHeld('MANAGED_CLIENT_BUDGET_INVALID') from None


@dataclass(frozen=True)
class ManagedClientGrant:
    target_key: str
    source_digest: str
    provider_revision: str
    atlas_resource: str
    budget_sha256: str
    desired: int
    valid_until: float


class ManagedClientAuthority(Protocol):
    def verify(self, *, target_key: str, source_digest: str, provider_revision: str,
               atlas_resource: str, desired: int, budget: dict) -> ManagedClientGrant:
        """No I/O; verify actual enforced slot/credential-custody bounds.

        Grant expiry is proof freshness only, never permission to release slots.
        Bounds must survive PENDING/UNKNOWN outcomes, controller crash and
        reconciliation, independently of expiry. No implementation is shipped;
        a caller's JSON is not proof.
        """
        ...


class DisabledManagedClientAuthority:
    def verify(self, **kwargs):raise ResourceHeld('MANAGED_CLIENT_AUTHORITY_UNAVAILABLE')


def managed_client_admission(authority, *, target_key, source_digest,
                             provider_revision, atlas_resource, desired, budget, now, max_age):
    if not isinstance(budget,dict) or not integer(budget.get('other_connections_per_node'),0):
        raise ResourceHeld('EXTERNAL_CLIENT_ALLOWANCE_UNKNOWN')
    if not integer(desired,1):raise ResourceHeld('MANAGED_CLIENT_DESIRED_INVALID')
    digest=budget_digest(budget)
    try:
        grant=authority.verify(target_key=target_key,source_digest=source_digest,
                               provider_revision=provider_revision,atlas_resource=atlas_resource,desired=desired,
                               budget=json.loads(json.dumps(budget,allow_nan=False)))
    except ResourceHeld:raise
    except Exception:raise ResourceHeld('MANAGED_CLIENT_AUTHORITY_FAILED') from None
    if type(grant) is not ManagedClientGrant:raise ResourceHeld('MANAGED_CLIENT_GRANT_REQUIRED')
    if (grant.target_key!=target_key or grant.source_digest!=source_digest or
            grant.provider_revision!=provider_revision or grant.atlas_resource!=atlas_resource or
            grant.budget_sha256!=digest or type(grant.desired) is not int or grant.desired!=desired):raise ResourceHeld('MANAGED_CLIENT_GRANT_BINDING_MISMATCH')
    if (type(grant.valid_until) not in(int,float) or not math.isfinite(grant.valid_until) or
            not 0 < grant.valid_until-now<=max_age):raise ResourceHeld('MANAGED_CLIENT_GRANT_EXPIRED')
    return grant


def redis_memory_admission(budget, *, application_target_key, redis_target_key, source_digest,
                           approved_memory_envelope_bytes, now, max_age):
    if not isinstance(budget,dict):raise ResourceHeld('REDIS_MEMORY_BUDGET_UNKNOWN')
    if (budget.get('application_target_key')!=application_target_key or
            budget.get('redis_target_key')!=redis_target_key or
            budget.get('source_digest')!=source_digest):
        raise ResourceHeld('REDIS_MEMORY_TARGET_SOURCE_MISMATCH')
    stamp=budget.get('observed_at')
    if type(stamp) not in(int,float) or not math.isfinite(stamp) or not 0<=now-stamp<=max_age:
        raise ResourceHeld('REDIS_MEMORY_OBSERVATION_STALE')
    minimums={'maxmemory_bytes':1,'used_memory_bytes':1,'intended_dataset_bytes':1,
              'parent_rss_upper_bound_bytes':1,'persistence_cow_upper_bound_bytes':0,
              'excluded_buffers_upper_bound_bytes':0,'other_process_upper_bound_bytes':0,
              'safety_reserve_bytes':1,'approved_memory_envelope_bytes':1,
              'provider_enforced_limit_bytes':1}
    if any(not integer(budget.get(k),n)for k,n in minimums.items()):raise ResourceHeld('REDIS_MEMORY_COMPONENT_UNKNOWN')
    if not integer(approved_memory_envelope_bytes,1) or budget['approved_memory_envelope_bytes']!=approved_memory_envelope_bytes:
        raise ResourceHeld('REDIS_APPROVED_MEMORY_ENVELOPE_MISMATCH')
    mode=budget.get('persistence_mode')
    rdb,aof=budget.get('rdb_enabled'),budget.get('aof_enabled')
    if type(rdb) is not bool or type(aof) is not bool or mode not in('forking','no_fork'):
        raise ResourceHeld('REDIS_PERSISTENCE_MODE_UNKNOWN')
    if mode=='forking' and budget['persistence_cow_upper_bound_bytes']<budget['parent_rss_upper_bound_bytes']:
        raise ResourceHeld('REDIS_FORK_COW_BOUND_INSUFFICIENT')
    if mode=='no_fork' and (rdb or aof):raise ResourceHeld('REDIS_PERSISTENCE_MODE_MISMATCH')
    if budget.get('policy')!='noeviction' or budget.get('startup_config_writes') is not False:
        raise ResourceHeld('REDIS_MEMORY_POLICY_UNSAFE')
    cap=budget['maxmemory_bytes']
    if cap<=budget['used_memory_bytes'] or cap<budget['intended_dataset_bytes'] or budget['parent_rss_upper_bound_bytes']<cap:
        raise ResourceHeld('REDIS_DATASET_HEADROOM_UNQUALIFIED')
    total=sum(budget[k]for k in ('parent_rss_upper_bound_bytes','persistence_cow_upper_bound_bytes',
                                'excluded_buffers_upper_bound_bytes','other_process_upper_bound_bytes','safety_reserve_bytes'))
    if not total<=budget['approved_memory_envelope_bytes']<=budget['provider_enforced_limit_bytes']:
        raise ResourceHeld('REDIS_SERVICE_MEMORY_ENVELOPE_EXCEEDED')
    return {'maxmemory_bytes':cap,'service_upper_bound_bytes':total,
            'approved_memory_envelope_bytes':budget['approved_memory_envelope_bytes']}
