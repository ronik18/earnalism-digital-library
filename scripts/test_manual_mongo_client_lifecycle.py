"""Execute exact function ASTs with dummy DB ownership; never import/run a script."""
import ast
import builtins
import __future__
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PATHS = ('capture_mongo_book_artifact', 'controlled_publication_publish',
         'mark_books_draft', 'migrate_publication_workflow',
         'prod_dracula_diagnostic', 'reconcile_publication_workflow_inputs',
         'repair_dracula_production_record')


class DummyClient:
    def __init__(self, mode):
        self.mode = mode
        self.close_count = 0
        self.admin = self
        self.db = DummyDatabase(self)
    def __getitem__(self, key):
        if self.mode=='database_error':raise RuntimeError('dummy database selection failure')
        return self.db
    def assert_open(self):
        if self.close_count:
            raise AssertionError('Client closed before DB use completed')
    def command(self, *args):
        self.assert_open()
        if self.mode == 'ping_error':
            raise RuntimeError('dummy ping failure')
        if self.mode == 'interrupt':
            raise KeyboardInterrupt('dummy cancellation')
        return {}
    def close(self):
        self.close_count += 1


class DummyDatabase:
    def __init__(self, client):
        self.client = client
        self.name = 'fixture'
        self.books = DummyCollection(self)
    def __getitem__(self, key):
        return self.books


class DummyCollection:
    def __init__(self, database):
        self.database = database
        self.book = {'slug': 'fixture', 'chapters': [{'content': 'dummy content'}],
                     'rights_metadata': {'copyright_owner': 'Ronik Basak',
                                         'commercial_use_allowed': True},
                     'cover_url': 'fixture-front', 'back_cover_url': 'fixture-back'}
    def find_one(self, *args):
        client = self.database.client
        client.assert_open()
        if client.mode in {'read_error', 'interrupt'}:
            if client.mode == 'interrupt':raise KeyboardInterrupt('dummy cancellation')
            raise RuntimeError('dummy read failure')
        return None if client.mode == 'missing' else dict(self.book)
    def find(self, *args):
        self.database.client.assert_open()
        if self.database.client.mode in {'read_error', 'interrupt'}:
            if self.database.client.mode == 'interrupt':raise KeyboardInterrupt('dummy cancellation')
            raise RuntimeError('dummy iterator failure')
        return []
    def count_documents(self, *args):
        self.database.client.assert_open()
        return 1
    def update_one(self, query, update, **kwargs):
        self.database.client.assert_open()
        if self.database.client.mode == 'write_error':
            raise RuntimeError('dummy write failure')
        self.book.update(update.get('$set', {}))
        return SimpleNamespace(modified_count=1, matched_count=1)


class Parser:
    def __init__(self, args):self.args = args
    def add_argument(self, *args, **kwargs):pass
    def parse_args(self):return self.args


def load_functions(name, output, mode='success'):
    created = []
    def factory(*args, **kwargs):
        client = DummyClient(mode)
        created.append(client)
        return client
    adapter = SimpleNamespace(canonical_update=lambda value: {},
                              canonical_audit_event=lambda *args: {})
    def importing(name, *args, **kwargs):
        if name == 'pymongo':return SimpleNamespace(MongoClient=factory)
        if name == 'backend.publication_workflow_adapter':return adapter
        raise AssertionError('Unexpected import in isolated function: ' + name)
    env = {'MONGODB_URL': 'mongodb://dummy.invalid/fixture'}
    args = SimpleNamespace(slug='dracula' if name == 'controlled_publication_publish' else 'fixture',
                           slugs=['bn-058'], output_root=output, output=output/'report.json',
                           report=str(output/'report.json'), artifact_root=output, commit=False, live_verify=False)
    ns = {'__builtins__': {**vars(builtins), '__import__': importing},
          '__doc__': 'dummy lifecycle test', '__file__': str(ROOT/'scripts'/(name+'.py')),
          'urlparse': lambda uri: SimpleNamespace(path='/fixture'), 'MongoClient': factory, 'os': SimpleNamespace(environ=env),
          'argparse': SimpleNamespace(ArgumentParser=lambda *a, **kw: Parser(args)),
          'datetime': datetime, 'timezone': timezone, 'Path': Path,
          'json': json, 'hashlib': hashlib, 'print': lambda *a, **kw: None,
          'sha': lambda v: hashlib.sha256(v.encode() if isinstance(v, str) else v).hexdigest(),
          'SCHEMA_NAME': 'dummy', 'SCHEMA_VERSION': 1,
          'load_validation_context': lambda: (SimpleNamespace(source_evidence={}), []),
          'validate_context': lambda context: [], 'utc_now': lambda: 'dummy-time',
          'ALLOWED_SLUG': 'dracula', 'public_state': lambda value: dict(value),
          'write_publication_report': lambda *a: None,
          'controlled_publication_update': lambda *a, **kw: {},
          'canonical_update': adapter.canonical_update, 'rollback_plan': lambda state: [],
          'database_name_from_url': lambda url: 'fixture',
          'database_name_from_mongo_url': lambda url: 'fixture',
          'dracula_artifact_status': lambda: {'available': True, 'issues': []},
          'safe_dracula_document': lambda: {'slug': 'dracula', 'chapters': [{}]*27,
                                          'audio_enabled': False, 'audiobook_enabled': False},
          'comparable_changes': lambda current, desired: [], 'UNSAFE_AUDIO_FIELDS': [],
          'now_iso': lambda: 'dummy-time', 'write_reports': lambda *a, **kw: None}
    if mode == 'report_error':
        def broken_report(*args, **kwargs):raise RuntimeError('dummy report failure')
        ns['write_reports'] = broken_report
        ns['write_publication_report'] = broken_report
    tree = ast.parse((ROOT/'scripts'/ (name+'.py')).read_text())
    target = {'controlled_publication_publish': {'publish'},
              'migrate_publication_workflow': {'mongo_report'},
              'prod_dracula_diagnostic': {'read_only_db_status'},
              'repair_dracula_production_record': {'connect_books_collection', 'run_repair'}}.get(name, {'main'})
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in target]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), name, 'exec',
                 flags=__future__.annotations.compiler_flag), ns)
    return ns, args, created


def invoke(name, ns, args, output):
    if name == 'controlled_publication_publish':return ns['publish'](args)
    if name == 'migrate_publication_workflow':
        return ns['mongo_report'](root=output, apply=False,
                                  report_path=output/'report.json', skip_slugs=set())
    if name == 'prod_dracula_diagnostic':return ns['read_only_db_status']()
    if name == 'repair_dracula_production_record':return ns['run_repair'](apply=False, output_dir=output)
    return ns['main']()


class ClientLifecycleTests(unittest.TestCase):
    def test_success_closes_each_owned_client_once(self):
        for name in PATHS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp); ns, args, clients = load_functions(name, output)
                invoke(name, ns, args, output)
                self.assertEqual(len(clients), 1)
                self.assertEqual(clients[0].close_count, 1)

    def test_operation_error_closes_each_owned_client_once(self):
        for name in PATHS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                mode = 'read_error' if name == 'controlled_publication_publish' else 'ping_error'
                output = Path(tmp); ns, args, clients = load_functions(name, output, mode)
                try:invoke(name, ns, args, output)
                except RuntimeError:pass
                self.assertEqual(len(clients), 1)
                self.assertEqual(clients[0].close_count, 1)

    def test_system_exit_and_missing_record_return_close(self):
        for name in ('capture_mongo_book_artifact', 'mark_books_draft', 'controlled_publication_publish'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp); ns, args, clients = load_functions(name, output, 'missing')
                try:invoke(name, ns, args, output)
                except SystemExit:pass
                self.assertEqual(clients[0].close_count, 1)

    def test_base_exception_closes_all_owners(self):
        for name in PATHS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp); ns, args, clients = load_functions(name, output, 'interrupt')
                with self.assertRaises(KeyboardInterrupt):invoke(name, ns, args, output)
                self.assertEqual(clients[0].close_count, 1)

    def test_reader_database_selection_failure_closes_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp);ns,args,clients=load_functions('verify_reader_startup_readonly',output,'database_error')
            with self.assertRaises(RuntimeError):ns['main']()
            self.assertEqual(len(clients),1);self.assertEqual(clients[0].close_count,1)

    def test_repair_helper_transfers_live_client_to_caller(self):
        with tempfile.TemporaryDirectory() as tmp:
            ns, args, clients = load_functions('repair_dracula_production_record', Path(tmp))
            collection, error = ns['connect_books_collection']()
            self.assertEqual(error, '')
            self.assertEqual(clients[0].close_count, 0)
            collection.find_one({})
            collection.database.client.close()
            self.assertEqual(clients[0].close_count, 1)

    def test_repair_read_or_report_failure_closes_transferred_client(self):
        for mode in ('read_error', 'report_error'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp); ns, args, clients = load_functions('repair_dracula_production_record', output, mode)
                try:invoke('repair_dracula_production_record', ns, args, output)
                except RuntimeError:pass
                self.assertEqual(clients[0].close_count, 1)

    def test_repair_apply_and_write_failure_close_after_live_use(self):
        for mode in ('success', 'write_error'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                output=Path(tmp);ns,args,clients=load_functions('repair_dracula_production_record',output,mode)
                if mode == 'write_error':
                    with self.assertRaises(RuntimeError):ns['run_repair'](apply=True,output_dir=output)
                else:
                    report=ns['run_repair'](apply=True,output_dir=output)
                    self.assertTrue(report['mutation_performed'])
                self.assertEqual(clients[0].close_count,1)

    def test_invalid_artifact_does_not_allocate_repair_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp);ns,args,clients=load_functions('repair_dracula_production_record',output)
            ns['dracula_artifact_status']=lambda:{'available':False,'issues':['dummy']}
            ns['safe_dracula_document']=lambda:None
            ns['run_repair'](apply=False,output_dir=output)
            self.assertEqual(clients,[])


if __name__ == '__main__':unittest.main()
