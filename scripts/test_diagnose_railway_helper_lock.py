"""Safe fixtures only; mock Cargo never creates real execution evidence."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from unittest.mock import Mock
import diagnose_railway_helper_lock as m

HERE=Path(__file__).parent
HELPER=HERE/'test_helpers/railway_archiver_v5710'
if not HELPER.exists(): HELPER=HERE.parent/'proposal/scripts/test_helpers/railway_archiver_v5710'
ORIGINAL=(HELPER/'Cargo.lock').read_bytes()
UPSTREAM=(HELPER/'upstream-Cargo.lock').read_bytes()


def render(d):
    lines=['version = 4\n']
    for p in d['package']:
        lines.append('[[package]]')
        for k,v in p.items(): lines.append(k+' = '+json.dumps(v))
        lines.append('')
    return ('\n'.join(lines)+'\n').encode()


class Candidate(unittest.TestCase):
    def setUp(self):self.d=tomllib.loads(ORIGINAL.decode())
    def validate(self):return m.validate_candidate(ORIGINAL,render(self.d),UPSTREAM)
    def package(self,name):return next(p for p in self.d['package'] if p['name']==name)
    def test_same_semantics_format_candidate_nonqualifying(self):
        r=self.validate();self.assertFalse(r['helper_executed']);self.assertTrue(r['requires_independent_review_and_source_pinning'])
    def test_dependency_reference_format_only(self):
        self.package('gzp')['dependencies']=[x.split()[0] if x.startswith('thiserror ') else x for x in self.package('gzp')['dependencies']]
        self.validate()
    def test_leaf_package_and_edges_pruned(self):
        leaf='adler2';self.d['package']=[p for p in self.d['package'] if p['name']!=leaf]
        for p in self.d['package']:
            if 'dependencies' in p:p['dependencies']=[x for x in p['dependencies'] if x.split()[0]!=leaf]
        self.assertEqual(self.validate()['candidate_registry_packages'],91)
    def test_new_version_denied(self):
        self.package('anyhow')['version']='99.0.0'
        with self.assertRaises(ValueError):self.validate()
    def test_new_checksum_denied(self):
        self.package('anyhow')['checksum']='0'*64
        with self.assertRaises(ValueError):self.validate()
    def test_new_source_denied(self):
        self.package('anyhow')['source']='git+https://example.invalid/repo'
        with self.assertRaises(ValueError):self.validate()
    def test_added_edge_denied(self):
        self.package('anyhow')['dependencies']=['tar']
        with self.assertRaises(ValueError):self.validate()
    def test_direct_pin_removal_denied(self):
        p=self.package(m.ROOT[0]);p['dependencies']=p['dependencies'][1:]
        with self.assertRaises(ValueError):self.validate()
    def test_root_version_changed_denied(self):
        self.package(m.ROOT[0])['version']='0.2.0'
        with self.assertRaises(ValueError):self.validate()
    def test_dangling_dependency_denied(self):
        self.d['package']=[p for p in self.d['package'] if p['name']!='adler2']
        with self.assertRaises(ValueError):self.validate()
    def test_upstream_change_denied(self):
        with self.assertRaises(ValueError):m.validate_candidate(ORIGINAL,ORIGINAL,UPSTREAM+b'\n')
    def test_duplicate_package_denied(self):
        self.d['package'].append(copy.deepcopy(self.package('anyhow')))
        with self.assertRaises(ValueError):self.validate()


class Diagnostic(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name).resolve();self.package=self.base/'source'
        shutil.copytree(HELPER,self.package)
        self.env={'GITHUB_ACTIONS':'true','GITHUB_EVENT_NAME':'pull_request','GITHUB_REPOSITORY':'ronik18/earnalism-digital-library','RUNNER_TEMP':str(self.base),'PATH':'/usr/bin:/bin','PROVIDER_SECRET':'MUST_NOT_TRANSFER'}
    def tearDown(self):self.temp.cleanup()
    def call(self,run):return m.diagnose(self.package,self.base/'diagnostic',run=run,env=self.env)
    def test_exact_conservative_command_no_backcopy_no_build(self):
        before=(self.package/'Cargo.lock').read_bytes()
        run=Mock(return_value=subprocess.CompletedProcess([],0,b'',b''));r=self.call(run)
        argv=run.call_args.args[0]
        self.assertEqual(argv[:4],['cargo','update','--offline','--workspace'])
        self.assertNotIn('PROVIDER_SECRET',run.call_args.kwargs['env'])
        self.assertEqual((self.package/'Cargo.lock').read_bytes(),before)
        self.assertTrue(r['source_inputs_unchanged']);self.assertFalse(r['helper_executed']);self.assertTrue(r['original_gate_must_remain_failed'])
        self.assertTrue((self.base/'diagnostic/diagnostic.json').exists())
    def test_offline_failure_persisted_without_raw_secret_output(self):
        run=Mock(return_value=subprocess.CompletedProcess([],101,b'',b'error: no matching package named `gzp` found\nPRIVATE_TOKEN'))
        r=self.call(run);self.assertEqual(r['status'],'OFFLINE_METADATA_UNAVAILABLE')
        self.assertEqual(r['missing_public_crate'],'gzp')
        self.assertNotIn('PRIVATE_TOKEN',(self.base/'diagnostic/diagnostic.json').read_text())
        self.assertTrue((self.base/'diagnostic/lock.diff').exists())
    def test_timeout_persisted(self):
        r=self.call(Mock(side_effect=subprocess.TimeoutExpired(['cargo'],120)))
        self.assertEqual(r['status'],'DIAGNOSTIC_FAILED_NOT_QUALIFIED')
        self.assertTrue((self.base/'diagnostic/diagnostic.json').exists())
    def test_untrusted_candidate_persisted_not_accepted(self):
        def run(argv,**kw):
            p=Path(kw['cwd'])/'Cargo.lock';p.write_text(p.read_text().replace('version = "1.0.95"','version = "99.0.0"'))
            return subprocess.CompletedProcess(argv,0,b'',b'')
        r=self.call(run);self.assertEqual(r['status'],'DIAGNOSTIC_FAILED_NOT_QUALIFIED')
        self.assertTrue((self.base/'diagnostic/candidate-Cargo.lock').exists())
    def test_quarantine_manifest_mutation_denied(self):
        def run(argv,**kw):
            p=Path(kw['cwd'])/'Cargo.toml';p.write_text(p.read_text()+'\n# changed\n');return subprocess.CompletedProcess(argv,0,b'',b'')
        self.assertEqual(self.call(run)['status'],'QUARANTINE_CODE_CHANGED_REJECTED')
    def test_local_and_dispatch_denied_before_subprocess(self):
        for key,value in [('GITHUB_ACTIONS','false'),('GITHUB_EVENT_NAME','workflow_dispatch')]:
            before=dict(self.env);self.env[key]=value;run=Mock()
            with self.assertRaises(ValueError):self.call(run)
            run.assert_not_called();self.env=before
    def test_output_escape_denied(self):
        with self.assertRaises(ValueError):m.diagnose(self.package,Path('/private/tmp/escaped-lock-output'),run=Mock(),env=self.env)


if __name__=='__main__':unittest.main()
