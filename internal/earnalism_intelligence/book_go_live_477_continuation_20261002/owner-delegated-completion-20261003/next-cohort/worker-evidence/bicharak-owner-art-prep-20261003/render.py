from pathlib import Path
import json,hashlib,re,unicodedata
from PIL import Image,ImageDraw,ImageFont,ImageChops,features
from fontTools.ttLib import TTFont
R=Path('/tmp/earnalism-main-approved-integration');O=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SERIF=R/'frontend/src/assets/fonts/noto-serif-bengali-600.ttf';SANS=R/'frontend/src/assets/fonts/noto-sans-bengali-500.ttf'
font=lambda p,n:ImageFont.truetype(str(p),n,layout_engine=ImageFont.Layout.RAQM)
assert all(features.check(k) for k in ['raqm','harfbuzz','fribidi','freetype2'])
b=json.loads((R/'data/controlled_publications/book-5704b31005/public_book.json').read_text());source=json.loads((R/'internal/legal/catalogue_clearance_20261002/bengali/book-5704b31005-final-source-comparison.json').read_text());excerpt=source['source_paragraphs'][2]
text=[b['title'],b['author'],excerpt];fonts=[]
for p in [SERIF,SANS]:
 tt=TTFont(p);cmap={cp for tab in tt['cmap'].tables for cp in tab.cmap};assert not {c for t in text for c in t if not c.isspace() and ord(c) not in cmap};names=[{'name_id':n.nameID,'value':n.toUnicode()} for n in tt['name'].names if n.nameID in [0,13,14]];assert any(n['name_id']==14 and n['value']=='https://openfontlicense.org' for n in names);fonts.append({'path':str(p.relative_to(R)),'sha256':sha(p),'embedded_copyright_license':names,'required_codepoints_pass':True})
def center(d,t,y,f,w=1040):
 box=d.textbbox((0,0),t,font=f,direction='ltr',language='bn');assert box[2]-box[0]<w;d.text(((1600-(box[2]-box[0]))/2-box[0],y),t,font=f,fill=(245,223,171),direction='ltr',language='bn')
def wrap(d,t,f,w):
 res=[];line=''
 for word in t.split():
  trial=(line+' '+word).strip();bounds=d.textbbox((0,0),trial,font=f,direction='ltr',language='bn')
  if bounds[2]-bounds[0]>w:assert line;res.append(line);line=word
  else:line=trial
 if line:res.append(line)
 return res
assets={};bg=(67,19,28)
for kind in ['front','back']:
 op=O/'recovered'/f'{kind}.png';receipt=json.loads((O/'recovered'/f'{kind}-http-receipt.json').read_text());assert sha(op)==receipt['sha256'];original=Image.open(op).convert('RGB');im=original.copy();d=ImageDraw.Draw(im)
 if kind=='front':
  masks=[(470,750,1130,1100),(225,1880,1375,2050)]
  for z in masks:d.rectangle(z,fill=bg)
  center(d,b['title'],785,font(SERIF,148),640);center(d,b['author'],998,font(SANS,60),640)
 else:
  masks=[(240,410,1380,1585)];d.rectangle(masks[0],fill=bg);center(d,b['title'],445,font(SERIF,148));center(d,b['author'],675,font(SANS,63));lines=wrap(d,excerpt,font(SERIF,59),1040);assert len(lines)<=8
  for i,line in enumerate(lines):center(d,line,845+i*79,font(SERIF,59));assert 845+(i+1)*79<1545
 png=O/(kind+'-prepared.png');assert not png.exists(),'NO_ART_RETRY';im.save(png,format='PNG',compress_level=9)
 webp=O/(kind+'-delivery.webp');im.resize((800,1200),Image.Resampling.LANCZOS).save(webp,format='WEBP',quality=72,method=6);assert webp.stat().st_size<=(80000 if kind=='front' else 180000)
 mask=Image.new('L',im.size,255);md=ImageDraw.Draw(mask)
 for z in masks:md.rectangle(z,fill=0)
 diff=ImageChops.difference(original,im);assert Image.composite(diff,Image.new('RGB',im.size),mask).getbbox() is None
 assets[kind]={'original':{'path':str(op),'url':receipt['url'],'sha256':sha(op),'bytes':op.stat().st_size,'dimensions':list(original.size),'http_receipt_sha256':sha(O/'recovered'/f'{kind}-http-receipt.json')},'prepared_png':{'path':str(png),'sha256':sha(png),'dimensions':list(im.size),'bytes':png.stat().st_size},'delivery':{'path':str(webp),'sha256':sha(webp),'dimensions':[800,1200],'bytes':webp.stat().st_size,'budget':80000 if kind=='front' else 180000,'recipe':'RGB; Lanczos800x1200; WebPquality72method6'},'repair_zones':masks,'outside_repair_zones_exact_rgb_identity':True,'body_excerpt':excerpt if kind=='back' else None}
prep={'schema':'earnalism.bicharak-owner-cover-bounded-copy-preparation.v1','slug':'book-5704b31005','metadata_binding':{k:b[k] for k in ['title','author']},'first_complete_source_paragraph':excerpt,'excerpt_source_snapshot_sha256':sha(R/'internal/legal/catalogue_clearance_20261002/bengali/book-5704b31005-final-source-comparison.json'),'method':'ONE combined precise-mask repair of false LIVE badge, coin-occluded title/author and clipped back copy/source furniture, replacing copy with entire actual first source paragraph; licensed repository Noto + RAQM. Original artwork remains pixel-identical outside masks. Original creation method UNKNOWN; owner provenance held under actual direct directive.','one_bounded_remediation_attempt':1,'fonts':fonts,'raqm_shaping_pass':True,'assets':assets,'renderer_sha256':sha(Path(__file__)),'paid_generation_calls':0,'approval_or_activation_claim':False}
(O/'cover-preparation.json').write_text(json.dumps(prep,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:a['delivery'] for k,a in assets.items()},indent=2))
