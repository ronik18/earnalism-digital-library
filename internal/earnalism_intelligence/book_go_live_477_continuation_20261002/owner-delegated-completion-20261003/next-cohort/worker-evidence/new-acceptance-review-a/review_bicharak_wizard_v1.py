from pathlib import Path
import json,hashlib,unicodedata,re,io,sys,datetime
from PIL import Image,ImageDraw,ImageChops,features
from fontTools.ttLib import TTFont
R=Path('/tmp/earnalism-main-approved-integration');C=Path('/workspace/scratch/181ef0a25f05');O=C/'new-acceptance-review-a'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hs(s):return hashlib.sha256(s.encode()).hexdigest()
def j(p):return json.loads(Path(p).read_text())
def norm(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFC',s.replace('\ufeff','').replace('\u200b',''))).strip()
def audit(slug,base,package,pre):
 files={str(p.relative_to(package)):h(p) for p in package.rglob('*') if p.is_file()}; allhash={h(p):str(p) for p in base.rglob('*') if p.is_file()};d=j(package/'rights_decision.json');checks=j(package/'checksum_manifest.json')['files']; assert all(h(package/x['file'])==x['sha256'] for x in checks)
 assert all(v in allhash for v in d['components'].values());assert d['territories']==['IN'] and not d['conditions_satisfied'] and d['status'] in ['PROPOSED','PENDING_REVIEW']
 for f in ['source_evidence.json','highlight_sync.json']+[str(x.relative_to(pre)) for x in (pre/'chapters').glob('*.json')]:assert h(package/f)==h(pre/f),f
 if (pre/'license_notice.json').exists():assert h(package/'license_notice.json')==h(pre/'license_notice.json')
 book=j(package/'public_book.json');reader=j(package/'reader_manifest.json');a=j(package/'approval_evidence.json');m=j(package/'publication_manifest.json');assert not book['isLive'] and not book['isPublic'] and not book['approved_to_publish'] and not a['approved_to_publish'];assert not reader['audio_enabled'] and not reader['audiobook_enabled'];assert not m['reader_release']['exposed'] and not m['audio_release']['exposed']
 oldreader=j(pre/'reader_manifest.json'); newclean={k:v for k,v in reader.items() if not re.search(r'audio|listen|sync',k,re.I)};oldclean={k:v for k,v in oldreader.items() if not re.search(r'audio|listen|sync',k,re.I)};assert newclean==oldclean
 assets=[]
 for key in ['cover_url','back_cover_url']:
  suffix=book[key].split('/assets/',1)[1];p=next(iter((base).glob('**/frontend/public/assets/'+suffix)));im=Image.open(p);im.load();assert p.stat().st_size<= (80000 if key=='cover_url' else 180000);assets.append({'path':str(p),'sha256':h(p),'bytes':p.stat().st_size,'dimensions':list(im.size)})
 sys.path.insert(0,str(R/'backend'));from publication_manifest import validate_manifest
 assert not validate_manifest(m),validate_manifest(m)
 bad=[]
 def scan(x,path=''):
  if isinstance(x,dict):
   for k,v in x.items():
    if k in ['historical_admin_import_claim']:continue
    pp=path+'.'+k
    if re.search(r'audio|audiobook|listen',k,re.I):
     if (v is True and not any(t in k for t in ['not_propagated','disabled','excluded','preserved'])) or isinstance(v,str) and ('.mp3' in v or v in ['ACTIVE','LIVE','APPROVED']):bad.append((pp,v))
    if k in ['production_observed','runtime_observed'] and v is True:bad.append((pp,v))
    scan(v,pp)
  elif isinstance(x,list):
   for i,v in enumerate(x):scan(v,path+f'[{i}]')
 for fn in ['public_book.json','reader_manifest.json','approval_evidence.json','publication_authorization.json','cover_provenance.json']:scan(j(package/fn),fn)
 assert not bad,bad
 return {'package_inventory':files,'decision_sha256':h(package/'rights_decision.json'),'component_count':len(d['components']),'checksums_verified':len(checks),'source_chapters_license_sync_unchanged':True,'inactive_unaccepted_audio_neutral':True,'manifest_schema':'PASS','delivery':assets}
b=C/'bicharak-owner-art-prep-20261003';p=b/'proposal/data/controlled_publications/book-5704b31005';x=audit('book-5704b31005',b,p,b/'preimages/root');cp=j(b/'cover-preparation.json');sp=R/'internal/legal/catalogue_clearance_20261002/bengali/book-5704b31005-final-source-comparison.json';assert h(sp)==cp['excerpt_source_snapshot_sha256'];sj=j(sp);chapter=j(p/'chapters/chapter-001.json');assert norm('\n\n'.join(sj['source_paragraphs']))==norm(chapter['content']);assert cp['first_complete_source_paragraph']==sj['source_paragraphs'][2];assert cp['first_complete_source_paragraph']==cp['assets']['back']['body_excerpt'];assert hs(chapter['content'])=='c9e4ed3927535c11a5d1d5a4729f0c8a1371952a33a6e0e6d36514b3d249b089'
for side,asset in cp['assets'].items():
 for key in ['original','prepared_png','delivery']:assert h(asset[key]['path'])==asset[key]['sha256']
 orig=Image.open(asset['original']['path']).convert('RGB');new=Image.open(asset['prepared_png']['path']).convert('RGB');mask=Image.new('L',orig.size,255);draw=ImageDraw.Draw(mask)
 for box in asset['repair_zones']:draw.rectangle(box,fill=0)
 diff=ImageChops.difference(orig,new);assert not ImageChops.multiply(diff,Image.merge('RGB',(mask,mask,mask))).getbbox()
 buf=io.BytesIO();new.resize((800,1200),Image.Resampling.LANCZOS).save(buf,format='WEBP',quality=72,method=6);assert hashlib.sha256(buf.getvalue()).hexdigest()==asset['delivery']['sha256']
assert features.check('raqm')
for font in cp['fonts']:
 fp=R/font['path'];assert h(fp)==font['sha256'];ff=TTFont(fp);codes=ff.getBestCmap();required={ord(c) for c in cp['first_complete_source_paragraph']+cp['metadata_binding']['title']+cp['metadata_binding']['author'] if 0x980<=ord(c)<=0x9ff};assert required<=codes.keys();assert any('openfontlicense' in n.toUnicode().lower() for n in ff['name'].names)
x.update({'slug':'book-5704b31005','status':'PASS_PREPARATION_ONLY','source_review':{'complete_selected_source_paragraphs':len(sj['source_paragraphs']),'entire_reader_equality':'PASS_NFC_BOM_ZWSP_WHITESPACE_ONLY','primary_source_snapshot_sha256':h(sp),'source_gets':0},'visual_review':{'actual_prepared_png_and_webp_inspected':True,'title_author_copy_footer_legibility':'PASS','false_live_and_occlusion':'RESOLVED','back_copy':'EXACT_ENTIRE_FIRST_SOURCE_BODY_PARAGRAPH','aesthetic_limitation':'Rectangular maroon repair panels retain graphical coins outside masks; no substantive compliance conflict','outside_mask_rgb_identity':'PASS','delivery_recipe_reproduced_byte_exact':'PASS','licensed_bengali_font_cmap_raqm':'PASS'},'owner_basis_sha256':'0881001b09b5b47649f14ff289aaa7f64e98004adc3d800f67d90fab703f9264','original_creation_method':'UNKNOWN_NOT_INFERRED','remediation_attempts':1,'acceptance_or_production_claim':False})
wp=C/'wizard-preparation-20261003';pack=wp/'proposed-package/data/controlled_publications/the-wonderful-wizard-of-oz';w=audit('the-wonderful-wizard-of-oz',wp,pack,wp/'root-preimage');proof=j(wp/'wizard-whole-work-proof-reuse.json');assert h(wp/'current_whole_work_boundary_verification.json')==proof['proof_artifact_sha256'];t=proof['title_proof'];reader=j(pack/'reader_manifest.json');chapters=[j(pack/'chapters'/f"{c['id']}.json") for c in reader['chapters']];assert len(chapters)==25;assert {c['id']:hs(c['content']) for c in chapters}==t['ordered_chapter_hashes'];assert hs('\n\n'.join(c['content'] for c in chapters))==t['reader_aggregate_sha256'];assert len(t['internal_gaps'])==24;assert all('Chapter' in g['text'] and hs(g['text'])==g['sha256'] for g in t['internal_gaps']);assert t['source_boundary_after_last'].lstrip().startswith('*** END OF THE PROJECT GUTENBERG');assert not t['containment_alone_complete'];bind=j(wp/'proposed-cover-binding.json');assert h(wp/'owner_artwork_declaration.json')==bind['owner_design_declaration']['sha256']
for side in ['front','back']:
 o=bind['original_'+side];v=bind['delivery'][side];assert h(o['path'])==o['sha256'];assert h(v['path'])==v['sha256'];im=Image.open(o['path']).convert('RGB');buf=io.BytesIO();im.resize((500,750),Image.Resampling.LANCZOS).save(buf,format='WEBP',quality=45,method=6);assert hashlib.sha256(buf.getvalue()).hexdigest()==v['sha256']
w.update({'slug':'the-wonderful-wizard-of-oz','status':'PASS_PREPARATION_ONLY','source_review':{'scope':t['selected_edition_scope'],'raw_source_sha256':t['raw_source_sha256'],'proof_inventory_sha256':proof['proof_artifact_sha256'],'chapter_body_hashes_and_aggregate':'PASS_25_EXACT','source_boundary_and_24_heading_only_gaps':'REUSED_EXACT_PERSISTED_COMPLETE_SCOPE_PROOF','historical_containment_limitation_preserved':True,'physical_book_dedication_and_illustrations':'EXCLUDED_SELECTED_SCOPE','source_gets':0},'visual_review':{'actual_original_png_and_delivery_webp_inspected':True,'title_author_fullframe_footer':'PASS','back':'Illustrative scene/map without attributed synopsis or quotation','derivative_recipe_reproduced_byte_exact':'PASS_FULLFRAME_LANCZOS_500X750_Q45_METHOD6','art_repairs':0},'owner_basis_sha256':bind['owner_design_declaration']['sha256'],'original_creation_method':'UNKNOWN_NOT_INFERRED','acceptance_or_production_claim':False})
for slug,out in [('bicharak',x),('wizard',w)]:
 out.update({'reviewer':'independent-agent-A','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'next_gate':'SECOND_INDEPENDENT_PASS_THEN_ACTUAL_PROSPECTIVE_ACCEPTANCE_SERIALIZED_INTEGRATION_CI_DEPLOYMENT_CANARY_READBACK','new_network_requests':0,'paid_calls':0,'canonical_mutations':0});dest=O/f'{slug}-preparation-review-a-v1.json';assert not dest.exists();dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(dest,h(dest),out['status'],out['component_count'],out['checksums_verified'])
