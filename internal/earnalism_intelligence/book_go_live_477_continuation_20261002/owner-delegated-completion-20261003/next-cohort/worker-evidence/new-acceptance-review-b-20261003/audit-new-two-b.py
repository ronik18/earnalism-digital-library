import json,hashlib,pathlib,unicodedata,re,datetime
import numpy as np
from PIL import Image
B=pathlib.Path('/workspace/scratch/181ef0a25f05'); R=pathlib.Path('/tmp/earnalism-main-approved-integration'); O=B/'new-acceptance-review-b-20261003'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(j):return hashlib.sha256(json.dumps(j,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def load(p):return json.loads(p.read_text())
def norm(s):return ' '.join(unicodedata.normalize('NFC',s).replace('\ufeff','').replace('\u200b','').split())
def audit(c,pre,validation):
 out={'files':{},'checksum_count':0,'component_count':0,'unchanged_files':[],'audio_claims':[]}
 inv=validation.get('package_inventory',validation.get('all_candidate_files',{}))
 for n,h in inv.items():assert sha(c/n)==h,n
 out['files']={str(p.relative_to(c)):sha(p) for p in c.rglob('*') if p.is_file()}
 for x in load(c/'checksum_manifest.json')['files']: assert sha(c/x['file'])==x['sha256'],x;out['checksum_count']+=1
 d=load(c/'rights_decision.json');assert d['territories']==['IN'];assert d['status']=='PROPOSED' and d['conditions_satisfied']==False
 for n,h in d['components'].items(): assert sha(c/(n+'.json'))==h,n;out['component_count']+=1
 out['decision_raw_sha256']=sha(c/'rights_decision.json');out['decision_canonical_sha256']=canon(d)
 for p in (c/'chapters').glob('*.json'):
  assert p.read_bytes()==(pre/'chapters'/p.name).read_bytes();j=load(p);assert hashlib.sha256(j['content'].encode()).hexdigest()==j['content_hash'];out['unchanged_files'].append('chapters/'+p.name)
 for n in ['source_evidence.json','highlight_sync.json','license_notice.json']:
  if (c/n).exists():assert(c/n).read_bytes()==(pre/n).read_bytes(),n;out['unchanged_files'].append(n)
 def scan(j,k=''):
  if isinstance(j,dict):
   for a,v in j.items():scan(v,k+'.'+a)
  elif isinstance(j,list):
   for i,v in enumerate(j):scan(v,k+f'[{i}]')
  elif ('audio'in k.lower() or 'listen'in k.lower()) and (j is True or isinstance(j,str) and j.startswith('http')):out['audio_claims'].append([k,j])
 for n in ['public_book.json','reader_manifest.json','approval_evidence.json','publication_authorization.json','publication_manifest.json']:
  if(c/n).exists():scan(load(c/n),n)
 return out
t=B/'bicharak-owner-art-prep-20261003';c=t/'proposal/data/controlled_publications/book-5704b31005';v=load(t/'validation.json');a=audit(c,t/'preimages/root',v);prep=load(t/'cover-preparation.json');sv=load(t/'source-validation.json');proof=R/sv['source_snapshot'];assert sha(proof)==sv['source_snapshot_sha256'];source=load(proof)['source_paragraphs'];ch=load(c/'chapters/chapter-001.json');assert len(source)==40;assert norm(ch['content'])==norm('\n\n'.join(source));assert prep['first_complete_source_paragraph']==next(x for x in source if len(x)>200);assets=[]
for side,x in prep['assets'].items():
 for k in ['original','prepared_png','delivery']:
  z=x[k];q=pathlib.Path(z['path']);assert sha(q)==z['sha256'];im=Image.open(q);im.load();assert list(im.size)==z['dimensions']
 old=np.array(Image.open(x['original']['path']).convert('RGB'));new=np.array(Image.open(x['prepared_png']['path']).convert('RGB'));mask=np.ones(old.shape[:2],bool)
 for x1,y1,x2,y2 in x['repair_zones']:mask[y1:y2+1,x1:x2+1]=False
 assert np.array_equal(old[mask],new[mask]);assert x['delivery']['bytes']<=x['delivery']['budget'];assets.append({'side':side,'original':x['original']['sha256'],'prepared':x['prepared_png']['sha256'],'delivery':x['delivery']['sha256'],'bytes':x['delivery']['bytes'],'outside_precise_masks_exact':True})
for x in prep['fonts']:assert sha(R/x['path'])==x['sha256']
assert not a['audio_claims'];assert not(c/'approval_evidence 2.json').exists();assert sha(t/'preimages/root/approval_evidence 2.json')=='bd7b06c58b8eb1efa01ec1d051f60d79463205c51027615a924603eba0980bd5';cp=load(c/'cover_provenance.json');print('BichCPowner',cp.get('owner_declaration'),cp.keys());a.update({'slug':'book-5704b31005','reviewer':'Independent Codex reviewer B','disposition':'PASS_FRESH_PREPARATION_UNACCEPTED_NOT_RELEASED','whole_source_identity':'Exact entire captured40paragraphs equals whole unchanged canonical story under NFC/BOM/zero-width-space/whitespace only; first full229character narrative paragraph after story/section headings binds actualbackcopy','source_proof_sha256':sha(proof),'assets':assets,'visual_png_and_webp':'PASS: title-author/copy now legible and not coin-occluded; complete sourceparagraph shows without clipping; false LIVE badge removed, intact Earnalism footer. Coin motif aesthetics disclosed; no substantive compliance/source dispute.','font_and_RAqm':'Exact repository licensed Noto bytes+embedded OFL/RAQM; real new glyphs correctly shaped, no originalmethod inferred.','owner_artwork_directive_sha256':'0881001b09b5b47649f14ff289aaa7f64e98004adc3d800f67d90fab703f9264','original_art_method':'UNKNOWN_NOT_INFERRED','historical_positive_duplicate_approval_archive_only':True,'source_art_reviews_downloads_renders_paid_calls_by_B':0,'canonical_mutations':False,'production_observed':False,'actual_acceptance_by_B':False,'reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()});out=O/'bicharak-new-preparation-review-b.json';out.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');print('BICHRECEIPT',sha(out))
t=B/'wizard-preparation-20261003';stage=t/'proposed-package';c=stage/'data/controlled_publications/the-wonderful-wizard-of-oz';prior=t/'root-preimage';d=load(c/'rights_decision.json');binding=load(t/'proposed-cover-binding.json');delivery=load(t/'delivery-receipt.json');checks={};components={}
for k,val in d['components'].items():
 if '_original_asset'in k:q=c/'covers'/('original-front.png'if'front'in k else'original-back.png')
 elif '_delivery_asset'in k:q=pathlib.Path(delivery['assets']['front'if'front'in k else'back']['path'])
 else:q=c/(k+'.json')
 assert sha(q)==val;components[k]=val
for x in load(c/'checksum_manifest.json')['files']:assert sha(c/x['file'])==x['sha256']
assert d['status']=='PENDING_REVIEW'and not d['conditions_satisfied'];assert d['territories']==['IN'];assert sha(c/'owner_artwork_declaration.json')=='0881001b09b5b47649f14ff289aaa7f64e98004adc3d800f67d90fab703f9264'
for q in c.rglob('*'):
 if q.is_file():assert sha(q)==sha(stage/'backend/data/controlled_publications/the-wonderful-wizard-of-oz'/q.relative_to(c))
for n in ['source_evidence.json','highlight_sync.json']+[str(q.relative_to(c))for q in(c/'chapters').glob('*.json')]:assert(c/n).read_bytes()==(prior/n).read_bytes()
proof=load(t/'wizard-whole-work-proof-reuse.json');assert sha(R/'internal/legal/catalogue_clearance_20261002/english/current_whole_work_boundary_verification.json')==proof['proof_artifact_sha256'];bd=proof['title_proof'];chapterlist=[]
for q in sorted((c/'chapters').glob('*.json')):
 ch=load(q);assert ch['content_hash']==bd['ordered_chapter_hashes'][ch['id']];chapterlist.append(ch)
assert len(chapterlist)==25;assert hashlib.sha256('\n\n'.join(x['content']for x in chapterlist).encode()).hexdigest()==bd['reader_aggregate_sha256'];assert len(bd['internal_gaps'])==24;assert bd['source_boundary_after_last'].lstrip().startswith('*** END OF THE PROJECT GUTENBERG');assert all(len(x['text'])<200 for x in bd['internal_gaps'])
assets=[]
for side,x in delivery['assets'].items():
 z=binding['original_'+side];assert sha(pathlib.Path(z['path']))==z['sha256']==x['source_sha256'];assert sha(pathlib.Path(x['path']))==x['sha256'];im=Image.open(x['path']);im.load();assert im.size==(500,750);assert x['bytes']<=(80000 if side=='front' else 180000);assets.append({'side':side,'original':z['sha256'],'delivery':x['sha256'],'bytes':x['bytes'],'fullframe_no_art_change':True})
claims=[]
def scan(j,k=''):
 if isinstance(j,dict):
  for key,v in j.items():scan(v,k+'.'+key)
 elif isinstance(j,list):
  for i,v in enumerate(j):scan(v,k+f'[{i}]')
 elif ('audio'in k.lower()or'listen'in k.lower())and(j is True or isinstance(j,str)and j.startswith('http')):claims.append([k,j])
for n in ['public_book.json','reader_manifest.json','approval_evidence.json','publication_authorization.json','publication_manifest.json']:scan(load(c/n),n)
assert not claims;pub=load(c/'public_book.json');assert not pub['isLive']and not pub['isPublic'];assert pub['cover_dimensions']=={'front':[500,750],'back':[500,750]};a={'slug':'the-wonderful-wizard-of-oz','reviewer':'Independent Codex reviewer B','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'disposition':'PASS_FRESH_PREPARATION_UNACCEPTED_NOT_RELEASED','decision_raw_sha256':sha(c/'rights_decision.json'),'decision_components':components,'checksum_entries':len(load(c/'checksum_manifest.json')['files']),'source_preservation':'Exactunchanged source/highlight/25chapters includingauthorIntro; allhashes/aggregate/first-last/24heading-onlygaps match complete priorproof; no freshsourceGET or inferred fullphysicaledition beyond selectedPG55','prior_complete_boundary_proof_sha256':proof['proof_artifact_sha256'],'assets':assets,'visual_actual_original_png_and_delivered_webp':'PASS: fullframe content-themed owner art, correct legible title/author/footer, intact frame. Actualcompressed title/footer remain legible; no falseLIVE/audio claims, unquoted fantasyplacenames used as graphical thematiccopy.','owner_artwork_directive_sha256':'0881001b09b5b47649f14ff289aaa7f64e98004adc3d800f67d90fab703f9264','original_art_and_glyph_creation_method':'UNKNOWN_NOT_INFERRED; exact ownercopyright/publicationprovenance accepted as userdirected, no extra externalrights/method investigation','active_audio_claims':claims,'root_backend_exact_mirror':True,'production_observed':False,'actual_acceptance_by_B':False,'canonical_mutations':False,'source_downloads_renders_paid_calls_by_B':0};out=O/'wizard-new-preparation-review-b.json';out.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');print('WIZARDRECEIPT',sha(out))
