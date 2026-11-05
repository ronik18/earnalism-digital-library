import pathlib,sys,tempfile,unittest,threading,urllib.request,urllib.error
from functools import partial
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from review_server import ReviewHandler
class RangeTests(unittest.TestCase):
 def test_actual_media_byte_ranges_and_unsatisfiable_range(self):
  with tempfile.TemporaryDirectory() as d:
   pathlib.Path(d,'media.mp4').write_bytes(b'0123456789')
   server=ThreadingHTTPServer(('127.0.0.1',0),partial(ReviewHandler,directory=d));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    url=f'http://127.0.0.1:{server.server_port}/media.mp4'
    with self.assertRaises(urllib.error.HTTPError) as listing:urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/')
    self.assertEqual(listing.exception.code,404)
    for header,expected in [('bytes=3-6',b'3456'),('bytes=-3',b'789'),('bytes=8-',b'89')]:
     with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':header})) as r:self.assertEqual(r.status,206);self.assertEqual(r.read(),expected)
    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=20-'}))
    self.assertEqual(error.exception.code,416)
   finally:server.shutdown();server.server_close();thread.join()
