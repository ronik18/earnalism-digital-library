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
for s in ['lokrahasya','mrinalini','bn-066']:
 t=B/'bengali-next-cohort-20261003'/s;c=t/'proposal/data/controlled_publications'/s;v=load(t/'validation.json');a=audit(c,t/'preimages/root',v)
 p=load(t/'cover-preparation.json');art=[]
 for side,x in p['assets'].items():
  for k in ['original','prepared_png','delivery']:
   z=x[k];pp=pathlib.Path(z['path']);assert sha(pp)==z['sha256'];im=Image.open(pp);im.load();assert list(im.size)==z['dimensions']
  old=np.array(Image.open(x['original']['path']).convert('RGB'));new=np.array(Image.open(x['prepared_png']['path']).convert('RGB'));mask=np.ones(old.shape[:2],bool)
  for x1,y1,x2,y2 in x['repair_zones']:mask[y1:y2+1,x1:x2+1]=False
  assert np.array_equal(old[mask],new[mask]);assert x['delivery']['bytes']<=x['delivery']['budget'];art.append({'side':side,'hashes':{k:x[k]['sha256'] for k in ['original','prepared_png','delivery']},'outside_masks_exact':True})
 for f in p['fonts']:assert sha(R/f['path'])==f['sha256']
 proof=R/f'internal/legal/catalogue_clearance_20261002/bengali/{s}-multichapter-source-comparison.json';j=load(proof);assert j['canonical_chapter_count']==j['source_leaf_count']==len(j['comparisons'])
 for x in j['comparisons']:
  ch=load(c/'chapters'/(x['id']+'.json'));assert ch['content_hash']==x['canonical_content_sha256'];assert norm(ch['content'])==norm('\n\n'.join(x['source_paragraphs_for_reader']))
 a.update({'reviewer':'Independent Codex reviewer B','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'slug':s,'disposition':'TERMINAL_HOLD_DROP_ACTIVE_SPRINT','source_full_complete_body':'PASS','source_boundary_proof_sha256':sha(proof),'visual_source_ownership_front_overlay_delivery':'PASS','assets':art,'package_integrity':'PASS','substantive_blocker':'Retained original back author-name line lies outside the deterministic repair zone; exact creation-method/font/renderer lineage absent. Owner design declaration proves design ownership only. Mandatory title_author_text_must_be_deterministic_overlay is not proven for this line. First bounded repair exhausted; no further art remediation. Preserve source/art/proposals/preimages, no acceptance or release.','canonical_mutations':False,'production_observed':False})
 out=O/(s+'-terminal-review-b.json');out.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');print(s,sha(out),a['checksum_count'])
