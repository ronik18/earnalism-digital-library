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


class MirroredPromotionTests(AcceptanceTests):
    def test_isolated_dry_run_then_atomic_source_apply(self):
        import tempfile, shutil
        root_source=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory(prefix='publication-test-') as tmp:
            root=Path(tmp).resolve()
            for side in ['data','backend/data']:
                shutil.copytree(root_source/side/'controlled_publications/the-open-window',root/side/'controlled_publications/the-open-window')
                shutil.copy2(root_source/side/'controlled_launch.json',root/side/'controlled_launch.json')
            for name in ['rights_decision_registry.json','approved_reader_bootstrap.json']:
                shutil.copy2(root_source/'backend/data'/name,root/'backend/data'/name)
            # Reconstruct an isolated pre-publication canary from the retained
            # immutable package. Synthetic rights rebinding is fixture-only.
            from rights_decision_gate import record_sha256
            primary=root/'data/controlled_publications/the-open-window'
            base=json.loads((primary/'public_book.json').read_text())
            descriptor=base['audiobook_active_release']['active_release_descriptor_sha256']
            if not base['audiobook_active_release']['candidate_release_descriptor_sha256']:
                hidden=base['audiobook_hidden_release_descriptor_sha256']
                fields={'audio_enabled':False,'audiobook_enabled':False,
                    'audiobook_active_release':manager.build_active_release_state(slug='the-open-window',active_release_descriptor_sha256=hidden,
                        retained_release_descriptor_sha256s=[hidden,descriptor],candidate_release_descriptor_sha256=descriptor,rollout_percentage=5,rollout_salt='synthetic-test'),
                    'audiobook_package_canary':{**base['audiobook_package_canary'],'status':'PUBLIC_AUDIO_PACKAGE_CANARY_APPROVED'}}
                for side in ['data','backend/data']:
                    folder=root/side/'controlled_publications/the-open-window'
                    payloads={}
                    for filename in ['public_book.json','reader_manifest.json']:
                        doc=json.loads((folder/filename).read_text());doc.update(fields)
                        payloads[filename]=manager.json_bytes(doc);(folder/filename).write_bytes(payloads[filename])
                    checksum=manager._checksum_document(json.loads((folder/'checksum_manifest.json').read_text()),payloads,'2026-10-26T00:00:00Z')
                    (folder/'checksum_manifest.json').write_bytes(manager.json_bytes(checksum))
                record=json.loads((primary/'rights_decision.json').read_text())
                for name in ['public_book','reader_manifest','checksum_manifest']:record['components'][name]=hashlib.sha256((primary/(name+'.json')).read_bytes()).hexdigest()
                for side in ['data','backend/data']:(root/side/'controlled_publications/the-open-window/rights_decision.json').write_bytes(manager.json_bytes(record))
                registry=json.loads((root/'backend/data/rights_decision_registry.json').read_text());registry['accepted_records'][record['decision_id']]=record_sha256(record)
                (root/'backend/data/rights_decision_registry.json').write_bytes(manager.json_bytes(registry))
            prior_protected = json.loads((root/'data/controlled_launch.json').read_text()).get('protected_package_public_slugs', [])
            before={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file()}
            b=json.loads((root/'data/controlled_publications/the-open-window/public_book.json').read_text())
            descriptor=b['audiobook_active_release']['candidate_release_descriptor_sha256'];package=b['audiobook_packages'][descriptor]
            ids=[c['segment_id'] for t in package['tracks'] for c in t['chunks']]
            self.playback.update(descriptor=descriptor,packageVersion=package['package_version'],durationMs=package['duration_ms'],segmentCount=len(ids),
                coverage=[dict(segment=k,durationMatches=True,ended=True,startedFromBeginning=True) for k in ids],
                timestamps=[dict(segment=k,http=200,sha256Matches=True) for k in ids])
            blobs={k:json.dumps(getattr(self,k)).encode() for k in ['playback','business','accounting']}
            args=dict(**{k+'_bytes':v for k,v in blobs.items()},expected_proof_hashes={k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()},
                audio_rights={'decision_id':'india-20261020-the-open-window-corrected-v1-audio-owner-adopted','canonical_sha256':'7f00f2deb1d2ab014801e5154429983bb9198324d8a8c37e17e7cae5a1511cef','territories':['IN'],'use':'audio_stream'},
                decision_id='india-fixture-the-open-window-public',approved_by='SYNTHETIC_FIXTURE_ONLY',generated_at='2026-10-26T13:20:00Z')
            result=manager.promote_new_title_package(root,'the-open-window',**args)
            self.assertFalse(result['applied'])
            self.assertEqual(before,{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file()})
            result=manager.promote_new_title_package(root,'the-open-window',apply=True,**args)
            self.assertTrue(result['applied'])
            for name,digest in result['files'].items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
            public=json.loads((root/'data/controlled_publications/the-open-window/public_book.json').read_text())
            self.assertEqual(public['audiobook_active_release']['active_release_descriptor_sha256'],descriptor)
            self.assertTrue(public['audiobook_hidden_release_descriptor_sha256'])
            config=json.loads((root/'data/controlled_launch.json').read_text())
            self.assertIs(config['public_audio_exposure_enabled'],False)
            self.assertEqual(config['protected_package_public_slugs'], sorted(set(prior_protected) | {'the-open-window'}))
            with self.assertRaises(manager.ReleasePointerError):manager.promote_new_title_package(root,'the-open-window',apply=True,**args)

if __name__=='__main__':unittest.main()
