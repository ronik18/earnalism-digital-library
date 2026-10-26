"""Proof admission only: no publication, provider requests or owner credentials."""
import copy
import hashlib
import json
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import audiobook_active_release_v2 as manager

class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.playback={'descriptor':'a'*64,'packageVersion':'sha256-'+'b'*64,'durationMs':1000,'segmentCount':1,
            'coverage':[{'segment':'one','durationMatches':True,'ended':True,'startedFromBeginning':True}],
            'timestamps':[{'segment':'one','http':200,'sha256Matches':True}],
            'requests':[{'http':206}], 'ended':True,'sessionEndHTTP':200,'pauseResumeSeekPass':True}
        self.business={'status':'PRODUCTION_SPEED_CONCURRENCY_AND_SERVER_BILLING_PASS','speedsObserved':[1,1.25,1.5],
            'secondClientStart':{'http':409,'code':'SESSION_ACTIVE_ELSEWHERE'},'allServerClockIntervalsMatch':True,
            'pausedIntervalsDebitZero':True,'nonPlayingPriorIntervalsDebitZero':True,'balanceDifferenceMatchesDebit':True,
            'ended':True,'endHTTP':200,'simultaneousPaidPlayback':False}
        self.accounting={'status':'DEPLOYED_ACCOUNTING_AND_AUTHENTICATED_USAGE_VERIFIED','sourceCommit':'c'*40,
            'deployedCommit':'c'*40,'fractionalRenewalRegressionPass':True,'authenticatedUsagePaginationPass':True}
    def args(self):
        blobs={k:json.dumps(getattr(self,k)).encode() for k in ('playback','business','accounting')}
        return dict(descriptor='a'*64,package_version='sha256-'+'b'*64,duration_ms=1000,segment_ids=['one'],
            **{k+'_bytes':v for k,v in blobs.items()},expected_proof_hashes={k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()})
    def test_exact_complete_proofs_admit_without_activation(self):
        self.assertIs(manager.validate_new_title_publication_acceptance(**self.args())['public_activation_performed'],False)
    def test_changed_proof_bytes_fail_even_with_valid_json(self):
        args=self.args();args['business_bytes']+=b' '
        with self.assertRaises(manager.ReleasePointerError): manager.validate_new_title_publication_acceptance(**args)
    def test_each_missing_gate_fails(self):
        for role,key,value in [('playback','descriptor','d'*64),('playback','durationMs',999),('playback','ended',False),
                ('playback','coverage',[]),('playback','timestamps',[]),('playback','requests',[]),
                ('business','allServerClockIntervalsMatch',False),('business','speedsObserved',[1]),
                ('business','secondClientStart',{}),('accounting','deployedCommit','d'*40),
                ('accounting','authenticatedUsagePaginationPass',False),('accounting','fractionalRenewalRegressionPass',False)]:
            with self.subTest(role=role,key=key):
                original=copy.deepcopy(getattr(self,role));getattr(self,role)[key]=value
                with self.assertRaises(manager.ReleasePointerError):manager.validate_new_title_publication_acceptance(**self.args())
                setattr(self,role,original)
    def test_malformed_rows_fail(self):
        self.playback['coverage']=['not-a-record']
        with self.assertRaises(manager.ReleasePointerError):manager.validate_new_title_publication_acceptance(**self.args())

if __name__=='__main__':unittest.main()
