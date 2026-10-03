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
for s in ['bharat-at-the-crossroads','the-principles-of-scientific-management','acres-of-diamonds','my-life-and-work']:
 t=B/'practical-batch-prep-20261003'/s;c=t/'inactive-candidate';v=load(t/'preparation-validation.json');d=load(c/'rights_decision.json');delivery=load(c/'cover_delivery_derivation.json');a={'slug':s,'reviewer':'Independent Codex reviewer B','inventory':{},'checksums':0,'components':0,'source_unchanged':[],'audio_claims':[]}
 for x in v['candidate_inventory']:assert sha(c/x['file'])==x['sha256'];a['inventory'][x['file']]=x['sha256']
 for x in load(c/'checksum_manifest.json')['files']:assert sha(c/x['file'])==x['sha256'];a['checksums']+=1
 for k,h in d['components'].items():
  if k in ['cover_front_asset','cover_back_asset']:p=c/'covers'/('front.png'if 'front'in k else'back.png')
  elif k in ['cover_front_delivery','cover_back_delivery']:p=t/next(x['delivery_file']for x in delivery['assets']if x['kind']==('front'if'front'in k else'back'))
  else:p=c/(k+'.json')
  assert sha(p)==h;a['components']+=1
 assert d['status']=='PROPOSED'and d['territories']==['IN']and d['conditions_satisfied']==False
 for n in ['source_evidence.json','highlight_sync.json']+[str(p.relative_to(c))for p in(c/'chapters').glob('*.json')]:assert(c/n).read_bytes()==(t/'preimages/root'/n).read_bytes();a['source_unchanged'].append(n)
 proof=load(t/'source-proof.json');raw=t/'recovered/source.txt';assert sha(raw)==proof['source_sha256'];src=norm(raw.read_text());last=0;gaps=[];chapters=[]
 for m in proof['matched_chapters']:
  ch=load(c/'chapters'/(m['id']+'.json'));assert hashlib.sha256(ch['content'].encode()).hexdigest()==ch['content_hash']==m['content_sha256'];body=norm(ch['content']);start=src.index(body,last);assert start==m['start']and len(body)==m['length'];gap=src[last:start];assert gap==m['source_gap_before'];gaps.append(gap);last=start+len(body);chapters.append(ch)
 tail=src[last:];assert hashlib.sha256(tail.encode()).hexdigest()==proof['tail_sha256'];assert not tail.strip()if s=='bharat-at-the-crossroads'else tail.lstrip().startswith('*** END OF THE PROJECT GUTENBERG')
 if s=='bharat-at-the-crossroads':assert raw.read_bytes()==chapters[0]['content'].encode();assert gaps==['']
 a['source_whole_work_complete']='PASS_ENTIRE_PROVIDED_MANUSCRIPT'if s=='bharat-at-the-crossroads'else'PASS_ORDERED_COMPLETE_PREFACE_INTRODUCTION_NARRATIVE_APPRECIATION_BODY_AND_ALL_GAPS';a['source_sha256']=sha(raw);a['source_proof_sha256']=sha(t/'source-proof.json');a['chapter_count']=len(chapters);a['source_gaps_after_first']=gaps[1:];a['source_prefix_excerpt']=gaps[0][-450:];a['source_tail_excerpt']=tail[:100];a['rights_basis_exact_prior']=load(t/'preimages/root/rights_decision.json')['basis']
 cover=load(c/'cover_provenance.json');decl=cover['owner_declaration'];assert sha(R/decl['path'])==decl['sha256'];a['art_hashes']=[]
 for x in delivery['assets']:
  side=x['kind'];orig=cover['original_assets_preserved'][side];assert sha(t/orig['file'])==orig['sha256'];assert sha(c/x['source_file'])==x['source_sha256'];assert sha(t/x['delivery_file'])==x['delivery_sha256'];im=Image.open(t/x['delivery_file']);im.load();assert list(im.size)==x['delivery_dimensions'];assert(t/x['delivery_file']).stat().st_size==x['delivery_bytes']<= (80000 if side=='front' else 180000)
  p=next(z for z in cover['derivative_lineage']['typography_overlay_proof']if z['side']==side);assert sha(B/cover['derivative_lineage']['font_license_path'])==p['font_license_sha256'];assert p['font_file_sha256']=='8f2c103bfa3fd5de71f1b92b18f21906b5a26871fb7e19a9a4c9af539c3cc7ab';old=np.array(Image.open(t/orig['file']).convert('RGB'));new=np.array(Image.open(c/x['source_file']).convert('RGB'));mask=np.ones(old.shape[:2],bool)
  for x1,y1,x2,y2 in p['precise_masks']:mask[y1:y2+1,x1:x2+1]=False
  assert np.array_equal(old[mask],new[mask]);a['art_hashes'].append({'side':side,'original':orig['sha256'],'overlay':x['source_sha256'],'delivery':x['delivery_sha256'],'delivery_bytes':x['delivery_bytes'],'outside_precise_masks_exact':True})
 def scan(j,k=''):
  if isinstance(j,dict):
   for name,val in j.items():scan(val,k+'.'+name)
  elif isinstance(j,list):
   for i,val in enumerate(j):scan(val,k+f'[{i}]')
  elif ('audio'in k.lower()or'listen'in k.lower())and(j is True or isinstance(j,str)and j.startswith('http')):a['audio_claims'].append([k,j])
 for n in ['public_book.json','reader_manifest.json','approval_evidence.json','publication_authorization.json','publication_manifest.json']:scan(load(c/n),n)
 a.update({'visual_delivery':'TERMINAL_HOLD_CLIPPED_SUBTITLE'if s=='bharat-at-the-crossroads'else'PASS','binding_disposition':'HOLD_EFFECTIVE_AUDIO_URL_AND_LISTENING_APPROVAL_REQUIRE_ARCHIVE_AND_NORMALIZATION'if a['audio_claims']else'PASS_UNACCEPTED_PROPOSAL','substantive_blocker':'Title overlay clips original subtitle in front PNG and delivered WebP; first bounded repair exhausted. Exclude active sprint, preserve all original and proposal/source/decision versions.'if s=='bharat-at-the-crossroads'else None,'prospective_acceptance_by_root_still_required':True,'canonical_mutations':False,'production_observed':False,'no_new_GET_or_asset_render':True,'reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 p=O/(s+'-practical-proposed-review-b.json');p.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');results.append({'slug':s,'path':str(p),'sha256':sha(p),'visual':a['visual_delivery'],'audio':a['audio_claims']})
print(json.dumps(results,indent=2))
