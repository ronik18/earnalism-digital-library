"""Loopback-only private review server with byte ranges for media seeking."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import argparse,re
class ReviewHandler(SimpleHTTPRequestHandler):
 def list_directory(self,path):
  self.send_error(404,"Directory browsing is disabled")
  return None
 def send_head(self):
  self.remaining=None
  header=self.headers.get('Range')
  if not header:return super().send_head()
  path=self.translate_path(self.path)
  try:f=open(path,'rb')
  except OSError:return super().send_head()
  f.seek(0,2);size=f.tell();match=re.fullmatch(r'bytes=(\d*)-(\d*)',header)
  try:
   if not match or not any(match.groups()):raise ValueError()
   a,b=match.groups()
   if a:start=int(a);end=min(int(b),size-1) if b else size-1
   else:start=max(0,size-int(b));end=size-1
   if start<0 or start>=size or end<start:raise ValueError()
  except ValueError:
   f.close();self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return None
  self.send_response(206);self.send_header('Content-Type',self.guess_type(path));self.send_header('Accept-Ranges','bytes');self.send_header('Content-Range',f'bytes {start}-{end}/{size}');self.send_header('Content-Length',str(end-start+1));self.end_headers();f.seek(start);self.remaining=end-start+1;return f
 def copyfile(self,source,outputfile):
  if self.remaining is None:return super().copyfile(source,outputfile)
  remaining=self.remaining
  while remaining:
   data=source.read(min(65536,remaining))
   if not data:break
   outputfile.write(data);remaining-=len(data)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--port',type=int,default=8775);a=p.parse_args()
 from functools import partial
 ThreadingHTTPServer(('127.0.0.1',a.port),partial(ReviewHandler,directory=a.directory)).serve_forever()
