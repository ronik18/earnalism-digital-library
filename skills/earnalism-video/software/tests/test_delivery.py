import os,functools,http.server,json,pathlib,subprocess,sys,tempfile,threading,unittest,zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio
class TransferTests(unittest.TestCase):
 def test_archive_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);z=p/'bad.zip'
   with zipfile.ZipFile(z,'w') as f:f.writestr('../escape','x')
   with self.assertRaisesRegex(ValueError,'Unsafe'):studio.import_narration(z,p/'out')
 def test_archive_hash_corruption_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);z=p/'bad.zip'
   with zipfile.ZipFile(z,'w') as f:
    f.writestr('episode.json','{}');f.writestr('transfer-manifest.json',json.dumps({'episode.json':'0'*64}))
   with self.assertRaisesRegex(ValueError,'hash mismatch'):studio.import_narration(z,p/'out')
 def test_archive_valid_readback(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);data=(studio.BASE/'episodes/private-test.json').read_bytes();z=p/'ok.zip'
   with zipfile.ZipFile(z,'w') as f:
    f.writestr('episode.json',data);f.writestr('transfer-manifest.json',json.dumps({'episode.json':__import__('hashlib').sha256(data).hexdigest()}))
   studio.import_narration(z,p/'out');self.assertEqual((p/'out/episode.json').read_bytes(),data)
 def test_real_download_and_decode_with_tone_fixture(self):
  # This is an explicit tone fixture, never speech/narration success.
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);movie=p/'tone-fixture.mp4'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=navy:s=160x284:r=30:d=1','-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(movie)],check=True)
   handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=d)
   server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    result=studio.verify_download(f'http://127.0.0.1:{server.server_port}/tone-fixture.mp4',studio.sha(movie),p/'received.mp4')
    self.assertEqual(result['decode'],'PASS');self.assertTrue(result['audio_present']);self.assertEqual(result['sha256'],studio.sha(movie))
   finally:server.shutdown();server.server_close();thread.join()
 def test_silent_audio_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   movie=pathlib.Path(d)/'silent.mp4'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=navy:s=160x284:r=30:d=1','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(movie)],check=True)
   with self.assertRaisesRegex(ValueError,'Silent'):studio.verify_media(movie)
 def test_all_embedded_notebook_modules_compile(self):
  import ast
  n=json.loads((pathlib.Path(os.environ.get('EARNALISM_TEST_PROJECT',studio.BASE.parent))/'Earnalism_Video_Narration_Pipeline.ipynb').read_text())
  for c in n['cells']:
   if c['cell_type']!='code':continue
   tree=ast.parse(''.join(c['source']))
   for a in tree.body:
    if isinstance(a,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FILES' for t in a.targets):
     for name,text in ast.literal_eval(a.value).items():
      if name.endswith('.py'):compile(text,name,'exec')
if __name__=='__main__':unittest.main()
