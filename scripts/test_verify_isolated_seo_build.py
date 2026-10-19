import json
import os
from pathlib import Path
import subprocess
import shlex
import sys
import tempfile
import unittest

from scripts.verify_isolated_seo_build import prepare, verify


class IsolatedSeoBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='earnalism SEO isolation ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'exact source with spaces'
        self.root.mkdir()
        self.generated = self.base / 'generated SEO with spaces'
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Local SEO fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.root / '.gitignore').write_text('.vercel/\nfrontend/build/\n')
        self.public = self.root / 'frontend/public'
        self.public.mkdir(parents=True)
        self.sitemap = b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://theearnalism.com/</loc><lastmod>2026-10-03</lastmod></url></urlset>'
        self.robots = b'User-agent: *\nAllow: /\nSitemap: https://theearnalism.com/sitemap.xml\n'
        (self.public / 'sitemap.xml').write_bytes(self.sitemap)
        (self.public / 'robots.txt').write_bytes(self.robots)
        (self.root / 'frontend/package.json').write_text('{"name":"local-fixture"}\n')
        (self.root / 'frontend/package-lock.json').write_text('{"lockfileVersion":3}\n')
        self.git('add', '.')
        self.git('commit', '-m', 'Exact SEO input fixture')
        self.sha = self.git('rev-parse', 'HEAD').strip()
        for folder in ('frontend/build', '.vercel/output/static'):
            output = self.root / folder
            output.mkdir(parents=True)
            (output / 'sitemap.xml').write_bytes(self.sitemap)
            (output / 'robots.txt').write_bytes(self.robots)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args],
                                       text=True, stderr=subprocess.DEVNULL)

    def generate(self):
        prepare(self.root, self.generated, self.sha)
        (self.generated / 'sitemap.xml').write_bytes(self.sitemap.replace(b'2026-10-03', b'2026-10-18'))
        (self.generated / 'robots.txt').write_bytes(self.robots)

    def test_exact_source_and_published_bytes_are_preserved_with_changed_side_output(self):
        self.generate()
        result = verify(self.root, self.generated, self.sha)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all'), '')
        asset = result['assets']['sitemap.xml']
        self.assertEqual(asset['exact_F_preimage_sha256'], asset['prebuilt_static_sha256'])
        self.assertNotEqual(asset['exact_F_preimage_sha256'], asset['isolated_generated_sha256'])
        self.assertFalse(asset['generated_bytes_published'])

    def test_prepare_rejects_existing_destination_and_preserves_unrelated_file(self):
        self.generated.mkdir()
        marker = self.generated / 'preserve.txt'
        marker.write_text('existing evidence')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            prepare(self.root, self.generated, self.sha)
        self.assertEqual(marker.read_text(), 'existing evidence')

    def test_prepare_rejects_source_overlap_ancestors_and_symlink(self):
        for path in (self.root, self.root / 'generated', self.base):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'overlaps'):
                prepare(self.root, path, self.sha)
        self.generated.symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            prepare(self.root, self.generated, self.sha)

    def test_wrong_head_and_tracked_or_untracked_mutations_fail_without_contents(self):
        self.generate()
        with self.assertRaisesRegex(ValueError, 'HEAD mismatch'):
            verify(self.root, self.generated, '0' * 40)
        secret_marker = 'FILE_CONTENT_MUST_NEVER_APPEAR'
        (self.public / 'robots.txt').write_text(secret_marker)
        (self.root / 'unexpected.txt').write_text(secret_marker)
        with self.assertRaisesRegex(ValueError, 'checkout dirty') as caught:
            verify(self.root, self.generated, self.sha)
        self.assertNotIn(secret_marker, str(caught.exception))
        self.assertIn('robots.txt', str(caught.exception))
        self.assertIn('unexpected.txt', str(caught.exception))

    def test_missing_generator_output_is_rejected(self):
        prepare(self.root, self.generated, self.sha)
        with self.assertRaisesRegex(ValueError, 'exactly'):
            verify(self.root, self.generated, self.sha)

    def test_unexpected_lockfile_mutation_remains_fail_closed(self):
        self.generate()
        (self.root / 'frontend/package-lock.json').write_text('{"lockfileVersion":3,"unexpected":true}\n')
        with self.assertRaisesRegex(ValueError, 'checkout dirty'):
            verify(self.root, self.generated, self.sha)

    def test_build_failure_stops_before_success_attestation(self):
        from scripts.test_manual_production_release_workflow import ROOT, step_script
        binary = self.base / 'bin'
        binary.mkdir()
        stub = binary / 'python3'
        stub.write_text('#!/bin/bash\nif [[ "$1" == -m && "$2" == scripts.frontend_public_build ]]; then\n  printf "local simulated generator/build failure\\n" >&2\n  exit 73\nfi\nexec ' + shlex.quote(sys.executable) + ' "$@"\n')
        stub.chmod(0o700)
        result = subprocess.run(['bash', '-eu', '-c', step_script('Build frontend for Vercel')],
                                cwd=ROOT, text=True, capture_output=True,
                                env={**os.environ, 'PATH': str(binary) + os.pathsep + os.environ['PATH'],
                                     'FRONTEND_DIR': str(self.root), 'FRONTEND_SHA': self.sha,
                                     'RUNNER_TEMP': str(self.base), 'GITHUB_WORKSPACE': str(ROOT),
                                     'VERCEL_SCOPE': ''})
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertIn('local simulated generator/build failure', result.stderr)
        self.assertNotIn('"status": "PASS"', result.stdout)
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all'), '')

    def test_wrong_generated_schema_or_origin_is_rejected(self):
        self.generate()
        (self.generated / 'sitemap.xml').write_text('<wrong/>')
        with self.assertRaisesRegex(ValueError, 'schema mismatch'):
            verify(self.root, self.generated, self.sha)
        (self.generated / 'sitemap.xml').write_bytes(self.sitemap.replace(b'theearnalism.com', b'example.invalid'))
        with self.assertRaisesRegex(ValueError, 'unexpected origins'):
            verify(self.root, self.generated, self.sha)

    def test_changed_final_build_or_prebuilt_bytes_are_rejected(self):
        self.generate()
        for folder in ('frontend/build', '.vercel/output/static'):
            with self.subTest(folder=folder):
                path = self.root / folder / 'sitemap.xml'
                path.write_bytes(self.sitemap.replace(b'2026-10-03', b'2026-10-18'))
                with self.assertRaisesRegex(ValueError, 'differs from exact-F'):
                    verify(self.root, self.generated, self.sha)
                path.write_bytes(self.sitemap)

    def test_extra_or_symlinked_generator_output_is_rejected(self):
        self.generate()
        (self.generated / 'unexpected.txt').write_text('unrelated fixture')
        with self.assertRaisesRegex(ValueError, 'exactly'):
            verify(self.root, self.generated, self.sha)
        (self.generated / 'unexpected.txt').unlink()
        (self.generated / 'robots.txt').unlink()
        (self.generated / 'robots.txt').symlink_to(self.public / 'robots.txt')
        with self.assertRaisesRegex(ValueError, 'symlinked'):
            verify(self.root, self.generated, self.sha)

    def test_workflow_sets_hook_only_on_build_and_verifies_before_packaging(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / '.github/workflows/reader-frontend-production.yml').read_text()
        block = workflow.split('      - name: Build frontend for Vercel\n', 1)[1].split('      - name: Verify source and prebuilt function packaging', 1)[0]
        invocation = 'python3 -m scripts.frontend_public_build --source-root "$FRONTEND_DIR" --generated-root "$generated_seo_dir" --receipt /tmp/vercel-public-build.json'
        self.assertEqual(workflow.count(invocation), 1)
        self.assertIn(invocation, block)
        self.assertLess(block.index('--prepare --source-root "$FRONTEND_DIR"'), block.index(invocation))
        self.assertIn('--expected-sha "$FRONTEND_SHA" --output /tmp/vercel-isolated-seo.json', block)
        self.assertIn('[[ -z "$(git -C "$FRONTEND_DIR" status --porcelain --untracked-files=all)" ]] || exit 1', block)
        self.assertNotIn('git reset', block)
        self.assertNotIn('git restore', block)
        self.assertNotIn('NPM_CONFIG_PACKAGE_LOCK=false', block)


if __name__ == '__main__':
    unittest.main()
