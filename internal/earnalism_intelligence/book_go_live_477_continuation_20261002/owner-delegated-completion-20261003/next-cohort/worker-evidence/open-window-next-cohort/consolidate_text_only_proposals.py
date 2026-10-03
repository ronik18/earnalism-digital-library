from pathlib import Path
import json,hashlib,shutil
from PIL import Image
BASE=Path('/workspace/scratch/181ef0a25f05')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canon=lambda d:hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
read=lambda p:json.loads(p.read_text())
def put(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
for slug,name in [('the-open-window','open-window-next-cohort'),('the-selfish-giant','selfish-giant-next-cohort')]:
 o=BASE/name;p=o/'proposal/data/controlled_publications'/slug;a=o/'archive-before-consolidated-text-only-paperwork';a.mkdir(exist_ok=True)
 before={str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file()};fields={}
 for f in p.glob('*.json'):
  if not (a/f.name).exists():shutil.copy2(f,a/f.name)
 book=read(p/'public_book.json');dims={k:list(Image.open(o/(k+'-delivery.webp')).size) for k in ['front','back']};fields['public_book']={'cover_dimensions':{'before':book['cover_dimensions'],'after':dims}};book['cover_dimensions']=dims
 original_text_basis=read(o/'preimages/root/rights_decision.json')['basis']
 fields['public_book']['rights_basis']={'before':book.get('rights_basis'),'after':original_text_basis};book['rights_basis']=original_text_basis
 if isinstance(book.get('rights_metadata'),dict):
  fields['public_book']['rights_metadata.rights_basis']={'before':book['rights_metadata'].get('rights_basis'),'after':original_text_basis};book['rights_metadata']['rights_basis']=original_text_basis;book['rights_metadata']['publication_region']='IN'
 put(p/'public_book.json',book)
 old=read(p/'approval_evidence.json')
 # Reconstruct the effective text-only proposed approval from an allowlist.
 # Every historical metric, audio observation and legacy approval remains in
 # the byte-exact source/backend preimages and this dated proposal archive.
 keep=['slug','approved_to_publish','rights_tier','verification_status','qa_status','approval_scope','allowCheckout','allowPayment','audiobook_enabled','audiobook_use_approved','audiobook_use_approval_source','audiobook_use_approved_at','audio_public_release','verified_at','publication_authorization_sha256','cover_provenance_sha256','independent_reviews']
 app={k:old[k] for k in keep if k in old};source=read(p/'source_evidence.json');app.update(source_hash=source['source_hash'],content_hash=source['content_hash'],approval_scope='PROPOSED_OWNER_DELEGATED_EXACT_IN_TEXT_AND_COVER_BINDING_PENDING_TWO_REVIEWS',approved_to_publish=False,audiobook_enabled=False,audiobook_use_approved=False,audiobook_use_approval_source='',audiobook_use_approved_at='',audio_public_release='PUBLIC_AUDIO_RELEASE_NOT_APPROVED',independent_reviews=[],binding_review_status='PENDING_TWO_FRESH_EXACT_PACKAGE_REVIEWS',qa_scope='Existing independently evidenced noncover text identity/complete work only; no audio or production observation.')
 fields['approval_evidence']={'removed_fields':sorted(set(old)-set(app)),'changed_fields':{k:{'before':old.get(k),'after':v} for k,v in app.items() if old.get(k)!=v}}
 put(p/'approval_evidence.json',app)
 removed=[]
 for f in p.glob('*audio*evidence*.json'):
  assert (a/f.name).read_bytes()==f.read_bytes();removed.append({'file':f.name,'sha256':sha(f),'archive_path':str(a/f.name)});f.unlink()
 # Reader effective fields already scrubbed in the previous correction.
 reader=read(p/'reader_manifest.json')
 assert set(k for k in reader if k.startswith(('audio','audiobook'))) <= {'audio_enabled','audiobook_enabled'}
 assert reader.get('audio_enabled') is False and reader.get('audiobook_enabled') is False
 checksum=read(p/'checksum_manifest.json');checksum['files']=[{'file':str(f.relative_to(p)),'sha256':sha(f)} for f in sorted(p.rglob('*')) if f.is_file() and f.name not in ('checksum_manifest.json','publication_manifest.json','rights_decision.json')];put(p/'checksum_manifest.json',checksum)
 man=read(p/'publication_manifest.json');man['artifacts']={f.stem:sha(f) for f in p.glob('*.json') if f.name not in ('rights_decision.json','publication_manifest.json','checksum_manifest.json','highlight_sync.json')};man['audio_release']={'status':'NOT_REQUESTED','exposed':False,'required_for_reader_release':False};man.pop('manifest_sha256',None);man['manifest_sha256']=canon(man);put(p/'publication_manifest.json',man)
 dec=read(p/'rights_decision.json')
 for k in list(dec['components']):
  if not (p/(k+'.json')).exists():del dec['components'][k]
  else:dec['components'][k]=sha(p/(k+'.json'))
 assert dec['status']=='PROPOSED' and dec['conditions_satisfied'] is False;put(p/'rights_decision.json',dec)
 # Disallow all positive audio observations/status/URLs from effective records.
 for n in ['public_book','reader_manifest','approval_evidence','publication_manifest']:
  d=read(p/(n+'.json'));text=json.dumps(d).lower()
  assert all(s not in text for s in ['backblazeb2','.mp3','audiobook_active_release','production_audio_evidence','release_descriptor','technical_audio_qa','uploaded_artifact_sha256','listening_qa','asr_manuscript_score','duration_seconds','audio_sha256'])
 assert book['formats']==['Ebook']
 after={str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file()}
 assert all(before[f]==after[f] for f in before if f.startswith(('covers/','chapters/')) or f in ('source_evidence.json','license_notice.json','highlight_sync.json'))
 receipt={'slug':slug,'scope':'FINAL_CONSOLIDATED_UNACCEPTED_TEXT_ONLY_PAPERWORK_CORRECTION','changed_fields':fields,'removed_current_components_archived':removed,'changed_files':{f:{'before':before.get(f),'after':after.get(f)} for f in sorted(set(before)|set(after)) if before.get(f)!=after.get(f)},'no_active_audio_positive_observations_or_urls_in_effective_public_reader_approval_manifest':True,'source_chapter_license_sync_original_repair_delivery_bytes_unchanged':True,'cover_delivery_dimensions_derived_from_actual_bytes':dims,'actual_acceptance_created':False,'new_package_files_sha256':after,'package_inventory_canonical_sha256':canon(after),'decision_raw_sha256':sha(p/'rights_decision.json'),'decision_canonical_sha256':canon(dec)}
 put(o/'consolidated-final-paperwork.json',receipt)
 val=read(o/'validation.json');val.update(proposed_components=dec['components'],rights_decision_raw_sha256=sha(p/'rights_decision.json'),rights_decision_canonical_sha256=canon(dec),proposed_package_inventory_canonical_sha256=canon(after),consolidated_final_paperwork_sha256=sha(o/'consolidated-final-paperwork.json'),active_approval_audio_observations='NONE_ARCHIVE_ONLY',cover_delivery_dimensions=dims);put(o/'validation.json',val)
 print(json.dumps({'slug':slug,'package_inventory_sha256':canon(after),'decision_raw_sha256':sha(p/'rights_decision.json'),'decision_canonical_sha256':canon(dec),'validation_sha256':sha(o/'validation.json'),'removed_files':[x['file'] for x in removed],'final_receipt':str(o/'consolidated-final-paperwork.json')},indent=2))
