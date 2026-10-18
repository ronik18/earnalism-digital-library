import copy
import datetime
import hashlib
import json
from pathlib import Path
import stat
import shutil
import tempfile
import unittest
from unittest import mock
import zipfile

from scripts.capture_prebuilt_bundle import seal, inspect_archive, preserve_failure, CAP, safe_name
from scripts.test_manual_production_release_workflow import ROOT, parse_workflow


class CompleteCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.root=self.base/'source';self.root.mkdir()
        self.reports=self.base/'reports';self.reports.mkdir()
        self.names=['.vercel/output/config.json','.vercel/output/builds.json',
                    '.vercel/output/static/asset-manifest.json','.vercel/output/static/static/js/main.fixture.js',
                    'frontend/build/journal-app-shell.html']
        self.names += ['.vercel/output/functions/api/'+name+'.func/.vc-config.json' for name in ('proxy','journal','missing','removed')]
        for name in self.names:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
            data=b'fixture payload'
            if name.endswith('.json'):data=json.dumps({'runtime':'nodejs24.x'} if '.vc-config' in name else {}).encode()
            p.write_bytes(data);p.chmod(0o644)
        (self.reports/'prebuilt-packaging.json').write_text(json.dumps({'required_assets':{'frontend/build/journal-app-shell.html':hashlib.sha256(b'fixture payload').hexdigest()}}))
        (self.reports/'RESULT.json').write_text('{"status":"SYNTHETIC_FIXTURE_ONLY"}')
        self.context={'function_runtime':'nodejs24.x','function_regions':['iad1'],'authority':'SYNTHETIC_TEST_ONLY'}
        self.selected={'files':[{'path':name,'size':(self.root/name).stat().st_size,'mode':stat.S_IFREG|0o644,
                               'sha':hashlib.sha1((self.root/name).read_bytes()).hexdigest()} for name in self.names]}

    def test_complete_bundle_preserves_every_payload_mode_hash_and_trace_asset(self):
        out=self.base/'upload'
        result=seal(self.root,self.reports,self.selected,self.context,out)
        manifest,bodies=inspect_archive(out/'release-candidate.zip',result['archive_sha256'])
        self.assertEqual(manifest['payload_files'],len(self.names))
        self.assertEqual(len([x for x in bodies if x.startswith('payload/')]),len(self.names))
        for name in self.names:self.assertEqual(bodies['payload/'+name],(self.root/name).read_bytes())
        self.assertLess(result['raw_total_bytes'],CAP)

    def test_unsafe_paths_links_private_files_and_changed_payload_fail(self):
        for name in ('..','../outside','/absolute','payload//double','x/./y','C:/bad','.env.production.local','node_modules/x'):
            with self.subTest(name=name),self.assertRaises(ValueError):safe_name(name)
        (self.root/self.names[0]).write_text('{"changed":true}')
        with self.assertRaisesRegex(ValueError,'changed'):seal(self.root,self.reports,self.selected,self.context,self.base/'bad')

    def test_raw_compressed_caps_and_digest_tamper_fail_without_omission(self):
        with self.assertRaises(ValueError):seal(self.root,self.reports,self.selected,self.context,self.base/'small',cap=100)
        with self.assertRaises(ValueError):seal(self.root,self.reports,self.selected,self.context,self.base/'increase',cap=CAP+1)
        result=seal(self.root,self.reports,self.selected,self.context,self.base/'good')
        with self.assertRaises(ValueError):inspect_archive(self.base/'good/release-candidate.zip','0'*64)

    def test_private_json_cannot_be_called_complete(self):
        name=self.names[-1];p=self.root/name;p.write_text('{"runtime":"nodejs24.x","access_token":"SYNTHETIC_PRIVATE"}')
        for row in self.selected['files']:
            if row['path']==name:row.update(size=p.stat().st_size,sha=hashlib.sha1(p.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError,'private'):seal(self.root,self.reports,self.selected,self.context,self.base/'private')

    def test_workflow_preserves_T_semantics_caps_retention_and_no_deploy(self):
        workflow=parse_workflow((ROOT/'.github/workflows/regression.yml').read_text())
        job=workflow['jobs']['frontend_build_only'];text=json.dumps(job)
        self.assertEqual(job['permissions'],{'contents':'read'});self.assertEqual(job['timeout-minutes'],25)
        self.assertNotIn('secrets.',text);self.assertNotIn('environment',job);self.assertNotIn('vercel deploy',text)
        self.assertNotIn('input-attestation',text);self.assertNotIn('capture_profile',text)
        upload=[x for x in job['steps'] if x.get('id')=='capture_upload'][0]
        self.assertEqual(upload['with']['retention-days'],3);self.assertEqual(upload['with']['compression-level'],0)
        self.assertIn('64 * 1024 * 1024',text)
        source=(ROOT/'scripts/qualify_frontend_build_only.py').read_text()
        self.assertNotIn('validate_inputs',source)
        self.assertNotIn('node-shim',source)
        self.assertIn('UNCHANGED_T_EMPTY_APP_ENV_STATIC_SETTINGS',source)
        self.assertIn("'REACT_APP_BACKEND_URL': '', 'REACT_APP_API_URL': '', 'SEO_API_BASE_URL': ''",source)

    def test_internal_link_materializes_bytes_and_external_link_fails(self):
        name = self.names[3]
        path = self.root / name
        original = path.read_bytes()
        target = path.with_name('internal-target.js')
        target.write_bytes(original)
        path.unlink()
        path.symlink_to(target.name)
        result = seal(self.root,self.reports,self.selected,self.context,self.base/'linked')
        manifest,bodies = inspect_archive(self.base/'linked/release-candidate.zip',result['archive_sha256'])
        self.assertEqual(bodies['payload/'+name],original)
        self.assertTrue(next(x for x in manifest['entries'] if x['path']=='payload/'+name)['original_internal_link'])
        path.unlink()
        outside = self.base/'outside.js';outside.write_bytes(original)
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'external'):
            seal(self.root,self.reports,self.selected,self.context,self.base/'external')

    def test_duplicate_selection_and_private_report_fail(self):
        selected = copy.deepcopy(self.selected)
        selected['files'].append(selected['files'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            seal(self.root,self.reports,selected,self.context,self.base/'duplicate')
        (self.reports/'.env.production').write_text('SYNTHETIC_NOT_A_SECRET')
        with self.assertRaisesRegex(ValueError,'Private'):
            seal(self.root,self.reports,self.selected,self.context,self.base/'private-report')

    def test_failure_reports_are_retained_with_explicit_nonqualification(self):
        preserve_failure(self.reports,self.base/'failed-upload','SyntheticFailure')
        marker=json.loads((self.base/'failed-upload/CAPTURE-FAILURE.json').read_text())
        self.assertEqual(marker['status'],'HOLD_CAPTURE_INCOMPLETE')
        self.assertTrue(marker['payload_not_qualified'])
        self.assertTrue((self.base/'failed-upload/failure-evidence.zip').is_file())



if __name__=='__main__':unittest.main()
