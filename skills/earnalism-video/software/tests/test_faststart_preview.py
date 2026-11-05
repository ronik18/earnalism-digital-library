import unittest,tempfile,pathlib,subprocess,sys,struct
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio
class FaststartPreviewTests(unittest.TestCase):
 def test_mp4_previews_are_progressive_and_keep_audio_video_streams(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=navy:s=160x284:r=30:d=1','-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(p/'portrait-captioned.mp4')],check=True)
   import shutil;shutil.copy2(p/'portrait-captioned.mp4',p/'landscape.mp4');studio.create_faststart_previews(p)
   for name in ('landscape-preview.mp4','portrait-preview.mp4'):
    data=(p/name).read_bytes();atoms=[];offset=0
    while offset<len(data):
     size,kind=struct.unpack('>I4s',data[offset:offset+8]);atoms.append(kind);self.assertGreater(size,0);offset+=size
    self.assertLess(atoms.index(b'moov'),atoms.index(b'mdat'))
    stream_hash=lambda f:subprocess.check_output(['ffmpeg','-v','error','-i',str(f),'-map','0','-c','copy','-f','streamhash','-'])
    self.assertEqual(stream_hash(p/'portrait-captioned.mp4'),stream_hash(p/name))
 def test_primary_preview_is_mp4_and_recovery_replaces_the_player(self):
  template=(studio.BASE/'watch-template.html').read_text()
  self.assertLess(template.index('landscape-preview.mp4'),template.index('landscape-preview.webm'))
  self.assertIn('old.replaceWith(fresh)',template);self.assertIn("document.addEventListener('visibilitychange'",template)
