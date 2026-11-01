"""Evaluate only real source constructor expressions; never run a script or connect."""
import ast
from pathlib import Path
import unittest
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
MANUAL_PATHS = (
    'scripts/capture_mongo_book_artifact.py',
    'scripts/controlled_publication_publish.py',
    'scripts/mark_books_draft.py',
    'scripts/migrate_publication_workflow.py',
    'scripts/prod_dracula_diagnostic.py',
    'scripts/reconcile_publication_workflow_inputs.py',
    'scripts/repair_dracula_production_record.py',
    'scripts/verify_reader_startup_readonly.py',
)


class ManualMongoPoolBounds(unittest.TestCase):
    def constructor(self, path):
        tree = ast.parse((ROOT / path).read_text())
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == 'MongoClient']
        self.assertEqual(len(calls), 1, path)
        call = calls[0]
        keyword = {k.arg: k.value for k in call.keywords}
        self.assertEqual(ast.literal_eval(keyword['maxPoolSize']), 8)
        self.assertEqual(ast.literal_eval(keyword['minPoolSize']), 0)
        self.assertEqual(ast.literal_eval(keyword['maxConnecting']), 2)
        return call

    def test_every_actual_factory_has_finite_pool(self):
        for path in MANUAL_PATHS:
            with self.subTest(path=path):
                self.constructor(path)

    def test_keyword_bounds_override_uri_unlimited_and_oversized_minimum(self):
        # connect=False is inserted by the dummy-only factory, not production code.
        # Reading client.options does not request selection, ping, DNS or a socket.
        for path in MANUAL_PATHS:
            for query in ('maxPoolSize=0&minPoolSize=99&maxConnecting=99',
                          'maxPoolSize=100&minPoolSize=99&maxConnecting=99',
                          'maxPoolSize=1&minPoolSize=0'):
                with self.subTest(path=path, query=query):
                    uri = 'mongodb://127.0.0.1:27999/?' + query
                    call = self.constructor(path)
                    created = []
                    def disconnected_factory(*args, **kwargs):
                        kwargs['connect'] = False
                        client = MongoClient(*args, **kwargs)
                        created.append(client)
                        return client
                    expression = ast.Expression(body=call)
                    try:
                        client = eval(compile(expression, path, 'eval'), {
                            'MongoClient': disconnected_factory, 'mongo_url': uri,
                            'url': uri, 'uri': uri,
                        })
                        self.assertEqual(client.options.pool_options.max_pool_size, 8)
                        self.assertEqual(client.options.pool_options.min_pool_size, 0)
                        self.assertEqual(client.options.pool_options.max_connecting, 2)
                    finally:
                        for client in created:
                            client.close()


if __name__ == '__main__':
    unittest.main()
