"""Exercise the checked-in CI admission in bounded disposable local Git clones."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from scripts.test_paired_bootstrap_source_export import PairFixture
from scripts import test_purchase_guard_source_successor as historical
from scripts import purchase_guard_source as guard

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which('git')


def history_parts():
    source = (ROOT / '.github/workflows/regression.yml').read_text()
    step = source.split('      - name: Fetch bounded reviewed catalogue history', 1)[1].split('\n      - name:', 1)[0]
    body = textwrap.dedent(step.split('        run: |\n', 1)[1])
    prefix = body.split('bindings=()', 1)[0]
    pair = body.split('# BEGIN bounded current guarded source pair admission\n', 1)[1].split('# END bounded current guarded source pair admission', 1)[0]
    blobs = body[body.index('missing_blobs=()'):]
    return prefix, pair, blobs


class HistoryFixture(PairFixture):
    def setUp(self):
        super().setUp()
        # New source-only protocol record is separate from immutable A/B/C.
        self.write_json(guard.PROTOCOL_PATH, {
            'schema': 'earnalism.purchase-protocol-application.v1',
            'scope': 'SOURCE_PROTOCOL_ONLY_NOT_NATIVE_RECOVERY', 'state': 'OPEN',
            'historical_contract_sha256': guard.sha((self.repo / guard.PATH).read_bytes()),
            'application_source_sha': self.historical,
            'application_server_sha256': guard.sha(self.normal),
            'application_closed_server_sha256': guard.sha(self.closed),
        })
        self.commit('fixture current source-only protocol, historical roles unchanged')

    def write(self, name, data):
        # Existing historical negative tests deliberately rename this async API.
        if (name == 'backend/server.py' and hasattr(self, 'normal')
                and data == self.normal and b'\ndef payments_verify(' in data):
            self.normal = self.normal.replace(b'\ndef payments_verify(', b'\nasync def payments_verify(')
            self.closed = guard.guard_only_server(guard.sha(self.normal), self.normal)
            data = self.normal
        return super().write(name, data)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = HistoryFixture(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.git('config', 'uploadpack.allowFilter', 'true')
        self.workspace = Path(self.fixture.tmp.name)
        self.commands = self.workspace / 'git-commands.jsonl'
        self.bin = self.workspace / 'bin'
        self.bin.mkdir()
        wrapper = self.bin / 'git'
        wrapper.write_text('#!' + sys.executable + '\n' + '''import json,os,sys
with open(os.environ['PAIR_GIT_COMMANDS'],'a') as stream:stream.write(json.dumps(sys.argv[1:])+'\\n')
if os.environ.get('PAIR_FAIL_TREE_METADATA')=='1' and 'fetch' in sys.argv and '--filter=tree:0' in sys.argv:
 sys.stderr.write('synthetic local metadata transport failure\\n');sys.exit(73)
os.execv(os.environ['PAIR_REAL_GIT'],[os.environ['PAIR_REAL_GIT'],*sys.argv[1:]])
''')
        wrapper.chmod(0o755)

    def descendants(self, count):
        for i in range(count):
            self.fixture.write('feature-notes.txt', str(i).encode())
            self.fixture.commit('fixture-only normal descendant')

    def merge_head(self):
        f = self.fixture
        feature = f.git('symbolic-ref', '--short', 'HEAD').decode().strip()
        f.git('switch', '-q', '-c', 'parallel-main-fixture', f.parent)
        f.write('mainline-notes.txt', b'fixture')
        f.commit('fixture-only parallel main')
        f.git('merge', '--no-ff', '-qm', 'fixture merge head', feature)

    def clone(self, *, prior=None):
        target = self.workspace / 'shallow-checkout'
        subprocess.run([GIT, 'clone', '-q', '--depth=1', 'file://' + str(self.fixture.repo), str(target)],
            capture_output=True, check=True, timeout=15)
        self.assertTrue((target / '.git/shallow').is_file())
        if prior:
            for key, value in prior.items():
                subprocess.run([GIT, 'config', '--local', key, value], cwd=target, check=True, timeout=10)
        return target

    @staticmethod
    def config(root):
        result = {}
        for key in ('remote.origin.promisor', 'remote.origin.partialclonefilter'):
            p = subprocess.run([GIT, 'config', '--local', '--get', key], cwd=root, capture_output=True, text=True, timeout=10)
            result[key] = p.stdout.strip() if p.returncode == 0 else None
        return result

    def run_admission(self, clone, *, pin=None, fail=False, source_only=False, reference=None, reference_tree=None, retained=None, retained_tree=None):
        prefix, pair, blobs = history_parts()
        script = prefix + '''
bindings=("$PAIR_HISTORICAL_PIN:backend/server.py")
pair_bootstrap_pin="$PAIR_BOOTSTRAP_PIN"
# Model the existing catalogue admission of exact role/historical commit trees.
git -c gc.auto=0 fetch --filter=blob:none --no-tags --depth=1 origin "$pair_bootstrap_pin" "$PAIR_HISTORICAL_PIN"
''' + pair + blobs + '''
printf '%s\\0' "${bindings[@]}" > "$PAIR_BINDINGS_RESULT"
'''
        env = {**os.environ, 'PATH': str(self.bin) + os.pathsep + os.environ['PATH'],
            'GIT_NO_LAZY_FETCH': '1', 'GIT_NO_REPLACE_OBJECTS': '1',
            'PAIR_REAL_GIT': GIT, 'PAIR_GIT_COMMANDS': str(self.commands),
            'PAIR_HISTORICAL_PIN': self.fixture.historical,
            'PAIR_BOOTSTRAP_PIN': pin or self.fixture.bootstrap,
            'PAIR_BINDINGS_RESULT': str(self.workspace / 'bindings-result'),
            'PAIR_SOURCE_ONLY': source_only if isinstance(source_only,str) else 'true' if source_only else 'false',
            'HISTORICAL_PAIR_CONTROLLER_SHA': reference or self.fixture.controller,
            'HISTORICAL_PAIR_CONTROLLER_TREE': reference_tree or self.fixture.git('rev-parse', (reference or self.fixture.controller)+'^{tree}').decode().strip(),
            'HISTORICAL_PAIR_BOOTSTRAP_SHA': self.fixture.bootstrap,
            'HISTORICAL_PAIR_APPLICATION_SHA': json.loads(self.fixture.git('show',self.fixture.controller+':'+guard.PATH))['application_source_sha'],
            'RETAINED_PAIR_CONTROLLER_SHA': retained or self.fixture.git('rev-parse','HEAD').decode().strip(),
            'RETAINED_PAIR_CONTROLLER_TREE': retained_tree or self.fixture.git('rev-parse',(retained or 'HEAD')+'^{tree}').decode().strip(),
            'PAIR_FAIL_TREE_METADATA': '1' if fail else '0'}
        result = subprocess.run(['bash', '-c', script], cwd=clone, env=env,
            capture_output=True, text=True, timeout=30)
        commands = [json.loads(line) for line in self.commands.read_text().splitlines()]
        return result, commands

    def assert_exact_body_fetches(self, commands, *, historical_reference=False):
        f = self.fixture
        expected = {f.git('rev-parse', ref + ':' + path).decode().strip()
            for ref, path in [(f.bootstrap, 'backend/server.py'),
                              (f.bootstrap, 'backend/.runtime-source-manifest.json'),
                              (f.bootstrap, guard.PATH), (f.parent, guard.PATH)]}
        body_fetches = [args for args in commands if 'fetch' in args
                        and not any(x.startswith('--filter=') for x in args)]
        self.assertEqual(len(body_fetches), 1)
        self.assertEqual(set(body_fetches[0][body_fetches[0].index('origin') + 1:]), expected)
        for args in commands:
            self.assertNotIn('--unshallow', args)
            self.assertNotIn('--all', args)
        self.assertEqual(sum('--filter=tree:0' in args for args in commands), 1)
        self.assertEqual(sum('--refetch' in args for args in commands), 2 if historical_reference else 1)

    def test_shallow_merge_head_hydrates_only_exact_bodies_and_runs_six_historical_cases(self):
        self.descendants(2)
        self.merge_head()
        clone = self.clone()
        before = self.config(clone)
        result, commands = self.run_admission(clone)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config(clone), before)
        self.assert_exact_body_fetches(commands)
        refs = (self.workspace / 'bindings-result').read_bytes().split(b'\0')
        self.assertIn((self.fixture.bootstrap + ':backend/.runtime-source-manifest.json').encode(), refs)
        self.assertIn((self.fixture.parent + ':' + guard.PATH).encode(), refs)
        with patch.object(historical, 'ROOT', clone):
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(historical.SuccessorContractTests)
            nested = unittest.TestResult()
            suite.run(nested)
        self.assertEqual(nested.testsRun, 6)
        self.assertTrue(nested.wasSuccessful(), str(nested.errors + nested.failures))

    def test_new_application_source_ci_does_not_claim_historical_recovery(self):
        self.fixture.write('backend/later_reviewed_application.py', b'fixture-only new application')
        self.fixture.commit('later application candidate is not historical A')
        # Protocol unit evidence stays valid; native full-backend recovery does not.
        guard.validate_purchase_protocol_source(self.fixture.repo)
        with self.assertRaisesRegex(ValueError, 'backend differs'):
            guard.validate(self.fixture.repo)
        clone = self.clone()
        result, commands = self.run_admission(clone, source_only=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('HISTORICAL_PAIR_ONLY_NOT_CURRENT_BACKEND_RECOVERY_QUALIFICATION', result.stdout)
        self.assert_exact_body_fetches(commands, historical_reference=True)
        self.assert_historical_controller_export(clone)

    def assert_historical_controller_export(self, clone):
        workflow = (ROOT / '.github/workflows/regression.yml').read_text()
        code = workflow.split("          python3 - <<'PYEXPORT'\n", 1)[1].split('\n          PYEXPORT', 1)[0]
        code = textwrap.dedent(code)
        original = Path.cwd()
        env = {'HISTORICAL_PAIR_CONTROLLER_SHA':self.fixture.controller,
               'HISTORICAL_PAIR_CONTROLLER_TREE':self.fixture.git('rev-parse', self.fixture.controller+'^{tree}').decode().strip(),
               'HISTORICAL_PAIR_BOOTSTRAP_SHA':self.fixture.bootstrap,'HISTORICAL_PAIR_APPLICATION_SHA':json.loads(self.fixture.git('show',self.fixture.controller+':'+guard.PATH))['application_source_sha'],'RUNNER_TEMP':str(self.workspace),
               'RETAINED_PAIR_CONTROLLER_SHA':getattr(self,'retained_controller',self.fixture.git('rev-parse','HEAD').decode().strip()),
               'RETAINED_PAIR_CONTROLLER_TREE':self.fixture.git('rev-parse',getattr(self,'retained_controller','HEAD')+'^{tree}').decode().strip()}
        (self.workspace/'paired-helper-proof').mkdir()
        from scripts.purchase_guard_source import validate_paired_source
        namespace = {'Path':Path,'os':os,'json':json,'validate_paired_source':validate_paired_source}
        with patch.dict(os.environ, env):
            try:
                os.chdir(clone)
                exec(compile(code, 'actual-workflow-historical-controller', 'exec'), namespace)
            finally:
                os.chdir(original)
        current = self.fixture.git('rev-parse','HEAD').decode().strip()
        context = json.loads((self.workspace/'paired-helper-proof/historical-context.json').read_text())
        self.assertEqual(context['ci_checkout_sha'], current)
        self.assertEqual(context['historical_controller_sha'],self.fixture.controller)
        self.assertFalse(context['current_candidate_recovery_qualified'])
        self.assertNotEqual(current,self.fixture.controller)
        report=json.loads((self.workspace/'paired-helper-proof/offline-export-report.json').read_text())
        self.assertEqual(report['controller_source'],self.fixture.controller)
        self.assertEqual(report['source'],self.fixture.bootstrap)
        self.assertFalse(report['native_archive_qualification'])

    def test_new_current_pair_and_old_helper_pair_are_admitted_separately(self):
        f=self.fixture
        f.write_json(guard.PATH,f.contract)
        f.write('backend/current-only-fixture.py',b'current source must survive')
        f.inventory();f.commit('new inventoried normal parent')
        current_normal_manifest=(f.repo/'backend/.runtime-source-manifest.json').read_bytes()
        f.write('backend/server.py',f.closed)
        f.write_json(guard.PATH,{**f.contract,'state':'CLOSED'})
        f.inventory();current_bootstrap=f.commit('new separate CLOSED child')
        f.write('backend/server.py',f.normal)
        f.write('backend/.runtime-source-manifest.json',current_normal_manifest)
        f.write_json(guard.PATH,{**f.paired,'guarded_bootstrap_source_sha':current_bootstrap})
        current_controller=f.commit('new controller, historical helper untouched')
        guard.validate_paired_source(f.repo)
        self.retained_controller=current_controller
        f.write('backend/diagnostic-only-fixture.py',b'new diagnostic is not retained recovery')
        f.inventory();f.commit('source-only diagnostic successor')
        with self.assertRaisesRegex(ValueError,'backend differs'):
            guard.validate_paired_source(f.repo)
        clone=self.clone()
        invalid,invalid_commands=self.run_admission(clone,pin=current_bootstrap,source_only='invalid')
        self.assertNotEqual(invalid.returncode,0)
        self.assertFalse(any('fetch' in x and not any(y.startswith('--filter=') for y in x) for x in invalid_commands))
        result,commands=self.run_admission(clone,pin=current_bootstrap,source_only=True,retained=current_controller)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('CURRENT_PAIR_SOURCE_AND_SEPARATE_HISTORICAL_HELPER_NOT_NATIVE_QUALIFICATION',result.stdout)
        self.assert_historical_controller_export(clone)
        current=json.loads((self.workspace/'paired-helper-proof/current-source-pair.json').read_text())
        self.assertEqual(current['controller_source_sha'],current_controller)
        self.assertEqual(current['bootstrap_source_sha'],current_bootstrap)
        self.assertEqual(current['scope'],'SOURCE_ONLY_NOT_PROVIDER_OR_APPROVAL_QUALIFICATION')
        context=json.loads((self.workspace/'paired-helper-proof/retained-context.json').read_text())
        self.assertNotEqual(context['ci_checkout_sha'],current_controller)
        self.assertFalse(context['current_candidate_recovery_qualified'])
        self.assertFalse(context['current_candidate_or_provider_recovery_qualified'])
        workflow=(ROOT/'.github/workflows/regression.yml').read_text()
        code=textwrap.dedent(workflow.split("            python3 - <<'PYCURRENTEXPORT'\n",1)[1].split('\n          PYCURRENTEXPORT',1)[0])
        original=Path.cwd()
        try:
            os.chdir(clone)
            with patch.dict(os.environ,{'RUNNER_TEMP':str(self.workspace),'RETAINED_PAIR_CONTROLLER_SHA':current_controller}):exec(compile(code,'actual-workflow-current-closed-export','exec'),{})
        finally:os.chdir(original)
        prepared=json.loads((self.workspace/'paired-helper-proof/current-offline-export-report.json').read_text())
        self.assertEqual(prepared['source'],current_bootstrap)
        self.assertEqual(prepared['controller_source'],current_controller)
        self.assertEqual(prepared['runtime_expected_sha256'],current['closed_runtime_sha256'])
        self.assertEqual(prepared['scope'],'OFFLINE_EXACT_COMMITTED_EXPORT_NOT_NATIVE_ARCHIVE_OR_PROVIDER_UPLOAD')
        self.assertFalse(prepared['native_archive_qualification']);self.assertEqual(prepared['provider_writes'],0)
        self.assertIn('backend/current-only-fixture.py',{x['path'] for x in prepared['files']})
        self.assertFalse(any('--all' in x or '--unshallow' in x for x in commands))

    def successor_pair_with_diagnostic(self):
        f=self.fixture
        f.write_json(guard.PATH,f.contract)
        f.write('backend/retained-feature.py',b'retained normal source')
        f.inventory();f.commit('retained normal parent')
        normal_manifest=(f.repo/'backend/.runtime-source-manifest.json').read_bytes()
        f.write('backend/server.py',f.closed)
        f.write_json(guard.PATH,{**f.contract,'state':'CLOSED'})
        f.inventory();bootstrap=f.commit('retained closed child')
        f.write('backend/server.py',f.normal)
        f.write('backend/.runtime-source-manifest.json',normal_manifest)
        f.write_json(guard.PATH,{**f.paired,'guarded_bootstrap_source_sha':bootstrap})
        controller=f.commit('retained controller')
        f.write('backend/diagnostic.py',b'diagnostic candidate')
        f.inventory();f.commit('candidate differs from retained recovery')
        return bootstrap,controller

    def assert_retained_ancestry_rejection(self, bootstrap, controller):
        clone=self.clone(prior={'remote.origin.promisor':'false',
                                'remote.origin.partialclonefilter':'blob:limit=1024'})
        before=self.config(clone)
        result,commands=self.run_admission(clone,pin=bootstrap,source_only=True,
            retained=controller)
        self.assertEqual(result.returncode,1,result.stderr)
        ancestry=[args for args in commands if 'merge-base' in args]
        self.assertTrue(ancestry)
        self.assertEqual(ancestry[-1][-4:],
            ['merge-base','--is-ancestor',controller,'HEAD'])
        # A rejection at this boundary must precede A/B body hydration.
        self.assertFalse(any('fetch' in args and '--depth=2' in args for args in commands))
        self.assertFalse(any('fetch' in args and not any(x.startswith('--filter=') for x in args)
                             for args in commands))
        self.assertFalse(any('--all' in args or '--unshallow' in args for args in commands))
        self.assertEqual(self.config(clone),before)

    def test_unrelated_retained_controller_with_matching_custody_is_rejected(self):
        bootstrap,controller=self.successor_pair_with_diagnostic()
        f=self.fixture
        candidate_branch=f.git('symbolic-ref','--short','HEAD').decode().strip()
        f.git('switch','-q','-c','unrelated-retained-controller',controller)
        f.write('sibling-only-note.txt',b'valid retained pair on a sibling branch')
        unrelated=f.commit('sibling retained controller, custody unchanged')
        # The retained pair itself is valid; only its candidate ancestry is wrong.
        guard.validate_paired_source(f.repo)
        f.git('switch','-q',candidate_branch)
        for path in (guard.PATH,f.receipt_path):
            self.assertEqual(f.git('show',unrelated+':'+path),f.git('show','HEAD:'+path))
        self.assert_retained_ancestry_rejection(bootstrap,unrelated)

    def test_retained_controller_beyond_bounded_candidate_history_is_rejected(self):
        bootstrap,controller=self.successor_pair_with_diagnostic()
        self.descendants(70)
        # It is a true ancestor in the complete fixture, but the bounded clone
        # must fail closed rather than expanding or retrying history admission.
        self.fixture.git('merge-base','--is-ancestor',controller,'HEAD')
        self.assert_retained_ancestry_rejection(bootstrap,controller)

    def test_retained_tree_mismatch_is_rejected(self):
        bootstrap,controller=self.successor_pair_with_diagnostic()
        result,_=self.run_admission(self.clone(),pin=bootstrap,source_only=True,
            retained=controller,retained_tree='0'*40)
        self.assertNotEqual(result.returncode,0)

    def test_changed_owner_custody_is_rejected(self):
        bootstrap,controller=self.successor_pair_with_diagnostic()
        self.fixture.write(self.fixture.receipt_path,b'{}')
        self.fixture.commit('unapproved receipt substitution')
        result,_=self.run_admission(self.clone(),pin=bootstrap,source_only=True,retained=controller)
        self.assertNotEqual(result.returncode,0)

    def test_changed_contract_custody_is_rejected(self):
        bootstrap,controller=self.successor_pair_with_diagnostic()
        contract=json.loads((self.fixture.repo/guard.PATH).read_text())
        self.fixture.write_json(guard.PATH,{**contract,'application_server_sha256':'0'*64})
        self.fixture.commit('unapproved contract substitution')
        result,_=self.run_admission(self.clone(),pin=bootstrap,source_only=True,retained=controller)
        self.assertNotEqual(result.returncode,0)

    def test_retained_controller_cannot_bypass_manual_release_equality(self):
        bootstrap,controller=self.successor_pair_with_diagnostic()
        result,_=self.run_admission(self.clone(),pin=bootstrap,source_only=False,retained=controller)
        self.assertNotEqual(result.returncode,0)

    def test_distinct_historical_application_body_is_explicitly_hydrated(self):
        f=self.fixture
        f.normal += b'\ndef safe_new_fixture_feature():\n    return 1\n'
        f.closed=guard.guard_only_server(guard.sha(f.normal),f.normal)
        f.write('backend/server.py',f.normal);f.inventory()
        application=f.commit('distinct historical application body')
        f.contract={**f.contract,'application_source_sha':application,'application_server_sha256':guard.sha(f.normal),'application_closed_server_sha256':guard.sha(f.closed)}
        f.write_json(guard.PATH,f.contract);f.parent=f.commit('historical normal parent with distinct application')
        f.normal_manifest=(f.repo/'backend/.runtime-source-manifest.json').read_bytes()
        f.write('backend/server.py',f.closed);f.write_json(guard.PATH,{**f.contract,'state':'CLOSED'});f.inventory();f.bootstrap=f.commit('historical closed role')
        f.write('backend/server.py',f.normal);f.write('backend/.runtime-source-manifest.json',f.normal_manifest)
        f.paired={**f.contract,'schema':guard.PAIRED_SCHEMA,'guarded_bootstrap_source_sha':f.bootstrap}
        f.write_json(guard.PATH,f.paired);f.controller=f.commit('historical helper role with distinct application')
        self.descendants(1)
        clone=self.clone();result,commands=self.run_admission(clone,source_only=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn((application+':backend/server.py').encode(),(self.workspace/'bindings-result').read_bytes().split(b'\0'))
        self.assert_historical_controller_export(clone)
        self.assertFalse(any('--all' in x or '--unshallow' in x for x in commands))

    def test_wrong_historical_controller_role_is_rejected(self):
        clone = self.clone()
        result, commands = self.run_admission(clone, source_only=True, reference=self.fixture.parent)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('fetch' in args and not any(x.startswith('--filter=') for x in args) for args in commands))

    def test_wrong_historical_tree_is_rejected(self):
        clone = self.clone()
        result, commands = self.run_admission(clone, source_only=True, reference_tree='0'*40)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('fetch' in args and not any(x.startswith('--filter=') for x in args) for args in commands))

    def test_manual_release_still_rejects_new_application_against_old_recovery(self):
        self.fixture.write('backend/later_reviewed_application.py', b'fixture-only new application')
        self.fixture.commit('later application cannot borrow old native recovery')
        clone = self.clone()
        result, commands = self.run_admission(clone, source_only=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('fetch' in args and not any(x.startswith('--filter=') for x in args) for args in commands))

    def test_existing_filter_config_restored_exactly_on_success(self):
        clone = self.clone(prior={'remote.origin.promisor': 'false',
                                  'remote.origin.partialclonefilter': 'blob:limit=1024'})
        before = self.config(clone)
        result, _ = self.run_admission(clone)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config(clone), before)

    def test_transport_failure_stops_without_retry_and_restores_config(self):
        clone = self.clone(prior={'remote.origin.promisor': 'true',
                                  'remote.origin.partialclonefilter': 'blob:none'})
        before = self.config(clone)
        result, commands = self.run_admission(clone, fail=True)
        self.assertEqual(result.returncode, 73)
        self.assertEqual(self.config(clone), before)
        self.assertEqual(sum('--filter=tree:0' in args for args in commands), 1)
        self.assertFalse(any('fetch' in args and not any(x.startswith('--filter=') for x in args) for args in commands))

    def test_over_bound_history_is_rejected_without_bulk_fallback(self):
        self.descendants(70)
        clone = self.clone()
        result, commands = self.run_admission(clone)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum('--filter=tree:0' in args for args in commands), 1)
        self.assertFalse(any('fetch' in args and not any(x.startswith('--filter=') for x in args) for args in commands))
        self.assertEqual(self.config(clone), {'remote.origin.promisor': None, 'remote.origin.partialclonefilter': None})

    def test_extra_closed_path_rejected_before_body_hydration(self):
        f = self.fixture
        f.git('switch', '-q', '-c', 'bad-extra-path-fixture', f.parent)
        f.write('backend/server.py', f.closed)
        f.write_json(guard.PATH, {**f.contract, 'state': 'CLOSED'})
        f.inventory()
        f.write('backend/unrelated.py', b'not admitted')
        f.bootstrap = f.commit('bad extra path B')
        f.write('backend/server.py', f.normal)
        f.write('backend/.runtime-source-manifest.json', f.normal_manifest)
        (f.repo / 'backend/unrelated.py').unlink()
        f.write_json(guard.PATH, {**f.paired, 'guarded_bootstrap_source_sha': f.bootstrap})
        f.commit('normal C for negative metadata test')
        clone = self.clone()
        result, commands = self.run_admission(clone)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('fetch' in args and not any(x.startswith('--filter=') for x in args) for args in commands))

    def test_two_parent_bootstrap_rejected_before_body_hydration(self):
        f = self.fixture
        tree = f.git('rev-parse', f.bootstrap + '^{tree}').decode().strip()
        merge = subprocess.check_output([GIT, 'commit-tree', tree, '-p', f.parent,
            '-p', f.historical], cwd=f.repo, input=b'isolated two-parent bootstrap fixture\n', timeout=10).decode().strip()
        f.git('switch', '-q', '-c', 'two-parent-bootstrap-fixture', merge)
        f.write('backend/server.py', f.normal)
        f.write('backend/.runtime-source-manifest.json', f.normal_manifest)
        f.bootstrap = merge
        f.write_json(guard.PATH, {**f.paired, 'guarded_bootstrap_source_sha': merge})
        f.commit('normal C for two-parent negative')
        clone = self.clone()
        result, commands = self.run_admission(clone)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('fetch' in args and not any(x.startswith('--filter=') for x in args) for args in commands))

    def test_nonancestor_is_rejected_without_body_hydration(self):
        f = self.fixture
        branch = f.git('symbolic-ref', '--short', 'HEAD').decode().strip()
        f.git('switch', '-q', '-c', 'unrelated-source-fixture', f.parent)
        f.write('unrelated-commit.txt', b'fixture')
        rogue = f.commit('unrelated exact source')
        f.git('switch', '-q', branch)
        clone = self.clone()
        result, commands = self.run_admission(clone, pin=rogue)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any('fetch' in args and not any(x.startswith('--filter=') for x in args) for args in commands))

    def test_selector_retains_existing_gates_and_adds_both_bridge_suites(self):
        source = (ROOT / 'scripts/run_pr_regression_gates.sh').read_text()
        for module in ('scripts.test_india_release_provider_adapter', 'scripts.test_startup_dispatch_qualification',
                       'scripts.test_backend_upload_payload', 'scripts.test_guarded_release_controller',
                       'scripts.test_provider_journal_durability', 'scripts.test_paired_bootstrap_source_export',
                       'scripts.test_current_guarded_bootstrap_restore', 'scripts.test_guarded_pair_ci_history'):
            self.assertIn(module, source)
        self.assertIn('scripts.test_purchase_guard_source_successor', source)
        self.assertIn('backend/tests/test_sredni_initial_review_mongo_integration.py', source)


class ArchivedApplicationBindingTests(unittest.TestCase):
    """Execute the actual archival selector before bounded body hydration."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.archive=self.root/'internal/legal/history/pr656-source-only-0d3a5d58'
        self.archive.mkdir(parents=True)
        workflow=(ROOT/'.github/workflows/regression.yml').read_text()
        self.block=textwrap.dedent(workflow.split(
            '          # BEGIN archived application bindings\n',1)[1].split(
            '          # END archived application bindings',1)[0])

    def select(self, native, protocol):
        for name,value in [('purchase_guard_source.json',native),
                           ('purchase_protocol_application_source.json',protocol)]:
            (self.archive/name).write_text(json.dumps(value))
        return subprocess.run(['bash','-c','set -euo pipefail\nbindings=()\n'+self.block+
            '\nprintf "%s\\n" "${bindings[@]}"'],cwd=self.root,text=True,
            capture_output=True,timeout=10)

    def test_each_archived_application_is_explicitly_selected(self):
        result=self.select({'application_source_sha':'a'*40},{'application_source_sha':'b'*40})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.splitlines(),['a'*40+':backend/server.py',
                                                     'b'*40+':backend/server.py'])

    def test_malformed_archived_pin_is_rejected(self):
        result=self.select({'application_source_sha':'not-a-sha'},{'application_source_sha':'b'*40})
        self.assertNotEqual(result.returncode,0)

    def test_missing_archived_field_is_rejected(self):
        self.assertNotEqual(self.select({}, {'application_source_sha':'b'*40}).returncode,0)

    def test_later_invalid_archive_cannot_hide_behind_valid_first(self):
        self.assertNotEqual(self.select({'application_source_sha':'a'*40},
            {'application_source_sha':None}).returncode,0)


class RetainedBindingBatchTests(unittest.TestCase):
    """Exercise the actual workflow batch block with local immutable Git objects."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name)/'repo';self.repo.mkdir()
        self.env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
        self.git('init','-q')
        self.git('config','user.name','Binding fixture')
        self.git('config','user.email','binding@example.invalid')
        (self.repo/'dir').mkdir()
        (self.repo/'dir/source.txt').write_text('immutable fixture')
        (self.repo/'dir/source bytes.txt').write_text('whitespace fixture')
        self.git('add','.')
        self.git('commit','-qm','local binding fixture')
        self.commit=self.git('rev-parse','HEAD').strip()
        workflow=(ROOT/'.github/workflows/regression.yml').read_text()
        self.block=textwrap.dedent(workflow.split(
            '          # BEGIN retained commit/blob batch checks\n',1)[1].split(
            '          # END retained commit/blob batch checks',1)[0])

    def git(self,*args):
        return subprocess.check_output([GIT,'-c','core.hooksPath=/dev/null',*args],
            cwd=self.repo,env=self.env,text=True,stderr=subprocess.PIPE)

    def batch(self,bindings):
        return subprocess.run(['bash','-c','set -euo pipefail\nbindings=("$@")\n'+self.block,
            'retained-binding-fixture',*bindings],cwd=self.repo,env=self.env,
            text=True,capture_output=True,timeout=10)

    def test_exact_committed_blob_passes(self):
        result=self.batch([self.commit+':dir/source.txt'])
        self.assertEqual(result.returncode,0,result.stderr)

    def test_duplicate_bindings_preserve_required_row_count(self):
        result=self.batch([self.commit+':dir/source.txt']*3)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_whitespace_in_bound_path_is_not_split(self):
        result=self.batch([self.commit+':dir/source bytes.txt'])
        self.assertEqual(result.returncode,0,result.stderr)

    def test_missing_commit_is_rejected(self):
        self.assertNotEqual(self.batch(['f'*40+':dir/source.txt']).returncode,0)

    def test_missing_blob_is_rejected(self):
        self.assertNotEqual(self.batch([self.commit+':dir/missing.txt']).returncode,0)

    def test_tree_in_blob_role_is_rejected(self):
        self.assertNotEqual(self.batch([self.commit+':dir']).returncode,0)

    def test_blob_in_commit_role_is_rejected(self):
        blob=self.git('rev-parse',self.commit+':dir/source.txt').strip()
        self.assertNotEqual(self.batch([blob+':dir/source.txt']).returncode,0)

    def test_later_invalid_binding_cannot_be_hidden_by_first_success(self):
        self.assertNotEqual(self.batch([self.commit+':dir/source.txt',
            self.commit+':dir/missing.txt']).returncode,0)


if __name__ == '__main__':
    unittest.main()
