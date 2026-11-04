"""Source/lock tamper negatives; no Rust or network execution."""
from pathlib import Path
import shutil
import json
import hashlib
import tomllib
import tempfile
import unittest
import verify_railway_helper_source as m


class SourceAdmission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'helper'
        shutil.copytree(Path(__file__).parent/'test_helpers/railway_archiver_v5710', self.root)

    def tearDown(self): self.temp.cleanup()

    def change(self, name, before, after):
        p=self.root/name;p.write_text(p.read_text().replace(before,after,1))

    def test_exact_source_admitted_without_execution(self):
        self.assertFalse(m.check(self.root)['helper_executed'])

    def test_changed_upstream_module_rejected(self):
        self.change('upstream-upload.rs.txt','use std::path::Path;', 'use std::path::Path; // changed')
        with self.assertRaises(ValueError): m.check(self.root)

    def test_changed_upstream_lock_rejected(self):
        with (self.root/'upstream-Cargo.lock').open('a') as f:f.write('\n# changed\n')
        with self.assertRaises(ValueError): m.check(self.root)

    def test_changed_derived_lock_rejected(self):
        self.change('Cargo.lock','version = "1.0.95"','version = "1.0.96"')
        with self.assertRaises(ValueError): m.check(self.root)

    def test_changed_helper_function_rejected(self):
        self.change('src/main.rs','builder.follow_links(true)', 'builder.follow_links(false)')
        with self.assertRaises(ValueError): m.check(self.root)

    def test_added_network_entrypoint_rejected(self):
        with (self.root/'src/main.rs').open('a') as f:f.write('\n// reqwest network dependency\n')
        with self.assertRaises(ValueError): m.check(self.root)

    def test_unpinned_direct_dependency_rejected(self):
        self.change('Cargo.toml','anyhow = "=1.0.95"','anyhow = "1"')
        with self.assertRaises(ValueError): m.check(self.root)

    def test_unpublishable_harness_required(self):
        self.change('Cargo.toml','publish = false','publish = true')
        with self.assertRaises(ValueError): m.check(self.root)


    def resign_lock(self, change):
        p=self.root/'Cargo.lock'; d=tomllib.loads(p.read_text()); change(d)
        lines=['version = 4']
        for row in d['package']:
            lines.append('[[package]]')
            lines.extend(k+' = '+json.dumps(v) for k,v in row.items())
        p.write_text('\n'.join(lines)+'\n')
        pins_path=self.root/'SOURCE-PINS.json';pins=json.loads(pins_path.read_bytes())
        pins['derived_lock_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        pins['registry_package_closure']=sum(bool(x.get('source')) for x in d['package'])
        pins_path.write_text(json.dumps(pins))

    def test_checksum_drift_rejected_even_with_local_hash_replaced(self):
        def change(d):next(p for p in d['package'] if p['name']=='anyhow')['checksum']='0'*64
        self.resign_lock(change)
        with self.assertRaisesRegex(ValueError,'registry'):m.check(self.root)

    def test_version_drift_rejected_even_with_local_hash_replaced(self):
        def change(d):next(p for p in d['package'] if p['name']=='anyhow')['version']='99.0.0'
        self.resign_lock(change)
        with self.assertRaises(ValueError):m.check(self.root)

    def test_new_edge_rejected_even_with_local_hash_replaced(self):
        def change(d):next(p for p in d['package'] if p['name']=='anyhow')['dependencies']=['tar']
        self.resign_lock(change)
        with self.assertRaisesRegex(ValueError,'dependency edge'):m.check(self.root)

    def test_omitted_direct_pin_rejected_even_with_local_hash_replaced(self):
        def change(d):
            root=next(p for p in d['package'] if not p.get('source'))
            root['dependencies']=[x for x in root['dependencies'] if x.split()[0]!='anyhow']
            d['package']=[p for p in d['package'] if p['name']!='anyhow']
        self.resign_lock(change)
        with self.assertRaisesRegex(ValueError,'direct dependency'):m.check(self.root)

    def test_unreachable_original_package_rejected(self):
        upstream=tomllib.loads((self.root/'upstream-Cargo.lock').read_text())
        row=next(p for p in upstream['package'] if (p['name'],p['version'])==('simd-adler32','0.3.8'))
        self.resign_lock(lambda d:d['package'].append(row))
        with self.assertRaisesRegex(ValueError,'unreachable'):m.check(self.root)

    def test_dependency_refs_compare_semantically(self):
        rows={('x','1.0.0'):{'name':'x','version':'1.0.0'}}
        self.assertEqual(m._edges({'dependencies':['x']},rows),m._edges({'dependencies':['x 1.0.0']},rows))


if __name__ == '__main__': unittest.main()
