"""Unwired Custom API controller. No credential loading, listener or native adapter.

Only an explicitly injected provider can perform an operation. The default is
read/write disabled. Tests inject a dummy provider. Local SQLite durability is
single-host preparation, not a multi-host/off-device runtime qualification.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hmac
import copy
from contextlib import contextmanager
import stat
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Protocol
import uuid

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from scripts.check_scaling_readiness import connection_envelope
from scripts.scaling_resource_admission import (
    ResourceHeld, DisabledManagedClientAuthority,
    managed_client_admission, redis_memory_admission,
)


class Held(Exception):
    def __init__(self, code='ADMISSION_HELD', status=503):
        self.code, self.status = code, status


@dataclass(frozen=True)
class Target:
    project_id: str
    environment_id: str
    service_id: str

    def __post_init__(self):
        for value in (self.project_id, self.environment_id, self.service_id):
            if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value):
                raise ValueError('Exact native target UUIDs required')

    @property
    def key(self):
        return '/'.join((self.project_id, self.environment_id, self.service_id))


@dataclass(frozen=True)
class Policy:
    target: Target
    source_digest: str
    min_scale: int
    max_scale: int
    atlas_resource: str
    enabled: bool = False
    evidence_max_age: float = 15
    provider_timeout: float = 2
    redis_target: Target | None = None
    approved_redis_memory_envelope_bytes: int | None = None

    def __post_init__(self):
        if not isinstance(self.target,Target):raise ValueError('Exact native target required')
        if not isinstance(self.source_digest,str) or not re.fullmatch('[0-9a-f]{64}', self.source_digest):raise ValueError('Exact source digest required')
        if not all(type(x) is int and x > 0 for x in (self.min_scale,self.max_scale)) or self.min_scale > self.max_scale:
            raise ValueError('Explicit finite scale range required')
        if not isinstance(self.atlas_resource,str) or not re.fullmatch('[0-9a-f]{24}/[A-Za-z0-9_.-]{1,64}',self.atlas_resource):raise ValueError('Exact Atlas project/cluster binding required')
        if type(self.enabled) is not bool:raise ValueError('Explicit execution mode required')
        if self.redis_target is not None and not isinstance(self.redis_target,Target):raise ValueError('Exact Redis target required')
        if self.redis_target==self.target:raise ValueError('Redis service must be distinct from application service')
        if self.approved_redis_memory_envelope_bytes is not None and (type(self.approved_redis_memory_envelope_bytes) is not int or self.approved_redis_memory_envelope_bytes<=0):raise ValueError('Positive explicit approved Redis envelope required')
        for value in (self.evidence_max_age,self.provider_timeout):
            if type(value) not in (int,float) or not math.isfinite(value) or not 0 < value <= 30:
                raise ValueError('Bounded evidence and transport deadlines required')


@dataclass(frozen=True)
class Observation:
    """Trusted adapter output, never accepted from a public request body.

    A future adapter must verify exclusive control, source, shared-state and
    drain proofs against actual provider evidence. These fields are not proof
    merely because a JSON file says true. No real adapter is supplied here.
    """
    target: Target
    source_digest: str
    revision: str
    observed_at: float
    running: int
    configured: int
    pending: bool
    exclusive_control: bool
    shared_state_ready: bool
    drain_ready: bool
    config: dict
    limits: dict


@dataclass(frozen=True)
class Receipt:
    operation_id: str
    target: Target
    source_digest: str
    desired: int
    settled: bool
    provider_operation_id: str


class Provider(Protocol):
    async def observe(self, target: Target) -> Observation: ...
    async def compare_and_set(self, target: Target, desired: int, *, revision: str, operation_id: str) -> Receipt: ...
    async def lookup(self, target: Target, operation_id: str) -> Receipt | None: ...


class DisabledProvider:
    async def observe(self, target):raise Held('PROVIDER_ADAPTER_UNAVAILABLE')
    async def compare_and_set(self, *args, **kwargs):raise Held('PROVIDER_ADAPTER_UNAVAILABLE')
    async def lookup(self, *args):raise Held('PROVIDER_ADAPTER_UNAVAILABLE')


class Journal:
    """Crash-persistent at-most-once intent barrier for one shared local DB.

    No auto expiry or retry. PENDING and UNKNOWN block all subsequent writes for
    the target, including after process restart. BEGIN IMMEDIATE+unique index
    serialize concurrent claims across same-host processes; lock errors deny.
    """
    def __init__(self, path):
        self.path=Path(path)
        if self.path.is_symlink():raise ValueError('Journal symlink forbidden')
        self.path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        parent=self.path.parent.stat()
        if self.path.parent.is_symlink() or parent.st_uid!=os.getuid() or parent.st_mode & 0o077:
            raise ValueError('Private journal directory required')
        fd=os.open(self.path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        os.close(fd)
        metadata=self.path.stat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid!=os.getuid() or metadata.st_mode & 0o077:
            raise ValueError('Private regular journal required')
        barrier_sql="CREATE UNIQUE INDEX one_unresolved ON operations(target) WHERE state IN ('PENDING','UNKNOWN')"
        with self.connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS operations(
                id TEXT PRIMARY KEY, target TEXT NOT NULL, desired INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PENDING','UNKNOWN','APPLIED','NOT_APPLIED')),
                before_revision TEXT NOT NULL, source TEXT NOT NULL, provider_receipt TEXT)""")
            index=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='one_unresolved'").fetchone()
            if index is None:
                db.execute(barrier_sql)
                index=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='one_unresolved'").fetchone()
            # Never case-fold or remove whitespace inside SQL string literals.
            # Unknown schemas fail closed instead of silently rebuilding them.
            if index['sql']!=barrier_sql:raise ValueError('Unknown intent barrier schema')
        fd=os.open(self.path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    @contextmanager
    def connection(self):
        db=sqlite3.connect(self.path,timeout=0)
        try:
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA synchronous=FULL')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:db.close()

    def active(self,target):
        with self.connection() as db:
            return db.execute("SELECT * FROM operations WHERE target=? AND state IN ('PENDING','UNKNOWN')",(target.key,)).fetchone()

    def claim(self,target,desired,observation):
        operation=str(uuid.uuid4())
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,NULL)',(operation,target.key,desired,'PENDING',observation.revision,observation.source_digest))
        # Commit is complete before any provider mutation is called.
        return operation

    def finish(self,operation,state,provider_receipt=None):
        if state not in {'APPLIED','UNKNOWN','NOT_APPLIED'}:raise ValueError('Invalid journal state')
        with self.connection() as db:
            changed=db.execute("UPDATE operations SET state=?, provider_receipt=? WHERE id=? AND state IN ('PENDING','UNKNOWN')",(state,provider_receipt,operation)).rowcount
            if changed!=1:raise Held('JOURNAL_RECONCILIATION_REQUIRED')


class Controller:
    def __init__(self,policy,journal,provider=None,clock=time.time,managed_client_authority=None):
        self.policy,self.journal,self.provider,self.clock=policy,journal,provider or DisabledProvider(),clock
        self.managed_client_authority=managed_client_authority or DisabledManagedClientAuthority()

    async def observe(self):
        o=copy.deepcopy(await asyncio.wait_for(self.provider.observe(self.policy.target),self.policy.provider_timeout))
        if not isinstance(o,Observation) or o.target!=self.policy.target:raise Held('TARGET_MISMATCH')
        if type(o.observed_at) not in (int,float) or not math.isfinite(o.observed_at):raise Held('OBSERVATION_STALE')
        age=self.clock()-o.observed_at
        if not 0 <= age <= self.policy.evidence_max_age:raise Held('OBSERVATION_STALE')
        if o.source_digest!=self.policy.source_digest:raise Held('SOURCE_MISMATCH')
        if not isinstance(o.revision,str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,128}',o.revision):raise Held('REVISION_REQUIRED')
        if not all(type(x) is int and x>=1 for x in (o.running,o.configured)):raise Held('REPLICA_COUNT_UNKNOWN')
        if o.pending is not False or o.running!=o.configured:raise Held('PROVIDER_NOT_SETTLED')
        return o

    def admit(self,o,desired):
        if o.exclusive_control is not True:raise Held('NATIVE_CONTROLLER_BYPASS')
        if max(o.running,desired)>1 and o.shared_state_ready is not True:raise Held('SHARED_STATE_UNQUALIFIED')
        if desired<o.running and o.drain_ready is not True:raise Held('DRAIN_UNQUALIFIED')
        if not isinstance(o.config,dict) or not isinstance(o.limits,dict):raise Held('CAPACITY_INPUTS_UNKNOWN')
        if o.limits.get('atlas_resource')!=self.policy.atlas_resource:raise Held('ATLAS_TARGET_MISMATCH')
        if o.limits.get('autoscaler_max_replicas')!=self.policy.max_scale:raise Held('POLICY_RANGE_DRIFT')
        budget=o.limits.get('database_connection_budget',{})
        current_bound=budget.get('max_current_web_replicas') if isinstance(budget,dict) else None
        if type(current_bound) is not int or current_bound<max(o.running,desired):raise Held('ROLLOUT_BOUND_UNKNOWN')
        result=connection_envelope(o.config,o.limits,o.running)
        if result['status']!='CONDITIONAL_BOUND' or result['metadataEnvelopeWithinQuota'] is not True:raise Held('ATLAS_HEADROOM_UNQUALIFIED')
        if self.policy.redis_target is None:raise Held('REDIS_TARGET_REQUIRED')
        if self.policy.approved_redis_memory_envelope_bytes is None:raise Held('REDIS_APPROVED_MEMORY_ENVELOPE_REQUIRED')
        try:
            managed_client_admission(self.managed_client_authority,
                target_key=o.target.key,source_digest=o.source_digest,
                provider_revision=o.revision,atlas_resource=self.policy.atlas_resource,
                desired=desired,budget=budget,now=self.clock(),max_age=self.policy.evidence_max_age)
            redis_memory_admission(o.limits.get('redis_memory_budget'),
                application_target_key=o.target.key,redis_target_key=self.policy.redis_target.key,source_digest=o.source_digest,
                approved_memory_envelope_bytes=self.policy.approved_redis_memory_envelope_bytes,now=self.clock(),max_age=self.policy.evidence_max_age)
        except ResourceHeld as exc:raise Held(exc.code) from None
        return result

    @staticmethod
    def same_observation(a,b):
        # Include capacity and all admission proofs, not merely running count.
        return a==b

    def verified_receipt(self,r,operation,desired,source_digest=None):
        return (isinstance(r,Receipt) and r.operation_id==operation and r.target==self.policy.target
                and r.source_digest==(self.policy.source_digest if source_digest is None else source_digest) and type(r.desired) is int and r.desired==desired
                and r.settled is True and isinstance(r.provider_operation_id,str)
                and bool(re.fullmatch('[A-Za-z0-9_.:-]{1,128}',r.provider_operation_id)))

    async def scale(self,desired):
        if type(desired) is not int or not self.policy.min_scale<=desired<=self.policy.max_scale:raise Held('SCALE_OUT_OF_RANGE',400)
        if not self.policy.enabled:raise Held('EXECUTION_DISABLED')
        operation=None;submitted=False
        try:
            if self.journal.active(self.policy.target):raise Held('OUTCOME_RECONCILIATION_REQUIRED',409)
            first=await self.observe();self.admit(first,desired)
            if desired==first.running:return {'status':'ALREADY_AT_SCALE','scale':desired}
            operation=self.journal.claim(self.policy.target,desired,first)
            # Re-read after durable claim to detect concurrent/deployment drift.
            second=await self.observe();self.admit(second,desired)
            # Observation time may advance, while every actual proof must match.
            from dataclasses import replace
            if not self.same_observation(first,replace(second,observed_at=first.observed_at)):
                raise Held('OBSERVATION_CHANGED')
            submitted=True
            receipt=await asyncio.wait_for(self.provider.compare_and_set(self.policy.target,desired,revision=second.revision,operation_id=operation),self.policy.provider_timeout)
            if not self.verified_receipt(receipt,operation,desired):raise Held('PROVIDER_OUTCOME_UNCERTAIN')
            self.journal.finish(operation,'APPLIED',receipt.provider_operation_id)
            return {'status':'APPLIED','scale':desired,'operation_id':operation}
        except BaseException:
            if operation is not None:
                try:self.journal.finish(operation,'UNKNOWN' if submitted else 'NOT_APPLIED')
                except Exception:pass  # Durable PENDING remains a blocking barrier.
            raise

    async def reconcile(self):
        """Operator-only library method. Read-only provider lookup, never replay.

        A matching count alone cannot establish an operation receipt. This is
        deliberately NOT exposed as a public HTTP route.
        """
        row=self.journal.active(self.policy.target)
        if not row:return {'status':'NO_UNRESOLVED_OPERATION'}
        if not isinstance(row['source'],str) or not re.fullmatch('[0-9a-f]{64}',row['source']):raise Held('JOURNAL_SOURCE_INVALID')
        receipt=await asyncio.wait_for(self.provider.lookup(self.policy.target,row['id']),self.policy.provider_timeout)
        if not self.verified_receipt(receipt,row['id'],row['desired'],row['source']):raise Held('OUTCOME_STILL_UNKNOWN',409)
        self.journal.finish(row['id'],'APPLIED',receipt.provider_operation_id)
        return {'status':'RECONCILED','operation_id':row['id']}


def create_app(controller, bearer_token):
    """Standalone factory only: no import-time listener, env reads or app wiring."""
    if not isinstance(bearer_token,str) or not re.fullmatch('[A-Za-z0-9_-]{32,256}',bearer_token):raise ValueError('Explicit private bearer context required')

    def authorize(request):
        values=request.headers.getlist('authorization')
        if len(values)!=1 or not hmac.compare_digest(values[0].encode(),('Bearer '+bearer_token).encode()):raise Held('UNAUTHORIZED',401)

    def response(data,status=200):return JSONResponse(data,status_code=status,headers={'Cache-Control':'no-store'})

    async def dispatch(request):
        try:
            authorize(request)
            if request.method=='GET':
                o=await controller.observe()
                return response([{'id':controller.policy.target.service_id,'group':controller.policy.target.environment_id,'scale':o.running,'web':True}])
            if request.path_params['service_id']!=controller.policy.target.service_id:raise Held('SERVICE_NOT_FOUND',404)
            if request.headers.get('content-type','').split(';')[0].lower()!='application/json':raise Held('JSON_REQUIRED',415)
            body=bytearray()
            async with asyncio.timeout(controller.policy.provider_timeout):
                async for part in request.stream():
                    if len(body)+len(part)>1024:raise Held('REQUEST_TOO_LARGE',413)
                    body.extend(part)
            def unique(pairs):
                value={}
                for k,v in pairs:
                    if k in value:raise ValueError('duplicate')
                    value[k]=v
                return value
            try:data=json.loads(body,object_pairs_hook=unique)
            except (ValueError,UnicodeError):raise Held('INVALID_JSON',400)
            if not isinstance(data,dict) or set(data)!={'scale'}:raise Held('SCALE_ONLY_BODY_REQUIRED',400)
            return response(await controller.scale(data['scale']))
        except Held as exc:return response({'code':exc.code},exc.status)
        except Exception:return response({'code':'CONTROLLER_UNAVAILABLE'},503)

    return Starlette(routes=[Route('/services',dispatch,methods=['GET']),Route('/services/{service_id}',dispatch,methods=['PATCH'])])
