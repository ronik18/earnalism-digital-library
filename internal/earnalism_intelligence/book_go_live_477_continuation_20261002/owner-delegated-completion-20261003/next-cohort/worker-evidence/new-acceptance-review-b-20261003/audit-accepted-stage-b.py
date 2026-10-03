import pathlib,json,hashlib,sys,datetime
repo=pathlib.Path('/tmp/earnalism-main-approved-integration');sys.path.insert(0,str(repo/'backend'));from rights_decision_gate import record_sha256,evaluate_accepted_record
stage=pathlib.Path(sys.argv[1]);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();r=json.loads((stage/'acceptance-receipt.json').read_text());inventory=[]
for entry in r['cohort']:
 slug=entry['slug'];p=stage/'data/controlled_publications'/slug;prior=stage/'preserved-proposals'/slug;record=json.loads((p/'rights_decision.json').read_text());checks={};components={};cover=json.loads((p/'cover_provenance.json').read_text())
 for k,v in record['components'].items():
  q=p/f'{k}.json'
  if k.startswith('acceptance_review_'):q=p/'evidence'/('review_'+k[-1]+'.json')
  if k.startswith('cover_') and any(s in k for s in ['_asset','_delivery']) and k not in ['cover_delivery_derivation']:
   side='front' if 'front' in k else 'back'
   if 'original' in k:q=pathlib.Path(cover['original_'+side]['path'])
   elif 'delivery' in k:q=stage/entry['assets'][side]['path']
   else:q=p/'covers'/f'{side}.png'
  components[k]=h(q);checks['component:'+k]=components[k]==v
 cm=json.loads((p/'checksum_manifest.json').read_text())
 for x in cm['files']:checks['checksum:'+x['file']]=h(p/x['file'])==x['sha256']
 for q in p.rglob('*'):
  if q.is_file():checks['mirror:'+str(q.relative_to(p))]=h(q)==h(stage/'backend/data/controlled_publications'/slug/q.relative_to(p))
 for q in (prior/'chapters').glob('*.json'):checks['chapter_unchanged:'+q.name]=h(q)==h(p/'chapters'/q.name)
 for f in ['source_evidence.json','highlight_sync.json']:checks['source_unchanged:'+f]=h(prior/f)==h(p/f)
 checks['decision_receipt']=record_sha256(record)==entry['canonical_record_sha256'];checks['publication_auth_receipt']=h(p/'publication_authorization.json')==entry['publication_authorization_sha256']
 for side,a in entry['assets'].items():checks['asset:'+side]=h(stage/a['path'])==a['sha256']
 pub=json.loads((p/'public_book.json').read_text());app=json.loads((p/'approval_evidence.json').read_text());auth=json.loads((p/'publication_authorization.json').read_text());cover=json.loads((p/'cover_provenance.json').read_text());man=json.loads((p/'publication_manifest.json').read_text())
 for k,v in man['artifacts'].items():checks['manifest_artifact:'+k]=h(p/(k+'.json'))==v
 for name,doc in [('pub',pub),('approval',app)]:
  checks[name+'_auth_binding']=doc['publication_authorization_sha256']==h(p/'publication_authorization.json');checks[name+'_cover_binding']=doc.get('cover_provenance_sha256')==h(p/'cover_provenance.json')
 checks['auth_cover_binding']=auth['cover_provenance_sha256']==h(p/'cover_provenance.json');checks['INonly']=record['territories']==['IN'] and auth['territories']==['IN'];checks['audiofalse']=all(pub.get(k) is False for k in ['audio_enabled','audiobook_enabled','generate_audiobook']) and auth['audio_authorized'] is False
 now=datetime.datetime.fromisoformat(r['actual_acceptance_at'])+datetime.timedelta(seconds=1)
 verdicts={use:evaluate_accepted_record(record,edition_id=slug,operator_id='reo-enterprise',country='IN',country_trusted=True,use=use,required_components=components,accepted_records={record['decision_id']:record_sha256(record)},revoked_decision_ids=frozenset(),now=now).passed for use in record['uses']}
 for use in ['audio_stream','audio_download']:verdicts[use]=evaluate_accepted_record(record,edition_id=slug,operator_id='reo-enterprise',country='IN',country_trusted=True,use=use,required_components=components,accepted_records={record['decision_id']:record_sha256(record)},revoked_decision_ids=frozenset(),now=now).passed
 inv={'slug':slug,'rights_decision_raw_sha256':h(p/'rights_decision.json'),'rights_decision_canonical_sha256':record_sha256(record),'components':components,'checksum_count':len(cm['files']),'chapter_count':len(list((p/'chapters').glob('*.json'))),'all_hash_integrity_checks_pass':all(checks.values()),'failed_checks':[k for k,v in checks.items() if not v],'isolated_candidate_evaluator':verdicts,'current_delegation_actor':record['accepted_by'],'acceptance_at':record['valid_from'],'acceptance_matches_receipt':record['valid_from']==r['actual_acceptance_at'],'metadata_semantics':{'cover':{k:v for k,v in cover.items() if k in ['status','visual_review_status','commercial_use_authorized','cover_display_approved','scope','independent_reviews']},'approval_scope':app.get('approval_scope')}};inventory.append(inv)
 print(slug,'integrity',inv['all_hash_integrity_checks_pass'],'failed',inv['failed_checks'],'components',len(components),'checksums',len(cm['files']),'chapters',inv['chapter_count'],'digest',inv['rights_decision_canonical_sha256'])
output=pathlib.Path(sys.argv[2]);output.write_text(json.dumps({'reviewer':'independent_reviewer_B','stage':str(stage),'acceptance_receipt_sha256':h(stage/'acceptance-receipt.json'),'global_gate':r['global_gate'],'production_observed':False,'canonical_mutations_by_B':False,'inventory':inventory},ensure_ascii=False,indent=2)+'\n');print('audit_file',output,h(output))
