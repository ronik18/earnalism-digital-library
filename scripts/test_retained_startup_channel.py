"""Dummy captured receipts and mocked real collectors; no database/provider reads."""
import copy
from datetime import timedelta
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import test_reader612_phase_collectors as fixtures
p=fixtures.p
SNAP=fixtures.SNAP
spec=importlib.util.spec_from_file_location('candidate_startup',Path(__file__).with_name('startup_dispatch_qualification.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class RetainedStartupChannel(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.Collect();self.f.setUp();self.now=self.f.c.clock()
        self.capture=Mock(side_effect=lambda:copy.deepcopy(self.f.startup))
        self.captured=self.capture() # Dummy stand-in for separately authorized durable capture operator.
        self.channel=m.bind_retained_startup_projection(self.f.P,self.captured,clock=lambda:self.now)
        self.f.c.startup_read=self.channel
    def tearDown(self):self.f.tearDown()
    def test_real_preflight_reuses_one_captured_projection(self):
        f=self.f
        source={'source_sha':f.n['source_sha'],'tree_sha':f.n['tree_sha'],'runtime_sha256':f.n['runtime_sha256'],'payload_membership_sha256':__import__('hashlib').sha256(b'[]').hexdigest(),'payload_files':0}
        with patch.object(f.c,'_flag_source_equivalence'),patch.object(f.c,'_baseline_source'),patch.object(f.c,'_signed_frontend_compatibility',return_value='f'*64),patch.object(p,'qualify_binding',return_value=source):
            first=f.c.collect_preflight(f.n,{},f.expected)
            second=f.c.collect_preflight(f.n,{},f.expected)
        self.assertEqual(first['provider_actual']['startup_data_qualification'],second['provider_actual']['startup_data_qualification'])
        self.capture.assert_called_once_with()
        for _ in range(4):m.validate_startup_qualification(f.P,{'config_sha256':f.P['config_sha256']},self.channel(f.P),self.now)
        self.capture.assert_called_once_with()
    def test_real_closed_reconcile_does_not_recapture(self):
        f=self.f;f.runtime=f.n['runtime_sha256'];r=f.closed()
        # Reconcile must not invoke startup_read at all, even though the new
        # expected binding differs from the preflight's immutable channel.
        f.c.startup_read=Mock(side_effect=AssertionError('NO_RECAPTURE_ON_RECONCILE'))
        source={'source_sha':f.n['source_sha'],'tree_sha':f.n['tree_sha'],'runtime_sha256':f.runtime}
        probe=lambda *args,**kw:(503,{'cache-control':'no-store'},b'{"detail":{"code":"PURCHASE_INITIATION_CLOSED"}}')
        with patch.object(p,'qualify_binding',return_value=source),patch('scripts.purchase_guard_source.validate',return_value=({'state':'CLOSED'},b'',(f.root/'backend/server.py').read_bytes())):
            result=f.c.collect_closed(r,f.expected,purchase_probe=probe)
        self.assertEqual(result['snapshot_id'],SNAP);f.c.startup_read.assert_not_called();self.capture.assert_called_once_with()
    def test_stale_original_time_denies_without_refresh(self):
        original=self.channel(self.f.P)['startup_data_qualification']['observed_at']
        self.now+=timedelta(minutes=16)
        with self.assertRaisesRegex(ValueError,'Stale'):self.channel(self.f.P)
        self.capture.assert_called_once_with();self.assertEqual(self.captured['startup_data_qualification']['observed_at'],original)
    def test_binding_swap_and_mutable_input_cannot_rebind_or_refresh(self):
        original=self.channel(self.f.P)
        self.captured['startup_data_qualification']['observed_at']='2099-01-01T00:00:00+00:00'
        self.assertEqual(self.channel(self.f.P),original)
        changed={**self.f.P,'source_sha':'f'*40}
        with self.assertRaisesRegex(ValueError,'binding differs'):self.channel(changed)
        original['startup_data_qualification']['observed_at']='2099-01-01T00:00:00+00:00'
        self.assertNotEqual(self.channel(self.f.P),original);self.capture.assert_called_once_with()

if __name__=='__main__':unittest.main()
