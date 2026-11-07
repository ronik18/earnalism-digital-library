import pathlib,sys,unittest,tempfile,subprocess
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from label_ink_check import check,ink_pixels
class InkTests(unittest.TestCase):
 def test_connector_color_does_not_stand_in_for_label_ink(self):
  self.assertEqual(ink_pixels(bytes([140,215,223])*200),0)
  with patch('label_ink_check.subprocess.check_output',return_value=bytes([140,215,223])*200),self.assertRaisesRegex(ValueError,'missing or obscured'):check('fixture',(0,0,20,10))
 def test_label_presence_is_not_claimed_as_ocr_or_approval(self):
  with patch('label_ink_check.subprocess.check_output',return_value=bytes([155,180,195])*200):r=check('fixture',(0,0,20,10))
  self.assertEqual(r['matching_ink_pixels'],200);self.assertFalse(r['human_approval'])
  with patch('label_ink_check.subprocess.check_output',return_value=bytes([220,100,20])*200):self.assertEqual(check('fixture',(0,0,20,10),reference=(220,100,20))['matching_ink_pixels'],200)

 def test_odd_pixel_regions_work_on_real_yuv420_encoded_video(self):
  with tempfile.TemporaryDirectory() as d:
   movie=pathlib.Path(d)/'color.mp4'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=0x9bb4c3:s=32x32:d=0.1','-c:v','libx264','-pix_fmt','yuv420p',str(movie)],check=True)
   result=check(movie,(1,1,3,3),minimum=1)
   self.assertEqual(result['matching_ink_pixels'],9)

if __name__=='__main__':unittest.main()
