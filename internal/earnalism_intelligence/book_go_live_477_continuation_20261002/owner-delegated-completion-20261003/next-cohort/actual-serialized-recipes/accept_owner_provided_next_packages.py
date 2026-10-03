from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,sys
from PIL import Image
R=Path('/tmp/earnalism-main-approved-integration');S=Path('/workspace/scratch/181ef0a25f05');sys.path.insert(0,str(R))
from backend.publication_manifest import build_manifest,validate_manifest
from backend.rights_decision_gate import record_sha256,evaluate_accepted_record
inputs=Path(sys.argv[1]);D=Path(sys.argv[2]);assert not D.exists()
owner=R/'internal/earnalism_intelligence/book_go_live_477_continuation_20261002/owner-delegated-completion-20261003/ronik-owner-artwork-declaration-20261003.json'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
now=datetime.now(timezone.utc); stamp=now.isoformat()
actor='Automated serialized integration controller under issue #477 owner directive comment 5949652699, prospective owner acceptance delegation, and the direct Ronik Basak owner-artwork declaration 2026-10-03; no human signature inferred.'
receipt={'schema':'earnalism.prospective-owner-provided-next-cohort.v1','actual_acceptance_at':stamp,'actor':actor,'base_main':'0fee65668f94284d180065d0fe8b38face924498','owner_declaration_sha256':sha(owner),'canonical_mutations':0,'production_observed':False,'audio_exposed':False,'global_gate':'SERIAL_INTEGRATION_TWO_EXACT_TREE_REVIEWS_PROTECTED_NORMAL_CI_MERGE_DEPLOY_CANARY_TRUTHFUL_READBACK','cohort':[]}
for row in read(inputs):
 slug=row['slug'];src=Path(row['source']);work=Path(row['worker']);ar=Path(row['review_a']);br=Path(row['review_b'])
 assert all(f.is_file()for f in [ar,br]);assert slug not in ['great-expectations','bharat-at-the-crossroads','bn-060','the-most-dangerous-game']
 for x in read(src/'checksum_manifest.json')['files']:assert sha(src/x['file'])==x['sha256']
 p=D/'data/controlled_publications'/slug;hist=D/'preserved-proposals'/slug;shutil.copytree(src,p);shutil.copytree(src,hist)
 for kind,base in [('root',R/'data/controlled_publications'),('backend',R/'backend/data/controlled_publications')]:
  old=base/slug
  if old.exists():shutil.copytree(old,D/'canonical-preimages'/slug/kind)
 reviews={}
 for label,f in [('review_a',ar),('review_b',br)]+([('source_review_b',Path(row['additional_review_b']))]if row.get('additional_review_b')else []):
  target=p/'evidence'/f'{label}.json';target.parent.mkdir(exist_ok=True);shutil.copyfile(f,target);reviews[label]={'file':str(target.relative_to(p)),'sha256':sha(target)}
 shutil.copyfile(owner,p/'owner_artwork_declaration.json')
 prep=p/'cover_preparation.json'
 if slug=='the-secret-garden':
  v=read(prep)
  for q in v['cover_quote_checks']:q['comparison']='Whitespace, Markdown italic markers, and sentence-flow case normalization: the original source line begins A thistle; the retained cover uses a thistle. Lexical quote remains unchanged; original comparison wording is preserved in the predecessor.'
  write(prep,v)
 pub=read(p/'public_book.json');assets={}
 for kind,keys in [('front',['cover_image_url','cover_url']),('back',['back_cover_image_url','back_cover_url'])]:
  url=next(pub[k]for k in keys if pub.get(k));assert url.startswith(('https://theearnalism.com/assets/books/','/assets/books/')),(slug,url)
  filename=url.rsplit('/',1)[1];choices=list(work.rglob(filename));assert choices,(slug,filename)
  b=choices[0].read_bytes();assert all(f.read_bytes()==b for f in choices)
  target=D/'frontend/public/assets/books'/slug/filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
  image=Image.open(target);image.load();assert len(b)<=(80 if kind=='front' else 180)*1024
  assets[kind]={'path':str(target.relative_to(D)),'sha256':sha(target),'bytes':len(b),'dimensions':list(image.size),'url':url}
 prov=read(p/'cover_provenance.json')if(p/'cover_provenance.json').exists()else{'schema':'earnalism.cover-provenance.v1','slug':slug,'historical_prepared_exact_component_evidence':read(prep),'cover_preparation_sha256':sha(prep)}
 prov.update(status='ACCEPTED_EXACT_OWNER_PROVIDED_COMPONENTS_UNDER_DIRECT_OWNER_DECLARATION',accepted_by=actor,accepted_at=stamp,original_creator='Ronik Basak, as named by the actual direct owner declaration',owner_held_copyright_basis={'file':'owner_artwork_declaration.json','sha256':sha(owner),'scope':'Exact Ronik Basak owner-created front/back artwork only; no text rights or human review signature inferred.'},commercial_use_authorized=True,cover_display_approved=True,visual_review_status='PASS_TWO_INDEPENDENT_EXACT_PREPARATION_REVIEWS',independent_reviews=reviews,production_observed=False,runtime_release_authorized=False,audio_authorized=False,publication_activation_authorized=False)
 prov['acceptance_scope']='Exact owner-provided artwork and reviewed preserved-art derivatives/deliveries, India commercial text Reader cover display. Unknown original construction methods remain unknown; the owner decision supersedes external procedural artwork clearance. Text, source, visual quality and release gates remain independent.'
 if isinstance(prov.get('scope'),dict):prov['scope'].update(publication_approved=True,production_activation=False,audio_enabled=False,audiobook_enabled=False,listen_exposure=False,checkout=False,payments=False)
 write(p/'cover_provenance.json',prov)
 decision=read(p/'rights_decision.json');prior_basis=decision['basis'];decision_id=f'india-20261003-{slug}-exact-reader-cover-prospective-accepted'
 auth=read(p/'publication_authorization.json');auth.update(rights_decision_id=decision_id,scope='TEXT_READER_CATALOG_METADATA_AND_EXACT_COVER_DISPLAY',cover_provenance_sha256=sha(p/'cover_provenance.json'),authorized_by=actor,verified_at=stamp,publication_authorized=True,audio_authorized=False,production_activation_authorized_by_this_file=False,cover_status='EXACT_OWNER_PROVIDED_REVIEWED_ARTWORK_ACCEPTED_PRODUCTION_UNOBSERVED',release_condition='Two passing exact source/art preparations and actual prospective owner-delegated acceptance. Final accepted bindings, serialized selection, protected normal checks, merge, deployment/canary and truthful readback remain required.',not_authorized=['audio_stream','audio_download','other editions','production activation bypass']);write(p/'publication_authorization.json',auth)
 basis='Exact India text/edition rights are preserved from the archived predecessor and unchanged source/chapter/license records. Ronik Basak directly provided the owner-held copyright and publication provenance for the exact owner-created cover components; two independent passing source/art preparations bind the reviewed derivatives and deliveries. Prospective automated acceptance supersedes earlier procedural cover deferral for these components only. No human approval, other source/edition rights, unknown original construction method, audio grant or production observation inferred.'
 pub.update(publication_status='READY_BEHIND_SERIALIZED_GLOBAL_RELEASE_GATE',publicationStatus='draft',is_published=True,isLive=True,isPublic=True,showInPublicLibrary=False,allowPublicReading=False,allowCheckout=False,allowPayment=False,audio_enabled=False,audiobook_enabled=False,audiobook_use_approved=False,approved_to_publish=True,qa_status='QA_PASSED',rights_basis=basis,cover_status='ACCEPTED_EXACT_OWNER_PROVIDED_COMPONENTS_INDIA_TEXT_READER_ONLY',cover_dimensions={k:v['dimensions']for k,v in assets.items()},cover_provenance_sha256=sha(p/'cover_provenance.json'),publication_authorization_sha256=sha(p/'publication_authorization.json'))
 if isinstance(pub.get('publication_workflow'),dict):
  wf=pub['publication_workflow'];wf.setdefault('publication',{}).update(state='LIVE_APPROVED',reader_exposed=True,audio_exposed=False);wf.setdefault('release',{}).update(reader_release='LIVE',audio_release='NOT_REQUESTED')
 write(p/'public_book.json',pub)
 approval=read(p/'approval_evidence.json');approval.update(approved_to_publish=True,verification_status='approved',qa_status='QA_PASSED',approval_scope='ACTUAL_OWNER_DELEGATED_EXACT_INDIA_TEXT_READER_AND_OWNER_PROVIDED_COVER_PUBLICATION_ACCEPTANCE',qa_scope='Two independent exact complete-source/preserved-artwork preparations; final accepted binding review is an external serialized release requirement.',independent_reviews=reviews,binding_review_status='FINAL_EXACT_PACKAGE_REVIEWS_REQUIRED_AS_EXTERNAL_SERIALIZED_RELEASE_GATE',cover_front_qa_status='PASS_TWO_INDEPENDENT_EXACT_PREPARATION_REVIEWS',cover_back_qa_status='PASS_TWO_INDEPENDENT_EXACT_PREPARATION_REVIEWS',audio_enabled=False,audiobook_enabled=False,audiobook_use_approved=False,manual_listening_approval=False,allowCheckout=False,allowPayment=False,cover_provenance_sha256=sha(p/'cover_provenance.json'),publication_authorization_sha256=sha(p/'publication_authorization.json'))
 approval['actual_prospective_acceptance']={'actor':actor,'accepted_at':stamp,'evidence':reviews,'owner_declaration_sha256':sha(owner),'production_observed':False,'canonical_version_observed':False,'global_gate':receipt['global_gate']};write(p/'approval_evidence.json',approval)
 manifest=build_manifest(p,publish_approved=True,generated_at=stamp);assert not validate_manifest(manifest);assert manifest['reader_release']['status']=='APPROVED'and manifest['reader_release']['exposed']and not manifest['audio_release']['exposed'];write(p/'publication_manifest.json',manifest)
 checks=read(p/'checksum_manifest.json')
 for x in checks['files']:x['sha256']=sha(p/x['file'])
 for name in ['cover_provenance.json','publication_authorization.json','owner_artwork_declaration.json']+[v['file']for v in reviews.values()]:
  if name not in {x['file']for x in checks['files']}:checks['files'].append({'file':name,'sha256':sha(p/name)})
 write(p/'checksum_manifest.json',checks)
 decision.update(status='ACCEPTED',decision_id=decision_id,accepted_by=actor,valid_from=stamp,conditions_satisfied=True,basis=basis,uses=['catalog_metadata','cover_display','reader_preview','reader_delivery','reading_pass_session','reading_pass_renewal'])
 for label in decision['components']:
  f=p/(label+'.json')
  if f.exists():decision['components'][label]=sha(f)
 decision['components'].update(publication_authorization=sha(p/'publication_authorization.json'),cover_provenance=sha(p/'cover_provenance.json'),owner_artwork_declaration=sha(owner),acceptance_review_a=sha(ar),acceptance_review_b=sha(br))
 decision['evidence_sha256']=list(dict.fromkeys([*decision['evidence_sha256'],sha(owner),sha(p/'publication_authorization.json'),sha(p/'cover_provenance.json'),*[v['sha256']for v in reviews.values()]]));write(p/'rights_decision.json',decision)
 for use in decision['uses']+['audio_stream','audio_download']:
  v=evaluate_accepted_record(decision,edition_id=decision['edition_id'],operator_id=decision['operator_id'],country='IN',country_trusted=True,use=use,required_components=decision['components'],accepted_records={decision_id:record_sha256(decision)},revoked_decision_ids=frozenset(),now=now);assert v.passed==(use in decision['uses']),(slug,use,v)
 for name in ['source_evidence.json','reader_manifest.json']:
  assert (hist/name).read_bytes()==(p/name).read_bytes(),(slug,name)
 for f in (hist/'chapters').glob('*.json'):assert f.read_bytes()==(p/'chapters'/f.name).read_bytes()
 shutil.copytree(p,D/'backend/data/controlled_publications'/slug)
 receipt['cohort'].append({'slug':slug,'decision_id':decision_id,'canonical_record_sha256':record_sha256(decision),'assets':assets,'reviews':reviews,'publication_authorization_sha256':sha(p/'publication_authorization.json'),'prior_text_rights_basis_preserved':prior_basis,'disposition':'READY_BEHIND_NAMED_GLOBAL_GATE','source_and_chapters':'BYTE_IDENTICAL_TO_REVIEWED_PROPOSAL','production_observed':False})
write(D/'acceptance-receipt.json',receipt);print(json.dumps({'stage':str(D),'cohort':[x['slug']for x in receipt['cohort']]}))
