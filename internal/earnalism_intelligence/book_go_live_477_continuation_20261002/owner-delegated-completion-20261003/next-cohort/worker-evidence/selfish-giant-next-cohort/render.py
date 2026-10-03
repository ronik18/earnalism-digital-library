from pathlib import Path
import json,hashlib,textwrap
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent
R=Path('/tmp/earnalism-main-approved-integration')
P=R/'data/controlled_publications/the-selfish-giant'
FONT=Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
M=(66,22,30);G=(223,183,92);C=(246,231,189)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def face(size):return ImageFont.truetype(str(FONT),size)
def centered(d,y,t,f,color):
 box=d.textbbox((0,0),t,font=f);d.text(((1600-(box[2]-box[0]))/2,y),t,font=f,fill=color)
def wrap(d,text,f,maxw):
 lines=[];line=''
 for w in text.split():
  trial=(line+' '+w).strip()
  if d.textbbox((0,0),trial,font=f)[2]>maxw:lines.append(line);line=w
  else:line=trial
 if line:lines.append(line)
 return lines
b=json.loads((P/'public_book.json').read_text());ch=json.loads((P/'chapters/chapter-001.json').read_text())
content=' '.join(ch['content'].split())
end=content.index('they cried to each other.')+len('they cried to each other.')
excerpt=content[:end];assert excerpt.endswith('.') and excerpt.startswith('EVERY afternoon')
outputs={}
for kind in ('front','back'):
 im=Image.open(O/(kind+'-original.png')).convert('RGB');d=ImageDraw.Draw(im)
 if kind=='front':
  # Only mask existing typography and its intersecting ornaments; preserve the
  # original owner artwork outside these documented repair zones.
  d.rounded_rectangle((210,710,1390,1290),radius=46,fill=M,outline=G,width=6)
  centered(d,780,'The Selfish',face(113),C);centered(d,938,'Giant',face(113),C)
  d.line((480,1100,1120,1100),fill=G,width=3);centered(d,1135,b['author'],face(66),C)
  d.rounded_rectangle((180,1830,1420,2140),radius=30,fill=M)
  zones=[[210,710,1390,1290],[180,1830,1420,2140]]
 else:
  d.rounded_rectangle((95,70,1505,2160),radius=52,fill=M)
  d.rounded_rectangle((125,70,1475,2160),radius=52,outline=G,width=6)
  centered(d,120,'BACK COVER',face(44),G)
  centered(d,245,'The Selfish',face(102),C);centered(d,380,'Giant',face(102),C)
  d.line((300,555,1300,555),fill=G,width=3)
  lines=wrap(d,excerpt,face(48),1120);assert len(lines)<=18,len(lines)
  for i,line in enumerate(lines):centered(d,630+i*72,line,face(48),C)
  centered(d,630+len(lines)*72+90,b['author'],face(62),C)
  zones=[[95,70,1505,2160]]
 full=O/(kind+'-layout-repair.png');im.save(full,format='PNG',compress_level=9,optimize=False)
 # Exact bounded same-art, same-copy delivery derivative; one fresh review
 # checks its PNG origin and WEBP pixels together. No repeated render variants.
 small=im.resize((800,1200),Image.Resampling.LANCZOS)
 delivery=O/(kind+'-delivery.webp');small.save(delivery,format='WEBP',quality=90,method=6)
 budget=80000 if kind=='front' else 180000;assert delivery.stat().st_size<=budget
 outputs[kind]={'original_sha256':sha(O/(kind+'-original.png')),'layout_png':{'path':str(full),'sha256':sha(full),'bytes':full.stat().st_size,'dimensions':[1600,2400]},'delivery':{'path':str(delivery),'sha256':sha(delivery),'bytes':delivery.stat().st_size,'dimensions':[800,1200],'recipe':'RGB; Lanczos downsample800x1200; WebPquality90method6'},'repair_zones':zones,'budget_bytes':budget}
receipt={'schema':'earnalism.selfish-giant-bounded-cover-repair.v1','slug':'the-selfish-giant','original_defects':['False LIVE CONTROLLED RELEASE badge','Decorative gold circles obscure front title and author','Back excerpt truncated mid-sentence and intersected by decorations'],'method':'One bounded deterministic local mask/typeset repair of existing recovered owner artwork; exact existing title/author and complete unchanged source excerpt only. No new art, generated copy or paid calls.','source_public_book_sha256':sha(P/'public_book.json'),'chapter_file_sha256':sha(P/'chapters/chapter-001.json'),'chapter_content_sha256':hashlib.sha256(ch['content'].encode()).hexdigest(),'source_excerpt':excerpt,'source_excerpt_method':'Whitespace-normalized exact opening through complete existing final sentence; no lexical/punctuation substitutions','font':{'path':str(FONT),'sha256':sha(FONT)},'renderer_sha256':sha(Path(__file__)),'assets':outputs,'paid_generation_calls':0,'network_requests_by_renderer':0,'repository_mutations':0,'approval_or_activation_claim':False,'remaining_gate':'TWO_INDEPENDENT_EXACT_REPAIR_DELIVERY_AND_PACKAGE_REVIEWS_THEN_ACTUAL_COMPONENT_ACCEPTANCE'}
(O/'repair-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps(outputs,indent=2))
