"""Lossless textual index tests; no semantic, voice, timing or release acceptance."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
import unicodedata
import urllib.request
from unittest.mock import patch

from scripts import earnalism_content_context as context


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class ContentContextTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'source.txt'
        self.output = self.root / 'context'
        self.text = 'Dr. Reed wrote: Cafe\u0301, then tea.\n\nA second line!  '
        self.source.write_bytes(self.text.encode('utf-8'))

    def build(self, **changes):
        args = dict(expected_sha256=sha(self.source.read_bytes()),
                    title='Generic fixture', language='en', page_size=32,
                    genre_notes=['Explicit editor note; no inferred emotion'])
        args.update(changes)
        return context.build(self.source, self.output, **args)

    def manifest(self):
        return json.loads((self.output / 'context.json').read_text())

    def save_manifest(self, data):
        (self.output / 'context.json').write_text(json.dumps(data))

    def units(self):
        return [unit for page in self.manifest()['pages']
                for unit in json.loads((self.output / page['path']).read_text())['units']]

    def assert_lossless(self):
        raw = self.source.read_bytes()
        text = raw.decode('utf-8')
        manifest = self.manifest()
        units = self.units()
        parents = {'work': manifest['work']} | {unit['id']: unit for unit in units}
        self.assertEqual(manifest['source']['sha256'], sha(raw))
        for unit in units:
            span = text[unit['start_char']:unit['end_char']]
            encoded = raw[unit['start_byte']:unit['end_byte']]
            self.assertEqual(encoded.decode('utf-8'), span)
            self.assertEqual(unit['text_sha256'], sha(encoded))
            self.assertLess(unit['start_char'], unit['end_char'])
            self.assertEqual(unit['direction_status'], 'UNASSESSED')
            self.assertEqual(unit['timing_status'], 'TEXT_ONLY_UNMEASURED')
        for kind, parent_kind in [('block', None), ('sentence_candidate', 'block'),
                                  ('phrase_candidate', 'sentence_candidate')]:
            groups = {}
            for unit in units:
                if unit['kind'] == kind:
                    groups.setdefault(unit['parent'], []).append(unit)
            wanted = ['work'] if parent_kind is None else [u['id'] for u in units if u['kind'] == parent_kind]
            self.assertEqual(set(groups), set(wanted))
            for parent, children in groups.items():
                children.sort(key=lambda unit: unit['start_char'])
                p = parents[parent]
                self.assertEqual(children[0]['start_char'], p['start_char'])
                self.assertEqual(children[-1]['end_char'], p['end_char'])
                self.assertTrue(all(a['end_char'] == b['start_char'] for a, b in zip(children, children[1:])))
                self.assertEqual(''.join(text[u['start_char']:u['end_char']] for u in children),
                                 text[p['start_char']:p['end_char']])
        self.assertFalse(manifest['production_ready'])
        self.assertFalse(manifest['publication_performed'])
        self.assertEqual(manifest['semantic_review'], 'UNASSESSED')
        self.assertEqual(manifest['audio_timing'], 'UNMEASURED')

    def test_english_utf8_combining_marks_and_whitespace_are_lossless(self):
        self.build()
        self.assert_lossless()
        self.assertNotEqual(self.source.read_bytes(), unicodedata.normalize('NFC', self.text).encode())

    def test_bengali_vowel_virama_joiner_and_combining_clusters_are_not_split(self):
        self.text = 'কি বলি, কৌতূহল আছে। ক্\u200dষ, ক্ষীণ!\n\nনতুন কথা; ঠিক আছে।  '
        self.source.write_bytes(self.text.encode())
        self.build(language='bn', title='সাধারণ পরীক্ষা')
        self.assert_lossless()
        boundaries = {u[k] for u in self.units() for k in ('start_char', 'end_char')}
        for cluster in ['কি', 'কৌ', 'ক্\u200dষ', 'ক্ষী']:
            start = self.text.index(cluster)
            self.assertTrue(boundaries.isdisjoint(range(start + 1, start + len(cluster))))

    def test_source_hash_mismatch_refuses_without_output(self):
        with self.assertRaises(ValueError):
            self.build(expected_sha256='0' * 64)
        self.assertFalse(self.output.exists())

    def test_invalid_utf8_refuses_without_output(self):
        self.source.write_bytes(b'\xff\xfe')
        with self.assertRaises(UnicodeDecodeError):
            self.build()
        self.assertFalse(self.output.exists())

    def test_pages_have_bounded_unit_count_and_cover_index_once(self):
        self.source.write_text('A phrase, another phrase.\n\n' * 80)
        self.build(page_size=32)
        manifest = self.manifest()
        self.assertGreater(len(manifest['pages']), 1)
        units = []
        for page in manifest['pages']:
            raw = (self.output / page['path']).read_bytes()
            data = json.loads(raw)
            self.assertLessEqual(len(data['units']), 32)
            self.assertGreater(len(data['units']), 0)
            self.assertEqual(len(raw), page['bytes'])
            self.assertEqual(sha(raw), page['sha256'])
            units.extend(data['units'])
        self.assertEqual(len(units), sum(manifest['counts'].values()))
        self.assertEqual(len(units), len({u['id'] for u in units}))
        self.assert_lossless()

    def test_page_size_limits_and_bool_refused(self):
        for value in [True, 0, 31, 513, '32']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.build(page_size=value)

    def test_unchanged_cache_reuses_exact_bytes(self):
        initial = self.build()
        manifest_before = (self.output / 'context.json').read_bytes()
        reused = self.build()
        self.assertFalse(initial['reused'])
        self.assertTrue(reused['reused'])
        self.assertEqual(initial['sha256'], reused['sha256'])
        self.assertEqual(manifest_before, (self.output / 'context.json').read_bytes())

    def test_changed_cached_page_refused(self):
        self.build()
        page = self.output / self.manifest()['pages'][0]['path']
        page.write_bytes(page.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            self.build()

    def test_changed_editorial_recipe_refused_preserving_cache(self):
        self.build()
        before = (self.output / 'context.json').read_bytes()
        with self.assertRaises(ValueError):
            self.build(genre_notes=['A different editor note'])
        self.assertEqual(before, (self.output / 'context.json').read_bytes())

    def test_changed_source_path_even_with_identical_bytes_refused(self):
        self.build()
        other = self.root / 'same-bytes.txt'
        other.write_bytes(self.source.read_bytes())
        self.source = other
        with self.assertRaises(ValueError):
            self.build()

    def test_direct_page_symlink_refused(self):
        self.build()
        page = self.output / self.manifest()['pages'][0]['path']
        external = self.root / 'external-page.json'
        external.write_bytes(page.read_bytes())
        page.unlink()
        page.symlink_to(external)
        with self.assertRaises(ValueError):
            self.build()

    def test_output_symlink_to_valid_cache_refused(self):
        self.build()
        alias = self.root / 'output-alias'
        alias.symlink_to(self.output, target_is_directory=True)
        self.output = alias
        with self.assertRaises(ValueError):
            self.build()

    def test_explicit_output_parent_alias_returns_actual_fresh_destination(self):
        real = self.root / 'real-parent'
        real.mkdir()
        alias = self.root / 'parent-alias'
        alias.symlink_to(real, target_is_directory=True)
        self.output = alias / 'new-context'
        source_before = self.source.read_bytes()
        result = self.build()
        self.assertEqual(Path(result['path']), real / 'new-context' / 'context.json')
        self.assertTrue((real / 'new-context').is_dir())
        self.assertEqual(source_before, self.source.read_bytes())
        self.assert_lossless()

    def test_explicit_readonly_source_alias_binds_resolved_source_and_exact_bytes(self):
        actual_source = self.source
        source_before = actual_source.read_bytes()
        alias = self.root / 'source-alias.txt'
        alias.symlink_to(self.source)
        self.source = alias
        self.build()
        self.assertEqual(self.manifest()['source']['path'], str(actual_source))
        self.assertEqual(source_before, actual_source.read_bytes())
        self.assertEqual(self.manifest()['source']['sha256'], sha(source_before))
        self.assert_lossless()

    def test_output_under_git_checkout_refused_even_through_parent_alias(self):
        checkout = self.root / 'checkout'
        checkout.mkdir()
        (checkout / '.git').write_text('gitdir: /generic/fixture-only\n')
        alias = self.root / 'checkout-alias'
        alias.symlink_to(checkout, target_is_directory=True)
        self.output = alias / 'private-context'
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse((checkout / 'private-context').exists())

    def test_cached_manifest_symlink_refused(self):
        self.build()
        manifest = self.output / 'context.json'
        external = self.root / 'outside-manifest.json'
        external.write_bytes(manifest.read_bytes())
        manifest.unlink()
        manifest.symlink_to(external)
        with self.assertRaises(ValueError):
            self.build()

    def test_cached_page_traversal_or_absolute_path_refused(self):
        self.build()
        manifest = self.manifest()
        page = self.output / manifest['pages'][0]['path']
        external = self.root / 'outside-page.json'
        external.write_bytes(page.read_bytes())
        for name in ['../outside-page.json', str(external)]:
            with self.subTest(name=name):
                modified = json.loads(json.dumps(manifest))
                modified['pages'][0]['path'] = name
                self.save_manifest(modified)
                with self.assertRaises(ValueError):
                    self.build()

    def test_cached_page_symlink_ancestor_refused(self):
        self.build()
        manifest = self.manifest()
        page = self.output / manifest['pages'][0]['path']
        external_dir = self.root / 'external-pages'
        external_dir.mkdir()
        (external_dir / page.name).write_bytes(page.read_bytes())
        (self.output / 'linked-pages').symlink_to(external_dir, target_is_directory=True)
        manifest['pages'][0]['path'] = 'linked-pages/' + page.name
        self.save_manifest(manifest)
        with self.assertRaises(ValueError):
            self.build()

    def test_cache_missing_children_refused_even_when_rehashed(self):
        self.build()
        manifest = self.manifest()
        first = manifest['pages'][0]
        page = self.output / first['path']
        data = json.loads(page.read_text())
        removed = data['units'].pop()
        manifest['counts'][removed['kind']] -= 1
        raw = json.dumps(data).encode()
        page.write_bytes(raw)
        first.update(sha256=sha(raw), bytes=len(raw))
        self.save_manifest(manifest)
        with self.assertRaises(ValueError):
            self.build()

    def test_cache_cannot_promote_publication_or_model_call_claims(self):
        self.build()
        retained = self.manifest()
        for field, value in [('publication_performed', True), ('codex_api_calls_by_indexer', 1)]:
            with self.subTest(field=field):
                modified = json.loads(json.dumps(retained))
                modified[field] = value
                self.save_manifest(modified)
                with self.assertRaises(ValueError):
                    self.build()

    def test_cache_page_size_bound_survives_rehashed_page_regrouping(self):
        self.source.write_text('One phrase, another phrase.\n\n' * 80)
        self.build(page_size=32)
        manifest = self.manifest()
        all_units = self.units()
        self.assertGreater(len(all_units), 32)
        first = manifest['pages'][0]
        raw = json.dumps({'source_sha256': sha(self.source.read_bytes()), 'units': all_units}).encode()
        (self.output / first['path']).write_bytes(raw)
        first.update(sha256=sha(raw), bytes=len(raw))
        manifest['pages'] = [first]
        self.save_manifest(manifest)
        with self.assertRaises(ValueError):
            self.build()

    def test_no_network_provider_or_subprocess_for_build_and_cache(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')), \
             patch.object(urllib.request, 'urlopen', side_effect=AssertionError('network forbidden')), \
             patch.object(subprocess, 'Popen', side_effect=AssertionError('process forbidden')):
            self.build()
            self.build()


if __name__ == '__main__':
    unittest.main()
