"""Exact reviewed registry-pin successor; no publication, providers or new rights."""
import base64,copy,hashlib,json,os,subprocess,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from scripts import catalogue_clearance_release_bindings as bindings
from backend.rights_decision_gate import record_sha256,evaluate_accepted_record

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE_ROOT=ROOT
REGISTRY='backend/data/rights_decision_registry.json'
REFERENCE='registry_sourceqa_successor_20261102'
OPEN_REFERENCE='open_window_scored_sourceqa_successor_20261102'
STAGE_REFERENCE='selfish_private_stage_authority_successor_20261102'
OPEN_STAGE_REFERENCE='open_window_private_stage_authority_successor_20261102'
SREDNI_REFERENCE='sredni_scored_sourceqa_successor_20261103'
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


def load_open_successor(baseline):
    raw=(EVIDENCE_ROOT/baseline[OPEN_REFERENCE]['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==baseline[OPEN_REFERENCE]['sha256'], 'Open scored registry review digest changed'
    successor=json.loads(raw)
    assert successor['schema']=='earnalism.reviewed_open_window_scored_registry_successor.v1'
    assert successor['predecessor']['registry_sha256']==load_receipt(baseline)['registry_history'][-1]['sha256']
    assert successor['publication_storage_or_runtime_approval'] is False
    return successor


def load_stage_successor(baseline):
    raw=(EVIDENCE_ROOT/baseline[STAGE_REFERENCE]['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==baseline[STAGE_REFERENCE]['sha256'], 'Private-stage review receipt changed'
    receipt=json.loads(raw)
    assert receipt['schema']=='earnalism.reviewed_selfish_private_stage_authority_successor.v1'
    assert receipt['runtime_grant_deployment_or_LIVE_approval'] is False
    for path,digest in receipt['predecessor_files'].items():
        assert hashlib.sha256((EVIDENCE_ROOT/path).read_bytes()).hexdigest()==digest, 'Private-stage predecessor changed'
    return receipt

def load_open_stage_successor(baseline):
    ref=baseline[OPEN_STAGE_REFERENCE];raw=(EVIDENCE_ROOT/ref['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ref['sha256'], 'Open private-stage review digest changed'
    receipt=json.loads(raw)
    assert receipt['schema']=='earnalism.reviewed_open_window_private_stage_authority_successor.v1'
    assert receipt['runtime_grant_deployment_or_LIVE_approval'] is False
    for path,digest in receipt['predecessor_files'].items():
        assert hashlib.sha256((EVIDENCE_ROOT/path).read_bytes()).hexdigest()==digest, 'Open private-stage predecessor changed'
    return receipt

def load_sredni_successor(baseline):
    ref=baseline[SREDNI_REFERENCE];raw=(EVIDENCE_ROOT/ref['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ref['sha256'], 'Sredni registry successor digest changed'
    r=json.loads(raw)
    assert r['schema']=='earnalism.reviewed_sredni_sourceqa_registry_successor.v1'
    assert r['active_publication_storage_runtime_grant_or_deployment'] is False
    assert r['predecessor_registry_sha256']==load_open_stage_successor(baseline)['reviewed_registry_sha256']
    assert hashlib.sha256((EVIDENCE_ROOT/r['preserved_predecessor_registry']).read_bytes()).hexdigest()==r['predecessor_registry_sha256']
    assert hashlib.sha256((EVIDENCE_ROOT/r['preserved_predecessor_authority']).read_bytes()).hexdigest()==r['predecessor_reviewed_authority_sha256']
    return r

def _add_sredni_sourceqa_registry(expected,baseline):
    if SREDNI_REFERENCE in baseline:
        r=load_sredni_successor(baseline)
        assert expected==json.loads((EVIDENCE_ROOT/r['preserved_predecessor_registry']).read_text()), 'Unexpected Sredni predecessor permissions'
        expected['accepted_records'].update(r['added_accepted_records'])
        for slug,bindings in r['added_audio_package_bindings'].items():
            expected['audio_package_bindings'].setdefault(slug,{}).update(bindings)
    return expected

def _add_sredni_sourceqa_baseline(expected,baseline):
    if SREDNI_REFERENCE in baseline:
        r=load_sredni_successor(baseline)
        assert expected==json.loads((EVIDENCE_ROOT/r['preserved_predecessor_authority']).read_text()), 'Unexpected Sredni predecessor authority'
        expected['authority_sha256'][REGISTRY]=r['reviewed_registry_sha256']
        expected[SREDNI_REFERENCE]=baseline[SREDNI_REFERENCE]
    return expected


def add_open_stage_registry(expected,baseline):
    if OPEN_STAGE_REFERENCE in baseline:
        r=load_open_stage_successor(baseline)
        archive=EVIDENCE_ROOT/r['preserved_shared_predecessor_files'][REGISTRY]
        assert expected==json.loads(archive.read_text()), 'Unexpected Open predecessor permissions'
        expected['accepted_records'].update(r['added_accepted_records'])
    return add_sredni_registry(expected,baseline)

def add_open_stage_baseline(expected,baseline):
    if OPEN_STAGE_REFERENCE in baseline:
        r=load_open_stage_successor(baseline)
        assert expected['titles'][r['title']]==r['predecessor_title_binding']
        assert expected['authority_sha256'][REGISTRY]==r['predecessor_registry_sha256']
        expected['authority_sha256'][REGISTRY]=r['reviewed_registry_sha256']
        expected['titles'][r['title']]=r['reviewed_title_binding']
        expected[OPEN_STAGE_REFERENCE]=baseline[OPEN_STAGE_REFERENCE]
    return add_sredni_baseline(expected,baseline)

def add_stage_registry(expected,baseline):
    if STAGE_REFERENCE in baseline:
        stage=load_stage_successor(baseline)
        archived=EVIDENCE_ROOT/'internal/legal/catalogue_clearance_20261002/selfish_private_stage_20261102/pre-stage-rights-registry.json'
        assert hashlib.sha256(archived.read_bytes()).hexdigest()==stage['predecessor_registry_sha256']
        assert expected==json.loads(archived.read_text()), 'Unexpected predecessor permissions'
        expected['accepted_records'].update(stage['added_accepted_records'])
    return add_open_stage_registry(expected,baseline)

def add_stage_baseline(expected,baseline):
    if STAGE_REFERENCE in baseline:
        stage=load_stage_successor(baseline)
        assert expected['titles'][stage['title']]==stage['predecessor_title_binding']
        expected['authority_sha256'][REGISTRY]=stage['reviewed_registry_sha256']
        expected['titles'][stage['title']]=stage['reviewed_title_binding']
        expected[STAGE_REFERENCE]=baseline[STAGE_REFERENCE]
    return add_open_stage_baseline(expected,baseline)


# Exact supported Sredni private-stage successor follows the preserved source-QA chain.

def _sredni_private_stage(baseline):
    ref=baseline['sredni_private_stage_authority_successor_20261103']
    raw=(EVIDENCE_ROOT/ref['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ref['sha256']
    r=json.loads(raw)
    assert r['schema']=='earnalism.reviewed_sredni_private_stage_authority_successor.v1'
    assert r['runtime_grant_deployment_or_LIVE_approval'] is False
    for path,want in r['predecessor_files'].items():
        assert hashlib.sha256((EVIDENCE_ROOT/path).read_bytes()).hexdigest()==want
    return r

def add_sredni_registry(expected,baseline):
    expected=_add_sredni_sourceqa_registry(expected,baseline)
    if 'sredni_private_stage_authority_successor_20261103' in baseline:
        r=_sredni_private_stage(baseline)
        assert expected==json.loads((EVIDENCE_ROOT/r['preserved_shared_predecessor_files'][REGISTRY]).read_text())
        expected['accepted_records'].update(r['added_accepted_records'])
    return expected

def add_sredni_baseline(expected,baseline):
    expected=_add_sredni_sourceqa_baseline(expected,baseline)
    if 'sredni_private_stage_authority_successor_20261103' in baseline:
        r=_sredni_private_stage(baseline)
        assert expected['titles'][r['title']]==r['predecessor_title_binding']
        assert expected['authority_sha256'][REGISTRY]==r['predecessor_registry_sha256']
        expected['authority_sha256'][REGISTRY]=r['reviewed_registry_sha256']
        expected['titles'][r['title']]=r['reviewed_title_binding']
        expected['sredni_private_stage_authority_successor_20261103']=baseline['sredni_private_stage_authority_successor_20261103']
    return expected


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
        if OPEN_REFERENCE in baseline:
            successor=load_open_successor(baseline)
            expected['authority_sha256'][REGISTRY]=successor['reviewed_registry_sha256']
            expected[OPEN_REFERENCE]=baseline[OPEN_REFERENCE]
        expected=add_stage_baseline(expected,baseline)
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
        if OPEN_REFERENCE in self.baseline():
            successor=load_open_successor(self.baseline())
            expected['accepted_records'].update(successor['added_accepted_records'])
            expected['audio_package_bindings']['the-open-window'].update(successor['added_audio_package_bindings']['the-open-window'])
        expected=add_stage_registry(expected,self.baseline())
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

    def test_open_scored_successor_only_exact_record_and_binding(self):
        baseline=self.baseline()
        self.assertIn(OPEN_REFERENCE,baseline)
        successor=load_open_successor(baseline)
        raw=git_bytes(successor['predecessor']['git_commit'],REGISTRY)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),successor['predecessor']['registry_sha256'])
        expected=json.loads(raw)
        source=ROOT/'internal/audiobook_lab/release_gate/open-window-scored-20261102'
        record=json.loads((source/'audio-use-decision.json').read_text())
        self.assertEqual(successor['added_accepted_records'],{record['decision_id']:record_sha256(record)})
        self.assertEqual(record['territories'],['IN']);self.assertEqual(record['uses'],['audio_stream'])
        self.assertEqual(record['valid_until'],'2036-10-02T00:00:00+00:00')
        expected['accepted_records'].update(successor['added_accepted_records'])
        expected['audio_package_bindings']['the-open-window'].update(successor['added_audio_package_bindings']['the-open-window'])
        expected=add_stage_registry(expected,self.baseline())
        self.assertEqual(json.loads((ROOT/REGISTRY).read_text()),expected)
        if STAGE_REFERENCE in baseline:
            stage=load_stage_successor(baseline)
            self.assertEqual(successor['reviewed_registry_sha256'],stage['predecessor_registry_sha256'])
            final=load_open_stage_successor(baseline)['reviewed_registry_sha256'] if OPEN_STAGE_REFERENCE in baseline else stage['reviewed_registry_sha256']
            if SREDNI_REFERENCE in baseline:final=load_sredni_successor(baseline)['reviewed_registry_sha256']
            if 'sredni_private_stage_authority_successor_20261103' in baseline:final=_sredni_private_stage(baseline)['reviewed_registry_sha256']
            self.assertEqual(bindings.sha(ROOT/REGISTRY),final)
        else:self.assertEqual(bindings.sha(ROOT/REGISTRY),successor['reviewed_registry_sha256'])
        for name,digest in successor['source_evidence_sha256'].items():self.assertEqual(bindings.sha(ROOT/name),digest)
        parent=json.loads(git_bytes(successor['predecessor']['git_commit'],bindings.REVIEWED_AUTHORITY))
        self.assertEqual(hashlib.sha256(git_bytes(successor['predecessor']['git_commit'],bindings.REVIEWED_AUTHORITY)).hexdigest(),successor['predecessor']['reviewed_authority_sha256'])
        parent['authority_sha256'][REGISTRY]=successor['reviewed_registry_sha256'];parent[OPEN_REFERENCE]=baseline[OPEN_REFERENCE]
        self.assertEqual(baseline,add_stage_baseline(parent,baseline))

    def test_actual_supported_private_stage_only_new_reader_record_and_exact14files(self):
        baseline=self.baseline();self.assertIn(STAGE_REFERENCE,baseline);receipt=load_stage_successor(baseline)
        folder=EVIDENCE_ROOT/'internal/legal/catalogue_clearance_20261002/selfish_private_stage_20261102'
        before=json.loads((folder/'pre-stage-rights-registry.json').read_text())
        oldbaseline=json.loads((folder/'pre-stage-reviewed-authority.json').read_text())
        snapshot=json.loads((folder/'prior-public-restore.snapshot.json').read_text())
        actual=json.loads((folder/'ACTUAL-PRIVATE-STAGE-RESULT.json').read_text())
        self.assertEqual(receipt['actual_transaction'],actual['transaction'])
        self.assertEqual(len(actual['transaction']['files']),14)
        for path,digest in actual['transaction']['files'].items():
            current=ROOT/path
            if OPEN_STAGE_REFERENCE in baseline and path in (REGISTRY,'backend/data/approved_reader_bootstrap.json'):
                current=EVIDENCE_ROOT/load_open_stage_successor(baseline)['preserved_shared_predecessor_files'][path]
            self.assertEqual(bindings.sha(current),digest)
        expected=copy.deepcopy(before);expected['accepted_records'].update(receipt['added_accepted_records'])
        self.assertEqual(json.loads((ROOT/REGISTRY).read_text()),add_open_stage_registry(expected,baseline))
        self.assertEqual(add_stage_baseline(oldbaseline,baseline),baseline)
        prior=json.loads(base64.b64decode(snapshot['files']['rights_decision.json']))
        current=json.loads((ROOT/'backend/data/controlled_publications/the-selfish-giant/rights_decision.json').read_text())
        self.assertEqual(receipt['added_accepted_records'],{current['decision_id']:record_sha256(current)})
        self.assertEqual(current['decision_id'],'india-20261102-the-selfish-giant-cedar-private-stage')
        for key in prior:
            if key not in ('decision_id','components','basis','evidence_sha256'):self.assertEqual(current[key],prior[key],key)
        self.assertEqual(receipt['reviewed_title_binding']['component_paths'],receipt['predecessor_title_binding']['component_paths'])
        for key,path in receipt['reviewed_title_binding']['component_paths'].items():self.assertEqual(current['components'][key],bindings.sha(ROOT/path))
        oldbook=json.loads(base64.b64decode(snapshot['files']['public_book.json']))
        newbook=json.loads((ROOT/'backend/data/controlled_publications/the-selfish-giant/public_book.json').read_text())
        for field in actual['old_public_fields_preserved']:self.assertEqual(newbook.get(field),oldbook.get(field),field)
        self.assertEqual(newbook['audiobook_native_replacement']['status'],'STAGED_PRIVATE')
        self.assertEqual(newbook['audiobook_active_release']['active_release_descriptor_sha256'],receipt['old_selected_public_audio_descriptor'])
        from backend.protected_package_publication import protected_package_publication_valid
        self.assertTrue(protected_package_publication_valid(newbook))
        bootstrap=json.loads((ROOT/'backend/data/approved_reader_bootstrap.json').read_text())
        row=[r for r in bootstrap['titles'] if r['slug']=='the-selfish-giant'][0]
        self.assertEqual(hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),actual['transaction']['target_bootstrap_row_sha256'])
        self.assertEqual(len(baseline['titles']),52)
        self.assertEqual(bindings.assert_current_reviewed_release(ROOT,'the-selfish-giant',baseline),ROOT/'backend/data/controlled_publications/the-selfish-giant')

    def test_sredni_sourceqa_adds_only_reviewed_india_stream_record_and_binding(self):
        baseline=self.baseline();r=load_sredni_successor(baseline)
        before=json.loads((ROOT/r['preserved_predecessor_registry']).read_text())
        expected=add_sredni_registry(copy.deepcopy(before),baseline)
        self.assertEqual(json.loads((ROOT/REGISTRY).read_text()),expected)
        record=json.loads((ROOT/'internal/audiobook_lab/release_gate/sredni-scored-20261103/prospective-registration/accepted-audio-use-decision.json').read_text())
        self.assertEqual(r['added_accepted_records'],{record['decision_id']:record_sha256(record)})
        self.assertEqual(len(r['added_audio_package_bindings']['sredni-vashtar']),1)
        descriptor=next(iter(r['added_audio_package_bindings']['sredni-vashtar']))
        self.assertEqual(descriptor,'dc53e6fdd5f74d71afbb56ea7b97c1484b781ffcceb12390b6546835e37336dc')
        for country,use,passed in [('IN','audio_stream',True),('US','audio_stream',False),('IN','audio_download',False)]:
            result=evaluate_accepted_record(record,edition_id='sredni-vashtar',operator_id='reo-enterprise',
                country=country,country_trusted=True,use=use,required_components=record['components'],
                accepted_records=expected['accepted_records'],revoked_decision_ids=frozenset(expected['revoked_decision_ids']),
                now=datetime(2026,11,4,tzinfo=timezone.utc))
            self.assertIs(result.passed,passed,(country,use,result.reasons))
        prior=json.loads((ROOT/r['preserved_predecessor_authority']).read_text())
        current_titles=copy.deepcopy(baseline['titles'])
        if 'sredni_private_stage_authority_successor_20261103' in baseline:
            stage=_sredni_private_stage(baseline)
            self.assertEqual(current_titles['sredni-vashtar'],stage['reviewed_title_binding'])
            current_titles['sredni-vashtar']=stage['predecessor_title_binding']
        self.assertEqual(prior['titles'],current_titles)
        self.assertEqual(len(prior['titles']),52)


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

    def test_open_private_stage_exact_reader_binding_without_public_or_scope_change(self):
        baseline=self.baseline();r=load_open_stage_successor(baseline)
        before=json.loads((EVIDENCE_ROOT/r['preserved_shared_predecessor_files'][REGISTRY]).read_text())
        expected=copy.deepcopy(before);expected['accepted_records'].update(r['added_accepted_records'])
        self.assertEqual(json.loads((ROOT/REGISTRY).read_text()),add_sredni_registry(expected,baseline))
        self.assertEqual(len(r['proposed_transaction']['files']),14)
        for path,digest in r['proposed_transaction']['files'].items():
            current=ROOT/path
            if SREDNI_REFERENCE in baseline and path==REGISTRY:
                current=EVIDENCE_ROOT/load_sredni_successor(baseline)['preserved_predecessor_registry']
            if 'sredni_private_stage_authority_successor_20261103' in baseline and path=='backend/data/approved_reader_bootstrap.json':
                current=EVIDENCE_ROOT/_sredni_private_stage(baseline)['preserved_shared_predecessor_files'][path]
            self.assertEqual(bindings.sha(current),digest)
        current=json.loads((ROOT/'backend/data/controlled_publications/the-open-window/rights_decision.json').read_text())
        self.assertEqual(r['added_accepted_records'],{current['decision_id']:record_sha256(current)})
        snapshot=json.loads((EVIDENCE_ROOT/'internal/legal/catalogue_clearance_20261002/open_window_private_stage_20261102/prior-public-restore.snapshot.json').read_text())
        prior=json.loads(base64.b64decode(snapshot['files']['rights_decision.json']))
        for key in prior:
            if key not in ('decision_id','components','basis','evidence_sha256'):self.assertEqual(current[key],prior[key],key)
        self.assertEqual(r['reviewed_title_binding']['component_paths'],r['predecessor_title_binding']['component_paths'])
        oldbook=json.loads(base64.b64decode(snapshot['files']['public_book.json']))
        book=json.loads((ROOT/'backend/data/controlled_publications/the-open-window/public_book.json').read_text())
        for field in ('audiobook_active_release','audiobook_public_package_approval','audiobook_publication_acceptance','audio_enabled','audiobook_enabled','chapters','content_hash'):
            self.assertEqual(book.get(field),oldbook.get(field),field)
        self.assertEqual(book['audiobook_native_replacement']['status'],'STAGED_PRIVATE')
        self.assertEqual(book['audiobook_active_release']['active_release_descriptor_sha256'],r['old_selected_public_audio_descriptor'])
        self.assertEqual(len(baseline['titles']),52)
        self.assertEqual(bindings.assert_current_reviewed_release(ROOT,'the-open-window',baseline),ROOT/'backend/data/controlled_publications/the-open-window')


    def test_sredni_private_stage_exact_record_and_actual_transaction(self):
        baseline=self.baseline();r=_sredni_private_stage(baseline)
        folder=EVIDENCE_ROOT/Path(baseline['sredni_private_stage_authority_successor_20261103']['path']).parent
        applied=json.loads((folder/'source-stage-APPLIED.json').read_text())
        self.assertTrue(applied['applied']);self.assertFalse(applied['public_audio_enabled'])
        self.assertEqual(len(applied['files']),12)
        for path,want in applied['files'].items():self.assertEqual(bindings.sha(ROOT/path),want)
        current=json.loads((ROOT/'backend/data/controlled_publications/sredni-vashtar/rights_decision.json').read_text())
        self.assertEqual(r['added_accepted_records'],{current['decision_id']:record_sha256(current)})
        snapshot=json.loads((folder/'source-stage-SNAPSHOT.private.json').read_text())
        old=json.loads(base64.b64decode(snapshot['files']['rights_decision.json']))
        for key,value in old.items():
            if key not in ('decision_id','components','basis','evidence_sha256'):self.assertEqual(current[key],value,key)
        raw=(ROOT/r['authority']['receipt_path']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),r['authority']['receipt_sha256'])
        self.assertEqual(bindings.assert_current_reviewed_release(ROOT,'sredni-vashtar',baseline),ROOT/'backend/data/controlled_publications/sredni-vashtar')

if __name__=='__main__':unittest.main()
