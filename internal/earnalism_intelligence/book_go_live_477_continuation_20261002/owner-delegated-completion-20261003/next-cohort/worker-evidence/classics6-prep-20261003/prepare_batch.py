from pathlib import Path
import json,hashlib,shutil,re,io
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont,ImageChops
import PIL
R=Path('/tmp/earnalism-main-approved-integration');O=Path(__file__).parent
SLUGS=['the-time-machine','the-great-gatsby','frankenstein','the-secret-garden','pride-and-prejudice','great-expectations']
BP=R/'internal/legal/catalogue_clearance_20261002/english/current_whole_work_boundary_verification.json'
BOUND={x['slug']:x for x in json.loads(BP.read_text())['titles']}
REC=json.loads((O/'recovery-receipts.json').read_text())
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rd(p):return json.loads(Path(p).read_text())
def wr(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
ownerfact=rd(R/'data/controlled_publications/the-call-of-the-wild/cover_provenance.json')['owner_design_fact']
FONT=R/'frontend/public/assets/fonts/eb-garamond-400.ttf'
assert h(FONT)=='ef9512f92f6d579e5dc75af59a5a4b1b8b47d2eda89e00b954d44520e5369027'
MASKBOTTOM={'the-time-machine':420,'the-great-gatsby':450,'frankenstein':420,'the-secret-garden':560,'pride-and-prejudice':540,'great-expectations':580}
PALETTE={'the-time-machine':'#14222b','the-great-gatsby':'#121e2b','frankenstein':'#1c242b','the-secret-garden':'#14251b','pride-and-prejudice':'#ead3aa','great-expectations':'#1e272c'}
def licensed_overlay(original,slug,kind,title,author):
 out=original.copy();draw=ImageDraw.Draw(out);box=(45,45,979,MASKBOTTOM[slug]) if kind=='front' else (55,1260,969,1460)
 fill=PALETTE[slug];ink='#342819' if slug=='pride-and-prejudice' else '#f0d8a1'
 draw.rounded_rectangle(box,radius=24,fill=fill,outline='#bda66a',width=3)
 size=76 if kind=='front' else 46;tf=ImageFont.truetype(str(FONT),size);af=ImageFont.truetype(str(FONT),44 if kind=='front' else 34)
 lines=[];line=''
 for word in title.split():
  test=(line+' '+word).strip()
  if draw.textlength(test,font=tf)>850 and line:lines.append(line);line=word
  else:line=test
 lines.append(line)
 total=len(lines)*(size+12)+(70 if kind=='front' else 48);y=(box[1]+box[3]-total)/2
 for line in lines:
  draw.text(((1024-draw.textlength(line,font=tf))/2,y),line,font=tf,fill=ink);y+=size+12
 draw.text(((1024-draw.textlength(author,font=af))/2,y+20),author,font=af,fill=ink)
 diff=ImageChops.difference(original,out).getbbox()
 assert diff is None or (diff[0]>=box[0] and diff[1]>=box[1] and diff[2]<=box[2]+1 and diff[3]<=box[3]+1)
 return out,box
batch=[]
for slug in SLUGS:
 p=R/'data/controlled_publications'/slug;o=O/slug;c=o/'candidate-inactive-unaccepted'
 try:
  book=rd(p/'public_book.json');source=rd(p/'source_evidence.json');old=rd(p/'rights_decision.json');cs=rd(p/'checksum_manifest.json');boundary=BOUND[slug]
  assert old['status']=='ACCEPTED' and old['territories']==['IN']
  assert all(h(p/x['file'])==x['sha256'] for x in cs['files'])
  assert all(h(p/(k+'.json'))==v for k,v in old['components'].items())
  assert boundary['raw_source_sha256']==source['source_hash'] and boundary['reader_aggregate_sha256']==source['content_hash']
  chapters=sorted((p/'chapters').glob('*.json'));assert len(chapters)==boundary['chapter_count']
  for ch in chapters:
   d=rd(ch);assert hashlib.sha256(d['content'].encode()).hexdigest()==boundary['ordered_chapter_hashes'][d['id']]==d['content_hash']
  for name,src in [('root',p),('backend',R/'backend/data/controlled_publications'/slug)]:
   if src.exists():shutil.copytree(src,o/'preimages'/name,dirs_exist_ok=True)
  shutil.copytree(p,c,dirs_exist_ok=True)
  # Historical duplicate approval/audio documents are archive-only; current evidence is hash-bound.
  archived=[]
  for f in c.glob('*'):
   if f.is_file() and re.search(r' [2-9]\.json$',f.name):archived.append(f.name);f.unlink()
  assets=[]
  for kind in ['front','back']:
   src=o/'assets'/f'original-{kind}.png';recovery=next(x for x in REC if x['slug']==slug and x['kind']==('cover_url' if kind=='front' else 'back_cover_url'));assert h(src)==recovery['sha256']
   original=Image.open(src).convert('RGB');assert original.size==(1024,1536)
   png,overlaymask=licensed_overlay(original,slug,kind,book['title'],book['author'])
   deterministic_png=o/'assets'/f'{slug}-{kind}-deterministic.png';png.save(deterministic_png,'PNG',compress_level=9)
   # One bounded deterministic delivery preparation: finite byte-budget calibration,
   # no artwork/copy/title/author edit and no repeat title review.
   profiles=[(600,900,40),(600,900,30),(540,810,35),(540,810,25)] if kind=='front' else [(800,1200,60),(800,1200,50),(800,1200,40)]
   limit=80000 if kind=='front' else 180000;attempts=[];selected=None
   for width,height,quality in profiles:
    buf=io.BytesIO();png.resize((width,height),Image.Resampling.LANCZOS).save(buf,'WEBP',quality=quality,method=6);data=buf.getvalue();attempts.append({'dimensions':[width,height],'quality':quality,'bytes':len(data)})
    if len(data)<=limit:selected=(width,height,quality,data);break
   if selected is None:raise ValueError(f'{kind}: bounded delivery budget profiles exhausted; retain hold')
   width,height,quality,data=selected;fname=f'{slug}-{kind}-{h(src)[:8]}.webp';out=o/'assets'/fname;out.write_bytes(data);(c/'covers').mkdir(exist_ok=True);shutil.copy2(src,c/'covers'/f'original-{kind}.png');shutil.copy2(deterministic_png,c/'covers'/deterministic_png.name);shutil.copy2(out,c/'covers'/fname)
   assets.append({'kind':kind,'source_file':f'covers/original-{kind}.png','source_sha256':h(src),'original_url':recovery['persisted_url'],'source_bytes':src.stat().st_size,'source_dimensions':[1024,1536],'licensed_deterministic_overlay':{'file':'covers/'+deterministic_png.name,'sha256':h(deterministic_png),'font_sha256':h(FONT),'text_title':book['title'],'text_author':book['author'],'mask_rectangle':list(overlaymask),'pixels_outside_mask_exactly_preserved':True,'attempt':1},'file':'covers/'+fname,'sha256':h(out),'bytes':len(data),'dimensions':[width,height],'url':f'https://theearnalism.com/assets/books/{slug}/{fname}','recipe':{'format':'WEBP','mode':'RGB','resize':[width,height],'quality':quality,'method':6,'resampling':'LANCZOS','pillow_version':PIL.__version__},'parameter_calibration':attempts,'review_status':'TWO_INDEPENDENT_NEW_EXACT_VISUAL_DELIVERY_REVIEWS_REQUIRED','production_observed':False})
  quotechecks=[]
  if slug in ['the-secret-garden','pride-and-prejudice']:
   q='Where you tend a rose, my lad, a thistle cannot grow' if slug=='the-secret-garden' else 'I could easily forgive his pride, if he had not mortified mine'
   for ch in chapters:
    text=' '.join(rd(ch)['content'].replace('_','').split())
    if q.casefold() in text.casefold():quotechecks.append({'quote':q,'chapter':ch.name,'chapter_file_sha256':h(ch),'comparison':'Whitespace and Markdown italic formatting markers only; no semantic text or punctuation substitution.'})
   assert quotechecks,'Unsupported quote: one bounded removal repair required, no false acceptance'
  preparation={'schema':'earnalism.classics-inactive-preparation.v1','slug':slug,'status':'INACTIVE_UNACCEPTED','prepared_at':datetime.now(timezone.utc).isoformat(),'category':'LEGACY_OWNER_DESIGNED_GRAPHICAL_COVER_DELIVERY_DERIVATIVE','owner_design_fact':ownerfact,'original_generation_method':'NOT_INFERRED','title_author_gate':{'required_unconditionally':True,'stored_title':book['title'],'stored_author':book['author'],'licensed_deterministic_typography_overlay':True,'font_file':'frontend/public/assets/fonts/eb-garamond-400.ttf','font_sha256':h(FONT),'independent_exact_review_required':True},'source_binding':{'existing_text_decision_id':old['decision_id'],'source_sha256':source['source_hash'],'content_sha256':source['content_hash'],'chapter_count':len(chapters),'all_content_hashes_match_exact_boundary_receipt':True,'boundary_receipt_path':str(BP.relative_to(R)),'boundary_receipt_file_sha256':h(BP),'existing_selected_narrative_complete_boundary_evidence_reused':True,'no_new_source_fetch':True,'containment_alone_not_treated_as_complete':True},'boundary_receipt':boundary,'cover_quote_checks':quotechecks,'assets':assets,'cover_typography_remediation_attempts':1,'cover_copy_repair_attempts':0,'delivery_preparation_attempts':1,'no_new_artwork_or_generation':True,'source_license_and_versions_preserved':True,'archived_historical_duplicate_approval_files':archived,'publication_accepted':False,'cover_display_accepted':False,'audio_authorized':False,'production_observed':False,'runtime_fallback_conformance_claimed':False}
  wr(c/'cover_preparation.json',preparation)
  # Current public metadata is preparation only; historical positive audio remains archive-only.
  book['rights_basis']=source['rights_basis'];book['cover_status']='UNACCEPTED_EXACT_OWNER_GRAPHICAL_DELIVERY_PREPARED';book['cover_category']=preparation['category'];book['cover_dimensions']={a['kind']:a['dimensions'] for a in assets};book.pop('cover_semantic_match_score',None)
  for key in ['approved_to_publish','isPublic','isLive','showInPublicLibrary','showInHomepage','allowPublicReading','is_published','audio_enabled','audiobook_enabled','generate_audiobook','allowCheckout','allowPayment']:book[key]=False
  book['publication_status']='DRAFT';book['publicationStatus']='draft'
  for key,value in list(book.items()):
   if 'audio' in key.lower() and key not in ['audio_enabled','audiobook_enabled','generate_audiobook']:
    if isinstance(value,str):book[key]=''
    elif isinstance(value,dict):book[key]={}
    elif isinstance(value,list):book[key]=[]
  if 'formats' in book:book['formats']=[x for x in book['formats'] if 'audio' not in str(x).lower()]
  for a in assets:
   for key in (['cover_url','cover_image_url','coverImage','cover_image'] if a['kind']=='front' else ['back_cover_url','back_cover_image_url','backCoverImage']):book[key]=a['url']
  wr(c/'public_book.json',book)
  auth=rd(c/'publication_authorization.json');auth.update(publication_authorized=False,cover_status='UNACCEPTED_EXACT_DELIVERY_PREPARATION',audio_authorized=False,production_activation_authorized_by_this_file=False);wr(c/'publication_authorization.json',auth)
  approval=rd(c/'approval_evidence.json');approval.update(approved_to_publish=False,approval_scope='INACTIVE_UNACCEPTED_EXACT_PREPARATION',publication_authorization_sha256=h(c/'publication_authorization.json'),audiobook_enabled=False,audio_public_release='NOT_AUTHORIZED');wr(c/'approval_evidence.json',approval)
  reader=rd(c/'reader_manifest.json');assert reader.get('audio_enabled',False) is False and reader.get('audiobook_enabled',False) is False
  # Remove active audio fields only in current approval/publication; raw versions retained above.
  for key,value in list(approval.items()):
   if ('audio' in key.lower() and key not in ['audiobook_enabled','audio_public_release']):
    if isinstance(value,str):approval[key]=''
    elif isinstance(value,dict):approval[key]={}
    elif isinstance(value,list):approval[key]=[]
  wr(c/'approval_evidence.json',approval)
  manifest=rd(c/'publication_manifest.json');manifest['reader_release'].update(status='INACTIVE_UNACCEPTED_PREPARATION',exposed=False,cover_url=assets[0]['url'],blockers=['TWO_INDEPENDENT_NEW_EXACT_REVIEWS_AND_SERIALIZED_ROOT_ACCEPTANCE_REQUIRED']);manifest['audio_release']={'status':'NOT_REQUESTED','exposed':False,'required_for_reader_release':False}
  names=[x['file'] for x in cs['files'] if x['file'] not in archived]+['cover_preparation.json']+[str(x.relative_to(c)) for x in (c/'covers').glob('*')]
  cs['files']=[{'file':n,'sha256':h(c/n)} for n in sorted(set(names))];wr(c/'checksum_manifest.json',cs)
  manifest['artifacts']={k:h(c/(k+'.json')) for k in ['public_book','reader_manifest','source_evidence','approval_evidence','publication_authorization','checksum_manifest','cover_preparation']};manifest.pop('manifest_sha256',None);manifest['manifest_sha256']=hashlib.sha256(json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();wr(c/'publication_manifest.json',manifest)
  decision=json.loads(json.dumps(old));decision.update(decision_id=f'proposal-20261003-{slug}-exact-cover-delivery',status='PROPOSED',conditions_satisfied=False,accepted_by='UNACCEPTED isolated preparation; root actual delegated acceptance required.');decision['components']={k:h(c/(k+'.json')) for k in ['public_book','reader_manifest','source_evidence','approval_evidence','checksum_manifest','publication_manifest','cover_preparation']};wr(c/'rights_decision.json',decision)
  assert all(h(c/x['file'])==x['sha256'] for x in cs['files'])
  for name in ['source_evidence.json','reader_manifest.json','highlight_sync.json']+[str(ch.relative_to(p)) for ch in chapters]:assert (c/name).read_bytes()==(p/name).read_bytes()
  report={'slug':slug,'status':'INACTIVE_UNACCEPTED_COMPLETE_SOURCE_AND_ART_READY_FOR_TWO_REVIEWS','checksums_pass':len(cs['files']),'source_reader_sync_chapters_byte_unchanged':True,'assets':assets,'archived_historical_positive_audio_and_duplicate_claims':True,'all_candidate_files':{str(x.relative_to(c)):h(x) for x in sorted(c.rglob('*')) if x.is_file()}}
  wr(o/'validation.json',report);batch.append({k:v for k,v in report.items() if k!='all_candidate_files'})
  print(slug,'READY',len(cs['files']),[(a['kind'],a['bytes'],a['dimensions']) for a in assets],flush=True)
 except Exception as ex:
  hold={'slug':slug,'status':'TERMINAL_HOLD_PREPARATION_BLOCKED','reason':str(ex),'source_records_preserved':True,'canonical_or_registry_mutated':False};wr(o/'terminal-hold.json',hold);batch.append(hold);print(slug,'HOLD',str(ex),flush=True)
wr(O/'batch-result.json',batch)
