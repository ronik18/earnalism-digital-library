from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,sys
R=Path('/tmp/earnalism-main-approved-integration');sys.path.insert(0,str(R));from backend.publication_manifest import build_manifest,validate_manifest
from backend.rights_decision_gate import record_sha256
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
slug='the-great-gatsby';p=R/'data/controlled_publications'/slug;L=R/'internal/earnalism_intelligence/book_go_live_477_continuation_20261002/owner-delegated-completion-20261003/next-cohort/gatsby-verification-remediation';assert not L.exists();L.mkdir(parents=True)
for n in ['public_book.json','publication_manifest.json','checksum_manifest.json','rights_decision.json']:shutil.copyfile(p/n,L/n)
pub=read(p/'public_book.json');assert pub['verification_status']=='reader_repair_verified';a=read(p/'approval_evidence.json');assert a['verification_status']=='approved' and a['actual_prospective_acceptance']['production_observed']is False;before={f.name:sha(f)for f in p.glob('*.json')};pub['verification_status']='approved';write(p/'public_book.json',pub)
manifest=build_manifest(p,publish_approved=True,generated_at=a['actual_prospective_acceptance']['accepted_at']);assert not validate_manifest(manifest);write(p/'publication_manifest.json',manifest)
checks=read(p/'checksum_manifest.json')
for x in checks['files']:x['sha256']=sha(p/x['file'])
write(p/'checksum_manifest.json',checks);dec=read(p/'rights_decision.json');old=record_sha256(dec)
for label in dec['components']:
 f=p/(label+'.json')
 if f.exists():dec['components'][label]=sha(f)
remap={h:sha(p/n)for n,h in before.items()if n!='rights_decision.json'};dec['evidence_sha256']=list(dict.fromkeys(remap.get(h,h)for h in dec['evidence_sha256']));write(p/'rights_decision.json',dec);new=record_sha256(dec)
mirror=R/'backend/data/controlled_publications'/slug
for n in ['public_book.json','publication_manifest.json','checksum_manifest.json','rights_decision.json']:shutil.copyfile(p/n,mirror/n)
rpath=R/'backend/data/rights_decision_registry.json';r=read(rpath);assert r['accepted_records'][dec['decision_id']]==old;r['accepted_records'][dec['decision_id']]=new;write(rpath,r)
bpath=R/'backend/data/approved_reader_bootstrap.json';b=read(bpath)
for row in b['titles']:
 if row['slug']==slug:assert row['record_sha256']==old;row['record_sha256']=new
write(bpath,b)
receipt={'schema':'earnalism.gatsby-existing-verification-paperwork-remediation.v1','actual_corrected_at':datetime.now(timezone.utc).isoformat(),'actor':'Sole automated integration controller under actual owner delegation; no human approval inferred.','trigger':'Actual controlled Reader validation rejected stale public verification_status reader_repair_verified; existing exact automated approval_evidence already approved.','actual_change':'public_book.verification_status normalized to approved, matching actual accepted evidence; only public/manifest/checksum/decision hash bindings and candidate registry/bootstrap pointers changed.','old_canonical_record_sha256':old,'new_canonical_record_sha256':new,'source_reader_chapters_artwork_authorization_approval_evidence':'BYTE_UNCHANGED','bounded_attempt':1,'production_observed':False,'next_gate':'Two independent exact integrated-tree reviewers inspect this metadata binding delta; protected normal checks unchanged.'};write(L/'remediation-receipt.json',receipt)
from backend import catalog_truth
issues={s:catalog_truth.controlled_reader_validation_issues(s)for s in read(R/'data/controlled_launch.json')['live_approved_slugs']};assert not any(issues.values()),issues;print(json.dumps({'slug':slug,'old_hash':old,'new_hash':new,'all52_active_reader_validation':'PASS'}))
