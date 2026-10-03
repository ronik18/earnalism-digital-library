from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,sys
R=Path('/tmp/earnalism-main-approved-integration');S=Path('/workspace/scratch/181ef0a25f05');sys.path.insert(0,str(R))
from backend.publication_manifest import build_manifest,validate_manifest
from backend.rights_decision_gate import record_sha256,evaluate_accepted_record
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
D=Path(sys.argv[1]);assert not D.exists();now=datetime.now(timezone.utc)
receipt={'schema':'earnalism.aggregate-exact-accepted-cohort.v1','binding_correction_at':now.isoformat(),'base_main':'0fee65668f94284d180065d0fe8b38face924498','production_observed':False,'canonical_mutations':0,'audio_exposed':False,'global_gate':'SERIAL_INTEGRATION_TWO_EXACT_TREE_REVIEWS_PROTECTED_NORMAL_CI_MERGE_DEPLOY_CANARY_TRUTHFUL_READBACK','correction_scope':'Current acceptance status and pointer closure only; unchanged artwork/source/chapter/license/sync evidence and all predecessor acceptance stages preserved. Historical nested preparation snapshots remain historical. No original construction method, human signature or production observation invented.','cohort':[],'predecessors':[]}
for stage in map(Path,sys.argv[2:]):
 sr=read(stage/'acceptance-receipt.json');receipt['predecessors'].append({'path':str(stage),'receipt_sha256':sha(stage/'acceptance-receipt.json')});shutil.copyfile(stage/'acceptance-receipt.json',D/'predecessor-receipts'/f'{stage.name}.json') if (D/'predecessor-receipts').exists() else (D/'predecessor-receipts').mkdir(parents=True)
 if not (D/'predecessor-receipts'/f'{stage.name}.json').exists():shutil.copyfile(stage/'acceptance-receipt.json',D/'predecessor-receipts'/f'{stage.name}.json')
 for row in sr['cohort']:
  slug=row['slug'];old=stage/'data/controlled_publications'/slug;p=D/'data/controlled_publications'/slug;assert not p.exists();shutil.copytree(old,p)
  for prefix in ['preserved-proposals','canonical-preimages']:
   q=stage/prefix/slug
   if q.exists():shutil.copytree(q,D/prefix/slug)
  archive=D/'predecessor-accepted-bindings'/slug;shutil.copytree(old,archive)
  for asset in row['assets'].values():
   q=stage/asset['path'];t=D/asset['path'];t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,t);assert sha(t)==asset['sha256']
  before={f.name:sha(f)for f in p.glob('*.json')};cp=read(p/'cover_provenance.json');actor=cp['accepted_by'];accepted_at=cp['accepted_at'];reviews=row['reviews']
  for name in ['cover_preparation.json','cover_delivery_derivation.json']:
   f=p/name
   if not f.exists():continue
   v=read(f)
   if name=='cover_preparation.json':v.update(status='ACCEPTED_EXACT_COMPONENT_PREPARATION_INDIA_TEXT_READER_ONLY',cover_display_accepted=True,publication_accepted=True)
   else:
    v['review_status']='PASS_TWO_INDEPENDENT_EXACT_PNG_WEBP_PREPARATION_REVIEWS'
    for key in ['state','status']:
     if key in v:v[key]='ACCEPTED_EXACT_DELIVERY_INDIA_TEXT_READER_ONLY'
   v['actual_acceptance']={'actor':actor,'accepted_at':accepted_at,'independent_reviews':reviews,'production_observed':False,'final_binding_review_gate':receipt['global_gate']}
   write(f,v)
  # Existing nested preparation snapshots represent historical methods/statuses and stay byte-equivalent.
  if (p/'cover_preparation.json').exists() and 'cover_preparation_sha256'in cp:cp['cover_preparation_sha256']=sha(p/'cover_preparation.json')
  if isinstance(cp.get('evidence_sha256'),dict):
   for key in list(cp['evidence_sha256']):
    if key in ['delivery_receipt','cover_delivery_derivation'] and (p/'cover_delivery_derivation.json').exists():cp['evidence_sha256'][key]=sha(p/'cover_delivery_derivation.json')
  if isinstance(cp.get('delivery_recipe'),dict) and 'current_delivery_receipt_sha256' in cp['delivery_recipe'] and (p/'cover_delivery_derivation.json').exists():cp['delivery_recipe']['current_delivery_receipt_sha256']=sha(p/'cover_delivery_derivation.json')
  write(p/'cover_provenance.json',cp)
  auth=read(p/'publication_authorization.json');auth['cover_provenance_sha256']=sha(p/'cover_provenance.json');write(p/'publication_authorization.json',auth)
  dec=read(p/'rights_decision.json')
  for name in ['public_book.json','approval_evidence.json']:
   v=read(p/name);v.update(cover_provenance_sha256=sha(p/'cover_provenance.json'),publication_authorization_sha256=sha(p/'publication_authorization.json'))
   if name=='public_book.json':v['cover_status']='ACCEPTED_EXACT_OWNER_COMPONENTS_INDIA_TEXT_READER_ONLY';v['rights_basis']=dec['basis']
   else:v['binding_review_status']='FINAL_EXACT_PACKAGE_REVIEWS_REQUIRED_AS_EXTERNAL_SERIALIZED_RELEASE_GATE'
   for key,file in [('cover_delivery_derivation_sha256','cover_delivery_derivation.json'),('cover_preparation_sha256','cover_preparation.json')]:
    if key in v and (p/file).exists():v[key]=sha(p/file)
   write(p/name,v)
  manifest=build_manifest(p,publish_approved=True,generated_at=accepted_at);assert not validate_manifest(manifest);assert not manifest['audio_release']['exposed'];write(p/'publication_manifest.json',manifest)
  checks=read(p/'checksum_manifest.json')
  for x in checks['files']:x['sha256']=sha(p/x['file'])
  write(p/'checksum_manifest.json',checks)
  for label in dec['components']:
   f=p/(label+'.json')
   if f.exists():dec['components'][label]=sha(f)
  # Keep unrelated historical evidence hashes; replace effective changed package evidence hashes.
  remap={h:sha(p/name)for name,h in before.items()if name!='rights_decision.json' and (p/name).exists()}
  dec['evidence_sha256']=list(dict.fromkeys(remap.get(h,h)for h in dec['evidence_sha256']))
  write(p/'rights_decision.json',dec)
  for x in checks['files']:assert sha(p/x['file'])==x['sha256']
  for f in (old/'chapters').glob('*.json'):assert f.read_bytes()==(p/'chapters'/f.name).read_bytes()
  for name in ['source_evidence.json','reader_manifest.json','license_provenance.json','sync_manifest.json']:
   if(old/name).exists():assert(old/name).read_bytes()==(p/name).read_bytes()
  for use in dec['uses']+['audio_stream','audio_download']:
   verdict=evaluate_accepted_record(dec,edition_id=dec['edition_id'],operator_id=dec['operator_id'],country='IN',country_trusted=True,use=use,required_components=dec['components'],accepted_records={dec['decision_id']:record_sha256(dec)},revoked_decision_ids=frozenset(),now=now);assert verdict.passed==(use in dec['uses']),(slug,use,verdict)
  shutil.copytree(p,D/'backend/data/controlled_publications'/slug)
  row.update(canonical_record_sha256=record_sha256(dec),publication_authorization_sha256=sha(p/'publication_authorization.json'),acceptance_stage_origin=str(stage),actual_acceptance_at=accepted_at);receipt['cohort'].append(row)
write(D/'acceptance-receipt.json',receipt)
print(json.dumps({'stage':str(D),'count':len(receipt['cohort']),'slugs':[r['slug']for r in receipt['cohort']],'receipt_sha256':sha(D/'acceptance-receipt.json')}))
