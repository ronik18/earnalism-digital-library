import json,pathlib,hashlib,shutil,datetime
B=pathlib.Path('/workspace/scratch/181ef0a25f05')
O=B/'bengali-order-only-20261003-v2'
MAP=B/'new-acceptance-review-a/bengali-source-order-review-a-v1.json'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def canon(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_text())
def put(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def inv(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
assert sha(MAP)=='8732ab1085ff2ccbcc12e570bb4dcd0b242b85a96290d7e15b83185acddbcf4f'
assert not O.exists(),'Version folder immutable; do not repeat attempt'
O.mkdir()
maps={x['slug']:x for x in read(MAP)}
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
results=[]
for slug in ['bn-066','lokrahasya']:
 S=B/f'bengali-next-cohort-20261003/{slug}/proposal/data/controlled_publications/{slug}'
 m=maps[slug];ids=m['source_page_order_ids'];r=read(S/'reader_manifest.json');p=read(S/'public_book.json');man=read(S/'publication_manifest.json');source=read(S/'source_evidence.json')
 chapters={x:read(S/'chapters'/f'{x}.json') for x in ids}
 assert set(ids)=={x['id'] for x in r['chapters']} and len(ids)==len(chapters)
 aggregate=hashlib.sha256('\n\n'.join(chapters[x]['content'] for x in ids).encode()).hexdigest()
 arraysmatch=all([x['id'] for x in rows]==ids and [x['order'] for x in rows]==list(range(1,len(ids)+1)) for rows in [r['chapters'],p['chapters'],man['content']['chapters']])
 filesmatch=all(chapters[x]['order']==i for i,x in enumerate(ids,1))
 checks=all(sha(S/z['file'])==z['sha256'] for z in read(S/'checksum_manifest.json')['files'])
 bindings=all(sha(S/f'{k}.json')==v for k,v in read(S/'rights_decision.json')['components'].items())
 if arraysmatch and filesmatch and source['content_hash']==aggregate and checks and bindings:
  results.append({'slug':slug,'disposition':'EXACT_EXISTING_PROPOSAL_SOURCE_ORDER_ALREADY_CORRECT_NO_DUPLICATE_REMEDY','proposal_path':str(S),'source_order_ids':ids,'source_page_order_review_sha256':sha(MAP),'content_hash':aggregate,'reader_order_file_order_arrays_all_pass':True,'checksum_and_component_bindings_pass':True,'existing_proposal_inventory_canonical_sha256':canon(inv(S)),'new_attempts':0,'actual_acceptance':False})
  continue
 assert slug=='lokrahasya'
 W=O/slug;P=W/f'proposal/data/controlled_publications/{slug}';A=W/'archive-prior-proposal';shutil.copytree(S,A);shutil.copytree(S,P)
 oldinventory=inv(S)
 titles={x['id']:x['title'].rsplit('/',1)[-1] for x in m['current_sequence']}
 order={x:i for i,x in enumerate(ids,1)}
 for x in ids:
  d=chapters[x];d['order']=order[x];d['title']=titles[x];d['updated_at']=stamp;put(P/'chapters'/f'{x}.json',d)
 for name in ['reader_manifest.json','public_book.json']:
  d=read(P/name);rows={x['id']:x for x in d['chapters']}
  d['chapters']=[dict(rows[x],order=order[x],title=titles[x],updated_at=stamp) for x in ids]
  if 'preview_chapter_ids' in d:d['preview_chapter_ids']=[x for x in ids if x in d['preview_chapter_ids']]
  if name=='reader_manifest.json':d['generated_at']=stamp
  else:d['content_hash']=aggregate;d['updated_at']=stamp
  put(P/name,d)
 receipt={'schema':'earnalism.reader-source-order-only-remedy.v1','slug':slug,'package_version':'20261003-source-page-order-v2','performed_at':stamp,'attempt':1,'status':'PROPOSED_PENDING_TWO_INDEPENDENT_EXACT_ORDER_BINDING_REVIEWS','prior_proposal_inventory_canonical_sha256':canon(oldinventory),'prior_content_hash':source['content_hash'],'new_content_hash':aggregate,'source_hash_unchanged':source['source_hash'],'owner_basis_receipt_sha256':'0881001b09b5b47649f14ff289aaa7f64e98004adc3d800f67d90fab703f9264','source_page_order_review_sha256':sha(MAP),'source_page_order_review_path':str(MAP),'mapping':[{'id':x,'new_order':order[x],'new_title':titles[x],'prior_order':read(A/'chapters'/f'{x}.json')['order'],'prior_title':read(A/'chapters'/f'{x}.json')['title'],'body_sha256':hashlib.sha256(chapters[x]['content'].encode()).hexdigest(),'source_sha256':chapters[x]['sourceSha256']} for x in ids],'raw_source_body_rights_facts_cover_assets_unchanged':True,'artwork_repairs':0,'fetches':0,'actual_acceptance_or_production_mutations':False,'historical_sync_preserved_and_audio_disabled':True}
 put(P/'reader_order_remedy.json',receipt)
 source['content_hash']=aggregate;source['canonical_reader_identity']['reader_content_sha256']=aggregate
 source['canonical_reader_identity']['chapter_content_sha256']={x:chapters[x]['content_hash'] for x in ids}
 source['reader_order_reconciliation']={'record':'reader_order_remedy.json','record_sha256':sha(P/'reader_order_remedy.json'),'chapter_ids_preserved':True,'literary_content_bytes_unchanged':True,'source_page_order_review_sha256':sha(MAP),'scope':'New proposed Reader metadata/version in exact persisted scanned-edition page order; old package preserved archive-only. No new rights/publication/cover acceptance.'}
 put(P/'source_evidence.json',source)
 license=read(P/'license_notice.json');license['chapter_sha256']=[chapters[x]['content_hash'] for x in ids];put(P/'license_notice.json',license)
 cover=read(P/'cover_provenance.json');cover['edition_binding']['content_sha256']=aggregate;put(P/'cover_provenance.json',cover)
 auth=read(P/'publication_authorization.json');auth['content_sha256']=aggregate;auth['chapter_sha256']={x:chapters[x]['content_hash'] for x in ids};auth['rights_decision_id']+='-source-order-v2';auth['license_notice_sha256']=sha(P/'license_notice.json');auth['cover_provenance_sha256']=sha(P/'cover_provenance.json');put(P/'publication_authorization.json',auth)
 for name in ['public_book.json','approval_evidence.json']:
  d=read(P/name);d['content_hash']=aggregate;d['publication_authorization_sha256']=sha(P/'publication_authorization.json');d['cover_provenance_sha256']=sha(P/'cover_provenance.json')
  if name=='public_book.json':d['license_notice_sha256']=sha(P/'license_notice.json')
  put(P/name,d)
 checks=read(P/'checksum_manifest.json');checks['generated_at']=stamp;checks['files']=[{'file':str(f.relative_to(P)),'sha256':sha(f)} for f in sorted(P.rglob('*')) if f.is_file() and f.name not in ['checksum_manifest.json','publication_manifest.json','rights_decision.json']];put(P/'checksum_manifest.json',checks)
 man=read(P/'publication_manifest.json');man['generated_at']=stamp;man['content']['content_hash']=aggregate;oldrows={x['id']:x for x in man['content']['chapters']};rows=[dict(oldrows[x],order=order[x],title=titles[x],sha256=sha(P/'chapters'/f'{x}.json')) for x in ids];man['content']['chapters']=rows;man['content']['chapter_index_sha256']=canon(rows)
 man['rights']['evidence_sha256']=sha(P/'source_evidence.json');man['artifacts']={f.stem:sha(f) for f in P.glob('*.json') if f.name not in ['rights_decision.json','publication_manifest.json','checksum_manifest.json','highlight_sync.json']};man.pop('manifest_sha256',None);man['manifest_sha256']=canon(man);put(P/'publication_manifest.json',man)
 dec=read(P/'rights_decision.json');dec['decision_id']+='-source-order-v2';dec['valid_from']=stamp;dec['components']={k:sha(P/f'{k}.json') for k in dec['components']};dec['components']['reader_order_remedy']=sha(P/'reader_order_remedy.json');dec['evidence_sha256'].append(sha(P/'reader_order_remedy.json'));assert dec['status']=='PROPOSED' and dec['conditions_satisfied'] is False;put(P/'rights_decision.json',dec)
 assert inv(S)==oldinventory,'Original proposal changed'
 for x in ids:
  before=read(A/'chapters'/f'{x}.json');after=read(P/'chapters'/f'{x}.json')
  assert {k:v for k,v in before.items() if k not in ['order','title','updated_at']}=={k:v for k,v in after.items() if k not in ['order','title','updated_at']}
 for f in S.rglob('*'):
  if f.is_file() and ('covers' in f.parts or f.name=='highlight_sync.json'):assert sha(f)==sha(P/f.relative_to(S))
 assert source['source_hash']==read(A/'source_evidence.json')['source_hash']
 assert all(sha(P/z['file'])==z['sha256'] for z in checks['files'])
 assert all(sha(P/f'{k}.json')==v for k,v in dec['components'].items())
 result={'slug':slug,'disposition':'FROZEN_NEW_ORDER_ONLY_PROPOSAL_PENDING_TWO_EXACT_REVIEWS','proposal_path':str(P),'prior_proposal_archive':str(A),'package_version':receipt['package_version'],'source_order_ids':ids,'old_content_hash':receipt['prior_content_hash'],'new_content_hash':aggregate,'source_hash_unchanged':source['source_hash'],'chapter_body_content_source_hashes_preserved':True,'artwork_sync_unchanged':True,'source_page_order_review_sha256':sha(MAP),'decision_raw_sha256':sha(P/'rights_decision.json'),'decision_canonical_sha256':canon(dec),'package_inventory_canonical_sha256':canon(inv(P)),'checksum_entries':len(checks['files']),'checksum_component_and_manifest_index_pass':True,'actual_acceptance':False,'new_attempts':1}
 put(W/'validation.json',result);results.append(result)
put(O/'batch-result.json',{'schema':'earnalism.bengali-order-remedy-or-noop.v1','captured_at':stamp,'titles':results,'no_canonical_writes':True,'no_artwork_retry_or_fetch':True,'actual_acceptance':False})
print(json.dumps(results,ensure_ascii=False,indent=2))
