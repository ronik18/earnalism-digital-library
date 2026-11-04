"""Synthetic binding/provenance tests; no archive, provider or receipt is produced."""
import copy
import unittest
from scripts import india_release_provider_adapter as a


def legacy_fixture():
    binding={'source_sha':'a'*40,'source_delivery_sha256':'2'*64,
        'closed_server_sha256':'3'*64,'config_sha256':'1'*64}
    actual={**binding,'scope':'ACTUAL_PROVIDER_AND_SOURCE','action':'release_guarded_bootstrap',
        'deployment_id':'legacy-observed-deployment','guarded_backend_deployment_id':'legacy-observed-deployment',
        'retained_image_id':'legacy-observed-image','recovery_receipt_sha256':'5'*64,
        'closed_guest_status':503,'purchase_pause_proof':'MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503',
        **dict.fromkeys(('startup_complete','database_healthy','source_attestation_matches',
            'native_can_rollback','config_compatible','existing_reader_listener_preserved',
            'verify_refund_webhook_code_preserved'),True)}
    return binding,actual




def synthetic_archive_inputs(binding, payload):
    """In-memory unit schema fixture; no helper/archive/CI run occurred."""
    import hashlib,json
    producer='f'*40
    components={name:('SYNTHETIC COMPONENT '+name).encode() for name in a.HELPER_COMPONENTS}
    package=a.HELPER_PACKAGE
    pins={'upstream_tag':'v'+a.CLI_VERSIONS['railway'],
        'upstream_upload_sha256':hashlib.sha256(components[package+'upstream-upload.rs.txt']).hexdigest(),
        'exact_function_sha256':'4'*64,
        'upstream_lock_sha256':hashlib.sha256(components[package+'upstream-Cargo.lock']).hexdigest(),
        'derived_lock_sha256':hashlib.sha256(components[package+'Cargo.lock']).hexdigest(),
        'registry_package_closure':92,'runtime_scope':'EXACT_UPSTREAM_HELPER_ONLY_NOT_INSTALLED_CLI_OR_NATIVE_PROOF',
        'executed':False}
    components[package+'SOURCE-PINS.json']=json.dumps(pins,indent=2).encode()
    content=sorted(copy.deepcopy(payload['files']),key=lambda row:row['path'])
    members=[{**row,'mode':0o644} for row in content]
    report={'schema':a.HELPER_REPORT_SCHEMA,'scope':a.HELPER_REPORT_SCOPE,'helper_executed':True,
        'input_git_source_sha':binding['source_sha'],'controller_source_sha':producer,
        'observed_at':'2026-11-04T00:00:00+00:00',
        'ci_context':{'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'e'*40,
            'GITHUB_JOB':'synthetic-unit-context-only','GITHUB_REPOSITORY':'ronik18/earnalism-digital-library',
            'GITHUB_EVENT_NAME':'pull_request','actual_controller_sha':producer},
        'actual_toolchain':{'rustc':'rustc 1.85.0 synthetic unit field','cargo':'cargo 1.85.0 synthetic unit field'},
        'helper_binary_sha256':'6'*64,'harness_source_sha256':hashlib.sha256(components[package+'src/main.rs']).hexdigest(),
        'derived_lock_sha256':pins['derived_lock_sha256'],
        'source_pins_sha256':hashlib.sha256(components[package+'SOURCE-PINS.json']).hexdigest(),
        'upstream_function_sha256':pins['exact_function_sha256'],'upstream_module_sha256':pins['upstream_upload_sha256'],
        'upstream_lock_sha256':pins['upstream_lock_sha256'],'offline_export_report_sha256':'8'*64,
        'archive_command':['synthetic-helper','/producer/export/backend','/producer/export','/producer/out.tgz'],
        'archive_sha256':'7'*64,'archive_member_manifest_sha256':a.digest(content),
        'archive_member_modes_sha256':a.digest(members),'regular_members':len(members),'directory_members':1,
        'uncompressed_regular_bytes':sum(row['bytes'] for row in content),'members':members,
        'runtime_expected_sha256':binding['source_delivery_sha256'],'runtime_input_count':payload['runtime_input_count'],
        'root_ignore_sha256':payload.get('root_ignore_sha256'),
        'provider_git_sha':None,'provider_git_metadata_status':'NOT_OBSERVED_NO_PROVIDER_CALL',
        'native_archive_qualification':False,'provider_upload_performed':False,'runtime_qualification':False,'provider_writes':0}
    contract={'schema':a.PAIRED_INPUT_SCHEMA,'input_git_source_sha':binding['source_sha'],
        'expected_archive_helper_report_sha256':a.digest(report),
        'archive_member_manifest_sha256':a.digest(content),'archive_member_modes_sha256':a.digest(members),
        'helper_archive_sha256':report['archive_sha256']}
    modes={row['path']:{'mode':'100644','bytes':row['bytes'],'oid':'a'*40} for row in content}
    return contract,report,components,modes


def synthetic_component_tree(components, ref, name):
    import hashlib
    data=components[name]
    oid=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    return ('100644 blob '+oid+'\t'+name+'\0').encode()


def synthetic_native_lineage(binding, report):
    """In-memory test only; never persisted as an actual observation receipt."""
    contract=binding['paired_content_provenance'];dep='11111111-1111-4111-8111-111111111111'
    actual={'scope':'ACTUAL_PROVIDER_AND_SOURCE','action':'release_guarded_bootstrap',
        'source_sha':None,'input_git_source_sha':binding['source_sha'],'source_delivery_sha256':binding['source_delivery_sha256'],
        'closed_server_sha256':binding['closed_server_sha256'],'config_sha256':binding['config_sha256'],
        'runtime_sha256':binding['source_delivery_sha256'],'operation_id':a.operation_identity('release_guarded_bootstrap',binding),
        'deployment_id':dep,'guarded_backend_deployment_id':dep,'retained_image_id':'synthetic-image-identity-only',
        'recovery_receipt_sha256':'5'*64,'native_observation_receipt_sha256':'a'*64,
        'runtime_attestation_receipt_sha256':'b'*64,'provider_git_sha':None,'archive_helper_report':report,
        'closed_guest_status':503,'purchase_pause_proof':'MEASURED_EXACT_EARLY_RETURN_AND_ANONYMOUS_503',
        **dict.fromkeys(('startup_complete','database_healthy','source_attestation_matches','native_can_rollback',
            'config_compatible','existing_reader_listener_preserved','verify_refund_webhook_code_preserved'),True)}
    actual['paired_content_provenance']={'schema':a.PAIRED_LINEAGE_SCHEMA,
        'lineage_kind':'CONTENT_ARCHIVE_MEMBERS_AND_RUNTIME_ATTESTATION','operation_id':actual['operation_id'],
        'input_git_source_sha':binding['source_sha'],'operations_journal_identity_sha256':'c'*64,
        'deployment_id':dep,'retained_image_id':actual['retained_image_id'],
        'runtime_sha256':binding['source_delivery_sha256'],'config_sha256':binding['config_sha256'],
        'archive_helper_report_sha256':contract['expected_archive_helper_report_sha256'],
        'archive_member_manifest_sha256':contract['archive_member_manifest_sha256'],
        'archive_member_modes_sha256':contract['archive_member_modes_sha256'],
        'native_observation_receipt_sha256':actual['native_observation_receipt_sha256'],
        'runtime_attestation_receipt_sha256':actual['runtime_attestation_receipt_sha256'],
        'provider_git_sha':None}
    return actual


class RuntimeBindingTests(unittest.TestCase):
    def test_observed_runtime_must_equal_delivered_source(self):
        b,o=legacy_fixture();o['runtime_sha256']='9'*64
        with self.assertRaisesRegex(ValueError,'runtime differs'):a.qualify_bootstrap_recovery(b,o)
    def test_matching_observed_runtime_is_accepted_for_legacy(self):
        b,o=legacy_fixture();o['runtime_sha256']='2'*64
        self.assertEqual(a.qualify_bootstrap_recovery(b,o),'5'*64)
    def test_invalid_concrete_runtime_is_rejected(self):
        for value in ['0'*64,'short',True,123]:
            b,o=legacy_fixture();o['runtime_sha256']=value
            with self.subTest(value=value),self.assertRaises(ValueError):a.qualify_bootstrap_recovery(b,o)
    def test_legacy_omitted_runtime_shape_is_preserved(self):
        b,o=legacy_fixture();before=copy.deepcopy(o)
        self.assertEqual(a.qualify_bootstrap_recovery(b,o),'5'*64);self.assertEqual(o,before)
        self.assertNotIn('runtime_sha256',o)
    def test_legacy_unknown_runtime_shape_is_preserved(self):
        b,o=legacy_fixture();o['runtime_sha256']=None;before=copy.deepcopy(o)
        self.assertEqual(a.qualify_bootstrap_recovery(b,o),'5'*64);self.assertEqual(o,before)
    def test_equal_delivery_labels_do_not_override_measured_runtime(self):
        b,o=legacy_fixture();b['source_delivery_sha256']=o['source_delivery_sha256']='9'*64;o['runtime_sha256']='2'*64
        with self.assertRaises(ValueError):a.qualify_bootstrap_recovery(b,o)
    def test_paired_role_cannot_omit_actual_runtime(self):
        b,o=legacy_fixture();b['backend_export_root']='/synthetic/private-export';o.update(input_git_source_sha=b['source_sha'],source_sha=None)
        with self.assertRaisesRegex(ValueError,'actual measured runtime'):a.qualify_bootstrap_recovery(b,o)
    def test_paired_role_cannot_use_unknown_runtime(self):
        b,o=legacy_fixture();b['backend_export_root']='/synthetic/private-export';o.update(runtime_sha256=None,input_git_source_sha=b['source_sha'],source_sha=None)
        with self.assertRaisesRegex(ValueError,'actual measured runtime'):a.qualify_bootstrap_recovery(b,o)
    def test_existing_source_and_scope_requirements_remain_strict(self):
        for field,value in [('scope','LOCAL_FIXTURE'),('source_sha','b'*40),('action','release_backend')]:
            b,o=legacy_fixture();o[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):a.qualify_bootstrap_recovery(b,o)


class PairedContentProvenanceTests(unittest.TestCase):
    """Fake schema objects and local journal fixtures only; no actual helper/CI/provider."""
    def setUp(self):
        self.binding={'source_sha':'a'*40,'controller_source_sha':'c'*40,
            'source_root':'/synthetic/controller','backend_export_root':'/synthetic/export',
            'source_delivery_sha256':'2'*64,'closed_server_sha256':'3'*64,'config_sha256':'1'*64}
        self.payload={'source':'a'*40,'controller_source':'c'*40,'files':[
            {'path':'backend/inert.py','bytes':1,'sha256':'f'*64}],
            'runtime_expected_sha256':'2'*64,'runtime_input_count':1,'root_ignore_sha256':None}
        self.contract,self.report,self.components,self.modes=synthetic_archive_inputs(self.binding,self.payload)
        self.binding['paired_content_provenance']=self.contract
        self.actual=synthetic_native_lineage(self.binding,self.report)
    def component_tree(self,repo,*args):
        return synthetic_component_tree(self.components,args[2],args[-1])
    def mocks(self):
        from contextlib import ExitStack
        from unittest.mock import patch
        stack=ExitStack()
        stack.enter_context(patch('scripts.purchase_guard_source._git_blob',side_effect=lambda repo,ref,path:self.components[path]))
        stack.enter_context(patch('scripts.purchase_guard_source._git',side_effect=self.component_tree))
        stack.enter_context(patch('scripts.purchase_guard_source.backend_tree',return_value=self.modes))
        return stack
    def reseal_report(self):
        self.contract['expected_archive_helper_report_sha256']=a.digest(self.report)
    def preflight(self):
        with self.mocks():a.validate_paired_archive_input(self.binding,{'archive_helper_report':self.report},self.payload)
    def post(self):
        with self.mocks():return a.qualify_bootstrap_recovery(self.binding,self.actual,expected_journal_identity_sha256='c'*64)
    def test_valid_content_lineage_accepts_separately_absent_native_git(self):
        self.preflight();self.assertEqual(self.post(),'5'*64)
        self.assertIsNone(self.actual['provider_git_sha']);self.assertNotIn('uploaded_archive_sha256',self.actual['paired_content_provenance'])
    def test_old_producer_head_and_raw_input_hash_survive_later_operator_head(self):
        before=copy.deepcopy(self.report)
        self.binding['controller_source_sha']='d'*40;self.payload['controller_source']='d'*40
        self.binding['backend_payload_sha256']=a.digest(self.payload)
        self.preflight();self.assertEqual(self.report,before)
        self.assertNotEqual(self.report['controller_source_sha'],self.binding['controller_source_sha'])
        self.assertNotEqual(self.report['offline_export_report_sha256'],a.digest(self.payload))
    def test_actual_native_git_value_is_kept_distinct_from_input_source(self):
        self.actual['provider_git_sha']=self.actual['paired_content_provenance']['provider_git_sha']='d'*40
        self.assertEqual(self.post(),'5'*64);self.assertNotEqual(self.actual['provider_git_sha'],self.binding['source_sha'])
    def test_unexecuted_or_scope_broadened_helper_report_rejected(self):
        for key,value in [('helper_executed',False),('schema','local-proposal'),('scope','LOCAL_PROPOSAL'),
            ('native_archive_qualification',True),('provider_upload_performed',True),('runtime_qualification',True),
            ('provider_writes',1),('provider_git_sha','a'*40)]:
            original=self.report[key];self.report[key]=value;self.reseal_report()
            with self.subTest(key=key),self.assertRaises(ValueError):self.preflight()
            self.report[key]=original
        self.reseal_report()
    def test_raw_file_hash_cannot_replace_canonical_executed_receipt_digest(self):
        import hashlib,json
        self.contract['expected_archive_helper_report_sha256']=hashlib.sha256(json.dumps(self.report,indent=2).encode()).hexdigest()
        with self.assertRaises(ValueError):self.preflight()
    def test_changed_report_module_function_lock_or_binary_is_rejected(self):
        for key in ['harness_source_sha256','derived_lock_sha256','source_pins_sha256',
                    'upstream_module_sha256','upstream_lock_sha256','upstream_function_sha256','helper_binary_sha256']:
            original=self.report[key];self.report[key]='0'*64;self.reseal_report()
            with self.subTest(key=key),self.assertRaises(ValueError):self.preflight()
            self.report[key]=original
        self.reseal_report()
    def test_producer_context_cannot_be_relabelled_to_operator(self):
        self.report['ci_context']['actual_controller_sha']=self.binding['controller_source_sha'];self.reseal_report()
        with self.assertRaisesRegex(ValueError,'producer context'):self.preflight()
    def test_changed_consumed_producer_component_or_mode_is_rejected(self):
        from unittest.mock import patch
        original=self.component_tree
        def changed(repo,*args):
            raw=original(repo,*args)
            if args[2]==self.report['controller_source_sha'] and args[-1]=='scripts/execute_railway_helper_check.py':
                return raw.replace(b'100644',b'100755',1)
            return raw
        with self.mocks(),patch('scripts.purchase_guard_source._git',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'component identity'):a.validate_paired_archive_input(self.binding,{'archive_helper_report':self.report},self.payload)
    def test_changed_b_members_modes_runtime_and_filter_are_rejected(self):
        for role in ['member','mode','runtime','count','ignore']:
            report=copy.deepcopy(self.report);contract=copy.deepcopy(self.contract)
            if role=='member':self.report['members'][0]['sha256']='9'*64
            elif role=='mode':self.report['members'][0]['mode']=0o777
            elif role=='runtime':self.report['runtime_expected_sha256']='9'*64
            elif role=='count':self.report['runtime_input_count']=2
            else:self.report['root_ignore_sha256']='9'*64
            self.reseal_report()
            with self.subTest(role=role),self.assertRaises(ValueError):self.preflight()
            self.report.clear();self.report.update(report);self.contract.clear();self.contract.update(contract)
    def test_committed_mode_projection_cannot_be_changed_by_report_binding(self):
        self.modes['backend/inert.py']['mode']='100755'
        with self.assertRaisesRegex(ValueError,'committed B'):self.preflight()
    def test_duplicate_or_noncanonical_helper_members_cannot_be_approved(self):
        self.report['members'].append(copy.deepcopy(self.report['members'][0]))
        self.report['regular_members']=2;self.report['uncompressed_regular_bytes']=2
        self.report['archive_member_manifest_sha256']=self.contract['archive_member_manifest_sha256']=a.digest([{k:r[k] for k in ('path','bytes','sha256')} for r in self.report['members']])
        self.report['archive_member_modes_sha256']=self.contract['archive_member_modes_sha256']=a.digest(self.report['members'])
        self.reseal_report()
        with self.assertRaises(ValueError):self.preflight()
    def test_helper_only_receipt_cannot_qualify_native_bootstrap(self):
        self.actual.pop('paired_content_provenance')
        with self.assertRaisesRegex(ValueError,'native content lineage'):self.post()
    def test_operation_deployment_image_runtime_config_lineage_must_match(self):
        for key in ['operation_id','deployment_id','retained_image_id','runtime_sha256','config_sha256',
                    'archive_helper_report_sha256','archive_member_manifest_sha256','archive_member_modes_sha256']:
            original=self.actual['paired_content_provenance'][key];self.actual['paired_content_provenance'][key]='different'
            with self.subTest(key=key),self.assertRaises(ValueError):self.post()
            self.actual['paired_content_provenance'][key]=original
    def test_native_and_runtime_observation_receipts_are_required(self):
        for key in ['native_observation_receipt_sha256','runtime_attestation_receipt_sha256']:
            original=self.actual[key];self.actual.pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):self.post()
            self.actual[key]=original
    def test_missing_or_copied_native_git_metadata_is_not_assumed(self):
        original=self.actual.pop('provider_git_sha')
        with self.assertRaisesRegex(ValueError,'native Git metadata'):self.post()
        self.actual['provider_git_sha']=original
        self.actual['paired_content_provenance']['provider_git_sha']=self.binding['source_sha']
        with self.assertRaisesRegex(ValueError,'native Git metadata'):self.post()
    def test_helper_gzip_is_not_an_uploaded_archive_checksum(self):
        self.actual['paired_content_provenance']['uploaded_archive_sha256']=self.contract['helper_archive_sha256']
        with self.assertRaisesRegex(ValueError,'native content lineage'):self.post()
    def test_original_helper_evidence_must_match_if_postwrite_supplies_another(self):
        other=copy.deepcopy(self.report);other['archive_sha256']='9'*64
        with self.mocks(),self.assertRaisesRegex(ValueError,'original input'):
            a.qualify_bootstrap_recovery(self.binding,{**self.actual,'archive_helper_report':other},archive_helper_report=self.report,expected_journal_identity_sha256='c'*64)
    def test_paired_journal_keeps_original_helper_once_and_native_proof_separate(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            journal=Path(directory)/'operations';journal.mkdir(mode=0o700)
            op=a.operation_identity('release_guarded_bootstrap',self.binding)
            record={'operation_id':op,'action':'release_guarded_bootstrap','binding':self.binding,
                'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED',
                'operations_journal_identity_sha256':a._operation_journal_identity(journal),
                'paired_archive_helper_evidence':self.report,'started_at':'2026-11-03T00:00:00+00:00'}
            a._durable_json(journal/(op+'.json'),record)
            a._durable_json(journal/'_write-barrier.json',{'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'})
            actual=copy.deepcopy(self.actual);actual.update(outcome='APPLIED',receipt_sha256='6'*64);actual.pop('archive_helper_report')
            actual['paired_content_provenance']['operations_journal_identity_sha256']=record['operations_journal_identity_sha256']
            with self.mocks():out=a.ProviderAdapter(journal,observe=lambda *_:actual).reconcile(op)
            self.assertEqual(out['state'],'APPLIED_VERIFIED')
            self.assertEqual(out['paired_archive_helper_evidence'],self.report)
            proof=out['qualified_bootstrap_evidence'];self.assertNotIn('archive_helper_report',proof)
            self.assertIn('paired_content_provenance',proof);self.assertIsNone(proof['provider_git_sha'])
            with self.mocks():self.assertEqual(a.qualify_bootstrap_recovery(self.binding,proof,archive_helper_report=out['paired_archive_helper_evidence'],expected_journal_identity_sha256=out['operations_journal_identity_sha256']),'5'*64)
            changed=copy.deepcopy(proof);changed['runtime_sha256']='9'*64
            with self.mocks(),self.assertRaises(ValueError):a.qualify_bootstrap_recovery(self.binding,changed,archive_helper_report=out['paired_archive_helper_evidence'],expected_journal_identity_sha256=out['operations_journal_identity_sha256'])
    def test_legacy_journal_dictionaries_gain_no_paired_fields(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            journal=Path(directory)/'operations';journal.mkdir(mode=0o700)
            b,actual=legacy_fixture();op=a.operation_identity('release_guarded_bootstrap',b)
            a._durable_json(journal/(op+'.json'),{'operation_id':op,'action':'release_guarded_bootstrap',
                'binding':b,'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'})
            a._durable_json(journal/'_write-barrier.json',{'operation_id':op,'state':'INTENT_RECONCILE_BEFORE_RETRY'})
            actual.update(operation_id=op,outcome='APPLIED',receipt_sha256='6'*64)
            out=a.ProviderAdapter(journal,observe=lambda *_:actual).reconcile(op)
            self.assertNotIn('paired_archive_helper_evidence',out)
            for key in ['paired_content_provenance','provider_git_sha','native_observation_receipt_sha256']:
                self.assertNotIn(key,out['qualified_bootstrap_evidence'])

    def test_restore_revalidates_paired_original_proof_without_duplicating_helper_body(self):
        import tempfile
        from pathlib import Path
        from scripts.test_current_guarded_bootstrap_restore import fixture
        with tempfile.TemporaryDirectory() as directory:
            journal=Path(directory)/'operations';journal.mkdir(mode=0o700)
            restore,actual,boot,normal=fixture(journal)
            self.actual['paired_content_provenance']['operations_journal_identity_sha256']=boot['operations_journal_identity_sha256']
            proof={k:v for k,v in self.actual.items() if k!='archive_helper_report'}
            boot['binding']=copy.deepcopy(self.binding)
            boot['qualified_bootstrap_evidence']=proof
            boot['paired_archive_helper_evidence']=self.report
            boot['guarded_recovery_receipt_sha256']='5'*64
            path=journal/(boot['operation_id']+'.json');path.write_text(__import__('json').dumps(boot));path.chmod(0o600)
            context=restore['restore_context'];context['bootstrap_record_sha256']=a.digest(boot)
            context['target_retained_image_id']=proof['retained_image_id']
            actual['qualified_bootstrap_receipt']=proof
            actual['retained_bootstrap_native']['retained_image_id']=proof['retained_image_id']
            actual['retained_bootstrap_native'].pop('source_sha')
            actual['retained_bootstrap_native'].update(input_git_source_sha='a'*40,lineage_kind='CONTENT_ARCHIVE_MEMBERS_AND_RUNTIME_ATTESTATION',provider_git_sha=None)
            actual['guarded_restore_sha256']=a.digest(context)
            with self.mocks():self.assertEqual(a.validate_guarded_restore_context(journal,restore,actual),context)
            boot.pop('paired_archive_helper_evidence');path.write_text(__import__('json').dumps(boot));path.chmod(0o600)
            context['bootstrap_record_sha256']=a.digest(boot);actual['guarded_restore_sha256']=a.digest(context)
            with self.mocks(),self.assertRaises(ValueError):a.validate_guarded_restore_context(journal,restore,actual)

if __name__=='__main__':unittest.main()
