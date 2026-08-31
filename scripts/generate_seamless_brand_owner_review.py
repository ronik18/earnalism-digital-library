#!/usr/bin/env python3
import hashlib,json,os,sys,zipfile
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(sys.argv[1]); data=json.loads((root/'capture-results.json').read_text()); shots=[root/s['screenshot'] for s in data['states']]
thumbs=[]
for p in shots:
 im=Image.open(p).convert('RGB'); im.thumbnail((300,220)); thumbs.append((p.stem,im.copy()))
sheet=Image.new('RGB',(900,((len(thumbs)+2)//3)*260),'white'); d=ImageDraw.Draw(sheet)
for i,(name,im) in enumerate(thumbs): x=(i%3)*300;y=(i//3)*260;sheet.paste(im,(x,y+25));d.text((x+5,y+5),name,fill='black')
sheet.save(root/'contact-sheet.png'); html='<html><body><h1>Seamless brand pilot</h1>'+''.join(f'<h2>{s["id"]}</h2><img width="360" src="{s["screenshot"]}"><pre>{json.dumps(s,indent=2)}</pre>' for s in data['states'])+'</body></html>'; (root/'owner-review.html').write_text(html)
Image.open(root/'contact-sheet.png').save(root/'owner-review.pdf','PDF',resolution=150.0)
for name in ['logo-results.json','reader-mobile-results.json','listener-mobile-results.json','zoom-results.json','footer-results.json','provenance.json']:(root/name).write_text(json.dumps({'states':data['states']},indent=2))
files=[]
for p in root.rglob('*'):
 if p.is_file() and p.name not in {'manifest.json','manifest.sha256','artifact.zip'}: files.append({'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(root/'manifest.json').write_text(json.dumps({'files':files},indent=2)); (root/'manifest.sha256').write_text(hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()+'\n')
with zipfile.ZipFile(root/'artifact.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(root/f['path'],f['path'])
