from dataclasses import replace
import json
import linecache
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from scripts.mongo_reservation_accounting import Binding, CloseProof, Held, Ledger, initialize_offline, digest

BINDING = Binding('project/environment/service:atlas/cluster', 'a'*64, 'b'*64, 'revision-1', 'c'*32)
CAPS = {'node-a': 10, 'node-b': 10, 'node-c': 10}
UNITS = {'node-a': 6, 'node-b': 6, 'node-c': 6}

class FakeTrustedClose:
    def __init__(self, **changes): self.changes = changes
    def verify(self, *, binding, reservation):
        return replace(CloseProof(digest(binding), digest(reservation), 'd'*64, True, True), **self.changes)

class Accounting(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'ledger.sqlite'
        self.ledger = initialize_offline(self.path, BINDING, CAPS, offline=True)
    def reserve(self, intent='i1', resource='process-1/client-1', units=None, cohort='active_web'):
        return self.ledger.reserve(intent, resource=resource, cohort=cohort, units=UNITS if units is None else units)
    def test_explicit_offline_init_missing_ledger_and_generation(self):
        other = self.path.with_name('other.sqlite')
        with self.assertRaises(Held): initialize_offline(other, BINDING, CAPS)
        self.assertFalse(other.exists())
        with self.assertRaises(Held): Ledger(other, BINDING, CAPS)
        self.assertFalse(other.exists())
        with self.assertRaises(Held): initialize_offline(self.path, BINDING, CAPS, offline=True)
        with self.assertRaises(Held): initialize_offline(other, replace(BINDING, generation=''), CAPS, offline=True)
        self.assertFalse(other.exists())
    def test_strict_node_units_and_no_cross_node_budget_borrow(self):
        for units in ({'node-a': 6}, {'node-a': True,'node-b': 1,'node-c': 1}, {'node-a': 11,'node-b': 1,'node-c': 1}, {'node-a': 0,'node-b': 1,'node-c': 1}):
            with self.subTest(units=units), self.assertRaises(Held): self.reserve(units=units)
        self.assertEqual(self.ledger.snapshot()['charged_per_node'], dict.fromkeys(CAPS,0))
    def test_identical_intent_idempotent_changed_binding_or_client_denied(self):
        self.assertEqual(self.reserve(), 'RESERVED'); self.assertEqual(self.reserve(), 'RESERVED')
        for kwargs in ({'units':dict.fromkeys(CAPS,1)}, {'cohort':'recovery_web'}, {'resource':'another-client'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(Held): self.reserve(**kwargs)
        with self.assertRaises(Held): self.reserve('i2')
        self.assertEqual(self.ledger.snapshot()['charged_per_node'], UNITS)
    def test_bound_config_generation_revision_cannot_reopen(self):
        self.reserve()
        for change in ({'target':'different'}, {'source_sha256':'e'*64}, {'budget_sha256':'f'*64}, {'provider_revision':'r2'}, {'generation':'d'*32}):
            with self.subTest(change=change), self.assertRaises(Held): Ledger(self.path, replace(BINDING,**change), CAPS)
        with self.assertRaises(Held): Ledger(self.path, BINDING, dict.fromkeys(CAPS,11))
    def test_pending_unknown_drain_and_time_never_release(self):
        self.reserve()
        for state in ('ACTIVE','PENDING','UNKNOWN','DRAIN_REQUESTED'):
            self.ledger.mark('i1', state)
            reopened=Ledger(self.path,BINDING,CAPS)
            self.assertEqual(reopened.snapshot()['charged_per_node'],UNITS)
            with self.assertRaises(Held): self.reserve('i2',resource='new-client')
        with self.assertRaises(Held): self.ledger.mark('i1','CLOSE_CONFIRMED')
        with self.assertRaises(Held): self.ledger.release('i1')
    def test_default_release_faults_and_wrong_proof_retain_charge(self):
        self.reserve()
        class CallerJSON:
            def verify(self,**kwargs): return {'physical_closed_or_dead':True,'reconnect_fenced':True}
        class Fault:
            def verify(self,**kwargs): raise RuntimeError('custodian unavailable')
        verifiers=[None,CallerJSON(),Fault(),FakeTrustedClose(physical_closed_or_dead=False),FakeTrustedClose(reconnect_fenced=False),FakeTrustedClose(binding_sha256='0'*64),FakeTrustedClose(reservation_sha256='0'*64),FakeTrustedClose(evidence_sha256='')]
        for verifier in verifiers:
            with self.subTest(verifier=type(verifier).__name__),self.assertRaises(Held):self.ledger.release('i1',verifier=verifier)
            self.assertEqual(self.ledger.snapshot()['charged_per_node'],UNITS)
    def test_positive_fake_close_tombstone_cannot_reopen_or_reuse_instance(self):
        self.reserve();self.assertEqual(self.ledger.release('i1',verifier=FakeTrustedClose()),'CLOSE_CONFIRMED')
        self.assertEqual(self.ledger.snapshot()['charged_per_node'],dict.fromkeys(CAPS,0))
        self.assertFalse(self.ledger.snapshot()['custody_verified'])
        self.assertEqual(self.reserve(),'CLOSE_CONFIRMED')
        with self.assertRaises(Held): self.reserve('i2')
        with self.assertRaises(Held): self.ledger.mark('i1','ACTIVE')
        self.assertEqual(self.reserve('i2',resource='fresh-client'),'RESERVED')
    def test_two_separate_connections_atomic_quota_contention(self):
        barrier=threading.Barrier(2);out=[]
        def worker(n):
            ledger=Ledger(self.path,BINDING,CAPS);barrier.wait(timeout=2)
            try:result=ledger.reserve('i'+str(n),resource='client'+str(n),cohort='active_web',units=UNITS)
            except Held:result='HELD'
            out.append(result)
        threads=[threading.Thread(target=worker,args=(n,))for n in (1,2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=3);self.assertFalse(thread.is_alive())
        self.assertCountEqual(out,['RESERVED','HELD']);self.assertEqual(self.ledger.snapshot()['charged_per_node'],UNITS)
    def test_committed_reservation_survives_abrupt_process_exit(self):
        script="from scripts.mongo_reservation_accounting import *; import os; b=Binding(%r,%r,%r,%r,%r); l=Ledger(%r,b,%r); l.reserve('crashed',resource='crash-client',cohort='recovery_web',units=%r); l.mark('crashed','UNKNOWN'); os._exit(7)" % (BINDING.target,BINDING.source_sha256,BINDING.budget_sha256,BINDING.provider_revision,BINDING.generation,str(self.path),CAPS,UNITS)
        result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).parents[1],env={'PATH':os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=5)
        self.assertEqual(result.returncode,7);reopened=Ledger(self.path,BINDING,CAPS)
        self.assertEqual(reopened.snapshot()['states'],{'crashed':'UNKNOWN'})
        self.assertEqual(reopened.snapshot()['charged_per_node'],UNITS)
        with self.assertRaises(Held):self.reserve(resource='after-crash')
    def test_uncommitted_update_crash_cannot_release_charge(self):
        self.reserve()
        script="import sqlite3,os; c=sqlite3.connect(%r); c.execute('BEGIN IMMEDIATE'); c.execute('DELETE FROM reservations'); os._exit(9)"%str(self.path)
        result=subprocess.run([sys.executable,'-c',script],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,9);self.assertEqual(Ledger(self.path,BINDING,CAPS).snapshot()['charged_per_node'],UNITS)
    def test_checksum_corruption_and_missing_generation_fail_closed(self):
        self.reserve()
        with sqlite3.connect(self.path)as db:db.execute("UPDATE reservations SET checksum='wrong'")
        with self.assertRaises(Held):Ledger(self.path,BINDING,CAPS)
        with self.assertRaises(Held):self.ledger.snapshot()
    def test_metadata_deletion_schema_change_and_symlink_fail_closed(self):
        with sqlite3.connect(self.path)as db:db.execute('DELETE FROM metadata')
        with self.assertRaises(Held):Ledger(self.path,BINDING,CAPS)
        other=self.path.with_name('alias.sqlite');other.symlink_to(self.path)
        with self.assertRaises(Held):Ledger(other,BINDING,CAPS)
    def test_verifier_copy_cannot_modify_binding_or_reservation(self):
        self.reserve()
        class Mutator:
            def verify(self,*,binding,reservation):
                proof=FakeTrustedClose().verify(binding=binding,reservation=reservation)
                binding['capacities']['node-a']=999;reservation['units']['node-a']=999
                return proof
        self.ledger.release('i1',verifier=Mutator())
        self.assertEqual(self.reserve(),'CLOSE_CONFIRMED')
    def test_modified_quota_or_schema_is_not_trusted(self):
        with sqlite3.connect(self.path)as db:db.execute('CREATE TABLE surprise (x TEXT)')
        with self.assertRaises(Held):Ledger(self.path,BINDING,CAPS)

    def test_concurrent_identical_intent_charges_once(self):
        barrier=threading.Barrier(2);out=[]
        def worker():
            ledger=Ledger(self.path,BINDING,CAPS);barrier.wait(timeout=2)
            try:out.append(ledger.reserve('same',resource='one-instance',cohort='active_web',units=UNITS))
            except Held:out.append('HELD')
        threads=[threading.Thread(target=worker)for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(timeout=3);self.assertFalse(t.is_alive())
        self.assertEqual(out,['RESERVED','RESERVED']);self.assertEqual(self.ledger.snapshot()['charged_per_node'],UNITS)
    def test_bad_file_and_non_string_cohort_fail_closed(self):
        for value in (None,True,[]):
            with self.subTest(value=value),self.assertRaises(Held):self.reserve(cohort=value)
        self.path.write_bytes(b'not a SQLite ledger')
        with self.assertRaises(Held):Ledger(self.path,BINDING,CAPS)

    def test_caller_mutation_after_snapshot_does_not_change_reserved_binding(self):
        units=dict(UNITS);ready=threading.Event();changed=threading.Event()
        def mutate():
            if ready.wait(2):units['node-a']=9;changed.set()
        thread=threading.Thread(target=mutate);thread.start()
        def trace(frame,event,arg):
            if event=='line'and frame.f_code.co_name=='reserve'and 'Validate the detached snapshot'in linecache.getline(frame.f_code.co_filename,frame.f_lineno):
                ready.set();self.assertTrue(changed.wait(2))
            return trace
        sys.settrace(trace)
        try:self.assertEqual(self.reserve(units=units),'RESERVED')
        finally:sys.settrace(None);thread.join(timeout=3)
        self.assertFalse(thread.is_alive());self.assertEqual(units['node-a'],9)
        self.assertEqual(self.ledger.snapshot()['charged_per_node'],UNITS)
        self.assertEqual(self.reserve(units=UNITS),'RESERVED')

# Regression supplied by independent reviewer; original reproducer preserved separately.
class InputFreezeRace(unittest.TestCase):
 def test_mutated_input_must_not_return_reserved_or_corrupt_ledger(self):
  with tempfile.TemporaryDirectory()as directory:
   ledger=initialize_offline(Path(directory)/'ledger',Binding('target','a'*64,'b'*64,'revision','c'*32),{'node-a':10},offline=True)
   units={'node-a':6};ready=threading.Event();changed=threading.Event()
   def mutate():
    if ready.wait(2):units['node-a']=0;changed.set()
   thread=threading.Thread(target=mutate);thread.start()
   def trace(frame,event,arg):
    if event=='line'and frame.f_code.co_name=='reserve'and 'request = json.loads(canonical(request))'in linecache.getline(frame.f_code.co_filename,frame.f_lineno):
     ready.set();self.assertTrue(changed.wait(2))
    return trace
   sys.settrace(trace)
   try:
    with self.assertRaises(Held):ledger.reserve('intent',resource='client',cohort='active_web',units=units)
   finally:sys.settrace(None);thread.join(timeout=3)
   self.assertFalse(thread.is_alive());self.assertEqual(ledger.snapshot()['charged_per_node'],{'node-a':0});self.assertEqual(ledger.snapshot()['states'],{})

if __name__=='__main__':unittest.main()
