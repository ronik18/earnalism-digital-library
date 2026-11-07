"""Real silent FFmpeg fixture: frame/duration preservation, not narration QA."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from .append_ident import append, probe


class AppendIdentTests(unittest.TestCase):
    def test_real_h264_append_preserves_body_and_has_exact_silent_frames(self):
        with tempfile.TemporaryDirectory(prefix='sky-ident-engineering-') as tmp:
            root=Path(tmp)
            subprocess.run(['ffmpeg','-v','error','-n','-f','lavfi','-i',
              'color=c=navy:s=1080x1920:r=30','-frames:v','6','-an','-c:v','libx264',
              '-crf','20','-pix_fmt','yuv420p','-colorspace','bt709','-color_trc','bt709',
              '-color_primaries','bt709','-video_track_timescale','90000',
              str(root/'body-animation.mp4')],check=True)
            result=append(root,6)
            self.assertEqual(result['decoded_final_frames'],96)
            self.assertFalse(result['audio_processed'])
            bounds=result['portrait_ident_essential_review_rect']
            self.assertGreaterEqual(bounds['x'],72)
            self.assertLessEqual(bounds['x']+bounds['width'],900)
            self.assertGreaterEqual(bounds['y'],270)
            self.assertLessEqual(bounds['y']+bounds['height'],1500)
            self.assertEqual(len(probe(root/'animation.mp4')['streams']),1)
            before=(root/'animation.mp4').read_bytes()
            with self.assertRaisesRegex(ValueError,'Existing visual append'):
                append(root,6)
            self.assertEqual(before,(root/'animation.mp4').read_bytes())

    def test_invalid_frame_count_stops_before_any_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for value in (0,-1,True,3.5):
                with self.assertRaises(ValueError):append(root,value)
            self.assertEqual(list(root.iterdir()),[])


if __name__=='__main__':unittest.main()
