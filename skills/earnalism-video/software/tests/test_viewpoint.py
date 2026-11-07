import pathlib,subprocess,unittest
class ViewpointTests(unittest.TestCase):
 def test_actual_viewpoint_bridge_and_mobile_layout(self):
  subprocess.run(['node','--test',str(pathlib.Path(__file__).resolve().parents[1]/'src/viewpoint.test.mjs')],check=True,capture_output=True)
