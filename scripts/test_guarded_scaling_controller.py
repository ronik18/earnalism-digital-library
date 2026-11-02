"""In-memory HTTP/dummy provider and private temporary journal only."""
import asyncio
import copy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import httpx

from scripts.guarded_scaling_controller import (
    Controller, Held, Journal, Observation, Policy, Receipt, Target, create_app,
)

TARGET=Target('a8533934-35c4-463e-9f43-577a9ac391ee','580b250c-80ee-48ad-bfbe-fa4e31a6b378','5af42e7e-f518-4f6a-b602-d9950866501f')
REDIS_TARGET=replace(TARGET,service_id='f133dcdc-17f4-42a3-92c7-3aa76ccd26b1')
DIGEST='a'*64
ATLAS='1'*24+'/fixture'
TOKEN='dummy_test_only_'+'x'*32

from scripts.scaling_resource_admission import ManagedClientGrant, budget_digest

class DummyManagedAuthority:
    # Explicit synthetic authority, not an external-custody implementation.
    def verify(self, **kw):
        return ManagedClientGrant(kw['target_key'],kw['source_digest'],kw['provider_revision'],
            kw['atlas_resource'],budget_digest(kw['budget']),kw['desired'],1001)

def redis_budget():
    return {'application_target_key':TARGET.key,'redis_target_key':REDIS_TARGET.key,'source_digest':DIGEST,'observed_at':1000,
        'persistence_mode':'forking','rdb_enabled':True,'aof_enabled':False,
        'maxmemory_bytes':100,'used_memory_bytes':10,'intended_dataset_bytes':90,
        'parent_rss_upper_bound_bytes':120,'persistence_cow_upper_bound_bytes':120,
        'excluded_buffers_upper_bound_bytes':10,'other_process_upper_bound_bytes':10,
        'safety_reserve_bytes':20,'approved_memory_envelope_bytes':280,
        'provider_enforced_limit_bytes':300,'policy':'noeviction','startup_config_writes':False}


def observation():
    def cohort(role):return {'role':role,'replicas':10,'workers_per_replica':1,'clients_per_worker':1,'pool_per_client_per_node':8,'monitoring_sockets_per_client_per_node':2}
    limits={'atlas_resource':ATLAS,'autoscaler_max_replicas':10,'database_connection_quota':500,'database_connection_budget':{
        'nodes':3,'observed_running_replicas':2,'max_current_web_replicas':10,'max_replacement_replicas':10,
        'other_connections_per_node':20,'reserve_connections_per_node':50,
        'cohorts':[cohort('current_web'),cohort('replacement_web')]}}
    limits['redis_memory_budget']=redis_budget()
    return Observation(TARGET,DIGEST,'r1',1000,2,2,False,True,True,True,
        {'WEB_CONCURRENCY':1,'MONGODB_MAX_POOL_SIZE':8},limits)


class DummyProvider:
    def __init__(self):
        self.current=observation();self.reads=0;self.writes=[];self.receipts={}
        self.error=None;self.second=None;self.entered=asyncio.Event();self.release=None;self.on_write=None
    async def observe(self,target):
        self.reads+=1
        return self.second if self.reads==2 and self.second else self.current
    async def compare_and_set(self,target,desired,*,revision,operation_id):
        if self.on_write:self.on_write(operation_id)
        self.writes.append((target,desired,revision,operation_id));self.entered.set()
        if self.release:await self.release.wait()
        if self.current.revision!=revision:raise Held('DUMMY_CAS_REJECTED')
        receipt=Receipt(operation_id,target,DIGEST,desired,True,'dummy-op-1')
        self.receipts[operation_id]=receipt
        if self.error:raise self.error
        limits=copy.deepcopy(self.current.limits);limits['database_connection_budget']['observed_running_replicas']=desired
        self.current=replace(self.current,running=desired,configured=desired,revision='r2',limits=limits)
        return receipt
    async def lookup(self,target,operation_id):return self.receipts.get(operation_id)


class ControllerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'journal.sqlite'
        self.journal=Journal(self.path);self.provider=DummyProvider()
        self.policy=Policy(TARGET,DIGEST,1,10,atlas_resource=ATLAS,enabled=True,provider_timeout=.05,redis_target=REDIS_TARGET,approved_redis_memory_envelope_bytes=280)
        self.controller=Controller(self.policy,self.journal,self.provider,clock=lambda:1000,managed_client_authority=DummyManagedAuthority())
    def tearDown(self):self.temp.cleanup()

    async def test_allowed_call_has_committed_intent_before_single_write(self):
        def check(operation):self.assertEqual(Journal(self.path).active(TARGET)['id'],operation)
        self.provider.on_write=check
        result=await self.controller.scale(3)
        self.assertEqual(result['status'],'APPLIED');self.assertEqual(len(self.provider.writes),1)
        self.assertIsNone(self.journal.active(TARGET))
        self.assertEqual((await self.controller.scale(3))['status'],'ALREADY_AT_SCALE')
        self.assertEqual(len(self.provider.writes),1)

    async def test_disabled_default_never_calls_provider(self):
        c=Controller(replace(self.policy,enabled=False),self.journal,self.provider,clock=lambda:1000,managed_client_authority=DummyManagedAuthority())
        with self.assertRaises(Held):await c.scale(3)
        self.assertEqual(self.provider.reads,0);self.assertEqual(self.provider.writes,[])
        c=Controller(self.policy,self.journal,clock=lambda:1000,managed_client_authority=DummyManagedAuthority())
        with self.assertRaises(Held):await c.scale(3)

    async def test_authentication_and_supported_get_shape(self):
        app=create_app(self.controller,TOKEN)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://dummy.invalid') as client:
            for headers in ({},{'Authorization':'Bearer wrong'},[('Authorization','Bearer '+TOKEN),('Authorization','Bearer '+TOKEN)]):
                r=await client.get('/services',headers=headers);self.assertEqual(r.status_code,401)
            r=await client.get('/services',headers={'Authorization':'Bearer '+TOKEN})
            self.assertEqual(r.json(),[{'id':TARGET.service_id,'group':TARGET.environment_id,'scale':2,'web':True}])
            self.assertEqual(r.headers['cache-control'],'no-store')
        self.assertEqual(self.provider.writes,[])

    async def test_patch_rejects_forged_proofs_unknown_fields_and_bad_values(self):
        app=create_app(self.controller,TOKEN)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://dummy.invalid',headers={'Authorization':'Bearer '+TOKEN}) as client:
            for value in (True,0,-1,11,2.0,'3',None):
                r=await client.patch('/services/'+TARGET.service_id,json={'scale':value});self.assertEqual(r.status_code,400)
            for data in ({'scale':3,'exclusive_control':True},{'scale':3,'target':TARGET.key},[],{}):
                r=await client.patch('/services/'+TARGET.service_id,json=data);self.assertEqual(r.status_code,400)
            for body in ('{"scale":3,"scale":4}','{','x'*1025):
                r=await client.patch('/services/'+TARGET.service_id,content=body,headers={'Content-Type':'application/json'})
                self.assertIn(r.status_code,(400,413))
            r=await client.patch('/services/other',json={'scale':3});self.assertEqual(r.status_code,404)
            r=await client.patch('/services/'+TARGET.service_id,content='3');self.assertEqual(r.status_code,415)
        self.assertEqual(self.provider.reads,0);self.assertEqual(self.provider.writes,[])

    async def test_authorized_slow_request_body_is_bounded_before_provider(self):
        class SlowBody(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'{'
                await asyncio.Event().wait()
        app=create_app(self.controller,TOKEN)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://dummy.invalid',headers={'Authorization':'Bearer '+TOKEN}) as client:
            response=await asyncio.wait_for(client.patch('/services/'+TARGET.service_id,content=SlowBody(),headers={'Content-Type':'application/json'}),1)
            self.assertEqual(response.status_code,503)
        self.assertEqual(self.provider.reads,0);self.assertEqual(self.provider.writes,[])

    async def test_real_patch_traverses_guard_before_dummy_write(self):
        app=create_app(self.controller,TOKEN)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://dummy.invalid',headers={'Authorization':'Bearer '+TOKEN}) as client:
            self.provider.current=replace(self.provider.current,exclusive_control=False)
            r=await client.patch('/services/'+TARGET.service_id,json={'scale':3})
            self.assertEqual(r.status_code,503);self.assertEqual(r.json()['code'],'NATIVE_CONTROLLER_BYPASS')
            self.assertEqual(self.provider.writes,[])
            self.provider.current=replace(self.provider.current,exclusive_control=True)
            r=await client.patch('/services/'+TARGET.service_id,json={'scale':3})
            self.assertEqual(r.status_code,200);self.assertEqual(len(self.provider.writes),1)

    async def test_target_source_time_revision_and_pending_fail_closed(self):
        cases=[{'target':replace(TARGET,environment_id='1'*8+'-'+'1'*4+'-'+'1'*4+'-'+'1'*4+'-'+'1'*12)},
               {'source_digest':'b'*64},{'observed_at':900},{'observed_at':1001},{'observed_at':float('nan')},
               {'revision':''},{'pending':True},{'running':True},{'configured':3},
               {'exclusive_control':False},{'shared_state_ready':False}]
        for change in cases:
            with self.subTest(change=change):
                self.provider.current=replace(observation(),**change)
                with self.assertRaises(Held):await self.controller.scale(3)
                self.assertEqual(self.provider.writes,[]);self.assertIsNone(self.journal.active(TARGET))

    async def test_downscale_requires_exact_drain_proof(self):
        self.provider.current=replace(self.provider.current,drain_ready=False)
        with self.assertRaises(Held):await self.controller.scale(1)
        self.assertEqual(self.provider.writes,[])

    async def test_missing_other_clients_reserve_rollout_and_worker_drift_deny(self):
        for field in ('other_connections_per_node','reserve_connections_per_node','max_replacement_replicas','max_current_web_replicas'):
            with self.subTest(field=field):
                o=observation();o.limits['database_connection_budget'][field]=None;self.provider.current=o
                with self.assertRaises(Held):await self.controller.scale(3)
                self.assertEqual(self.provider.writes,[])
        o=observation();o.config['WEB_CONCURRENCY']=2;self.provider.current=o
        with self.assertRaises(Held):await self.controller.scale(3)
        self.assertEqual(self.provider.writes,[])

    async def test_capacity_evidence_cannot_be_borrowed_from_another_atlas_cluster(self):
        self.provider.current.limits['atlas_resource']='2'*24+'/other'
        with self.assertRaises(Held):await self.controller.scale(3)
        self.assertEqual(self.provider.writes,[])

    async def test_quota_and_policy_range_drift_deny(self):
        for field,value in (('database_connection_quota',200),('autoscaler_max_replicas',11)):
            o=observation();o.limits[field]=value;self.provider.current=o
            with self.assertRaises(Held):await self.controller.scale(3)
            self.assertEqual(self.provider.writes,[])

    async def test_second_read_drift_and_deep_copy_protect_fresh_admission(self):
        self.provider.second=replace(observation(),revision='different')
        with self.assertRaises(Held):await self.controller.scale(3)
        self.assertEqual(self.provider.writes,[]);self.assertIsNone(self.journal.active(TARGET))
        with self.journal.connection() as db:self.assertEqual(db.execute('SELECT state FROM operations').fetchone()[0],'NOT_APPLIED')

    async def test_timeout_lost_reply_restart_block_and_read_only_reconciliation(self):
        self.provider.error=TimeoutError('dummy lost reply, no secret export')
        with self.assertRaises(TimeoutError):await self.controller.scale(3)
        self.assertEqual(self.journal.active(TARGET)['state'],'UNKNOWN')
        c=Controller(self.policy,Journal(self.path),self.provider,clock=lambda:1000,managed_client_authority=DummyManagedAuthority())
        with self.assertRaises(Held):await c.scale(4)
        self.assertEqual(len(self.provider.writes),1)
        self.assertEqual((await c.reconcile())['status'],'RECONCILED')
        self.assertEqual(len(self.provider.writes),1);self.assertIsNone(self.journal.active(TARGET))

    async def test_no_count_only_reconciliation_or_mismatched_receipt(self):
        self.provider.error=RuntimeError('dummy uncertain')
        with self.assertRaises(RuntimeError):await self.controller.scale(3)
        row=self.journal.active(TARGET);self.provider.receipts={}
        with self.assertRaises(Held):await self.controller.reconcile()
        self.provider.receipts[row['id']]=Receipt(row['id'],TARGET,'b'*64,3,True,'dummy-op')
        with self.assertRaises(Held):await self.controller.reconcile()
        self.assertIsNotNone(self.journal.active(TARGET));self.assertEqual(len(self.provider.writes),1)

    async def test_restart_policy_drift_reconciles_only_original_intent_source(self):
        self.provider.error=TimeoutError('dummy lost reply')
        with self.assertRaises(TimeoutError):await self.controller.scale(3)
        row=self.journal.active(TARGET);original=self.provider.receipts[row['id']]
        changed=Controller(replace(self.policy,source_digest='b'*64),Journal(self.path),self.provider,clock=lambda:1000,managed_client_authority=DummyManagedAuthority())
        self.provider.receipts[row['id']]=replace(original,source_digest='b'*64)
        with self.assertRaises(Held):await changed.reconcile()
        self.assertIsNotNone(self.journal.active(TARGET))
        self.provider.receipts[row['id']]=original
        self.assertEqual((await changed.reconcile())['status'],'RECONCILED')
        self.assertEqual(len(self.provider.writes),1)

    async def test_corrupt_original_intent_source_cannot_fall_back_to_current_policy(self):
        self.provider.error=TimeoutError('dummy lost reply')
        with self.assertRaises(TimeoutError):await self.controller.scale(3)
        with self.journal.connection() as db:db.execute("UPDATE operations SET source='' ")
        with self.assertRaises(Held):await self.controller.reconcile()
        self.assertIsNotNone(self.journal.active(TARGET));self.assertEqual(len(self.provider.writes),1)

    async def test_concurrent_requests_cannot_issue_a_second_write(self):
        self.provider.release=asyncio.Event()
        first=asyncio.create_task(self.controller.scale(3))
        try:
            await asyncio.wait_for(self.provider.entered.wait(),1)
            other=Controller(self.policy,Journal(self.path),self.provider,clock=lambda:1000,managed_client_authority=DummyManagedAuthority())
            with self.assertRaises(Held):await other.scale(4)
        finally:self.provider.release.set();await first
        self.assertEqual(len(self.provider.writes),1)

    async def test_racing_preclaim_reads_are_serialized_by_durable_barrier(self):
        arrived=0;both=asyncio.Event()
        async def observe(target):
            nonlocal arrived
            arrived+=1
            if arrived<=2:
                if arrived==2:both.set()
                await both.wait()
            return self.provider.current
        self.provider.observe=observe;self.provider.release=asyncio.Event()
        other=Controller(self.policy,Journal(self.path),self.provider,clock=lambda:1000,managed_client_authority=DummyManagedAuthority())
        tasks=[asyncio.create_task(c.scale(3)) for c in (self.controller,other)]
        try:
            done,pending=await asyncio.wait(tasks,timeout=1,return_when=asyncio.FIRST_COMPLETED)
            self.assertEqual(len(done),1);self.assertEqual(len(pending),1)
            self.assertIsInstance(next(iter(done)).exception(),(sqlite3.IntegrityError,Held,sqlite3.OperationalError))
        finally:
            self.provider.release.set();await asyncio.gather(*tasks,return_exceptions=True)
        self.assertEqual(len(self.provider.writes),1)

    async def test_cancellation_after_submit_stays_unknown(self):
        self.provider.release=asyncio.Event();task=asyncio.create_task(self.controller.scale(3))
        await asyncio.wait_for(self.provider.entered.wait(),1);task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(self.journal.active(TARGET)['state'],'UNKNOWN')
        with self.assertRaises(Held):await self.controller.scale(3)
        self.assertEqual(len(self.provider.writes),1)

    async def test_bounded_provider_deadline(self):
        self.provider.release=asyncio.Event()
        with self.assertRaises(asyncio.TimeoutError):await self.controller.scale(3)
        self.assertEqual(self.journal.active(TARGET)['state'],'UNKNOWN')
        self.assertEqual(len(self.provider.writes),1)

    async def test_journal_failure_prevents_write_and_corrupt_outcome_blocks(self):
        with patch.object(self.journal,'claim',side_effect=sqlite3.OperationalError('dummy disk failure')):
            with self.assertRaises(sqlite3.OperationalError):await self.controller.scale(3)
        self.assertEqual(self.provider.writes,[])
        with patch.object(self.journal,'finish',side_effect=sqlite3.OperationalError('dummy fsync failure')):
            with self.assertRaises(sqlite3.OperationalError):await self.controller.scale(3)
        self.assertEqual(self.journal.active(TARGET)['state'],'PENDING')
        with self.assertRaises(Held):await self.controller.scale(4)
        self.assertEqual(len(self.provider.writes),1)

    def test_private_journal_and_symlink_requirements(self):
        unsafe=Path(self.temp.name)/'public.sqlite';unsafe.write_bytes(b'');unsafe.chmod(0o644)
        with self.assertRaises(ValueError):Journal(unsafe)
        link=Path(self.temp.name)/'link.sqlite';link.symlink_to(self.path)
        with self.assertRaises(ValueError):Journal(link)

    def test_reopened_journal_rejects_weakened_unique_barrier(self):
        with self.journal.connection() as db:
            db.execute('DROP INDEX one_unresolved')
            db.execute('CREATE INDEX one_unresolved ON operations(target)')
        with self.assertRaises(ValueError):Journal(self.path)

    def test_reopened_barrier_preserves_literal_case_and_whitespace(self):
        for predicate in ("('pending','unknown')", "('PEN DING','UN KNOWN')"):
            with self.subTest(predicate=predicate):
                with self.journal.connection() as db:
                    db.execute('DROP INDEX one_unresolved')
                    db.execute('CREATE UNIQUE INDEX one_unresolved ON operations(target) WHERE state IN '+predicate)
                with self.assertRaises(ValueError):Journal(self.path)

    def test_no_implicit_provider_or_secret_configuration(self):
        with self.assertRaises(ValueError):create_app(self.controller,'short')
        with self.assertRaises(ValueError):Policy(TARGET,DIGEST,1,10,atlas_resource=ATLAS,provider_timeout=0)
        with self.assertRaises(ValueError):Policy(TARGET,DIGEST,True,10,atlas_resource=ATLAS)
        self.assertFalse(Policy(TARGET,DIGEST,1,10,atlas_resource=ATLAS).enabled)

if __name__=='__main__':unittest.main()
