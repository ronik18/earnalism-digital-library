"""Source/lock tamper negatives; no Rust or network execution."""
from pathlib import Path
import shutil
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


if __name__ == '__main__': unittest.main()
