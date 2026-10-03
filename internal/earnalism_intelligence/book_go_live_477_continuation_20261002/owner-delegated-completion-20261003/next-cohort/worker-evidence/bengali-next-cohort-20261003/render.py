from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont,ImageChops,features
from fontTools.ttLib import TTFont
R=Path('/tmp/earnalism-main-approved-integration');O=Path(__file__).parent
SERIF=R/'frontend/src/assets/fonts/noto-serif-bengali-600.ttf';SANS=R/'frontend/src/assets/fonts/noto-sans-bengali-500.ttf'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(features.check(k) for k in ['raqm','harfbuzz','fribidi','freetype2'])
def font(p,n):return ImageFont.truetype(str(p),n,layout_engine=ImageFont.Layout.RAQM)
def center(d,t,y,f,fill):
 box=d.textbbox((0,0),t,font=f,direction='ltr',language='bn');x=(1024-(box[2]-box[0]))/2-box[0];d.text((x,y),t,font=f,fill=fill,direction='ltr',language='bn')
def wrap(d,t,f,w):
 lines=[];line=''
 for word in t.split():
  trial=(line+' '+word).strip();box=d.textbbox((0,0),trial,font=f,direction='ltr',language='bn')
  if box[2]-box[0]>w:assert line;lines.append(line);line=word
  else:line=trial
 if line:lines.append(line)
 return lines
SETTINGS={'lokrahasya':{'zone':[155,320,905,1000],'color':[23,19,13],'title_y':335,'blurb_y':495,'about_y':725,'width':650,'front_zone':[80,55,945,355]},'mrinalini':{'zone':[135,280,895,900],'color':[14,27,39],'title_y':300,'blurb_y':460,'about_y':660,'width':650,'front_zone':[65,35,959,410]},'bn-066':{'zone':[160,130,885,720],'color':[15,24,32],'title_y':150,'blurb_y':320,'about_y':545,'width':620,'front_zone':[100,40,924,375]}}
for slug,z in SETTINGS.items():
 out=O/slug;b=json.loads((R/'data/controlled_publications'/slug/'public_book.json').read_text());rec=json.loads((out/'recovery-receipt.json').read_text());assert rec['status'].startswith('RECOVERED')
 text=[b[k] for k in ['title','short_description','about_author']]
 fonts=[]
 for fp in [SERIF,SANS]:
  tt=TTFont(fp);cmap={cp for tab in tt['cmap'].tables for cp in tab.cmap};missing={x for t in text for x in t if not x.isspace() and ord(x) not in cmap};assert not missing
  fonts.append({'path':str(fp.relative_to(R)),'sha256':sha(fp),'required_codepoints_pass':True})
 assets={}
 for kind in ['front','back']:
  rr=next(x for x in rec['requests'] if x['kind']==kind);orig=Path(rr['path']);assert sha(orig)==rr['sha256'];im=Image.open(orig).convert('RGB');zones=[]
  if kind=='front':
   d=ImageDraw.Draw(im);d.rounded_rectangle(z['front_zone'],radius=24,fill=tuple(z['color']));center(d,b['title'],z['front_zone'][1]+25,font(SERIF,112),(218,176,83));center(d,b['author'],z['front_zone'][1]+205,font(SANS,45),(246,223,172));zones=[z['front_zone']]
  if kind=='back':
   d=ImageDraw.Draw(im);d.rounded_rectangle(z['zone'],radius=30,fill=tuple(z['color']));cream=(246,223,172);gold=(218,176,83)
   center(d,b['title'],z['title_y'],font(SERIF,74),gold)
   lines=wrap(d,b['short_description'],font(SERIF,44),z['width']);assert len(lines)<=3
   for i,l in enumerate(lines):center(d,l,z['blurb_y']+i*62,font(SERIF,44),cream)
   lines2=wrap(d,b['about_author'],font(SANS,36),z['width']);assert len(lines2)<=3
   for i,l in enumerate(lines2):center(d,l,z['about_y']+i*50,font(SANS,36),cream)
   assert z['about_y']+len(lines2)*50<z['zone'][3];zones=[z['zone']]
  png=out/(kind+'-prepared.png');im.save(png,format='PNG',compress_level=9)
  # A single delivery recipe sized to meet the pre-agreed cover budget.
  webp=out/(kind+'-delivery.webp');im.resize((450,675),Image.Resampling.LANCZOS).save(webp,format='WEBP',quality=82,method=6)
  budget=80000 if kind=='front' else 180000;assert webp.stat().st_size<=budget,(slug,kind,webp.stat().st_size)
  mask=Image.new('L',im.size,255);md=ImageDraw.Draw(mask)
  for zone in zones:md.rectangle(zone,fill=0)
  diff=ImageChops.difference(Image.open(orig).convert('RGB'),im);assert Image.composite(diff,Image.new('RGB',im.size),mask).getbbox() is None
  assets[kind]={'original':rr,'prepared_png':{'path':str(png),'sha256':sha(png),'dimensions':list(im.size),'bytes':png.stat().st_size},'delivery':{'path':str(webp),'sha256':sha(webp),'dimensions':[450,675],'bytes':webp.stat().st_size,'budget':budget,'recipe':'RGB; Lanczos450x675; WebPquality82method6'},'repair_zones':zones,'outside_repair_zones_exact_rgb_identity':True,'licensed_deterministic_front_title_author_overlay':kind=='front'}
 receipt={'schema':'earnalism.bengali-owner-cover-bounded-copy-preparation.v1','slug':slug,'metadata_binding':{k:b[k] for k in ['title','author','short_description','about_author']},'metadata_sha256':sha(R/'data/controlled_publications'/slug/'public_book.json'),'method':'One bounded title/author typography overlay on each front using repository Noto fonts and RAQM, combined with back copy-zone overlay replaces unbound decorative quotation and old summary with exact existing metadata only; illustrations outside documented zones remain byte-equivalent RGB. No new art or prose, no inferred generation method.','one_bounded_remediation_attempt':1,'fonts':fonts,'raqm_shaping_pass':True,'assets':assets,'renderer_sha256':sha(Path(__file__)),'paid_generation_calls':0,'approval_or_activation_claim':False,'next_gate':'TWO_FRESH_EXACT_PIXEL_DELIVERY_COPY_PACKAGE_REVIEWS'}
 (out/'cover-preparation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'slug':slug,'delivery':{k:{a:v for a,v in x['delivery'].items() if a in ['sha256','bytes','dimensions']} for k,x in assets.items()}},ensure_ascii=False))
