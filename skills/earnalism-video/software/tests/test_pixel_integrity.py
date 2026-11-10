import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import importlib.util
spec = importlib.util.spec_from_file_location('pixel_integrity', Path(__file__).resolve().parents[1]/'pixel_integrity.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class PixelRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.reference = self.root/'reference.pgm'
        self.reference.write_bytes(b'P5\n64 64\n255\n'+bytes([100])*4096)
        # Three frames: only frame zero is corrupt. Valid H264 encoding must not clear it.
        raw = bytes([220])*4096+bytes([100])*8192
        self.video = self.root/'video.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','rawvideo','-pixel_format','gray',
            '-video_size','64x64','-framerate','30','-i','-','-c:v','libx264','-crf','0',
            '-pix_fmt','yuv420p',str(self.video)],input=raw,check=True)
        self.config = self.root/'config.json'
        self.spec = {'schema':p.SCHEMA,'dimensions':[64,64],
            'reference_origin':'independent_composition_stills','checks':[
                {'reference':'reference.pgm','reference_sha256':p.sha(self.reference),
                 'frames':[0,3],'rect':[0,0,64,64],'sample_size':[16,16],'max_mae':5}]}
        self.save()

    def tearDown(self): self.tmp.cleanup()
    def save(self): self.config.write_text(json.dumps(self.spec))
    def test_valid_codec_does_not_hide_corrupt_frame_zero(self):
        r=p.analyze(self.video,self.config)
        self.assertEqual(r['state'],'PIXEL_REGRESSION_HOLD')
        self.assertEqual(r['checks'][0]['flagged_frames'],[0])
    def test_exclusive_range_preserves_frame_indices(self):
        self.spec['checks'][0]['frames']=[1,3];self.save()
        r=p.analyze(self.video,self.config)
        self.assertEqual(r['state'],p.PASS)
        self.assertEqual(r['checks'][0]['checked_frames'],2)
    def test_overrun_is_not_partial_pass(self):
        self.spec['checks'][0]['frames']=[0,4];self.save()
        with self.assertRaisesRegex(ValueError,'Incomplete'):p.analyze(self.video,self.config)
    def test_changed_reference_rejected(self):
        self.reference.write_bytes(b'P5\n64 64\n255\n'+bytes([99])*4096)
        with self.assertRaisesRegex(ValueError,'reference'):p.analyze(self.video,self.config)
    def test_wrong_geometry_rejected(self):
        self.spec['dimensions']=[65,64];self.save()
        with self.assertRaisesRegex(ValueError,'dimensions'):p.analyze(self.video,self.config)
    def test_nan_tolerance_rejected(self):
        self.spec['checks'][0]['max_mae']=float('nan');self.save()
        with self.assertRaisesRegex(ValueError,'tolerance'):p.analyze(self.video,self.config)
    def test_stale_report_cannot_clear_changed_source(self):
        self.spec['checks'][0]['frames']=[1,3];self.save()
        r=p.analyze(self.video,self.config); report=self.root/'report.json';report.write_text(json.dumps(r))
        p.verify_receipt(report,self.video)
        self.video.write_bytes(self.video.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'stale'):p.verify_receipt(report,self.video)
    def test_existing_report_and_media_not_overwritten(self):
        before=p.sha(self.video)
        with self.assertRaisesRegex(ValueError,'Preserve'):
            import sys
            from unittest.mock import patch
            with patch.object(sys,'argv',['pixel_integrity.py',str(self.video),'--config',str(self.config),'--report',str(self.video)]):p.main()
        self.assertEqual(before,p.sha(self.video))

class CoverageContract(unittest.TestCase):
    def spec(self):
        return {'dimensions':[64,64],'temporal_probe':{'frames':[0,5]},'checks':[
            {'rect':[0,0,64,64],'frames':[0,1]},
            {'rect':[0,0,64,64],'frames':[4,5]},
            {'rect':[2,2,20,20],'frames':[0,3]},
            {'rect':[2,2,20,20],'frames':[3,5]}]}
    def test_contiguous_phase_references(self):
        self.assertTrue(p.validate_delivery_coverage(self.spec(),5))
    def test_gap_cannot_clear_delivery(self):
        s=self.spec();s['checks'][3]['frames']=[4,5]
        with self.assertRaises(ValueError):p.validate_delivery_coverage(s,5)
    def test_missing_full_frame_zero_cannot_clear_delivery(self):
        s=self.spec();s['checks'].pop(0)
        with self.assertRaises(ValueError):p.validate_delivery_coverage(s,5)
    def test_failed_receipt_cannot_clear_delivery(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'video.mp4';source.write_bytes(b'exact source')
            report=Path(d)/'report.json';report.write_text(json.dumps({
                'schema':p.SCHEMA,'state':'PIXEL_REGRESSION_HOLD',
                'source_sha256':p.sha(source),'checker_sha256':p.sha(p.__file__)}))
            with self.assertRaisesRegex(ValueError,'failed'):
                p.verify_receipt(report,source)



class WholePictureDiscontinuities(unittest.TestCase):
    def test_non_anchor_flash_is_surfaced(self):
        a=bytes([100])*16; b=bytes([100])*8+bytes([240])*8
        flags=p.isolated_frame_candidates(a+a+b+a+a,16,5,6,.35)
        self.assertEqual([f['frame'] for f in flags],[2])
    def test_persistent_scene_cut_is_not_corruption(self):
        a=bytes([100])*16; b=bytes([240])*16
        self.assertEqual(p.isolated_frame_candidates(a+a+b+b+b,16,5,6,.35),[])
    def test_ordinary_smooth_motion_is_not_flash(self):
        frames=b''.join(bytes([100+i*3])*16 for i in range(5))
        self.assertEqual(p.isolated_frame_candidates(frames,16,5,6,.35),[])
    def test_missing_frames_fail_temporal_check(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            p.isolated_frame_candidates(bytes([100])*16,16,5,6,.35)
    def test_delivery_cannot_use_static_anchor_only(self):
        spec=CoverageContract().spec();spec.pop('temporal_probe')
        with self.assertRaisesRegex(ValueError,'temporal'):
            p.validate_delivery_coverage(spec,5)


class BoundaryCoverage(unittest.TestCase):
    def test_missing_last_frame_cannot_clear_delivery(self):
        s=CoverageContract().spec();s['checks'].pop(1)
        with self.assertRaisesRegex(ValueError,'last-body'):p.validate_delivery_coverage(s,5)


if __name__=='__main__':unittest.main()
