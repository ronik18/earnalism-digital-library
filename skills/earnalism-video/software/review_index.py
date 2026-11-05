"""Resolve the current private review by verified hashes, never by an old guide URL."""
from pathlib import Path
import json,hashlib,argparse,urllib.parse,urllib.request

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolve(record,check_http=False):
 record=Path(record).resolve();data=json.loads(record.read_text());root=record.parent.parent
 if data.get('private') is not True:raise ValueError('Private review record required')
 url=urllib.parse.urlsplit(data['base_url'])
 if url.scheme!='http' or url.hostname!='127.0.0.1' or url.username or url.password or url.query or url.fragment or url.path not in ('','/'):raise ValueError('Loopback-only review URL required')
 folder=(root/data['candidate']).resolve();manifest=folder/'delivery-manifest.json'
 if digest(manifest)!=data['delivery_manifest_sha256']:raise ValueError('Stale candidate manifest binding')
 files=json.loads(manifest.read_text())
 if not files or any(Path(n).name!=n or digest(folder/n)!=h for n,h in files.items()):raise ValueError('Candidate files changed')
 kit=root/data['review_kit']
 if digest(kit)!=data['review_kit_sha256']:raise ValueError('Review kit changed')
 urls={n:data['base_url'].rstrip('/')+'/'+n for n in ('watch.html','portrait-short.html','participant.html','participant-shorts.html')}
 for n,u in urls.items():
  if n not in files:raise ValueError('Missing private review page: '+n)
  if check_http:
   body=urllib.request.urlopen(u,timeout=10).read()
   if hashlib.sha256(body).hexdigest()!=files[n]:raise ValueError('Server is serving a different review edition')
 return {**data,'candidate_absolute':str(folder),'verified_pages':urls,'http_checked':check_http,'publication_approval':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('record');p.add_argument('--check-http',action='store_true');a=p.parse_args();print(json.dumps(resolve(a.record,a.check_http),indent=2))
