"""Independent arithmetic/hash/source/cue verification; does not adopt or upload."""
from pathlib import Path
import copy,hashlib,json,sys
P=Path(__file__).resolve().parent;V4=P.with_name('proposed-scored-sourceqa-20261102-v4');CAN=Path('/tmp/earnalism-main-approved-integration')
sys.path[:0]=[str(CAN/'backend'),str(CAN/'internal/audiobook_lab/scripts')]
import audiobook_package_builder_v2 as builder
import owner_produced_package as supported
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def lev(a,b):
 old=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  new=[i]
  for j,y in enumerate(b,1):new.append(min(new[-1]+1,old[j]+1,old[j-1]+(x!=y)))
  old=new
 return old[-1]
M=json.loads((P/'MANIFEST.PROPOSED.json').read_text());D=json.loads((P/'release-descriptor.PROPOSED.json').read_text());A=json.loads((P/'SOURCE-QA-ADOPTION.PROPOSED.json').read_text());source=(P/'manuscript.txt').read_text()
assert hashlib.sha256(canonical(D)).hexdigest()==M['descriptor_canonical_sha256']
assert M['status']=='PROPOSED_NOT_ADOPTED_NOT_UPLOAD_AUTHORITY' and A['status']=='PROPOSED_NOT_ADOPTED'
assert D['publication_approved'] is False and D['release_candidate_evidence']['all_release_gates_passed'] is False
checked=0
for ref in M['evidence'].values():assert sha(ref['path'])==ref['sha256'];checked+=1
for row in M['assets']:assert sha(row['local_path'])==row['sha256'] and Path(row['local_path']).stat().st_size==row['size_bytes'];checked+=1
assert sum(x['size_bytes'] for x in M['assets'])==M['total_four_asset_bytes_per_store']
R=json.loads((P/'evidence/ACTUAL-ASR-AND-SIX-OWNER-ADJUDICATIONS.json').read_text());old=json.loads((V4/'evidence/ACTUAL-ASR-AND-SIX-OWNER-ADJUDICATIONS.json').read_text())
assert R['normal_spoken_text_comparator']['aliases']=={'mr':'mister','mrs':'missus','endeavoured':'endeavored','favourite':'favorite','laboured':'labored'}
newowner=json.loads(Path(M['evidence']['owner_twelve_names']['path']).read_text());assert sha(M['evidence']['owner_twelve_names']['path'])=='e359a75515950401b14c8c1f0733b8d00c2fc1d49dd4d71f4e0ff2fdec28858e'
assert newowner['answer_verbatim']=='Framton heard in all twelve.'
assert len(R['twelve_CTC_scoped_changes'])==len(R['twelve_Whisper_scoped_changes'])==len(newowner['reviewed_windows'])==12
windows={x['number']:x for x in newowner['reviewed_windows']}
for changes in [R['twelve_CTC_scoped_changes'],R['twelve_Whisper_scoped_changes']]:
 assert {x['reviewed_clip_number'] for x in changes}==set(windows)
 for x in changes:
  w=windows[x['reviewed_clip_number']];assert x['historical_unit']==w['historical_unit'] and x['authority_sha256']==M['evidence']['owner_twelve_names']['sha256']
  assert x['reviewed_fullbook_seconds']==[w['full_book_start_seconds'],w['full_book_end_seconds']]
  if 'actual_retained_word_seconds' in x:assert w['full_book_start_seconds']<=(sum(x['actual_retained_word_seconds'])/2)<=w['full_book_end_seconds']
raw_tokens=[];six_tokens=[];all_tokens=[];cursor=0
for u,o in zip(R['units'],old['units']):
 assert u['id']==o['id'] and sha(u['raw_evidence']['path'])==o['raw_evidence']['sha256']
 assert u['current_recording_CTC_projection_tokens']==o['current_recording_CTC_projection_tokens'] and u['owner_six_adjudicated_tokens']==o['owner_six_adjudicated_tokens']
 text=source[u['source_char_start']:u['source_char_end']];assert not source[cursor:u['source_char_start']].strip();cursor=u['source_char_end']
 assert hashlib.sha256(text.encode()).hexdigest()==u['text_sha256']
 raw=json.loads(Path(u['raw_evidence']['path']).read_text());assert text.split()==raw['expected_text'].split()
 assert hashlib.sha256(' '.join(text.split()).encode()).hexdigest()==u['historical_text_sha256']
 t=list(u['owner_six_adjudicated_tokens'])
 for change in sorted(u['twelve_name_window_changes'],key=lambda x:x['recognized_token_span_before'][0],reverse=True):
  a,b=change['recognized_token_span_before'];assert t[a:b]==change['recognized_tokens_before'];t[a:b]=change['adjudicated_source_tokens']
 assert t==u['six_plus_twelve_scoped_adjudicated_tokens'];raw_tokens+=u['current_recording_CTC_projection_tokens'];six_tokens+=u['owner_six_adjudicated_tokens'];all_tokens+=t
assert not source[cursor:].strip() and len(R['units'])==39
assert all_tokens==R['six_plus_twelve_adjudicated_full_CTC_tokens']
import re
ref=re.findall(r"[a-z]+(?:'[a-z]+)*",source.lower().replace('’',"'"))
alias=R['normal_spoken_text_comparator']['aliases'];norm=lambda s:[alias.get(x,x) for x in s]
comparisons={'literal_current_CTC':(ref,raw_tokens),'six_owner_adjudicated_CTC':(ref,six_tokens),'six_plus_twelve_scoped_current_CTC':(ref,all_tokens),'six_plus_twelve_CTC_standard_spoken_comparator':(norm(ref),norm(all_tokens)),'literal_full_current_Whisper_projection':(ref,R['full_current_Whisper_projection_tokens']),'six_plus_twelve_scoped_full_Whisper':(ref,R['six_plus_twelve_adjudicated_full_Whisper_tokens']),'six_plus_twelve_full_Whisper_standard_spoken_comparator':(norm(ref),norm(R['six_plus_twelve_adjudicated_full_Whisper_tokens']))}
for name,(a,b) in comparisons.items():
 q=R['aggregate_metrics'][name];errors=lev(a,b);assert q['levenshtein_edits']==errors and q['reference_tokens']==len(a) and q['recognized_tokens']==len(b) and abs(q['score_0_to_10']-10*(1-errors/len(a)))<1e-12
assert R['first_last_source_tokens_match_both_adjudicated_recognizers'] is True
assert A['remaining_material_wording_findings']==[] and A['human_scores']==json.loads((P/'support/owner/OWNER-COMPLETE-SCORED-ACCEPTANCE-20261102.json').read_text())['ratings_0_to_10'] and A['confidence']==.97
actual=supported.reader_paragraph_map(source);saved=json.loads((P/'evidence/ACTUAL-SUPPORTED-READER-PARAGRAPH-MAP.json').read_text());assert actual==saved and len(actual['paragraphs'])==21
mapping=json.loads((P/'evidence/21-SUPPORTED-READER-MEASURED-CANDIDATE.json').read_text());groups={u['source_char_start']:u for u in mapping['original29_measured_groups']};assert len(groups)==29
for paragraph,row in zip(actual['paragraphs'],mapping['paragraphs']):assert row['source_char_start']==paragraph['source_start'] and row['source_char_end']==paragraph['source_end'] and row['start_ms']==groups[paragraph['source_start']]['start_ms']
side=json.loads((P/'assets/chapter-001-full.timestamps.json').read_text());args=dict(slug='the-open-window',audio_sha256=D['master_mp3_sha256'],manuscript_sha256=D['manuscript_sha256'],duration_seconds=23588944/48000)
cues=builder._validated_cues(side,**args);assert len(cues)==21 and ' '.join(' '.join(x['text'] for x in cues).split())==' '.join(source.split())
negative_cases=0
for key,value in [('audio_hash','0'*64),('source_text_hash','0'*64),('auto_estimated_sync',True)]:
 bad=copy.deepcopy(side);bad[key]=value
 try:builder._validated_cues(bad,**args)
 except builder.PackageBuildError:negative_cases+=1
 else:raise AssertionError('Cue negative guard unexpectedly admitted')
clock=json.loads(Path(M['evidence']['actual_clock_transfer']['path']).read_text());assert clock['status']=='PASS_ACTUAL_FULL_DECODE_AND_MEASURED_WAVEFORM_CLOCK_TRANSFER' and clock['publication_mp3_sha256']==D['master_mp3_sha256'] and clock['exact_lossless_and_decoded_frame_count']==23588944 and clock['maximum_absolute_best_lag_seconds']==0 and clock['minimum_correlation']>.99
result={'schema':'earnalism.open_window_v5_local_proposed_packet_checks.v1','status':'PASS_LOCAL_EXACT_FACT_AND_GENERIC_STRUCTURE_CHECKS_NOT_TRUST_ADOPTION','exact_hash_references_verified':checked,'raw39_units_and_prior6_adjudications_unchanged':True,'twelve_new_name_changes_per_recognizer':12,'no_global_proper_name_alias':True,'all_metrics_recomputed':True,'all39_source_spans_once_in_order':True,'first_and_last_source_tokens_match_both_actual_derived_recognizers':True,'actual_supported_reader_paragraphs':21,'all21_starts_exact_inherited29_measured_groups':True,'generic_cue_count':21,'negative_identity_estimation_guards':negative_cases,'actual48window_clock_proof_bound':True,'owner_full_mix_ratings_unchanged':True,'remaining_known_material_wording_findings':[],'source_profile_implementation_and_trusted_registration':'PENDING','external_storage_runtime_customer_gates':'UNPERFORMED','no_provider_or_model_or_canonical_or_active_budget_calls':True}
f=P/'LOCAL-PACKET-QUALITY-CHECKS.json';f.open('x').write(json.dumps(result,indent=2)+'\n');print(json.dumps({'report_sha256':sha(f),'status':result['status'],'references':checked,'positive21cues':True,'negativeguards':negative_cases,'no_current_trust_claim':True}))
