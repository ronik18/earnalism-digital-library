from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,sys,re
R=Path('/tmp/earnalism-main-approved-integration');S=Path('/workspace/scratch/181ef0a25f05');sys.path.insert(0,str(R))
from backend.rights_decision_gate import record_sha256
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
D=Path(sys.argv[1]); reviewfiles=list(map(Path,sys.argv[2:]));assert len(reviewfiles)==2
receipt=read(D/'acceptance-receipt.json');order=['dsires-baby','sredni-vashtar','the-cop-and-the-anthem','the-open-window','the-selfish-giant','the-science-of-getting-rich','bn-066','lokrahasya','mrinalini','frankenstein','pride-and-prejudice','the-great-gatsby','the-secret-garden','the-time-machine','acres-of-diamonds','my-life-and-work','the-principles-of-scientific-management','the-wonderful-wizard-of-oz','book-5704b31005']; assert set(order)=={r['slug']for r in receipt['cohort']};receipt['cohort'].sort(key=lambda r:order.index(r['slug']));slugs=[r['slug']for r in receipt['cohort']];assert len(slugs)==len(set(slugs));assert not set(slugs)&{'bn-060','the-most-dangerous-game','great-expectations','bharat-at-the-crossroads'}
# Final binding reviews are independent immutable receipts. Root verifies their actual result/scope before invocation.
for f in reviewfiles:assert f.is_file()
launch=read(R/'data/controlled_launch.json');prior=list(launch['live_approved_slugs']);assert len(prior)==33;assert not(set(prior)&set(slugs))
L=R/'internal/earnalism_intelligence/book_go_live_477_continuation_20261002/owner-delegated-completion-20261003/next-cohort'
assert not(L/'accepted-binding-receipt.json').exists()
for name in ['data/controlled_launch.json','backend/data/controlled_launch.json','backend/data/rights_decision_registry.json','backend/data/approved_reader_bootstrap.json','frontend/src/lib/controlledLaunch.js']:
 t=L/'runtime-preimages'/name;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/name,t)
for prefix in ['preserved-proposals','canonical-preimages','predecessor-accepted-bindings','predecessor-receipts','prior-ready-publication-declarations']:
 if(D/prefix).exists():shutil.copytree(D/prefix,L/prefix)
for i,f in enumerate(reviewfiles):shutil.copyfile(f,L/f'accepted-binding-review-{"ab"[i]}.json')
shutil.copyfile(D/'acceptance-receipt.json',L/'accepted-binding-receipt.json')
registry=read(R/'backend/data/rights_decision_registry.json');bootstrap=read(R/'backend/data/approved_reader_bootstrap.json')
for row in receipt['cohort']:
 slug=row['slug'];p=D/'data/controlled_publications'/slug;dec=read(p/'rights_decision.json');assert record_sha256(dec)==row['canonical_record_sha256'];assert dec['status']=='ACCEPTED'
 assert dec['decision_id'] not in registry['accepted_records'];assert slug not in {r['slug']for r in bootstrap['titles']}
 for prefix in ['data/controlled_publications','backend/data/controlled_publications']:
  target=R/prefix/slug
  if target.exists():
   archived=L/'canonical-preimages'/slug/('root'if prefix=='data/controlled_publications'else'backend')
   assert archived.exists(),(slug,prefix)
   # Preimages are durably preserved before removing superseded effective files.
   for f in target.rglob('*'):
    if f.is_file():assert f.read_bytes()==(archived/f.relative_to(target)).read_bytes()
   shutil.rmtree(target)
  shutil.copytree(p,target)
 for asset in row['assets'].values():
  target=R/asset['path'];target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()or sha(target)==asset['sha256'];shutil.copyfile(D/asset['path'],target);assert sha(target)==asset['sha256']
 registry['accepted_records'][dec['decision_id']]=row['canonical_record_sha256']
 registry['commercial_batch_dispositions']['controlled-'+slug]={'status':'PREVIEW_RELEASED_ENTITLEMENT_REQUIRED_FROM_PAGE_4','countries':['IN'],'access_mode':'COMMERCIAL_ENTITLEMENT','decision_id':dec['decision_id'],'production_readback':'NOT_RUN_FOR_NEW_COHORT','authority':'Actual prospective automated owner-delegated acceptance; two independent exact accepted-package reviews; normal protected release gates remain required. No production observation inferred.'}
 bootstrap['titles'].append({'slug':slug,'decision_id':dec['decision_id'],'record_sha256':row['canonical_record_sha256']})
 launch['live_approved_slugs'].append(slug);launch['title_access_modes'][slug]='COMMERCIAL_ENTITLEMENT'
assert len(launch['live_approved_slugs'])==33+len(slugs);assert launch['audio_enabled_slugs']==[]and launch['public_audio_exposure_enabled']is False
registry['registry_id']=f'india-{33+len(slugs)}-title-commercial-entitlement-reader-20261003'
registry['non_activation_note']=f'{33+len(slugs)} exact India text editions configured; {len(slugs)} prospective additions remain behind protected exact-head normal CI/merge/deploy/canary/readback. Prior 33 deployed under documented narrow observation waiver. No production canonical versions inferred; audio disabled and existing versions preserved.'
for name in ['data/controlled_launch.json','backend/data/controlled_launch.json']:write(R/name,launch)
write(R/'backend/data/rights_decision_registry.json',registry);write(R/'backend/data/approved_reader_bootstrap.json',bootstrap)
p=R/'frontend/src/lib/controlledLaunch.js';v=p.read_text();anchor='  "alices-adventures-in-wonderland",\n]);';assert v.count(anchor)==1;v=v.replace(anchor,'  "alices-adventures-in-wonderland",\n'+''.join(f'  "{s}",\n'for s in slugs)+']);');p.write_text(v)
write(L/'serialized-integration-receipt.json',{'schema':'earnalism.oct3-owner-art-serialized-integration.v1','integrated_at':datetime.now(timezone.utc).isoformat(),'base_main':receipt['base_main'],'accepted_stage_receipt_sha256':sha(D/'acceptance-receipt.json'),'accepted_binding_reviews':[{'file':f'accepted-binding-review-{c}.json','sha256':sha(f)}for c,f in zip('ab',reviewfiles)],'preserved_prior_released':prior,'new_exact_slugs':slugs,'configured_count':len(launch['live_approved_slugs']),'audio_exposed':False,'production_observed_for_new_cohort':False,'canonical_versions':None,'next_action':'Run exact current runtime/fixture/SEO checks and two independent integrated tree reviews; release through existing protected normal checks only.'})
print(json.dumps({'count':len(launch['live_approved_slugs']),'new':slugs,'registry':len(registry['accepted_records']),'bootstrap':len(bootstrap['titles'])}))
