"""Private review aid from hash-verified final-frame evidence; no approval generation."""
from pathlib import Path
import json,subprocess,os,sys
from strict_quality import load,sha
p=Path(sys.argv[1]).resolve();r=load(p/'strict-quality-review.json');out=Path(sys.argv[2]).resolve();out.mkdir(parents=True)
index=[]
for fmt in ('Landscape','Portrait'):
 rows=[(name,row) for name,row in r['graphical']['frames'].items() if f':{fmt}:' in name]
 for batch in range(0,len(rows),6):
  sub=out/f'{fmt}-{batch//6:02d}';sub.mkdir();group=rows[batch:batch+6]
  for i,(name,row) in enumerate(group):
   ref=row['evidence'][0];src=p/ref['path']
   if sha(src)!=ref['sha256']:raise ValueError('Frame changed')
   os.link(src,sub/f'frame-{i:02d}.png')
  sheet=out/f'{fmt}-{batch//6:02d}.png';w,h=(640,360) if fmt=='Landscape' else (360,640)
  subprocess.run(['ffmpeg','-v','error','-n','-framerate','1','-i',str(sub/'frame-%02d.png'),'-vf',f'scale={w}:{h},tile=3x2:nb_frames={len(group)}:padding=4:color=0x445566','-frames:v','1',str(sheet)],check=True)
  index.append({'sheet':sheet.name,'frames':[{'id':name,'seconds':row['seconds']} for name,row in group]})
(out/'index.json').write_text(json.dumps(index,indent=2));print(out)
