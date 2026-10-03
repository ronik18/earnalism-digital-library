from pathlib import Path
import json,hashlib,shutil,textwrap
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
R=Path('/tmp/earnalism-main-approved-integration');O=Path(__file__).parent;S='the-cop-and-the-anthem';P=R/'data/controlled_publications'/S;C=O/'candidate-inactive-unaccepted'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def w(n,d):
 p=C/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
for kind,src in [('root',P),('backend',R/'backend/data/controlled_publications'/S)]:
 if src.exists():shutil.copytree(src,O/'preimages'/kind,dirs_exist_ok=True)
cs=read(P/'checksum_manifest.json');old=read(P/'rights_decision.json')
assert all(h(P/x['file'])==x['sha256'] for x in cs['files'])
assert all(h(P/(k+'.json'))==v for k,v in old['components'].items())
shutil.copytree(P,C,dirs_exist_ok=True)
# Duplicate historical admin/audio claim remains byte-exact in preimages only.
# It is not an active candidate evidence file or authorization.
(C/'approval_evidence 2.json').unlink(missing_ok=True)
font=R/'frontend/public/assets/fonts/eb-garamond-400.ttf'
assert h(font)=='ef9512f92f6d579e5dc75af59a5a4b1b8b47d2eda89e00b954d44520e5369027'
chapter=read(P/'chapters/chapter-001.json');excerpt=' '.join(chapter['content'].split('A dead leaf fell')[0].split())
assert excerpt=='On his bench in Madison Square Soapy moved uneasily. When wild geese honk high of nights, and when women without sealskin coats grow kind to their husbands, and when Soapy moves uneasily on his bench in the park, you may know that winter is near at hand.'
maroon=(66,22,30,255);gold=(223,183,92,255);cream=(246,231,189,255)
def center(d,y,s,size):
 f=ImageFont.truetype(str(font),size);b=d.textbbox((0,0),s,font=f);d.text(((1600-b[2]+b[0])/2,y),s,font=f,fill=cream)
def render(kind):
 im=Image.open(O/f'assets/original-{kind}.png').convert('RGBA');d=ImageDraw.Draw(im)
 if kind=='front':
  d.rounded_rectangle((210,700,1390,1265),radius=46,fill=maroon,outline=gold,width=6)
  center(d,775,'The Cop and',112);center(d,925,'the Anthem',112);d.line((480,1080,1120,1080),fill=gold,width=3);center(d,1110,'O. Henry',65)
  d.rounded_rectangle((180,1830,1420,2140),radius=30,fill=maroon)
 else:
  d.rounded_rectangle((95,70,1505,2160),radius=52,fill=maroon)
  d.rounded_rectangle((125,70,1475,2160),radius=52,outline=gold,width=6)
  center(d,130,'BACK COVER',52);center(d,280,'The Cop and',112);center(d,440,'the Anthem',112);d.line((300,610,1300,610),fill=gold,width=3)
  f=ImageFont.truetype(str(font),60);lines=[];line=''
  for word in excerpt.split():
   test=(line+' '+word).strip()
   if d.textlength(test,font=f)>1120:lines.append(line);line=word
   else:line=test
  lines.append(line)
  for i,line in enumerate(lines):center(d,710+i*88,line,60)
  y=710+len(lines)*88+120;d.line((500,y,1100,y),fill=gold,width=3);center(d,y+50,'O. Henry',72)
 return im
assets=[]
for kind in ['front','back']:
 im=render(kind);png=O/f'assets/{S}-{kind}-inactive.png';im.save(png,'PNG',compress_level=9)
 # Same bounded preparation uses one deterministic delivery encoding, no artwork generation.
 webp=O/f'assets/{S}-{kind}-inactive.webp';im.convert('RGB').resize((800,1200),Image.Resampling.LANCZOS).save(webp,'WEBP',quality=80,method=6)
 shutil.copy2(png,C/'covers'/png.name) if (C/'covers').exists() else ((C/'covers').mkdir(),shutil.copy2(png,C/'covers'/png.name))
 shutil.copy2(webp,C/'covers'/webp.name)
 assets.append({'kind':kind,'original_sha256':h(O/f'assets/original-{kind}.png'),'png_sha256':h(png),'png_bytes':png.stat().st_size,'png_dimensions':[1600,2400],'webp_sha256':h(webp),'webp_bytes':webp.stat().st_size,'webp_dimensions':[800,1200],'png_file':'covers/'+png.name,'webp_file':'covers/'+webp.name,'delivery_url':f'https://theearnalism.com/assets/books/{S}/{webp.name}','review_status':'TWO_INDEPENDENT_EXACT_VISUAL_SOURCE_REVIEWS_REQUIRED'})
for kind in ['front','back']:shutil.copy2(O/f'assets/original-{kind}.png',C/'covers'/f'original-{kind}.png')
receipt={'schema':'earnalism.inactive-source-bound-cover-preparation.v1','slug':S,'status':'INACTIVE_UNACCEPTED','prepared_at':datetime.now(timezone.utc).isoformat(),'originals':read(O/'assets/recovery-receipt.json'),'existing_text_decision_id':old['decision_id'],'source_sha256':chapter['sourceSha256'],'content_sha256':read(P/'source_evidence.json')['content_hash'],'source_excerpt':excerpt,'source_excerpt_origin':'chapters/chapter-001.json exact complete opening paragraph, whitespace-only normalized','source_chapter_file_sha256':h(P/'chapters/chapter-001.json'),'font_sha256':h(font),'repair_attempt':1,'method':'Existing deterministic masked panels and typesetting workflow; title/author text placed on opaque card, false LIVE pill removed; truncated back excerpt replaced with exact complete existing source paragraph; no new art or generation. Original pixels outside panel rectangles preserved.','assets':assets,'cover_display_accepted':False,'publication_accepted':False,'audio_authorized':False,'production_observed':False,'runtime_mutations':False,'next_gate':'Two independent exact visual/source and new package/acceptance reviews; root serialized authority only.'}
w('cover_preparation.json',receipt)
book=read(C/'public_book.json');book['rights_basis']=read(P/'source_evidence.json')['rights_basis'];book['cover_status']='INACTIVE_UNACCEPTED_REPAIR_PREPARED';book['approved_to_publish']=False;book['publication_status']='DRAFT';book['publicationStatus']='draft'
book['cover_dimensions']={'front':[800,1200],'back':[800,1200]}
book['cover_category']='LEGACY_OWNER_DESIGNED_GRAPHICAL_DERIVATIVE'
book.pop('cover_semantic_match_score',None) # Historical score does not bind the new derivative.
for k in ['isPublic','isLive','showInPublicLibrary','showInHomepage','allowPublicReading','is_published','audio_enabled','audiobook_enabled','generate_audiobook','allowCheckout','allowPayment']:book[k]=False
for k in list(book):
 if k.startswith('audio') or k.startswith('audiobook'):
  if k in ['audio_enabled','audiobook_enabled','generate_audiobook']:book[k]=False
  elif isinstance(book[k],str):book[k]=''
  elif isinstance(book[k],dict):book[k]={}
  elif isinstance(book[k],list):book[k]=[]
for a in assets:
 for k in (['cover_url','cover_image_url','coverImage','cover_image'] if a['kind']=='front' else ['back_cover_url','back_cover_image_url','backCoverImage']):book[k]=a['delivery_url']
w('public_book.json',book)
approval=read(C/'approval_evidence.json');approval['approved_to_publish']=False;approval['approval_scope']='INACTIVE_UNACCEPTED_COVER_REPAIR_PREPARATION';approval['audiobook_enabled']=False;approval['audio_public_release']='NOT_AUTHORIZED';w('approval_evidence.json',approval)
auth=read(C/'publication_authorization.json');auth['publication_authorized']=False;auth['cover_status']='UNACCEPTED_EXACT_REPAIR_PREPARATION';auth['audio_authorized']=False;auth['production_activation_authorized_by_this_file']=False;w('publication_authorization.json',auth)
approval['publication_authorization_sha256']=h(C/'publication_authorization.json');w('approval_evidence.json',approval)
manifest=read(C/'publication_manifest.json');manifest['reader_release'].update(status='INACTIVE_UNACCEPTED_PREPARATION',exposed=False,cover_url=assets[0]['delivery_url'],blockers=['TWO_INDEPENDENT_REVIEWS_AND_ROOT_ACCEPTANCE_REQUIRED']);manifest['audio_release']={'status':'NOT_REQUESTED','exposed':False,'required_for_reader_release':False}
files=[x['file'] for x in cs['files'] if x['file']!='approval_evidence 2.json']+['cover_preparation.json']+[str(p.relative_to(C)) for p in (C/'covers').glob('*')]
cs['files']=[{'file':n,'sha256':h(C/n)} for n in sorted(set(files))];w('checksum_manifest.json',cs)
manifest['artifacts']={k:h(C/(k+'.json')) for k in ['public_book','reader_manifest','source_evidence','approval_evidence','publication_authorization','checksum_manifest','cover_preparation']};manifest.pop('manifest_sha256',None);manifest['manifest_sha256']=hashlib.sha256(json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();w('publication_manifest.json',manifest)
# Old accepted text record remains immutable in preimages; proposed changed hashes cannot inherit trust.
decision=json.loads(json.dumps(old));decision['decision_id']='proposal-20261003-the-cop-and-the-anthem-cover-preparation';decision['status']='PROPOSED';decision['conditions_satisfied']=False;decision['components']={k:h(C/(k+'.json')) for k in ['public_book','reader_manifest','source_evidence','approval_evidence','checksum_manifest','publication_manifest','cover_preparation']};decision['accepted_by']='UNACCEPTED preparation only; actual root delegated decision still required.';w('rights_decision.json',decision)
assert all(h(C/x['file'])==x['sha256'] for x in cs['files'])
for name in ['source_evidence.json','reader_manifest.json','highlight_sync.json','chapters/chapter-001.json']:assert (C/name).read_bytes()==(P/name).read_bytes()
report={'slug':S,'status':'INACTIVE_UNACCEPTED_SOURCE_READY_REVIEW_PENDING','prior6components_and_checksums_pass':True,'unchanged_source_reader_sync_chapter_files':True,'checksums_pass':len(cs['files']),'assets':assets,'paid_generation':False,'cover_repair_attempts':1,'source_fetches':0,'cover_fetches':2,'root_repository_mutations':False,'all_candidate_files':{str(p.relative_to(C)):h(p) for p in sorted(C.rglob('*')) if p.is_file()}}
(O/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='all_candidate_files'},ensure_ascii=False,indent=2))
