from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,sys,re
from PIL import Image,ImageDraw,ImageFont,ImageOps

ROOT=Path('/tmp/earnalism-main-approved-integration')
WORK=Path(__file__).resolve().parent
FONT=Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
LICENSE=Path('/usr/share/doc/fonts-dejavu-core/copyright')
OWNER=ROOT/'internal/legal/bengali_text_preparation_20261002/evidence_matrix.json'
AT=datetime.now(timezone.utc).isoformat()
CONFIG={
 'bharat-at-the-crossroads':{'title':['Bharat at','the Crossroads'],'front_title':(72,50,982,485),'front_author':(160,1360,898,1460),'back_title_author':(125,520,930,1095),'back_title_y':565,'back_font':51,'back_author_y':775,'bg':(8,18,27,255),'fg':(246,224,167,255),'border':(201,157,72,255),'front_font':88,'front_y':110,'front_step':135,'front_author_font':47,'back_author_font':42,'additional_back_masks':[(424,1300,990,1485)],'back_body':'EXACT_STORED_SHORT_DESCRIPTION','issues':['Unverified named endorsements removed; no human endorsement or approval fact invented.','Unverified ISBN/barcode and related publication furniture removed.','Original front source method unknown; first-party owner declaration retained, no typography-origin inference.']},
 'the-principles-of-scientific-management':{'title':['The Principles of','Scientific','Management'],'front_title':(80,80,944,580),'front_author':(120,1290,911,1412),'back_title_author':None,'back_title':(225,237,837,395),'back_author':(135,1254,893,1350),'back_title_y':250,'back_font':35,'back_author_y':1270,'bg':(9,27,35,255),'fg':(245,226,179,255),'border':(194,153,74,255),'front_font':69,'front_y':122,'front_step':129,'front_author_font':43,'back_author_font':43,'issues':['Existing unquoted explanatory artwork copy retained; no new attributed quotation or creation-method fact asserted.']},
 'acres-of-diamonds':{'title':['Acres of','Diamonds'],'front_title':(60,55,964,510),'front_author':(85,1314,936,1432),'back_title_author':None,'back_title':(90,65,934,485),'back_author':(217,908,808,994),'back_title_y':117,'back_font':84,'back_author_y':928,'bg':(242,224,175,255),'fg':(8,42,51,255),'border':(177,128,55,255),'front_font':109,'front_y':105,'front_step':159,'front_author_font':57,'back_author_font':43,'issues':['Original lecture/biography/appreciation text creators retain prior separately accepted evidence; no new creator or licence inferred.']},
 'my-life-and-work':{'title':['My Life','and Work'],'front_title':(80,50,944,458),'front_author':None,'back_title_author':None,'back_title':(150,343,873,547),'back_author':(185,1180,851,1257),'back_title_y':358,'back_font':66,'back_author_y':1200,'bg':(8,23,29,255),'fg':(245,224,176,255),'border':(192,143,61,255),'front_font':89,'front_y':86,'front_step':125,'front_author_font':33,'back_author_font':31,'additional_front_masks':[(45,460,188,536),(708,468,1009,610),(567,950,633,996),(31,1209,267,1412)],'issues':['Identified Ford wordmarks and two unsupported attributed quote/signature claims removed within precise masks.','No third-party portrait/photo origin, exact original creation method, or trademark licence invented. First-party owner-design declaration is the original-art evidence; reviewers must hold if a substantial contrary component remains.']}
}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def write(p,v):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def font(size):return ImageFont.truetype(str(FONT),size)
def center(draw,box,y,text,size,fill):
 f=font(size);bounds=draw.textbbox((0,0),text,font=f);assert bounds[2]-bounds[0]<box[2]-box[0]-20,(text,size,box)
 x=(box[0]+box[2]-(bounds[2]-bounds[0]))/2-bounds[0];draw.text((x,y),text,font=f,fill=fill)
def panel(draw,box,cfg):draw.rectangle(box,fill=cfg['bg']);draw.rectangle(box,outline=cfg['border'],width=2)
def lines(draw,text,size,width):
 f=font(size);result=[];line=''
 for word in text.split():
  trial=(line+' '+word).strip()
  if draw.textlength(trial,font=f)>width and line:result.append(line);line=word
  else:line=trial
 if line:result.append(line)
 return result
assert 'Owner states all front and back covers are designed by the owner.' in OWNER.read_text()
shutil.copyfile(LICENSE,WORK/'DejaVu-font-license.txt')
sys.path.insert(0,str(ROOT));from backend.publication_manifest import build_manifest,validate_manifest
from backend.rights_decision_gate import record_sha256
results=[]
for slug in (sys.argv[1:] or list(CONFIG)):
 cfg=CONFIG[slug]
 delivery_size=(600,900) if slug in ('the-principles-of-scientific-management','acres-of-diamonds') else (800,1200)
 base=WORK/slug;source=ROOT/'data/controlled_publications'/slug;out=base/'inactive-candidate';oldbook=load(source/'public_book.json');oldsource=load(source/'source_evidence.json')
 for label,p in [('root',source),('backend',ROOT/'backend/data/controlled_publications'/slug)]:
  if p.exists():shutil.copytree(p,base/'preimages'/label,dirs_exist_ok=True)
 shutil.copytree(source,out,dirs_exist_ok=True)
 archived=[]
 for p in out.glob('approval_evidence*.json'):
  if p.name!='approval_evidence.json':archived.append({'file':p.name,'sha256':sha(p)});p.unlink()
 assets=[];origins={};typography=[]
 try:
  reused=False
  if (out/'cover_delivery_derivation.json').exists() and (out/'cover_provenance.json').exists():
   previous_delivery=load(out/'cover_delivery_derivation.json');previous_provenance=load(out/'cover_provenance.json')
   assets=previous_delivery['assets'];origins=previous_provenance['original_assets_preserved'];typography=previous_provenance['derivative_lineage']['typography_overlay_proof'];reused=True
   assert all(sha(out/a['source_file'])==a['source_sha256'] and sha(base/a['delivery_file'])==a['delivery_sha256'] for a in assets)
  for side in (() if reused else ('front','back')):
   originalpath=base/'recovered'/f'{side}.png';original=Image.open(originalpath).convert('RGBA');im=original.copy();draw=ImageDraw.Draw(im);masks=[]
   target=out/'covers'/f'{side}.png'
   if target.exists():
    # The one executed typography repair produced this retained PNG before
    # the initial delivery budget gate failed. Reuse its exact bytes; never
    # repeat the art/typography mutation for a delivery-only refinement.
    im=Image.open(target).convert('RGBA')
    if side=='front':masks=[cfg['front_title']]+([cfg['front_author']] if cfg['front_author'] else [])+cfg.get('additional_front_masks',[])
    else:masks=([cfg['back_title_author']] if cfg.get('back_title_author') else [cfg['back_title'],cfg['back_author']])+cfg.get('additional_back_masks',[])
   elif side=='front':
    box=cfg['front_title'];panel(draw,box,cfg);masks.append(box)
    for i,t in enumerate(cfg['title']):center(draw,box,cfg['front_y']+i*cfg['front_step'],t,cfg['front_font'],cfg['fg'])
    if cfg['front_author']:
     box=cfg['front_author'];panel(draw,box,cfg);masks.append(box);center(draw,box,box[1]+17,oldbook['author'],cfg['front_author_font'],cfg['fg'])
    else:center(draw,cfg['front_title'],365,oldbook['author'],cfg['front_author_font'],cfg['fg'])
    for box in cfg.get('additional_front_masks',[]):draw.rectangle(box,fill=cfg['bg']);masks.append(box)
   else:
    if cfg.get('back_title_author'):
     box=cfg['back_title_author'];panel(draw,box,cfg);masks.append(box)
     for i,t in enumerate(cfg['title']):center(draw,box,cfg['back_title_y']+i*85,t,cfg['back_font'],cfg['fg'])
     center(draw,box,cfg['back_author_y'],oldbook['author'],cfg['back_author_font'],cfg['fg'])
     for i,t in enumerate(lines(draw,oldbook['short_description'],29,box[2]-box[0]-70)):center(draw,box,885+i*47,t,29,cfg['fg'])
    else:
     box=cfg['back_title'];panel(draw,box,cfg);masks.append(box)
     for i,t in enumerate(cfg['title']):center(draw,box,cfg['back_title_y']+i*(45 if slug=='the-principles-of-scientific-management' else 135 if slug=='acres-of-diamonds' else 85),t,cfg['back_font'],cfg['fg'])
     box=cfg['back_author'];panel(draw,box,cfg);masks.append(box);center(draw,box,cfg['back_author_y'],oldbook['author'],cfg['back_author_font'],cfg['fg'])
    for box in cfg.get('additional_back_masks',[]):draw.rectangle(box,fill=cfg['bg']);masks.append(box)
   # Exhaustive source-art preservation proof outside the precise pixel masks.
   changed=0;old=original.load();new=im.load()
   for y in range(im.height):
    for x in range(im.width):
     if old[x,y]!=new[x,y]:changed+=1;assert any(x1<=x<=x2 and y1<=y<=y2 for x1,y1,x2,y2 in masks),(slug,side,x,y)
   target.parent.mkdir(parents=True,exist_ok=True)
   if not target.exists():im.save(target,format='PNG',optimize=False,compress_level=9)
   filename=f'{slug}-{side}-{sha(target)[:8]}-{delivery_size[0]}.webp';web=base/'frontend/public/assets/books'/slug/filename;web.parent.mkdir(parents=True,exist_ok=True)
   fitted=ImageOps.contain(im.convert('RGB'),delivery_size,Image.Resampling.LANCZOS);canvas=Image.new('RGB',delivery_size,cfg['bg'][:3]);pad=((delivery_size[0]-fitted.width)//2,(delivery_size[1]-fitted.height)//2);canvas.paste(fitted,pad);canvas.save(web,format='WEBP',quality=64,method=6)
   assert web.stat().st_size<=(80000 if side=='front' else 180000),(slug,side,web.stat().st_size,'DELIVERY_BUDGET_FAILED_ONE_ATTEMPT_NO_RETRY')
   origins[side]={'url':oldbook['cover_url' if side=='front' else 'back_cover_url'],'file':f'recovered/{side}.png','sha256':sha(originalpath),'bytes':originalpath.stat().st_size,'dimensions':list(original.size),'method':'One successful GET per persisted original URL; no prior original-byte checksum or creation-method fact inferred.'}
   assets.append({'kind':side,'source_file':f'covers/{side}.png','source_sha256':sha(target),'source_bytes':target.stat().st_size,'source_dimensions':list(original.size),'delivery_file':str(web.relative_to(base)),'delivery_sha256':sha(web),'delivery_bytes':web.stat().st_size,'delivery_dimensions':list(delivery_size),'url':f'https://theearnalism.com/assets/books/{slug}/{filename}','recipe':{'format':'WEBP','mode':'RGB','quality':64,'method':6,'resampling':'LANCZOS','resize':f'aspect-preserving contain {delivery_size[0]}x{delivery_size[1]}','content_dimensions':list(fitted.size),'padding_xy':list(pad),'pillow_version':Image.__version__},'production_observed':False})
   typography.append({'side':side,'exact_title':oldbook['title'],'exact_author':oldbook['author'],'font_file_sha256':sha(FONT),'font_license_sha256':sha(LICENSE),'method':'Actual local deterministic Pillow + licensed DejaVuSerif title and author overlay executed unconditionally; no original glyph/creation method inferred.','precise_masks':masks,'changed_pixels':changed,'changed_pixels_outside_masks':0})
 except AssertionError as exc:
  reason=str(exc);write(base/'terminal-disposition.json',{'slug':slug,'status':'DROPPED_ACTIVE_PLAN_ONE_BOUNDED_REPAIR_FAILURE','reason':reason,'attempts':1,'source_originals_decisions_preserved':True,'paid_calls':0,'production_mutations':False});results.append({'slug':slug,'status':'DROPPED_ACTIVE_PLAN_ONE_BOUNDED_REPAIR_FAILURE','reason':reason});continue
 shutil.copyfile(base/'source-proof.json',out/'source_integrity_validation.json')
 write(out/'cover_provenance.json',{'schema':'earnalism.cover-provenance.v1','slug':slug,'status':'PROPOSED_COMPONENT_EVIDENCE_NOT_ACCEPTED_TWO_REVIEWS_REQUIRED','recorded_at':AT,'original_creator':'Repository/product owner; no other identity inferred','original_method':'UNKNOWN_NOT_INFERRED','owner_declaration':{'statement':'Owner states all front and back covers are designed by the owner.','path':str(OWNER.relative_to(ROOT)),'sha256':sha(OWNER),'scope':'COVER_DESIGN_ONLY'},'original_assets_preserved':origins,'derivative_lineage':{'method':'One bounded deterministic typography/copy repair of retained original art; no model/provider/image generation or new artwork.','typography_overlay_proof':typography,'issues_handled':cfg['issues'],'font_license_path':'practical-batch-prep-20261003/DejaVu-font-license.txt','commercial_font_permission':'Actual local Bitstream Vera licence grants use/publish/distribute; only raster output, no font software binary distributed.'},'commercial_use_authorized':False,'cover_display_approved':False,'audio_authorized':False,'publication_activation_authorized':False,'runtime_release_authorized':False,'scope':'Evidence-only exact proposal. Owner declaration and exact original-art bytes do not establish unsupported third-party origin/permissions; independent reviewers must hold any specifically evidenced component dispute.','independent_reviews':'PENDING_TWO_EXACT_SOURCE_ART_COMPLIANCE_PACKAGE_REVIEWS'})
 write(out/'cover_delivery_derivation.json',{'schema':'earnalism.exact-cover-delivery-derivation.v1','slug':slug,'assets':assets,'review_status':'PENDING_TWO_FRESH_EXACT_PNG_WEBP_VISUAL_CHECKS','production_observed':False,'runtime_observed':False})
 book=oldbook.copy()
 for k in ('cover_url','cover_image_url','coverImage','cover_image'):book[k]=assets[0]['url']
 for k in ('back_cover_url','back_cover_image_url','backCoverImage'):book[k]=assets[1]['url']
 book.update(approved_to_publish=False,publication_status='READY_FOR_APPROVAL',publicationStatus='draft',isPublic=False,isLive=False,showInPublicLibrary=False,showInHomepage=False,allowPublicReading=False,is_published=False,audio_enabled=False,audiobook_enabled=False,generate_audiobook=False,audiobook_assets={},audiobook={},audio_status='NOT_REQUESTED',audiobook_release_gate='NOT_REQUESTED',audio_qa_status='NOT_RUN',audio_url='',sync_tier='NONE',cover_status='EXACT_ORIGINAL_ART_DETERMINISTIC_TYPOGRAPHY_PROPOSAL_PENDING_REVIEW',cover_dimensions={'front':list(delivery_size),'back':list(delivery_size)},rights_basis=oldsource['rights_basis'])
 for k in ('audiobook_provider','audiobook_voice','audio_asset_slug','audiobook_assets_updated_at','audiobook_release_conveyor','audiobook_use_approval_source','audiobook_use_approved_at'):book.pop(k,None)
 if 'publication_workflow' in book:
  wf=book['publication_workflow'];wf['audio']={'status':'NOT_REQUESTED','release_status':'NOT_REQUESTED','qa_status':'NOT_RUN'};wf.setdefault('publication',{}).update(state='READY_FOR_APPROVAL',reader_exposed=False,audio_exposed=False);wf.setdefault('release',{}).update(reader_release='READY_FOR_APPROVAL',audio_release='NOT_REQUESTED')
 write(out/'public_book.json',book)
 reader=load(source/'reader_manifest.json');reader.update(audio_enabled=False,audiobook_enabled=False)
 for k in ('audiobook_assets','audio_status','audio_qa_status','sync_tier','audio_url'):reader.pop(k,None)
 write(out/'reader_manifest.json',reader)
 auth=load(source/'publication_authorization.json');auth.update(publication_authorized=False,scope='INACTIVE_TEXT_AND_EXACT_COVER_PROPOSAL_PENDING_REVIEW_NOT_AUTHORIZED',cover_provenance_sha256=sha(out/'cover_provenance.json'),cover_status='PENDING_TWO_INDEPENDENT_COVER_PACKAGE_REVIEWS',authorized_by='NOT_ACCEPTED. Root serialized controller may record genuine acceptance only after exact independent reviews pass.',verified_at=AT,release_condition='Existing raw noncover accepted text record retained in preimages. Exact proposal is inactive and requires two independent reviews then truthful prospective owner-delegated acceptance before any registry/allowlist/protected release.',audio_authorized=False,production_activation_authorized_by_this_file=False)
 write(out/'publication_authorization.json',auth)
 oldapproval=load(source/'approval_evidence.json');approval={k:v for k,v in oldapproval.items() if not any(t in k.lower() for t in ('audio','sync','tts','voice','provider','duration','endpoint','object','candidate','fingerprint'))};approval.update(approved_to_publish=False,approval_scope='INACTIVE_SOURCE_BOUND_EXACT_OWNER_ART_TYPOGRAPHY_PROPOSAL_PENDING_TWO_REVIEWERS',audio_public_release='PUBLIC_AUDIO_RELEASE_NOT_APPROVED',audio_enabled=False,audiobook_enabled=False,audio_status='NOT_REQUESTED',audiobook_release_gate='NOT_REQUESTED',audio_qa_status='NOT_RUN',sync_tier='NONE',audiobook_use_approved=False,audiobook_use_approval_source='',audiobook_use_approved_at='',publication_authorization_sha256=sha(out/'publication_authorization.json'),cover_provenance_sha256=sha(out/'cover_provenance.json'),cover_delivery_derivation_sha256=sha(out/'cover_delivery_derivation.json'),source_integrity_validation_sha256=sha(out/'source_integrity_validation.json'),cover_front_qa_status='PENDING',cover_back_qa_status='PENDING',production_observed=False,verified_at=AT)
 write(out/'approval_evidence.json',approval)
 manifest=build_manifest(out,publish_approved=False,generated_at=AT);assert not validate_manifest(manifest) and not manifest['reader_release']['blockers'] and not manifest['reader_release']['exposed'] and not manifest['audio_release']['exposed'];write(out/'publication_manifest.json',manifest)
 checksum={'slug':slug,'generated_at':AT,'files':[{'file':str(p.relative_to(out)),'sha256':sha(p)} for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ('checksum_manifest.json','publication_manifest.json','rights_decision.json')]};write(out/'checksum_manifest.json',checksum)
 dec=load(source/'rights_decision.json');dec.update(decision_id=f'india-20261003-{slug}-reader-cover-inactive-proposal',status='PROPOSED',conditions_satisfied=False,accepted_by='NOT_ACCEPTED; preparation worker makes no cover/publication acceptance decision.',valid_from=AT,basis='Unaccepted exact inactive proposal. Reuse prior accepted IN noncover text facts without inferred original methods, rights, human approval or production observation. Full selected-work proof plus one deterministic original-art title/author/copy repair awaits two independent reviewers and serialized owner-delegated controller acceptance.',components={k:sha(out/f'{k}.json') for k in ('public_book','reader_manifest','source_evidence','approval_evidence','checksum_manifest','publication_manifest','cover_provenance','cover_delivery_derivation')},uses=['catalog_metadata','cover_display','reader_preview','reader_delivery','reading_pass_session','reading_pass_renewal']);dec['components'].update(cover_front_asset=assets[0]['source_sha256'],cover_back_asset=assets[1]['source_sha256'],cover_front_delivery=assets[0]['delivery_sha256'],cover_back_delivery=assets[1]['delivery_sha256']);write(out/'rights_decision.json',dec)
 issues=[]
 def scan(v,path,ctx=''):
  if isinstance(v,dict):
   for k,x in v.items():
    p=ctx+'/'+k
    if any(t in p.lower() for t in ('audio','audiobook','sync_tier')) and (x is True or isinstance(x,str) and x.upper() in ('APPROVED','PUBLIC_AUDIO_RELEASE_APPROVED','AVAILABLE','LIVE','QA_PASSED','AUDIO_ONLY_NO_SYNC')):issues.append([path,p,x])
    if k in ('production_observed','runtime_observed','reader_exposed','audio_exposed','publication_observed') and x is True:issues.append([path,p,x])
    if k!='historical_admin_import_claim':scan(x,path,p)
  elif isinstance(v,list):
   for i,x in enumerate(v):scan(x,path,ctx+f'[{i}]')
 for p in out.rglob('*.json'):scan(load(p),str(p.relative_to(out)))
 assert not issues,(slug,issues)
 assert all(sha(out/e['file'])==e['sha256'] for e in checksum['files'])
 for p in source.rglob('*'):
  if p.is_file() and (p.name in ('source_evidence.json','highlight_sync.json') or p.parent.name=='chapters'):assert p.read_bytes()==(out/p.relative_to(source)).read_bytes()
 inv={label:[{'file':str(p.relative_to(base/'preimages'/label)),'sha256':sha(p)} for p in sorted((base/'preimages'/label).rglob('*')) if p.is_file()] for label in ('root','backend') if (base/'preimages'/label).exists()};write(base/'preimage-inventory.json',inv)
 validation={'schema':'earnalism.distinct-practical-title-preparation.v1','slug':slug,'status':'INACTIVE_UNACCEPTED_TWO_INDEPENDENT_REVIEWS_REQUIRED','recorded_at':AT,'source_proof_sha256':sha(out/'source_integrity_validation.json'),'source_originals_chapters_sync_decisions_preserved':True,'exact_prior_IN_text_basis':True,'one_get_per_original_cover':True,'one_bounded_typography_copy_attempt':True,'deterministic_typography_overlay_actual_execution_proven':True,'original_typography_creation_method_inferred':False,'font_license_actual_bytes_preserved':True,'cover_dimensions_actual':list(delivery_size),'delivery_budgets':'PASS_FRONT_80000_BACK_180000','all_active_JSON_audio_and_observation_claim_scan':'PASS_NO_POSITIVE_CLAIMS','historical_duplicates_archive_only':archived,'original_assets':origins,'delivery_assets':assets,'proposed_decision_record_sha256':record_sha256(dec),'candidate_inventory':[{'file':str(p.relative_to(out)),'sha256':sha(p)} for p in sorted(out.rglob('*')) if p.is_file()],'publication_accepted':False,'cover_accepted':False,'paid_generation_calls':0,'registry_allowlist_shared_source_production_mutations':False,'next_action':'Two independent fresh exact PNG/WebP/source/provenance/font-policy/package reviews. Substantial unresolved dispute after this attempt means terminal active-plan exclusion; no repeated art/source work.'};write(base/'preparation-validation.json',validation)
 results.append({'slug':slug,'status':validation['status'],'validation_sha256':sha(base/'preparation-validation.json'),'candidate_files':len(validation['candidate_inventory']),'checksum_entries':len(checksum['files']),'proposed_decision_record_sha256':record_sha256(dec),'delivery_assets':assets})
write(WORK/'batch-results.json',{'recorded_at':AT,'titles':results,'shared_mutations':False,'paid_calls':0})
print(json.dumps(results,ensure_ascii=False,indent=2))
