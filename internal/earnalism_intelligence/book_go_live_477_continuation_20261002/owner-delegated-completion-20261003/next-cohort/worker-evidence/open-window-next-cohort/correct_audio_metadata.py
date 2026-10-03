from pathlib import Path
import json,hashlib,shutil
BASE=Path('/workspace/scratch/181ef0a25f05')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canon=lambda d:hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
read=lambda p:json.loads(p.read_text())
def put(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
for slug,name in [('the-open-window','open-window-next-cohort'),('the-selfish-giant','selfish-giant-next-cohort')]:
 o=BASE/name;p=o/'proposal/data/controlled_publications'/slug
 before={str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file()}
 fields={}
 for n in ['public_book','reader_manifest']:
  f=p/(n+'.json');shutil.copy2(f,o/('prior-proposal-'+n+'-before-audio-correction.json'));d=read(f);fields[n]={}
  for k in list(d):
   if k.startswith(('audio','audiobook','generate_audiobook')) and k not in ('audio_enabled','audiobook_enabled','generate_audiobook','audiobook_assets','audiobook'):
    fields[n][k]='REMOVED_ACTIVE_DESCRIPTOR_PACKAGE_OR_MEDIA_METADATA';del d[k]
  for k in ('audio_enabled','audiobook_enabled'):
   assert d.get(k) is False
  if n=='public_book':
   assert d.get('generate_audiobook') is False
   assert d.get('audiobook_assets')=={} and d.get('audiobook')=={}
   if 'Audiobook' in d.get('formats',[]):fields[n]['formats']={'from':d['formats'],'to':['Ebook']};d['formats']=['Ebook']
   if 'candidate_fingerprint' in d:fields[n]['candidate_fingerprint']='REMOVED_HISTORICAL_AUDIO_CANDIDATE_POINTER';del d['candidate_fingerprint']
  put(f,d)
  # No public/Reader media, active release, or descriptor URLs may survive.
  encoded=json.dumps(d).lower()
  assert 'backblazeb2' not in encoded and '.mp3' not in encoded and 'audiobook_active_release' not in encoded and 'release_descriptor' not in encoded
 checksum=read(p/'checksum_manifest.json')
 for f in checksum['files']:f['sha256']=sha(p/f['file'])
 put(p/'checksum_manifest.json',checksum)
 man=read(p/'publication_manifest.json')
 for k in ('public_book','reader_manifest'):man['artifacts'][k]=sha(p/(k+'.json'))
 man.pop('manifest_sha256',None);man['manifest_sha256']=canon(man);put(p/'publication_manifest.json',man)
 dec=read(p/'rights_decision.json')
 for k in dec['components']:dec['components'][k]=sha(p/(k+'.json'))
 assert dec['status']=='PROPOSED' and dec['conditions_satisfied'] is False
 put(p/'rights_decision.json',dec)
 after={str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file()}
 changed=[f for f in sorted(before) if before[f]!=after[f]]
 assert set(changed)<={'public_book.json','reader_manifest.json','checksum_manifest.json','publication_manifest.json','rights_decision.json'}
 evidence={'slug':slug,'correction_scope':'ONE_PAPERWORK_CORRECTION_REMOVE_HISTORICAL_ACTIVE_AUDIO_METADATA_AND_POSITIVE_FORMAT_CLAIMS','changed_fields':fields,'changed_files':{f:{'before':before[f],'after':after[f]} for f in changed},'source_chapter_license_sync_cover_art_bytes_unchanged':True,'actual_acceptance_created':False,'prior_source_and_backend_preimages_preserved':True,'prior_proposal_public_reader_copies_preserved':True,'new_decision_raw_sha256':sha(p/'rights_decision.json'),'new_decision_canonical_sha256':canon(dec),'new_package_files_sha256':after,'new_package_inventory_canonical_sha256':canon(after)}
 put(o/'audio-metadata-correction.json',evidence)
 v=read(o/'validation.json');v.update(proposed_components=dec['components'],rights_decision_raw_sha256=sha(p/'rights_decision.json'),rights_decision_canonical_sha256=canon(dec),audio_metadata_correction_sha256=sha(o/'audio-metadata-correction.json'),proposed_public_reader_active_audio_claims='NONE_FALSE_FLAGS_EMPTY_MEDIA_ONLY',proposed_package_inventory_canonical_sha256=canon(after));put(o/'validation.json',v)
 prepare=o/'prepare.py';s=prepare.read_text();s=s.replace("reader=read(S/'reader_manifest.json');reader.update(audio_enabled=False,audiobook_enabled=False)","reader={k:v for k,v in read(S/'reader_manifest.json').items() if not k.startswith(('audio','audiobook','generate_audiobook'))};reader.update(audio_enabled=False,audiobook_enabled=False)");s=s.replace("put(P/'public_book.json',book);put(O/'historical-audio-preimage.json',historical)","book['formats']=['Ebook'];book.pop('candidate_fingerprint',None)\nput(P/'public_book.json',book);put(O/'historical-audio-preimage.json',historical)");prepare.write_text(s)
 print(json.dumps({'slug':slug,'changed_fields':fields,'changed_files':changed,'decision_raw_sha256':sha(p/'rights_decision.json'),'decision_canonical_sha256':canon(dec),'package_inventory_sha256':canon(after),'validation_sha256':sha(o/'validation.json')},indent=2))
