"""Hashed text chunks for UI-only recovery when Colab rich output/download fails."""
from pathlib import Path
import hashlib,json,base64,argparse
sha=lambda b:hashlib.sha256(b).hexdigest()
def export(archive,destination,chunk_bytes=196608):
 data=Path(archive).read_bytes();p=Path(destination);p.mkdir(parents=True,exist_ok=False);rows=[]
 for i,start in enumerate(range(0,len(data),chunk_bytes)):
  raw=data[start:start+chunk_bytes];name=f'part-{i:03}.txt';text=base64.b64encode(raw).decode();(p/name).write_text(text)
  rows.append({'name':name,'bytes':len(raw),'sha256':sha(raw)})
 m={'archive_name':Path(archive).name,'archive_bytes':len(data),'archive_sha256':sha(data),'parts':rows};(p/'manifest.json').write_text(json.dumps(m,indent=2));return m

def assemble(source,destination):
 p=Path(source);m=json.loads((p/'manifest.json').read_text());dest=Path(destination)
 if dest.exists():raise FileExistsError(dest)
 names=[x['name'] for x in m['parts']]
 if len(names)!=len(set(names)) or any(Path(n).name!=n for n in names):raise ValueError('Unsafe/duplicate chunk names')
 data=bytearray()
 for r in m['parts']:
  raw=base64.b64decode((p/r['name']).read_text().strip(),validate=True)
  if len(raw)!=r['bytes'] or sha(raw)!=r['sha256']:raise ValueError('Chunk mismatch')
  data.extend(raw)
 if len(data)!=m['archive_bytes'] or sha(data)!=m['archive_sha256']:raise ValueError('Archive mismatch')
 dest.write_bytes(data);return m
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('command',choices=['export','assemble']);a.add_argument('source');a.add_argument('destination');x=a.parse_args();print(json.dumps(globals()[x.command](x.source,x.destination),indent=2))
