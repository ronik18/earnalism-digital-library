"""Quick preflight must not secretly run the costly full regression suite."""
import pathlib,subprocess,sys,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class VerifyModesTests(unittest.TestCase):
 def test_quick_mode_skips_full_tests_and_full_mode_executes_them(self):
  candidates=[ROOT.parent/'scripts/verify.py',ROOT/'skill-update-lean/scripts/verify.py'];script=next(p for p in candidates if p.is_file())
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);sw=root/'video_studio';(sw/'tests').mkdir(parents=True)
   (sw/'studio.py').write_text("print('source checksum preflight')\n");(sw/'expectations.py').write_text("print('default preflight')\n")
   (sw/'tests/test_expensive.py').write_text("import unittest\nclass Fixture(unittest.TestCase):\n def test_full_was_run(self):self.fail('FULL_TEST_EXECUTED')\n")
   quick=subprocess.run([sys.executable,str(script),'--project',str(root)],capture_output=True,text=True)
   self.assertEqual(quick.returncode,0);self.assertIn('QUICK_PREFLIGHT_PASS',quick.stdout);self.assertNotIn('FULL_TEST_EXECUTED',quick.stderr)
   full=subprocess.run([sys.executable,str(script),'--project',str(root),'--full'],capture_output=True,text=True)
   self.assertNotEqual(full.returncode,0);self.assertIn('FULL_TEST_EXECUTED',full.stderr)
 def test_full_mode_discovers_renderer_layout_and_comparison_tests(self):
  candidates=[ROOT.parent/'scripts/verify.py',ROOT/'skill-update-lean/scripts/verify.py'];script=next(p for p in candidates if p.is_file())
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);sw=root/'video_studio'
   for folder in ('src','tests','comparison-player'):(sw/folder).mkdir(parents=True)
   (sw/'studio.py').write_text("print('checksum')\n");(sw/'expectations.py').write_text("print('defaults')\n")
   (sw/'tests/test_ok.py').write_text("import unittest\nclass Fixture(unittest.TestCase):\n def test_ok(self):pass\n")
   for folder,marker in [('src','RENDERER_DISCOVERED'),('tests','LAYOUT_DISCOVERED'),('comparison-player','COMPARE_DISCOVERED')]:
    (sw/folder/'discovery.test.mjs').write_text("import test from 'node:test';test('"+marker+"',()=>{});\n")
   result=subprocess.run([sys.executable,str(script),'--project',str(root),'--full'],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
   for marker in ['RENDERER_DISCOVERED','LAYOUT_DISCOVERED','COMPARE_DISCOVERED']:self.assertIn(marker,result.stdout)
if __name__=='__main__':unittest.main()
