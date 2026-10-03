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
results=[]
for s in ['the-time-machine','the-great-gatsby','frankenstein','the-secret-garden','pride-and-prejudice','great-expectations']:
 t=B/'classics6-prep-20261003'/s;c=t/'candidate-inactive-unaccepted';v=load(t/'validation.json');a=audit(c,t/'preimages/root',v);p=load(c/'cover_preparation.json');assets=[]
 for x in p['assets']:
  for rel,h in [(x['source_file'],x['source_sha256']),(x['file'],x['sha256']),(x['licensed_deterministic_overlay']['file'],x['licensed_deterministic_overlay']['sha256'])]: assert sha(c/rel)==h;Image.open(c/rel).load()
  old=np.array(Image.open(c/x['source_file']).convert('RGB'));new=np.array(Image.open(c/x['licensed_deterministic_overlay']['file']).convert('RGB'));mask=np.ones(old.shape[:2],bool);x1,y1,x2,y2=x['licensed_deterministic_overlay']['mask_rectangle'];mask[y1:y2+1,x1:x2+1]=False;assert np.array_equal(old[mask],new[mask]);assert Image.open(c/x['file']).size==tuple(x['dimensions']);assert (c/x['file']).stat().st_size==x['bytes']<= (80000 if x['kind']=='front' else 180000);assets.append(x)
 g=p['title_author_gate'];assert sha(R/g['font_file'])==g['font_sha256'];assert sha(R/g['font_license_file'])==g['font_license_sha256'];assert sha(pathlib.Path(p['owner_design_fact']['source']))==p['owner_design_fact']['sha256']
 source=p['source_binding'];assert sha(R/source['boundary_receipt_path'])==source['boundary_receipt_file_sha256'];persist=load(R/source['boundary_receipt_path'])['titles'];persist=next(x for x in persist if x['slug']==s);assert persist==p['boundary_receipt'];chunks=[]
 for q in sorted((c/'chapters').glob('*.json')):
  ch=load(q);assert ch['content_hash']==persist['ordered_chapter_hashes'][ch['id']];assert ch['sourceSha256']==persist['raw_source_sha256'];chunks.append(ch['content'])
 assert hashlib.sha256('\n\n'.join(chunks).encode()).hexdigest()==persist['reader_aggregate_sha256']
 assert len(chunks)==persist['chapter_count'];assert len(persist['internal_gaps'])==len(chunks)-1
 for gap in persist['internal_gaps']:assert hashlib.sha256(gap['text'].encode()).hexdigest()==gap['sha256'];assert gap['length']==len(gap['text'])
 for x in p['cover_quote_checks']:
  ch=load(c/'chapters'/x['chapter']);assert sha(c/'chapters'/x['chapter'])==x['chapter_file_sha256'];assert norm(x['quote']).casefold() in norm(ch['content'].replace('_','').replace('*','')).casefold()
 a.update({'slug':s,'reviewer':'Independent Codex reviewer B','source_prior_complete_boundary_reuse':'PASS_EXACT_ALL_CHAPTER_HASHES_AGGREGATE_FIRST_LAST_AND_HEADING_ONLY_GAPS','fresh_official_source_body_verification':'PENDING_SINGLE_AUTHORIZED_A_RECOVERY' if s not in ['the-great-gatsby','great-expectations']else'PRIOR_EXACT_COMPLETE_BOUNDARY_PROOF_REUSED','source_boundary_receipt_sha256':source['boundary_receipt_file_sha256'],'assets':assets,'font_license_provenance_and_pixel_masks':'PASS','visual_delivery':'HOLD' if s=='great-expectations' else'PASS','binding_disposition':'HOLD_METADATA_AUDIO_SCOPE_CORRECTION_REQUIRED' if a['audio_claims']else'PASS_UNACCEPTED_PROPOSAL','terminal_visual_blocker':'New back author/title overlay masks part of retained Earnalism footer; visible cut line in PNG and WebP. First bounded art repair exhausted; terminal active-sprint exclusion.'if s=='great-expectations'else None,'no_new_fetch_or_asset_render':True,'canonical_mutations':False,'production_observed':False,'reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 out=O/(s+'-proposed-review-b.json');out.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');results.append({'slug':s,'path':str(out),'sha256':sha(out),'audio_claims':a['audio_claims'],'visual_delivery':a['visual_delivery']})
print(json.dumps(results,indent=2))
