"""Hashed text chunks for UI-only recovery when Colab rich output/download fails."""
from pathlib import Path
import hashlib,json,base64,argparse,ast,re
sha=lambda b:hashlib.sha256(b).hexdigest()
VISIBLE_ARCHIVE_MAX_BYTES=8*1024**2

def recover_visible_data_link(href,destination,*,expected_bytes,expected_sha256):
 """Decode an already-observed visible href offline; never fetch or inspect a page.

 The caller supplies the independently observed archive size and digest. This
 establishes byte delivery only; normal safe ZIP/member import remains pending.
 """
 dest=Path(destination)
 if dest.exists() or dest.is_symlink():raise FileExistsError(dest)
 if type(expected_bytes) is not int or not 0<expected_bytes<=VISIBLE_ARCHIVE_MAX_BYTES:raise ValueError('Visible archive size must be between 1 byte and 8 MiB')
 if not isinstance(expected_sha256,str) or not re.fullmatch('[a-f0-9]{64}',expected_sha256):raise ValueError('Expected archive SHA256 required')
 prefix='data:application/zip;base64,'
 if not isinstance(href,str) or not href.startswith(prefix):raise ValueError('Exact visible ZIP data href required')
 # Check the bound before copying/decoding the payload. Do not accept a whole
 # HTML/snapshot, remote URL, folded base64, or executable recovery expression.
 if len(href)-len(prefix)!=4*((expected_bytes+2)//3):raise ValueError('Visible archive encoded size mismatch')
 encoded=href[len(prefix):]
 try:raw=base64.b64decode(encoded,validate=True)
 except ValueError:raise ValueError('Invalid visible archive base64') from None
 if base64.b64encode(raw).decode('ascii')!=encoded:raise ValueError('Noncanonical visible archive base64')
 if len(raw)!=expected_bytes or sha(raw)!=expected_sha256:raise ValueError('Visible archive hash/size mismatch')
 # Exclusive creation also rejects a destination/symlink introduced after the
 # initial check. Verification failures leave no output and never overwrite.
 with dest.open('xb') as handle:handle.write(raw)
 return {'archive_sha256':expected_sha256,'archive_bytes':len(raw),'visible_href_sha256':sha(href.encode('ascii')),'source_kind':'already_observed_visible_data_href','source_executed':False,'network_accessed':False,'media_qualification':'PENDING_NORMAL_ARCHIVE_IMPORT'}

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

def recover_notebook(source,destination):
 """Decode one saved recovery literal; never execute notebook source or outputs."""
 source=Path(source);dest=Path(destination)
 if dest.exists() or dest.is_symlink():raise FileExistsError(dest)
 if source.stat().st_size>16*1024**2:raise ValueError('Recovery notebook exceeds16MiB limit')
 notebook=json.loads(source.read_text());matches=[]
 keys={'EARNALISM_PRIVATE_RECOVERY_SHA256','EARNALISM_PRIVATE_RECOVERY_BASE64'}
 for cell in notebook.get('cells',[]):
  text=cell.get('source',[]);text=text if isinstance(text,str) else ''.join(text)
  if not text.startswith('EARNALISM_PRIVATE_RECOVERY_SHA256='):continue
  values={};tree=ast.parse(text)
  if len(tree.body)!=2:raise ValueError('Recovery cell must contain exactly two string assignments')
  for node in tree.body:
   if not isinstance(node,ast.Assign) or len(node.targets)!=1 or not isinstance(node.targets[0],ast.Name) or not isinstance(node.value,ast.Constant) or not isinstance(node.value.value,str):raise ValueError('Invalid recovery literal')
   name=node.targets[0].id
   if name not in keys or name in values:raise ValueError('Unknown/duplicate recovery assignment')
   values[name]=node.value.value
  if set(values)!=keys:raise ValueError('Incomplete recovery literal')
  expected=values['EARNALISM_PRIVATE_RECOVERY_SHA256'];encoded=values['EARNALISM_PRIVATE_RECOVERY_BASE64']
  if not re.fullmatch('[a-f0-9]{64}',expected) or len(encoded)>12*1024**2:raise ValueError('Invalid recovery digest/size')
  raw=base64.b64decode(encoded,validate=True)
  if len(raw)>8*1024**2 or sha(raw)!=expected:raise ValueError('Recovery archive hash/size mismatch')
  matches.append((raw,expected))
 if len(matches)!=1:raise ValueError('Exactly one unambiguous recovery cell required')
 raw,expected=matches[0]
 with dest.open('xb') as handle:handle.write(raw)
 return {'archive_sha256':expected,'archive_bytes':len(raw),'notebook_sha256':sha(source.read_bytes()),'source_executed':False,'media_qualification':'PENDING_NORMAL_ARCHIVE_IMPORT'}

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('command',choices=['export','assemble','recover-notebook']);a.add_argument('source');a.add_argument('destination');x=a.parse_args();print(json.dumps({'export':export,'assemble':assemble,'recover-notebook':recover_notebook}[x.command](x.source,x.destination),indent=2))
