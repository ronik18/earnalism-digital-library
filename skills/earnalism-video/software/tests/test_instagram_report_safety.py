"""Report-path boundary tests; no media encoding or paid/provider actions."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import instagram_preflight as preflight
import instagram_compat_export as compatibility


class InstagramReportSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name).resolve()
        self.source=self.root/'master.mp4';self.source.write_bytes(b'ORIGINAL_MASTER_BYTES')
        self.target=self.root/'export.mp4';self.target.write_bytes(b'EXISTING_DERIVATIVE_BYTES')
        (self.root/'subdir').mkdir()

    def tearDown(self):self.tmp.cleanup()

    def args(self,module,report):
        return [str(self.source)]+([str(self.target)] if module is compatibility else [])+['--report',str(report)]

    def snapshot(self):
        return {str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}

    def refused_before_processing(self,module,report):
        before=self.snapshot();processor='inspect' if module is preflight else 'export'
        with patch.object(module,processor) as processing,patch.object(module.subprocess,'run') as ffmpeg,patch.object(module.subprocess,'check_output') as probe,redirect_stderr(io.StringIO()),redirect_stdout(io.StringIO()):
            self.assertNotEqual(module.main(self.args(module,report)),0)
            processing.assert_not_called();ffmpeg.assert_not_called();probe.assert_not_called()
        self.assertEqual(self.snapshot(),before)

    def test_source_report_aliases_resolved_paths_and_symlinks_refuse(self):
        link=self.root/'source-report-link.json';link.symlink_to(self.source)
        for module in (preflight,compatibility):
            for report in (self.source,self.root/'subdir/../master.mp4',link):
                with self.subTest(module=module.__name__,report=report):self.refused_before_processing(module,report)
        self.assertTrue(link.is_symlink())

    def test_derivative_report_aliases_existing_and_future_target_refuse(self):
        link=self.root/'target-report-link.json';link.symlink_to(self.target)
        for report in (self.target,self.root/'subdir/../export.mp4',link):
            with self.subTest(report=report):self.refused_before_processing(compatibility,report)
        self.target=self.root/'future-export.mp4'
        self.refused_before_processing(compatibility,self.target)
        self.refused_before_processing(compatibility,self.root/'FUTURE-EXPORT.MP4')
        self.assertFalse(self.target.exists())

    def test_existing_report_dangling_symlink_and_missing_parent_refuse(self):
        existing=self.root/'existing.json';existing.write_bytes(b'PRESERVE_OLD_REPORT')
        dangling=self.root/'dangling-report.json';dangling.symlink_to(self.root/'absent.json')
        for module in (preflight,compatibility):
            for report in (existing,dangling,self.root/'missing-parent/report.json'):
                with self.subTest(module=module.__name__,report=report):self.refused_before_processing(module,report)
        self.assertTrue(dangling.is_symlink());self.assertFalse((self.root/'missing-parent').exists())

    def test_valid_new_report_is_created_without_media_changes(self):
        for module,state in ((preflight,'TECHNICAL_CHECKS_PASS_NOT_MOBILE_ACCEPTANCE'),
                             (compatibility,'TECHNICALLY_VERIFIED_PRIVATE_NATIVE_REVIEW_REQUIRED')):
            report=self.root/(module.__name__.split('.')[-1]+'.json');before=self.snapshot()
            processor='inspect' if module is preflight else 'export'
            with patch.object(module,processor,return_value={'state':state}) as processing,redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(self.args(module,report)),0);processing.assert_called_once()
            self.assertEqual(json.loads(report.read_text()),{'state':state})
            self.assertEqual({p:data for p,data in self.snapshot().items() if p!=str(report)},before)

    def test_processing_validation_failure_writes_only_exclusive_new_report(self):
        for module,state in ((preflight,'FAIL'),(compatibility,'HOLD')):
            report=self.root/(state+'.json');before=self.snapshot();processor='inspect' if module is preflight else 'export'
            with patch.object(module,processor,side_effect=ValueError('explicit validation failure')),redirect_stdout(io.StringIO()):
                self.assertNotEqual(module.main(self.args(module,report)),0)
            self.assertEqual(json.loads(report.read_text())['state'],state)
            self.assertEqual({p:data for p,data in self.snapshot().items() if p!=str(report)},before)

    def test_racing_existing_report_refuses_exclusive_create_before_processing(self):
        for module in (preflight,compatibility):
            for kind in ('file','symlink'):
                report=self.root/(module.__name__.split('.')[-1]+'-race-'+kind+'.json')
                def race(path,*media):
                    if kind=='symlink':path.symlink_to(self.source)
                    else:path.write_bytes(b'CONCURRENT_REPORT_PRESERVED')
                    return path
                processor='inspect' if module is preflight else 'export'
                with patch.object(module,'validate_report_path',side_effect=race),patch.object(module,processor) as processing,redirect_stderr(io.StringIO()):
                    self.assertNotEqual(module.main(self.args(module,report)),0);processing.assert_not_called()
                self.assertEqual(report.read_bytes(),b'ORIGINAL_MASTER_BYTES' if kind=='symlink' else b'CONCURRENT_REPORT_PRESERVED')
                self.assertEqual(self.source.read_bytes(),b'ORIGINAL_MASTER_BYTES')
                self.assertEqual(self.target.read_bytes(),b'EXISTING_DERIVATIVE_BYTES')

    def test_real_cli_alias_returns_nonzero_and_preserves_media(self):
        for module in (preflight,compatibility):
            before=self.snapshot()
            result=subprocess.run([sys.executable,module.__file__,*self.args(module,self.source)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('Report path refused',result.stderr)
            self.assertEqual(self.snapshot(),before)


if __name__=='__main__':unittest.main()
