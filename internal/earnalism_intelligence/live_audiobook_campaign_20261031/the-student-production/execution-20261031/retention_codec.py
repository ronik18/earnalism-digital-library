"""Offline notebook-output retention codec. No inference, network or allocation.

A local round-trip test is not proof of Google Drive autosave or audio quality.
The next real run must pass a small saved-notebook transport probe before synthesis.
"""
from pathlib import Path
import base64,hashlib,json
SCHEMA='earnalism.notebook-retained-file.v1'
def encode_file(path,relative_name):
 p=Path(path);name=Path(relative_name)
 if name.is_absolute() or '..' in name.parts:raise ValueError('Unsafe retained path')
 data=p.read_bytes()
 return {'schema':SCHEMA,'name':name.as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'base64':base64.b64encode(data).decode('ascii')}
def restore_outputs(notebook,output,required=()):
 root=Path(output).resolve();root.mkdir(exist_ok=True,parents=True);found={}
 for cell in notebook.get('cells',[]):
  for item in cell.get('outputs',[]):
   row=item.get('data',{}).get('application/json')
   if not isinstance(row,dict) or row.get('schema')!=SCHEMA:continue
   name=Path(row['name']);target=(root/name).resolve()
   if name.is_absolute() or '..' in name.parts or not target.is_relative_to(root):raise ValueError('Unsafe retained path')
   if not 0<=row['bytes']<=20_000_000:raise ValueError('Unexpected retained file size')
   data=base64.b64decode(row['base64'],validate=True)
   sha=hashlib.sha256(data).hexdigest()
   if len(data)!=row['bytes'] or sha!=row['sha256']:raise ValueError('Retained checksum mismatch')
   if name.as_posix() in found and found[name.as_posix()]!=sha:raise ValueError('Conflicting retained file versions')
   if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=sha:raise ValueError('Refuse overwrite of different retained bytes')
   target.parent.mkdir(exist_ok=True,parents=True);target.write_bytes(data);found[name.as_posix()]=sha
 if set(required)-set(found):raise ValueError('Required audio/receipt files missing')
 return found
