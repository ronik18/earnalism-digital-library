"""Root-only post-merge evidence recording. No fetch, commit, push, PR or release action.

Requires actual production receipt, frontend/backend canary reports, and truthful
per-title readback. Default writes a scratch preview; --apply records evidence and
updates only existing campaign state/README after exact merged-main validation.
"""
import argparse,copy,datetime,hashlib,json,pathlib,re,shutil,subprocess

PREDECESSOR_REVIEWED_HEAD='3c374472b07c86d28c15f0bdd6adde8e887a808c'
CAMPAIGN='internal/earnalism_intelligence/book_go_live_477_continuation_20261002'
NEXT='owner-delegated-completion-20261003/next-cohort'
STOP='STOP_NO_SAFE_ACTION_IN_THIS_ASSESSED_SPRINT; retain exact holds and resume only on materially new cleared evidence; no recurring retries or duplicate tasks.'
def load(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def canonical(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def require(ok,why):
 if not ok:raise ValueError(why)
def finalise(a):
 root=pathlib.Path(a.root).resolve();ledgerpath=root/CAMPAIGN/NEXT/'all-assessed-edition-dispositions-candidate.json';candidate=load(ledgerpath);integration=load(root/CAMPAIGN/NEXT/'serialized-integration-receipt.json')
 receiptpath=pathlib.Path(a.production_receipt).resolve();frontpath=pathlib.Path(a.frontend_canary).resolve();backpath=pathlib.Path(a.backend_canary).resolve();readpath=pathlib.Path(a.readback).resolve();checkspath=pathlib.Path(a.protected_checks).resolve()
 receipt,front,back,readback,protected=map(load,[receiptpath,frontpath,backpath,readpath,checkspath]);slugs=integration['new_exact_slugs'];slugset=set(slugs)
 if a.synthetic_fixture_test:
  require(not a.apply and all(x.get('synthetic_fixture') is True for x in [receipt,front,back,readback,protected]),'Synthetic validation must be explicitly labelled on every input and can never apply canonical changes')
 else:require(not any(x.get('synthetic_fixture') for x in [receipt,front,back,readback,protected]),'Synthetic inputs cannot create a real completion receipt')
 require(len(slugs)==19 and len(slugset)==19,'Exact current new cohort must contain19 distinct canonical editions')
 require(len(candidate['entries'])==231 and len({e['slug'] for e in candidate['entries']})==231,'All231 exact per-title dispositions required')
 require(candidate['released_retained_count']==33 and candidate['new_ready_count']==19 and candidate['terminal_active_sprint_exclusions']==179,'Unexpected predecessor disposition counts; reconcile rather than assume')
 require(receipt['merge_commit']==a.main_sha and receipt['reviewed_head']==a.reviewed_head_sha,'Actual receipt must bind latest reviewed PR511 head and exact merged main')
 require(protected['head_sha']==a.reviewed_head_sha and protected['all_required_checks_pass'] is True and protected['normal_protected_merge'] is True,'Actual protected-check evidence must bind the final amended reviewed head, never the predecessor')
 require(protected.get('required_checks') and all(str(c['conclusion']).lower()=='success' and c.get('name') and c.get('details_url') for c in protected['required_checks']),'Observed required checks must each carry actual identity/link and success')
 if a.reviewed_tree_sha:require(receipt.get('reviewed_tree')==a.reviewed_tree_sha,'Actual reviewed tree must match supplied amended reviewed tree')
 require(str(receipt['pr']).rstrip('/').endswith('/pull/511'),'Record only the existing PR511 integration')
 require(receipt['protected_exact_head_checks']=='ALL_PASS_NORMAL_MERGE_NO_BYPASS','Normal protected exact-head checks/merge evidence required')
 require(set(receipt['release_scope']['new_titles'])==slugset and receipt['release_scope']['territory']=='IN' and receipt['release_scope']['audio_exposed'] is False,'Receipt must bind exact19 IN text-only editions')
 require(receipt['frontend']['commit']==a.main_sha and receipt['frontend']['all_three_jobs']=='SUCCESS','Exact frontend regression/deployment/production-canary identity and success required')
 require(receipt['backend']['commit']==a.main_sha and receipt['backend']['status']=='SUCCESS' and receipt['backend']['native_canary_status']=='SUCCESS','Exact backend deployment/native-canary success required')
 require(front['result']=='PASS' and back['status']=='PASS' and back['deployment_sha']==a.main_sha,'Actual passing canary report bytes for exact merged deployment required')
 require(readback.get('main',readback.get('merged_main'))==a.main_sha and readback['production_mutation_performed'] is False,'Readback must be read-only and bind exact deployed main')
 native=readback.get('schema')=='earnalism.next19.actual-public-get-readback.v1'
 if native:
  require(readback['result']=='PASS' and readback['failure_count']==0 and readback['requests']==95 and readback['protected_manifest_routes']==38 and set(readback['new_titles'])==slugset,'Actual new19 probe must pass all95 routes including38 manifest readbacks')
  require(readback['native_inspector_sha256']==sha(root/'scripts/post_deploy_static_seo_canary.py'),'New19 native inspector identity must match exact deployed source')
  require(readback['india_backend_contract']=='NOT_RUN_FROM_NON_IN' and all(v is None for v in readback['observed_canonical_versions'].values()),'Actual US probe must retain truthful null India canonical versions')
 rows={r.get('path',r.get('route')):dict(r,status=r.get('status',r.get('status_code'))) for r in readback['rows']};frontrows={r['route']:r for r in front['routes']};versions={};denied=[]
 for slug in slugs:
  for route in [f'/book/{slug}',f'/reader/{slug}']:
   r=frontrows.get(route);require(r is not None and r.get('status_code')==200 and r.get('result')=='PASS' and not r.get('failures'),f'Actual deployed frontend route PASS required: {route}')
  listener=rows.get(f'/listener/{slug}');require(listener is not None and listener['status']==200,f'Actual listener HTTP200 required: {slug}')
  if native:require(listener.get('result')=='PASS' and listener.get('failures')==[] and isinstance(listener.get('body_sha256'),str) and re.fullmatch('[0-9a-f]{64}',listener['body_sha256']) is not None,f'Exact native disabled-listener semantic inspection and actual body hash required: {slug}')
  else:require(listener['unavailable_copy_present'] is True and listener['audio_or_media_control_present'] is False,f'Truthful disabled listener observation required: {slug}')
  apis=[rows.get(f'/api/reader/book/{slug}/manifest'),rows.get(f'/api/reading-pass/books/{slug}/manifest')];require(all(apis),f'Both actual Reader/Reading Pass readback rows required: {slug}')
  if all(r['status']==451 for r in apis):
   require(all(r['detail']['code']=='RELEASE_TERRITORY_DENIED' and isinstance(r['detail']['country'],str) and len(r['detail']['country'])==2 and r['detail']['country']!='IN' and r['detail']['allowed_countries']==['IN'] and r['observed_canonical_version'] is None for r in apis),f'Exact overseas denial and null version required: {slug}')
   if native:require(all(r['detail']['country']=='US' and r['result']=='PASS' and not r['failures'] for r in apis),'Actual next19 probe must preserve exact38 observed US451 denial rows')
   versions[slug]=None;denied.append(slug)
  else:
   require(all(r['status']==200 and isinstance(r.get('observed_canonical_version'),str) and r['observed_canonical_version'] for r in apis),f'Actual non-denied canonical version must be observed, never inferred: {slug}')
   require(apis[0]['observed_canonical_version']==apis[1]['observed_canonical_version'],f'Reader/Pass canonical identity mismatch: {slug}')
   versions[slug]=apis[0]['observed_canonical_version']
 # Reuse exact complete-source and active-Reader evidence; do not rerun a review.
 if denied:
  waiver=receipt['waiver_conditions'];require(waiver['exact_complete_integrity_clean_source'] is True and waiver['clean_active_reader_validation'] is True,'Conditional manual observation waiver preconditions must be established by exact retained evidence')
  require(waiver.get('evidence'),'Actual hash-bound waiver-precondition evidence required')
  require({'exact_complete_source_and_active_reader_validation','independent_final_review_a','independent_final_review_b'}<={e.get('role') for e in waiver['evidence']},'Exact local source/active Reader validation and two independent final reviews must be separately hash-bound')
  for e in waiver['evidence']:
   p=pathlib.Path(e['path']);p=p if p.is_absolute() else root/p;require(p.is_file() and sha(p)==e['sha256'],'Missing or changed exact waiver-precondition evidence: '+str(p))
 for slug in slugs:
  package=root/'data/controlled_publications'/slug;reader=load(package/'reader_manifest.json');source=load(package/'source_evidence.json');decision=load(package/'rights_decision.json');checks=load(package/'checksum_manifest.json')
  require(decision['status']=='ACCEPTED' and decision['conditions_satisfied'] is True and decision['territories']==['IN'],'Exact accepted IN decision required: '+slug)
  require(reader.get('audio_enabled') is False and reader.get('audiobook_enabled') is False,'Audio must remain disabled: '+slug)
  for e in checks['files']:require(sha(package/e['file'])==e['sha256'],'Changed accepted package file: '+slug+'/'+e['file'])
  units=[load(package/'chapters'/f'{c["id"]}.json') for c in sorted(reader['chapters'],key=lambda c:c['order'])]
  aggregate=hashlib.sha256('\n\n'.join(c['content'] for c in units).encode()).hexdigest();require(aggregate==source['content_hash'],'Changed ordered Reader content identity: '+slug)
  require(all(hashlib.sha256(c['content'].encode()).hexdigest()==c['content_hash'] for c in units),'Changed exact chapter body: '+slug)
 result=copy.deepcopy(candidate);stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for e in result['entries']:
  if e['slug'] in slugset:
   e['pre_completion_assessment_preserved']=copy.deepcopy(e);e.update(disposition='RELEASED_PROTECTED_MERGE_DEPLOY_CANARY_WITH_TRUTHFUL_READBACK',reason='Exact passing accepted edition released through existing protected normal checks, exact-main frontend/backend deployment and passing canaries. Canonical version is the actual readback value; scoped overseas denial remains null under the conditional waiver.',production_canonical_version_observed=versions[e['slug']],production_observation_scope='OVERSEAS_TERRITORY_DENIAL_ONLY_CONDITIONAL_WAIVER' if e['slug'] in denied else 'ACTUAL_SUCCESSFUL_CANONICAL_VERSION_READBACK',terminal_exclusion_from_active_sprint=False,exact_blockers=[],next_action='Retain released canonical edition and immutable evidence; no duplicate release.')
  elif e['terminal_exclusion_from_active_sprint']:e['next_action']=STOP
 require(sum(e['terminal_exclusion_from_active_sprint'] for e in result['entries'])==179,'Terminal holds changed unexpectedly')
 released=[e for e in result['entries'] if not e['terminal_exclusion_from_active_sprint']];require(len(released)==52,'Final released count must be52')
 english=[e for e in released if e['language_normalized']=='English'];bengali=[e for e in released if e['language_normalized']=='Bengali'];require(len(english)==43 and len(bengali)==9,'Final language counts must be43EN/9BN')
 require(sum(e['language_normalized']=='English' and e['terminal_exclusion_from_active_sprint'] for e in result['entries'])==81,'English holds must remain81 known-language records')
 if a.synthetic_fixture_test:
  destination=pathlib.Path(a.output).resolve();require(not destination.exists(),'Immutable synthetic result already exists');destination.mkdir(parents=True)
  test={'schema':'earnalism.pr511-completion-recorder.synthetic-validation-only.v1','synthetic_fixture':True,'actual_production':False,'canonical_writes':0,'completion_receipt_created':False,'verified_fixture_expected_counts':{'released':52,'English':43,'Bengali':9,'held':179,'English_held':81},'fixture_only_denial_rows':len(denied)*2,'fixture_only_null_versions':len([v for v in versions.values() if v is None]),'actual_receipt_required_before_root_applies':True}
  write(destination/'synthetic-validation-only.json',test);print(json.dumps(test));return
 result.update(schema='earnalism.all-assessed-editions-disposition.immutable-completed-sprint.v1',captured_at=stamp,prior_immutable_ledger_sha256=sha(ledgerpath),source_main=a.main_sha,latest_reviewed_head=a.reviewed_head_sha,latest_reviewed_tree=a.reviewed_tree_sha,predecessor_reviewed_head_preserved=PREDECESSOR_REVIEWED_HEAD,protected_exact_head_evidence_sha256=sha(checkspath),released_retained_count=52,new_ready_count=0,configured_count=52,production_observed_for_new_cohort='EXACT_DEPLOYMENTS_AND_CANARIES; SEE_PER_TITLE_NARROW_READBACK_SCOPE',canonical_versions=versions,canonical_versions_not_inferred=True,all_assessed_editions_released_or_terminal_held=True,terminal_active_sprint_exclusions=179,active_sprint_safe_actions_exhausted=True,entire_catalogue_live=False,safe_queue_exhaustion_claimed=False,next_action=STOP,production_receipt_sha256=sha(receiptpath))
 result['counts']={};
 for e in result['entries']:result['counts'][e['disposition']]=result['counts'].get(e['disposition'],0)+1
 result['english'].update(released_retained=43,new_ready=0,held_or_dropped=81,entire_English_catalogue_live=False);result['bengali'].update(released_retained=9,new_ready=0)
 destination=root/CAMPAIGN/'owner-delegated-completion-20261003/pr511-production' if a.apply else pathlib.Path(a.output).resolve()
 require(not destination.exists(),'Immutable destination already exists; append a newly reconciled receipt, never overwrite')
 if a.apply:
  head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();require(head==a.main_sha,'Root must be reconciled to exact merged main before recording')
  branch=subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip();require(branch in ['main','codex/main-approved-integration'],'Sole canonical integration authority required')
  subprocess.run(['git','merge-base','--is-ancestor',a.reviewed_head_sha,a.main_sha],cwd=root,check=True)
  if a.reviewed_tree_sha:require(subprocess.check_output(['git','rev-parse',a.reviewed_head_sha+'^{tree}'],cwd=root,text=True).strip()==a.reviewed_tree_sha,'Actual amended head/tree mismatch')
  require(not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip(),'Root canonical checkout must be clean before evidence-only recording')
 destination.mkdir(parents=True);evidence=destination/'evidence';evidence.mkdir()
 for p,name in [(receiptpath,'actual-production-receipt.json'),(frontpath,'frontend-canary.json'),(backpath,'backend-canary.json'),(readpath,'truthful-readback.json'),(checkspath,'actual-final-head-protected-checks.json')]:shutil.copy2(p,evidence/name);require(sha(evidence/name)==sha(p),'Evidence copy changed')
 write(destination/'all-assessed-edition-dispositions-final.json',result)
 reconciliation={'schema':'earnalism.book-go-live-477-final-production-reconciliation.v1','recorded_at':stamp,'pr':receipt['pr'],'reviewed_head':a.reviewed_head_sha,'reviewed_tree':a.reviewed_tree_sha,'predecessor_reviewed_head_preserved':PREDECESSOR_REVIEWED_HEAD,'merge_commit':a.main_sha,'released_new_slugs':slugs,'released_total':52,'english_released':43,'bengali_released':9,'terminal_active_sprint_exclusions':179,'english_held':81,'audio_exposed':False,'observed_canonical_versions':versions,'conditional_waiver_only_for_overseas_denied_slugs':denied,'canonical_versions_not_inferred':True,'entire_catalogue_live':False,'next_action':STOP,'evidence_sha256':{p.name:sha(p) for p in evidence.iterdir()},'final_disposition_ledger_sha256':sha(destination/'all-assessed-edition-dispositions-final.json')}
 write(destination/'reconciliation.json',reconciliation)
 if a.apply:
  statepath=root/CAMPAIGN/'state.json';state=load(statepath);write(destination/'predecessor-campaign-state.json',state)
  state.update(source_main=a.main_sha,latest_reviewed_head=a.reviewed_head_sha,configured_candidate_count=52,released_count=52,released_english=43,released_bengali=9,terminal_active_sprint_exclusions=179,continuation_status='ASSESSED_SPRINT_COMPLETE_52_RELEASED_179_TERMINAL_HELD',production_readback='PR511_EXACT_MAIN_FRONTEND_BACKEND_DEPLOY_CANARIES_PASS; ACTUAL_PER_TITLE_READBACK_VALUES_ONLY; OVERSEAS451_VALUES_NULL_CONDITIONAL_WAIVER',next_action=STOP,current_prepared_evidence_queue='NO_SAFE_ACTION_REMAINS_IN_ASSESSED_SPRINT',next_distinct_candidate=None,next_prepared=[],pr511_production_reconciliation=str((destination/'reconciliation.json').relative_to(root/CAMPAIGN)),final_all_assessed_dispositions=str((destination/'all-assessed-edition-dispositions-final.json').relative_to(root/CAMPAIGN)),audio_exposure=False,existing_versions_preserved=True)
  state['next_held']={e['slug']:'; '.join(e.get('exact_blockers') or [e['reason']]) for e in result['entries'] if e['terminal_exclusion_from_active_sprint']}
  state['validation'].update(protected_ci='PR511_EXACT_REVIEWED_HEAD_ALL_REQUIRED_NORMAL_CHECKS_PASS',canary='PR511_EXACT_MAIN_FRONTEND_BACKEND_CANARIES_PASS',production='PR511_EXACT_MAIN_DEPLOYMENTS_SUCCESS',production_canonical_versions=versions)
  state['owner_provided_next19_integration'].update(new_ready_count=0,released_new_count=19,production_observed='DEPLOYMENT_CANARY_SCOPE; CANONICAL_VERSION_READBACK_NOT_INFERRED',final_dispositions=state['final_all_assessed_dispositions']);write(statepath,state)
  with (root/CAMPAIGN/'README.md').open('a') as f:f.write('\n\nFinal assessed sprint reconciliation '+stamp+': PR511 exact reviewed head merged to `'+a.main_sha+'`; actual frontend/backend deployments and canaries PASS. All231 editions are classified:52 released (43English/9Bengali),179 retained terminal holds/exclusions. India canonical versions remain null for observed overseas451 rows under the narrowly conditional manual-observation waiver; no production version inferred. Audio stays disabled. Next action: '+STOP+'\n')
 print(json.dumps({'destination':str(destination),'final_ledger_sha256':sha(destination/'all-assessed-edition-dispositions-final.json'),'released':52,'held':179,'observed_versions':versions,'canonical_writes_performed':a.apply}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',default='/tmp/earnalism-main-approved-integration');p.add_argument('--production-receipt',required=True);p.add_argument('--frontend-canary',required=True);p.add_argument('--backend-canary',required=True);p.add_argument('--readback',required=True);p.add_argument('--protected-checks',required=True);p.add_argument('--reviewed-head-sha',required=True);p.add_argument('--reviewed-tree-sha');p.add_argument('--main-sha',required=True);p.add_argument('--apply',action='store_true');p.add_argument('--synthetic-fixture-test',action='store_true');p.add_argument('--output',default='/workspace/scratch/181ef0a25f05/pr511-final-recording-preview');finalise(p.parse_args())
