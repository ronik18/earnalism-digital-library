from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,sys
R=Path('/tmp/earnalism-main-approved-integration');S=Path('/workspace/scratch/181ef0a25f05');sys.path.insert(0,str(R))
from backend.publication_manifest import build_manifest,validate_manifest
from backend.rights_decision_gate import record_sha256
old=S/'next-owner-accepted-final-nineteen-20261003-v2';new=S/'next-owner-accepted-final-nineteen-20261003-v3';assert not new.exists();shutil.copytree(old,new)
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
r=read(new/'acceptance-receipt.json');r['serialized_selection_at']=datetime.now(timezone.utc).isoformat();r['selection_scope']='Current publication declarations selected for sole serialized release candidate. LIVE_APPROVED is manifest-backed authorization, not an observed production fact; protected release gate and production_observed:false remain explicit. All previous candidate declarations preserved.'
for row in r['cohort']:
 p=new/'data/controlled_publications'/row['slug'];prior=old/'data/controlled_publications'/row['slug'];pub=read(p/'public_book.json');before={f.name:sha(f)for f in p.glob('*.json')};pub.update(publication_status='LIVE_APPROVED',publicationStatus='published',showInPublicLibrary=True,allowPublicReading=True,reader_enabled=True,preview_enabled=True,release_gate_status='READY_BEHIND_SERIALIZED_GLOBAL_RELEASE_GATE',production_observed=False);write(p/'public_book.json',pub)
 manifest=build_manifest(p,publish_approved=True,generated_at=row['actual_acceptance_at']);assert not validate_manifest(manifest);write(p/'publication_manifest.json',manifest)
 checks=read(p/'checksum_manifest.json')
 for item in checks['files']:item['sha256']=sha(p/item['file'])
 write(p/'checksum_manifest.json',checks)
 dec=read(p/'rights_decision.json')
 for label in dec['components']:
  f=p/(label+'.json')
  if f.exists():dec['components'][label]=sha(f)
 remap={h:sha(p/name)for name,h in before.items()if name!='rights_decision.json'};dec['evidence_sha256']=list(dict.fromkeys(remap.get(h,h)for h in dec['evidence_sha256']));write(p/'rights_decision.json',dec);row['canonical_record_sha256']=record_sha256(dec)
 for name in ['source_evidence.json','reader_manifest.json','license_provenance.json','sync_manifest.json']:
  if(prior/name).exists():assert(prior/name).read_bytes()==(p/name).read_bytes()
 for f in (prior/'chapters').glob('*.json'):assert f.read_bytes()==(p/'chapters'/f.name).read_bytes()
 mirror=new/'backend/data/controlled_publications'/row['slug'];shutil.rmtree(mirror);shutil.copytree(p,mirror)
 # Preserve changed candidate declarations, rather than duplicating unchanged source/art bytes.
 hist=new/'prior-ready-publication-declarations'/row['slug'];hist.mkdir(parents=True)
 for name in ['public_book.json','publication_manifest.json','checksum_manifest.json','rights_decision.json']:shutil.copyfile(prior/name,hist/name)
write(new/'acceptance-receipt.json',r);print(json.dumps({'stage':str(new),'count':len(r['cohort']),'sha256':sha(new/'acceptance-receipt.json')}))
