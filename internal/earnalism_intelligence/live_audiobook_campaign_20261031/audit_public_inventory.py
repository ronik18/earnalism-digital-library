import json,hashlib,urllib.request,urllib.error,concurrent.futures,datetime
from pathlib import Path
ROOT=Path('/tmp/earnalism-main-approved-integration')
OUT=ROOT/'internal/earnalism_intelligence/live_audiobook_campaign_20261031'
if (OUT/'campaign-state.json').exists():
 print(json.dumps(json.loads((OUT/'campaign-state.json').read_text()),indent=2))
 raise SystemExit(0)
OUT.mkdir(exist_ok=True)
NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(data):return hashlib.sha256(data).hexdigest()
def load(p):return json.loads(p.read_text())
def receipt(p):return {'path':str(p.relative_to(ROOT)),'sha256':digest(p.read_bytes())}
def fetch(path):
 try:
  r=urllib.request.urlopen(urllib.request.Request('https://theearnalism.com'+path,headers={'User-Agent':'Earnalism-campaign-readonly-audit/1.0'}),timeout=30)
  body=r.read();return {'http':r.status,'sha256':digest(body),'body':body.decode(),'url':r.url}
 except urllib.error.HTTPError as e:return {'http':e.code,'url':'https://theearnalism.com'+path}
 except Exception as e:return {'http':None,'error':type(e).__name__}
registry=load(ROOT/'backend/data/rights_decision_registry.json')
provider=load(ROOT/'internal/earnalism_intelligence/provider_performance_memory.json')
history=load(ROOT/'internal/earnalism_intelligence/title_decision_history.json')
queue=load(ROOT/'internal/earnalism_intelligence/bengali_audiobook_campaign_queue.json')
q={x['slug']:x for x in queue['titles']}
raw=Path('/tmp/earnalism-canonical-recovery-20261031/public-books.json').read_bytes()
(OUT/'initial-public-inventory.json').write_bytes(raw)
books=[b for b in json.loads(raw) if b.get('reader_enabled') and b.get('publication_status')=='LIVE_APPROVED']
assert len(books)==len({b['slug'] for b in books})==52

def audit(b):
 slug=b['slug']; folder=ROOT/'backend/data/controlled_publications'/slug
 live=fetch('/api/reader/book/'+slug+'/manifest')
 livejson=json.loads(live.pop('body')) if live.get('http')==200 else {}
 (OUT/'public-manifests').mkdir(exist_ok=True)
 (OUT/'public-manifests'/(slug+'.json')).write_text(json.dumps(livejson,ensure_ascii=False,indent=2)+'\n')
 record={'slug':slug,'title':b['title'],'book_id':b['id'],'url':'https://theearnalism.com/book/'+slug,'stage':'RIGHTS_AND_PRODUCTION_PREFLIGHT','status':'BLOCKED','source_version':{'repository_commit':'9a1b166e189cebc9b2b75baf20a95d2eb33a3c12','catalog_updated_at':b.get('updated_at'),'public_manifest':live},'voice':{'status':'NOT_SELECTED_NOT_QUALIFIED','candidates':'Title/language-specific Ryan, Girija or qualified alternative; no voice-label-only acceptance'},'music':{'selection':'SILENCE','license_required':False,'reason':'No licensed score supplied; preserve intelligibility and avoid adding unqualified music'},'quality':{'content':'UNVERIFIED','pronunciation':'UNVERIFIED','listening':'UNVERIFIED','audio':'UNVERIFIED','sync':'UNVERIFIED','live_playback':'UNVERIFIED'},'repairs':[],'costs':{'new_provider_spend_usd':0,'new_storage_spend_usd':0,'new_paid_playback_spend_usd':0,'production_estimate_usd':None,'estimate_status':'NOT_ESTIMATED_BEFORE_RIGHTS_AND_PROVIDER_QUALIFICATION','historical_costs':'RETAINED_IN_EXISTING_LEDGERS_NOT_RESET'},'blockers':[]}
 for n in ['source_evidence.json','reader_manifest.json','rights_decision.json']:
  p=folder/n
  if p.exists():record['source_version'][n]=receipt(p)
 local=load(folder/'reader_manifest.json') if (folder/'reader_manifest.json').exists() else {}
 record['language']=livejson.get('language') or local.get('language') or q.get(slug,{}).get('language')
 record['source_version']['chapters']=[receipt(p) for p in sorted((folder/'chapters').glob('*.json'))]
 record['source_version']['live_chapter_count']=len(livejson.get('chapters',[]))
 record['source_version']['live_version']=livejson.get('version')
 record['source_version']['live_content_generation']=livejson.get('content_generation')
 record['source_version']['live_audio']=livejson.get('audio')
 record['source_version']['live_book_slug']=livejson.get('book',{}).get('slug')
 record['source_version']['live_manifest_fields']={k:livejson[k] for k in ['slug','language','chapter_count','audio_enabled','audiobook_enabled','audiobook_package_version','audiobook_duration_ms'] if k in livejson}
 if live.get('http')!=200:record['blockers'].append({'code':'PUBLIC_READER_MANIFEST_UNVERIFIED','action':'Resolve public manifest response before binding narration to the current live edition.'})
 bindings=registry.get('audio_package_bindings',{}).get(slug,{})
 record['rights']={'audio_package_bindings':bindings,'reader_rights_do_not_establish_audio_rights':True}
 if not bindings:
  record['blockers'].append({'code':'EXACT_EDITION_AUDIO_USE_AND_VOICE_LICENSE_NOT_QUALIFIED','action':'Qualify underlying literary audio rights and territory from retained source-term evidence; retain applicable stock voice/model terms and bind the exact narration package through the supported audio-use workflow. Current owner campaign authority covers routine work; do not infer a license or require duplicate cost-only approval.'})
  record['blockers'].append({'code':'QUALIFIED_FULL_TITLE_RECORDING_AND_QA_MISSING','action':'After rights/provider qualification, audition representative passages, freeze source/settings and produce or import one complete source-bound title; pass full content, pronunciation, acoustic, listening, measured-sync and protected-playback checks before release.'})
 if slug in q:
  old=q[slug];record['prior_campaign']={k:old.get(k) for k in ['current_campaign_state','known_blockers','selected_strategy','human_narration_packet','next_action'] if k in old}
  if old.get('known_blockers'):record['blockers'].append({'code':'PRIOR_CAMPAIGN_FAILURES_NO_BLIND_RETRY','action':old.get('next_action'),'evidence':old['known_blockers']})
  record['blockers'].append({'code':'BENGALI_PILOT_SCALE_AND_BUDGET_GATES','action':'Respect the current pilot-first campaign state; establish a supported qualified runtime and enforced numeric campaign/per-title budget gates before any paid request; do not replay failed fingerprints.'})
 if bindings:
  evidence=ROOT/('internal/audiobook_lab/release_gate/open_window_publication_evidence_20261026/playback.json' if slug=='the-open-window' else 'internal/audiobook_lab/release_gate/selfish-giant-20261029/production-acceptance/playback.json')
  playback=load(evidence);record['retained_playback_evidence']=receipt(evidence)
  record['retained_playback_summary']={k:playback.get(k) for k in ['packageVersion','descriptor','durationMs','segmentCount','status','ended','pauseResumeSeekPass'] if k in playback}
  record['retained_playback_summary']['coverage_segments']=len(playback.get('coverage',[]))
  record['catalog_audio']={k:b.get(k) for k in ['audio_enabled','audio_status','audio_qa_status','audiobook_enabled','audiobook_package_version','audiobook_delivery_mode','audiobook_duration_ms','audiobook_release_gate']}
  record['live_audio_manifest_guest']=fetch('/api/reader/book/'+slug+'/audiobook/manifest')
  record['customer_page']=fetch('/book/'+slug);record['customer_page'].pop('body',None)
  record['blockers'].append({'code':'EXISTING_AUDIOBOOK_CURRENT_ACCEPTANCE_REUSE_REVIEW','action':'Compare current public Reader package identity, active descriptor, protected denial, runtime/accounting dependencies and genuine full-playback evidence; perform browser discovery verification. No regeneration or publication toggle is authorized by a catalog flag alone.'})
  record['stage']='EXISTING_RELEASE_REUSE_VERIFICATION'
 (OUT/(slug+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 return record
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(audit,books))
summary={'schema':'earnalism.live-audiobook-campaign.v1','observed_at':NOW,'initial_inventory_count':len(records),'initial_inventory_sha256':digest(raw),'scope_frozen':True,'base_commit':'9a1b166e189cebc9b2b75baf20a95d2eb33a3c12','cost_only_authority':'OWNER_PREAUTHORIZED_COST_EFFECTIVE_IN_SCOPE_SUBJECT_TO_ENFORCED_LIMITS','new_provider_spend_usd':0,'new_publications':0,'verified_live':0,'blocked':len(records),'records':[{'slug':r['slug'],'status':r['status'],'record':r['slug']+'.json'} for r in records],'production_mutations':0,'note':'BLOCKED describes current evidence gaps, not a legal conclusion that the literary work is unavailable for audio. No missing check is PASS.'}
(OUT/'campaign-state.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'count':len(records),'manifest_http':{str(c):sum(r['source_version']['public_manifest'].get('http')==c for r in records) for c in set(r['source_version']['public_manifest'].get('http') for r in records)},'output':str(OUT)}))
