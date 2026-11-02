import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from backend import startup_data_guard as guard
from backend.test_startup_data_guard import POLICY, Collection
from scripts import startup_dispatch_qualification as q
from scripts.test_india_release_provider_adapter import startup_fixture


class CollectorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.policy = copy.deepcopy(POLICY)
        self.calls = []
        async def command(value):
            self.calls.append(value)
            return {'ok':1, 'authInfo':{'authenticatedUsers':[{'user':self.policy['principal'], 'db':'admin'}],
                'authenticatedUserRoles':[{'role':'readWrite','db':self.policy['database']}]}}
        self.client = SimpleNamespace(admin=SimpleNamespace(command=command))
        self.db = SimpleNamespace(name=self.policy['database'],
            books=Collection([{'id':m['uuid'],'slug':m['slug']} for m in self.policy['markers']]),
            reader_segment_manifests=Collection([{'book_slug':m['slug'],'status':'active',
                'version':m['version'],'segmentation_version':m['segmentation_version']} for m in self.policy['markers']]),
            reader_segment_activation_state=Collection([]))
        self.kw = {'source_sha':'a'*40, 'source_delivery_sha256':'d'*64,
            'config_sha256':'c'*64, 'guard_source_sha256':hashlib.sha256(Path(guard.__file__).read_bytes()).hexdigest(),
            'context_sha256':'4'*64, 'clock':lambda:self.now}

    async def test_exact_unchanged_guard_runs_without_raw_identity_in_receipt(self):
        raw = json.dumps(self.policy)
        proof = await q.collect_startup_qualification(self.client,self.db,raw,**self.kw)
        self.assertEqual(self.calls,[{'connectionStatus':1,'showPrivileges':False}])
        self.assertEqual(proof['policy_sha256'],hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(proof['marker_count'],2)
        self.assertNotIn(self.policy['principal'],json.dumps(proof))
        self.assertNotIn('authenticatedUsers',json.dumps(proof))
        binding = {**self.kw, 'startup_policy_sha256':proof['policy_sha256'],
            'startup_guard_source_sha256':proof['guard_source_sha256'],
            'startup_marker_identity_sha256':proof['marker_identity_sha256'],
            'startup_context_sha256':'4'*64, 'startup_data_receipt_sha256':q.digest(proof)}
        self.assertEqual(q.validate_startup_qualification(binding,{'config_sha256':'c'*64},
            {'startup_data_qualification':proof,'startup_policy_sha256':proof['policy_sha256']},self.now),proof)

    async def test_authorized_reader_successor_rejects_old_policy_then_accepts_exact_new_policy(self):
        for m,row in zip(self.policy['markers'],self.db.reader_segment_manifests.rows):
            row.update(version='successor-'+m['version'],segmentation_version='successor-blocks-v1')
            self.db.reader_segment_activation_state.rows.append({'book_slug':m['slug'],
                'active_segmentation_version':row['segmentation_version'],'generation':1})
        with self.assertRaisesRegex(guard.StartupDataGuardError,'PUBLICATION'):
            await q.collect_startup_qualification(self.client,self.db,json.dumps(self.policy),**self.kw)
        for m,row in zip(self.policy['markers'],self.db.reader_segment_manifests.rows):
            m.update(version=row['version'],segmentation_version=row['segmentation_version'],generation=1)
        proof = await q.collect_startup_qualification(self.client,self.db,json.dumps(self.policy),**self.kw)
        self.assertTrue(proof['guard_verified'])

    async def test_duplicate_manifest_wrong_generation_and_roles_do_not_produce_proof(self):
        original=copy.deepcopy(self.db.reader_segment_manifests.rows)
        self.db.reader_segment_manifests.rows.append(copy.deepcopy(original[0]))
        with self.assertRaisesRegex(guard.StartupDataGuardError,'PUBLICATION'):
            await q.collect_startup_qualification(self.client,self.db,json.dumps(self.policy),**self.kw)
        self.db.reader_segment_manifests.rows=original
        m=self.policy['markers'][0]
        self.db.reader_segment_activation_state.rows=[{'book_slug':m['slug'],
            'active_segmentation_version':m['segmentation_version'],'generation':True}]
        with self.assertRaisesRegex(guard.StartupDataGuardError,'ACTIVATION'):
            await q.collect_startup_qualification(self.client,self.db,json.dumps(self.policy),**self.kw)
        async def bad_role(_):
            return {'ok':1,'authInfo':{'authenticatedUsers':[{'user':self.policy['principal'],'db':'admin'}],
                'authenticatedUserRoles':[{'role':'root','db':'admin'}]}}
        self.client.admin.command=bad_role
        with self.assertRaisesRegex(guard.StartupDataGuardError,'ROLES'):
            await q.collect_startup_qualification(self.client,self.db,json.dumps(self.policy),**self.kw)

    async def test_guard_hash_and_method_mismatch_stop_before_database_read(self):
        for extra in [{'guard_source_sha256':'f'*64},{'method':'PROPOSED_POLICY_ONLY'},
                      {'method':'UNCHANGED_GUARD_OVER_AUTHORIZED_BOUNDED_SNAPSHOT','snapshot_sha256':None}]:
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                await q.collect_startup_qualification(self.client,self.db,json.dumps(self.policy),**{**self.kw,**extra})
        self.assertEqual(self.calls,[])

    async def test_snapshot_replay_is_explicit_and_not_relabelled_direct_live_read(self):
        proof=await q.collect_startup_qualification(self.client,self.db,json.dumps(self.policy),**self.kw,
            method='UNCHANGED_GUARD_OVER_AUTHORIZED_BOUNDED_SNAPSHOT',snapshot_sha256='5'*64,
            snapshot_observed_at=(self.now-timedelta(minutes=5)).isoformat())
        self.assertEqual(proof['snapshot_sha256'],'5'*64)
        self.assertIn('SNAPSHOT',proof['method'])
        self.assertEqual(proof['observed_at'],(self.now-timedelta(minutes=5)).isoformat())

    async def test_snapshot_replay_cannot_refresh_old_missing_future_or_naive_capture(self):
        for captured in [None,(self.now-timedelta(minutes=15,microseconds=1)).isoformat(),
                         (self.now+timedelta(microseconds=1)).isoformat(),self.now.replace(tzinfo=None).isoformat()]:
            with self.subTest(captured=captured),self.assertRaises(ValueError):
                await q.collect_startup_qualification(self.client,self.db,json.dumps(self.policy),**self.kw,
                    method='UNCHANGED_GUARD_OVER_AUTHORIZED_BOUNDED_SNAPSHOT',snapshot_sha256='5'*64,
                    snapshot_observed_at=captured)
        self.assertEqual(self.calls,[])


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,3,tzinfo=timezone.utc)
        self.binding,self.actual=startup_fixture({'source_sha':'a'*40,'source_delivery_sha256':'d'*64},self.now,'f'*64)
        self.approval={'config_sha256':'c'*64}

    def check(self,binding=None,actual=None):
        return q.validate_startup_qualification(binding or self.binding,self.approval,actual or self.actual,self.now)

    def test_old_compatibility_boolean_alone_cannot_qualify(self):
        with self.assertRaises(ValueError):self.check(actual={'startup_qualified':True})

    def test_receipt_fields_and_bound_installed_policy_cannot_be_substituted(self):
        for key,value in [('phase','PROPOSED_POLICY_ONLY'),('scope','OFFLINE_FIXTURE'),
                          ('source_sha','e'*40),('config_sha256','e'*64),('source_delivery_sha256','e'*64),
                          ('guard_source_sha256','e'*64),('marker_identity_sha256','e'*64),
                          ('context_sha256','e'*64),('marker_count',True),('marker_count',1),
                          ('guard_verified',False),('markers_sha256','0'*64)]:
            x=copy.deepcopy(self.actual);x['startup_data_qualification'][key]=value
            b={**self.binding,'startup_data_receipt_sha256':q.digest(x['startup_data_qualification'])}
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.check(b,x)
        with self.assertRaises(ValueError):self.check(actual={**self.actual,'startup_policy_sha256':'e'*64})

    def test_stale_future_naive_and_hash_tampering_denied(self):
        for at in [(self.now-timedelta(minutes=15,microseconds=1)).isoformat(),
                   (self.now+timedelta(microseconds=1)).isoformat(),self.now.replace(tzinfo=None).isoformat(),'invalid']:
            x=copy.deepcopy(self.actual);x['startup_data_qualification']['observed_at']=at
            b={**self.binding,'startup_data_receipt_sha256':q.digest(x['startup_data_qualification'])}
            with self.subTest(at=at),self.assertRaises(ValueError):self.check(b,x)
        x=copy.deepcopy(self.actual);x['startup_data_qualification']['markers_sha256']='e'*64
        with self.assertRaises(ValueError):self.check(actual=x)

    def test_extra_raw_fields_and_ambiguous_snapshot_method_denied(self):
        x=copy.deepcopy(self.actual);x['startup_data_qualification']['principal']='SYNTHETIC_DO_NOT_RETURN'
        with self.assertRaises(ValueError):self.check(actual=x)
        x=copy.deepcopy(self.actual);x['startup_data_qualification']['snapshot_sha256']='5'*64
        b={**self.binding,'startup_data_receipt_sha256':q.digest(x['startup_data_qualification'])}
        with self.assertRaises(ValueError):self.check(b,x)


if __name__=='__main__':unittest.main()
