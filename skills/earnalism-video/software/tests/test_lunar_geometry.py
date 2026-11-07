import pathlib,subprocess,unittest
class LunarGeometryTests(unittest.TestCase):
 def test_actual_renderer_geometry(self):
  subprocess.run(['node','--test',str(pathlib.Path(__file__).with_name('lunar-geometry.test.mjs'))],check=True,capture_output=True)
