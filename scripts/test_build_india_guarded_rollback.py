import ast
import asyncio
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import tarfile
from types import SimpleNamespace
from scripts import build_india_guarded_rollback as b


class GuardedContainmentTests(unittest.TestCase):
    def source(self):
        return b.git('show', b.BASE + ':backend/server.py').decode()

    def test_preserves_current_ast_except_single_closed_purchase_branch(self):
        source = self.source(); result = b.guard_only_server(source, source)
        old, new = b.function(source), b.function(result)
        branch = new.body.pop(1)
        self.assertIn('PURCHASE_INITIATION_CLOSED', ast.unparse(branch))
        self.assertIn('503', ast.unparse(branch))
        self.assertEqual(ast.dump(old, include_attributes=False), ast.dump(new, include_attributes=False))
        # Bytes outside middleware, including all latest financial functions,
        # remain identical. Never transplant an old whole server.
        before = source.splitlines(keepends=True)
        after = result.splitlines(keepends=True)
        self.assertEqual(before[:old.lineno-1], after[:old.lineno-1])
        self.assertEqual(before[old.end_lineno:], after[b.function(result).end_lineno:])

    def test_old_source_substitution_rejected(self):
        with self.assertRaises(ValueError): b.guard_only_server(self.source(), 'changed source')

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): b.build(Path(tmp))

    def test_repository_output_forbidden(self):
        with self.assertRaises(ValueError): b.build(b.ROOT / 'do-not-create-rollback-output')

    def test_containment_closes_only_initiation_at_middleware_layer(self):
        node = b.function(b.guard_only_server(self.source(), self.source()))
        node.decorator_list = []
        env = {'Request': object, 'ENVIRONMENT': 'production',
               'COMMERCE_ORDER_PATH': '/api/payments/topup',
               'PUBLIC_READER_EXPOSURE_ENABLED': False,
               'JSONResponse': lambda status_code, **kwargs: SimpleNamespace(status_code=status_code)}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<inert middleware>', 'exec'), env)
        async def inert(request): return SimpleNamespace(status_code=204)
        for path, status in [('/api/payments/topup', 503), ('/api/payments/verify', 204),
                             ('/api/payments/refund', 204), ('/api/payments/webhook', 204)]:
            request = SimpleNamespace(method='POST', url=SimpleNamespace(path=path), headers={})
            with self.subTest(path=path):
                self.assertEqual(asyncio.run(env['enforce_public_release_country'](request, inert)).status_code, status)

    def test_archive_group_write_does_not_change_git_file_modes(self):
        source = self.source().encode(); stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for name, data, mode in [('backend/server.py', source, 0o664),
                                     ('backend/entry.sh', b'#!/bin/sh\nexit 0\n', 0o775)]:
                item = tarfile.TarInfo(name); item.size = len(data); item.mode = mode
                archive.addfile(item, io.BytesIO(data))
        def frozen_git(*args): return stream.getvalue() if args[0] == 'archive' else source
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(b, 'git', side_effect=frozen_git):
            output = Path(tmp) / 'new-source'; report = b.build(output)
            self.assertEqual((output/'backend/server.py').stat().st_mode & 0o777, 0o644)
            self.assertEqual((output/'backend/entry.sh').stat().st_mode & 0o777, 0o755)
            self.assertEqual(report['files']['backend/entry.sh']['mode'], '0o755')
