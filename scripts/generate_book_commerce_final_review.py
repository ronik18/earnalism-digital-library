#!/usr/bin/env python3
import hashlib,json,os,shutil,sys,zipfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path('.').resolve(); work=Path(os.environ.get('BOOK_COMMERCE_REVIEW_WORK','uat/evidence/book-commerce-final-review')).resolve(); before=work/'before'; current=work/'current'; out=work/'owner-review-final'; out.mkdir(parents=True,exist_ok=True)
required=['capture-results.json','book-interaction-results.json','fixture-offer-results.json','commerce-geometry-results.json','heading-results.json','book-content-capability-results.json','live-offer-results.json','book-commerce-browser-results.json']
for name in required:
 if not (current/name).is_file() or not (current/name).stat().st_size: raise RuntimeError('Missing current evidence '+name)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
captures=json.loads((current/'capture-results.json').read_text()); head=captures['provenance']['actual_checkout_sha']
if captures['provenance']['pr_head_sha']!=head: raise RuntimeError('PR head and checkout head mismatch')
for file in current.iterdir():
 if file.is_file(): shutil.copy2(file,out/file.name)
for file in before.glob('*.png'):
 shutil.copy2(file,out/f'before-{file.name}')
before_capture=json.loads((before/'capture-results.json').read_text()) if (before/'capture-results.json').exists() else {'states':[]}
def state(report, state_id): return next((x for x in report.get('states',[]) if x['id']==state_id),None)
def height(before_id, after_id):
 a,b=state(before_capture,before_id),state(captures,after_id)
 if not a or not b:return {'status':'FAIL','reason':'missing capture'}
 reduction=a['document_height']-b['document_height']
 return {'status':'PASS' if reduction>0 else 'FAIL','before':a['document_height'],'after':b['document_height'],'reduction_pixels':reduction,'reduction_percent':round(reduction*100/a['document_height'],2) if a['document_height'] else 0}
heights={'desktop':height('book-about-desktop-1440','book-about-desktop-1440'),'mobile':height('book-about-mobile-390','book-about-mobile-390')}
(out/'book-height-results.json').write_text(json.dumps(heights,indent=2)+'\n')
imgs=sorted(out.glob('*.png')); tiles=[]
for img in imgs:
 im=Image.open(img).convert('RGB'); im.thumbnail((380,240)); tiles.append((img.name,im.copy()))
sheet=Image.new('RGB',(1600,max(1,((len(tiles)+3)//4))*280),'#f6f1e8'); d=ImageDraw.Draw(sheet)
for i,(name,im) in enumerate(tiles):
 x=(i%4)*400+10;y=(i//4)*280+28;d.text((x,y-18),name,fill='#142019',font=ImageFont.load_default());sheet.paste(im,(x,y))
sheet.save(out/'contact-sheet.png'); sheet.save(out/'owner-review.pdf','PDF',resolution=144.0)
summary={'head':head,'book_interaction':json.loads((current/'book-interaction-results.json').read_text()),'book_heights':heights,'commerce':json.loads((current/'commerce-geometry-results.json').read_text()),'headings':json.loads((current/'heading-results.json').read_text()),'browser_matrix':json.loads((current/'book-commerce-browser-results.json').read_text())}
(out/'score-report.json').write_text(json.dumps(summary,indent=2)+'\n')
(out/'provenance.json').write_text(json.dumps({'schema_version':'pr341-book-commerce-provenance-v1','pr_head_sha':captures['provenance']['pr_head_sha'],'actual_checkout_sha':head,'tree_sha':captures['provenance']['tree_sha'],'workflow_event_sha':captures['provenance']['workflow_event_sha'],'capture_script_sha256':captures['provenance']['capture_script_sha256'],'browser':captures['provenance']['browser'],'browser_version':captures['provenance']['browser_version'],'fixture_sha256':captures['provenance']['fixture_sha256']},indent=2)+'\n')
(out/'owner-review.html').write_text('<!doctype html><title>PR341 Book & Commerce review</title><h1>PR341 Book Detail & Commerce focused review</h1><p>Exact head: '+head+'</p><img src="contact-sheet.png" style="max-width:100%"><pre>'+json.dumps(summary,indent=2)+'</pre>')
files=[]
for p in sorted(out.iterdir()):
 if p.name in {'manifest.json','artifact.zip'}: continue
 files.append({'relative_path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
(out/'manifest.json').write_text(json.dumps({'head':head,'files':files},indent=2)+'\n')
with zipfile.ZipFile(out/'artifact.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in out.iterdir():
  if p.name!='artifact.zip':z.write(p,p.name)
print(json.dumps({'status':'PASS','head':head,'artifact_sha256':sha(out/'artifact.zip')}))
