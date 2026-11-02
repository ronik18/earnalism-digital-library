"""Exact reviewed registry-pin successor; no publication, providers or new rights."""
import copy,hashlib,json,os,subprocess,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from scripts import catalogue_clearance_release_bindings as bindings
from backend.rights_decision_gate import record_sha256,evaluate_accepted_record

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE_ROOT=ROOT
REGISTRY='backend/data/rights_decision_registry.json'
REFERENCE='registry_sourceqa_successor_20261102'
PREDECESSOR='b4bc7585a87b7546db3270f3bfd63bd436e8585a'
CONTINUOUS='f5706d328e08ab330f65f604f51df322b65646f1'
CEDAR='c980ff2da048db7a164648f06f707440b2a8124c'
D2='d2dbc302427a535e5a3e89dfb82f0b9b880729ea6c56837fd9d9f18ea1077258'


def git_bytes(ref,path):
    return subprocess.check_output(['git','-c','remote.origin.promisor=false','show',ref+':'+path],cwd=ROOT,
        env={**os.environ,'GIT_NO_LAZY_FETCH':'1'},timeout=10)


def load_receipt(baseline):
    raw=(EVIDENCE_ROOT/baseline[REFERENCE]['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==baseline[REFERENCE]['sha256'], 'Registry successor receipt digest changed'
    return json.loads(raw)


class RegistrySuccessorTests(unittest.TestCase):
    def baseline(self):return bindings.load(ROOT/bindings.REVIEWED_AUTHORITY)

    def test_prior_authority_titles_pins_and_history_preserved_except_exact_registry_successor(self):
        baseline=self.baseline();receipt=load_receipt(baseline)
        old=git_bytes(PREDECESSOR,'internal/legal/catalogue_clearance_20261002/reviewed_release_authority_20261003.v1.json')
        self.assertEqual(hashlib.sha256(old).hexdigest(),receipt['predecessor_reviewed_authority']['sha256'])
        expected=json.loads(old)
        self.assertEqual(expected['authority_sha256'],receipt['predecessor_reviewed_authority']['authority_sha256'])
        expected['authority_sha256'][REGISTRY]=receipt['registry_history'][-1]['sha256']
        expected[REFERENCE]=baseline[REFERENCE]
        self.assertEqual(baseline,expected)  # Includes every title/component, old scope and historical field.
        self.assertEqual(bindings.sha(ROOT/REGISTRY),baseline['authority_sha256'][REGISTRY])
        self.assertEqual(len(baseline['titles']),52)
        self.assertEqual(baseline[REFERENCE]['predecessor_registry_sha256'],receipt['predecessor_reviewed_authority']['authority_sha256'][REGISTRY])
        self.assertEqual(baseline[REFERENCE]['reviewed_registry_sha256'],receipt['registry_history'][-1]['sha256'])
        for name,expected_sha in receipt['source_evidence_sha256'].items():self.assertEqual(bindings.sha(ROOT/name),expected_sha)

    def test_exact_two_step_additive_sourceqa_history_has_no_other_permission_changes(self):
        receipt=load_receipt(self.baseline());history=receipt['registry_history']
        self.assertEqual([row['commit'] for row in history],[PREDECESSOR,CONTINUOUS,CEDAR])
        versions=[]
        for row in history:
            raw=git_bytes(row['commit'],REGISTRY)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);versions.append(json.loads(raw))
        expected=copy.deepcopy(versions[0]);expected['accepted_records'].update(history[1]['added_accepted_records'])
        self.assertEqual(versions[1],expected)
        expected['accepted_records'].update(history[2]['added_accepted_records'])
        expected['audio_package_bindings']['the-selfish-giant'][D2]=history[2]['added_audio_package_bindings']['the-selfish-giant'][D2]
        self.assertEqual(versions[2],expected)
        self.assertEqual(json.loads((ROOT/REGISTRY).read_text()),expected)
        self.assertEqual(sum(len(row.get('added_accepted_records',{})) for row in history),3)
        self.assertEqual(history[2]['added_audio_package_bindings']['the-selfish-giant'][D2]['territories'],['IN'])
        self.assertEqual(history[2]['added_audio_package_bindings']['the-selfish-giant'][D2]['uses'],['audio_stream'])
        self.assertFalse(receipt['source_bound_scope']['storage_runtime_or_live_approval'])

    def test_added_hashes_resolve_only_exact_india_stream_sourceqa_records(self):
        source=ROOT/'internal/audiobook_lab/release_gate'
        retained=json.loads((source/'retained_master_derivative_adoptions.json').read_text())
        records=[row['record']['audio_use_decision'] for row in retained['adoptions']]
        records.append(json.loads((source/'selfish-giant-cedar-20261102/audio-use-decision.json').read_text()))
        receipt=load_receipt(self.baseline());expected={}
        for row in receipt['registry_history']:expected.update(row.get('added_accepted_records',{}))
        self.assertEqual({r['decision_id']:record_sha256(r) for r in records},expected)
        current=json.loads((ROOT/REGISTRY).read_text())
        for record in records:
            self.assertEqual(record['territories'],['IN']);self.assertEqual(record['uses'],['audio_stream'])
            for country,use,passed in [('IN','audio_stream',True),('US','audio_stream',False),('IN','audio_download',False)]:
                verdict=evaluate_accepted_record(record,edition_id=record['edition_id'],operator_id='reo-enterprise',
                    country=country,country_trusted=True,use=use,required_components=record['components'],
                    accepted_records=current['accepted_records'],revoked_decision_ids=frozenset(current['revoked_decision_ids']),
                    now=datetime(2026,11,2,tzinfo=timezone.utc))
                self.assertIs(verdict.passed,passed,(record['decision_id'],country,use,verdict.reasons))

    def test_current_exact_registry_pin_passes_unmodified_authority_assertion(self):
        self.assertEqual(bindings.assert_reviewed_authority(ROOT),self.baseline())

    def test_unreviewed_future_record_revocation_or_scope_change_still_denied(self):
        baseline=self.baseline()
        for mutation in ('extra-record','alter-prior-hash','revocation','wider-country','download'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);newpin=root/'baseline.json';newpin.write_text(json.dumps(baseline))
                for name in baseline['authority_sha256']:
                    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/name).read_bytes())
                registry=json.loads((root/REGISTRY).read_text())
                if mutation=='extra-record':registry['accepted_records']['unreviewed-test-record']='f'*64
                elif mutation=='alter-prior-hash':registry['accepted_records'][next(iter(registry['accepted_records']))]='f'*64
                elif mutation=='revocation':registry['revoked_decision_ids'].append('test-revocation')
                elif mutation=='wider-country':registry['audio_package_bindings']['the-selfish-giant'][D2]['territories'].append('US')
                else:registry['audio_package_bindings']['the-selfish-giant'][D2]['uses'].append('audio_download')
                (root/REGISTRY).write_text(json.dumps(registry))
                from unittest.mock import patch
                with patch.object(bindings,'REVIEWED_AUTHORITY',str(newpin)):
                    with self.assertRaisesRegex(AssertionError,'Unreviewed release authority change'):
                        bindings.assert_reviewed_authority(root)


if __name__=='__main__':unittest.main()
