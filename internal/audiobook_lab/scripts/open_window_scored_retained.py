"""Exact reviewed retained Ryan scored successor, SOURCE_QA only.

The immutable submitted descriptor remains e412 (including its historical proposal
labels). A separately committed adoption resolves its two source-registration
holds; it never clears the four storage/runtime holds or grants public release.
Raw recognition and scoped owner adjudication remain separate measurements.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

import owner_produced_package as common
import native_scored_package as media
import audiobook_package_builder_v2 as builder
from audiobook_packages import validate_audiobook_package
from rights_decision_gate import evaluate_accepted_record, load_production_registry, load_audio_package_binding, record_sha256

POLICY = 'open_window_scored_retained_successor.v1'
DATA = Path(__file__).resolve().parents[1] / 'release_gate/open-window-scored-20261102'
REGISTRY = Path(__file__).resolve().parents[1] / 'release_gate/open_window_scored_adoptions.json'
DESCRIPTOR_SHA = 'e41267aae8dca016c76c38f1e7123493eee0f94fe70651ced2211428494a6219'
FINAL_MANIFEST_SHA = '89b0623e0e94289b1f615b1fb6c072644799346aa47cbc7c92965c9fd41989df'
OWNER_SHA = 'fe85c11059c4f7a3154226bab97ad5e2ddc2485de64916d9980c8b2dadd91d1a'
NAMES_SHA = 'e359a75515950401b14c8c1f0733b8d00c2fc1d49dd4d71f4e0ff2fdec28858e'
SOURCE = {'slug': 'the-open-window', 'controlled_source_sha256': '058d0cda5a3c8449cbce06e0698048251881be4c6fc8d06fd0bc3a1bb8ec8587', 'manuscript_sha256': 'f43d04cc2097668e91190ada89e283ad4908c360c4d7f6011a44b8f83d9659be', 'master_wav_sha256': 'f2b80840b9797819934282f20f2f139b3cda33aef8f05825378cbb499eae4167', 'master_mp3_sha256': '32827f8c28b9815b0fccf50ec8486e23e563dfb952c00920610e6c8e8c5730a9'}
LISTENED_SHA = 'f9c9e103003b1a71e68ab2f293f48f0ba2c3c3d5854a28dc55a664592414ea3f'
GENERATION = {'provider': 'owner_retained_qwen', 'voice': 'Ryan', 'model': 'Qwen3-TTS-12Hz-1.7B-CustomVoice', 'model_revision': '0c0e3051f131929182e2c023b9537f8b1c68adfe', 'new_synthesis_or_allocations': 0}
SYNC = 'PARAGRAPH_OR_SECTION_SYNC_PREMIUM'
FRAMES, DURATION, WORDS, PARAGRAPHS = 23588944, 491436, 1208, 21
SIX = {'u000002': [('igt', 'aunt')], 'u000010': [('merried', 'married')], 'u000017': [('dust', 'dusk')], 'u000031': [('with the look', 'with a look')], 'u000034': [('our manton', 'framton')], 'u000035': [('bear', 'bearer')]}
ALIASES = {'mr': 'mister', 'mrs': 'missus', 'endeavoured': 'endeavored', 'favourite': 'favorite', 'laboured': 'labored'}
class Error(ValueError): pass

def require(ok, message):
    if not ok: raise Error(message)

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def sha(raw): return hashlib.sha256(raw).hexdigest()
def tokens(text): return re.findall(r"[a-z]+(?:'[a-z]+)*", text.lower().replace('’', "'"))
def load(path): return json.loads(Path(path).read_text())

def edit_distance(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        new = [i]
        for j, y in enumerate(b, 1): new.append(min(new[-1] + 1, row[j] + 1, row[j-1] + (x != y)))
        row = new
    return row[-1]

def ordered_matches(a, b):
    """Exact ordered lexical coverage; source-plan custody is a different fact."""
    row = [0] * (len(b) + 1)
    for x in a:
        new = [0]
        for j, y in enumerate(b, 1): new.append(row[j-1] + 1 if x == y else max(row[j], new[-1]))
        row = new
    return row[-1]

def replace_once(seq, before, after):
    positions = [i for i in range(len(seq)-len(before)+1) if seq[i:i+len(before)] == before]
    require(len(positions) == 1, 'Owner correction must identify exactly one scoped sequence')
    i = positions[0]
    return seq[:i] + after + seq[i+len(before):]

class Evidence:
    def __init__(self, expected_index_sha):
        raw = (DATA / 'evidence-index.json').read_bytes()
        require(sha(raw) == expected_index_sha, 'Reviewed evidence index changed')
        self.index = json.loads(raw)
        self.by_sha = {}
        for name, ref in self.index['files'].items():
            path = (DATA / name).resolve()
            require(path.is_relative_to(DATA.resolve()) and path.is_file() and not path.is_symlink(), 'Evidence path escape')
            raw = path.read_bytes()
            require(sha(raw) == ref['sha256'] and len(raw) == ref['bytes'], 'Committed evidence bytes changed: ' + name)
            self.by_sha[ref['sha256']] = raw
    def raw(self, digest):
        require(digest in self.by_sha, 'Missing committed evidence reference')
        return self.by_sha[digest]
    def json(self, digest): return json.loads(self.raw(digest))
    def file(self, name): return load(DATA / 'frozen-v5' / name)

def load_adoption():
    registry = load(REGISTRY)
    require(registry.get('schema') == 'earnalism.open-window-scored-adoptions.v1', 'Scored adoption registry schema')
    entries = registry.get('adoptions', [])
    matches = [x for x in entries if x.get('record', {}).get('descriptor_sha256') == DESCRIPTOR_SHA]
    require(len(matches) == 1, 'Exactly one separately reviewed scored adoption required')
    entry = matches[0]; record = entry['record']
    require(sha(canonical(record)) == entry['record_sha256'], 'Scored adoption digest mismatch')
    require(record.get('status') == 'ADOPTED' and record.get('policy') == POLICY and record.get('identity') == SOURCE
            and record.get('scope') == 'SOURCE_QA_ONLY_STORAGE_AND_RUNTIME_PENDING'
            and record.get('adopted_by') and record.get('authority_reference')
            and record.get('remaining_material_wording_findings') == [] and record.get('all_release_gates_passed') is False,
            'Scored source adoption missing; proposed records cannot authorize')
    return record

def recognize(evidence, source):
    """Reconstruct actual retained recording ASR, then only 6 + 12 owner scopes."""
    report = evidence.file('evidence/ACTUAL-ASR-AND-SIX-OWNER-ADJUDICATIONS.json')
    require(report['normal_spoken_text_comparator']['aliases'] == ALIASES, 'No phonetic/global proper-name alias')
    names = evidence.json(NAMES_SHA)
    require(names['answer_verbatim'] == 'Framton heard in all twelve.' and names['source_final_mp3_sha256'] == SOURCE['master_mp3_sha256']
            and names['source_listened_full_mix_sha256'] == LISTENED_SHA, 'Exact twelve-window owner receipt')
    windows = {r['number']: r for r in names['reviewed_windows']}
    require(set(windows) == set(range(1,13)), 'All twelve exact windows required')
    repair = evidence.file('support/raw-ASR/FOCUSED_REPAIR_QA.json')
    cursor = 0; raw_ctc = []; six_ctc = []; scoped_ctc = []
    for index, unit in enumerate(report['units'], 1):
        require(unit['id'] == f'u{index:06}' and index <= 39, '39 authoritative ordered source units')
        start, end = unit['source_char_start'], unit['source_char_end']; text = source[start:end]
        require(not source[cursor:start].strip() and start >= cursor and end > start, 'Source gaps/duplicates/reordering')
        cursor = end
        raw = evidence.json(unit['raw_evidence']['sha256'])
        require(text.split() == raw['expected_text'].split() and sha(text.encode()) == unit['text_sha256']
                and sha(' '.join(text.split()).encode()) == unit['historical_text_sha256'], 'Raw Reader/source-unit binding')
        actual = tokens(raw['ctc_transcript'])
        if index == 24:
            actual = [t for w in raw['ctc_words'] if (w['start']+w['end'])/2 < 281.62 for t in tokens(w['word'])] + tokens(repair['ctc'])
        require(actual == unit['current_recording_CTC_projection_tokens'], 'Raw current CTC projection changed')
        shift = -183274 / 24000 if index > 24 else 0
        timed = [{'token': t, 'start': w['start']+shift, 'end': w['end']+shift} for w in raw['ctc_words'] for t in tokens(w['word'])]
        if index == 24:
            timed = [w for w in timed if (w['start']+w['end'])/2 < 281.62] + [{'token': t, 'start':281.62, 'end':285.86} for t in tokens(repair['ctc'])]
        require([w['token'] for w in timed] == actual, 'Actual retained CTC word clock/token projection')
        six = actual[:]
        expected_changes = SIX.get(unit['id'], [])
        require([(x['old'], x['new'], x['authority']) for x in unit['owner_changes']] == [(tokens(a), tokens(b), OWNER_SHA) for a,b in expected_changes], 'Only original six owner scopes allowed')
        for a,b in expected_changes: six = replace_once(six, tokens(a), tokens(b))
        require(six == unit['owner_six_adjudicated_tokens'], 'Six-source-word derivative changed')
        scoped = six[:]
        for change in sorted(unit['twelve_name_window_changes'], key=lambda x: x['recognized_token_span_before'][0], reverse=True):
            window = windows[change['reviewed_clip_number']]
            require(change['authority_sha256'] == NAMES_SHA and change['historical_unit'] == unit['id'] == window['historical_unit']
                    and change['reviewed_fullbook_seconds'] == [window['full_book_start_seconds'],window['full_book_end_seconds']]
                    and change['adjudicated_source_tokens'] == ['framton'], 'Name correction outside exact owner window')
            a,b = change['recognized_token_span_before']
            require(scoped[a:b] == change['recognized_tokens_before'], 'Name recognized span mismatch')
            require(all(window['full_book_start_seconds'] <= (w['start']+w['end'])/2 <= window['full_book_end_seconds'] for w in timed[a:b]), 'CTC name emission outside heard clip')
            scoped[a:b] = ['framton']
        require(scoped == unit['six_plus_twelve_scoped_adjudicated_tokens'], 'Name-scoped CTC derivative changed')
        raw_ctc += actual; six_ctc += six; scoped_ctc += scoped
    require(len(report['units']) == 39 and not source[cursor:].strip(), 'Complete authoritative source once')
    all_changes = [x for u in report['units'] for x in u['twelve_name_window_changes']]
    require(sorted(x['reviewed_clip_number'] for x in all_changes) == list(range(1,13)) and all_changes == report['twelve_CTC_scoped_changes'], 'Exactly twelve CTC changes')
    original = evidence.file('support/raw-ASR/FULL_MASTER_WHISPER.json')
    words = [w for s in original['result']['segments'] for w in s['words']]
    current = [dict(w) for w in words if w['end'] <= 281.62]
    current += [{**w, 'start': w['start']+281.62, 'end': w['end']+281.62} for s in repair['whisper']['segments'] for w in s['words']]
    delta = -183274 / 24000
    current += [{**w, 'start': w['start']+delta, 'end': w['end']+delta} for w in words if w['start'] >= 293.4964166666667]
    flattened = [{'token': t, 'start': w['start'], 'end': w['end']} for w in current for t in tokens(w['word'])]
    raw_whisper = [x['token'] for x in flattened]
    require(raw_whisper == report['full_current_Whisper_projection_tokens'], 'Full raw Whisper projection changed')
    def scoped_replace(before, after, bounds):
        nonlocal flattened
        positions = [i for i in range(len(flattened)-len(before)+1)
            if [w['token'] for w in flattened[i:i+len(before)]] == before
            and all(bounds[0] <= (w['start']+w['end'])/2 <= bounds[1] for w in flattened[i:i+len(before)])]
        require(len(positions) == 1, 'Whisper owner change must be unique inside exact heard interval')
        i=positions[0]; span=flattened[i:i+len(before)]
        flattened[i:i+len(before)] = [{'token':t,'start':span[0]['start'],'end':span[-1]['end']} for t in after]
    require(len(report['full_Whisper_owner_changes']) == 5, 'Actual five edits within six original groups')
    for change in report['full_Whisper_owner_changes']:
        require(change['authority_sha256'] == OWNER_SHA, 'Six group owner authority')
        scoped_replace(change['old'],change['new'],change['actual_recognized_span_seconds'])
    six_whisper = [w['token'] for w in flattened]
    require(six_whisper == report['six_owner_adjudicated_full_Whisper_tokens'], 'Six-group Whisper derivative changed')
    changes = report['twelve_Whisper_scoped_changes']
    require(sorted(x['reviewed_clip_number'] for x in changes) == list(range(1,13)), 'Exactly twelve Whisper name changes')
    for change in changes:
        window=windows[change['reviewed_clip_number']]; bounds=[window['full_book_start_seconds'],window['full_book_end_seconds']]
        require(change['authority_sha256'] == NAMES_SHA and change['historical_unit'] == window['historical_unit']
                and change['reviewed_fullbook_seconds'] == bounds and change['adjudicated_source_token'] == 'framton', 'Exact name window binding')
        scoped_replace([change['recognized_token_before']],['framton'],bounds)
    scoped_whisper = [w['token'] for w in flattened]
    require(scoped_ctc == report['six_plus_twelve_adjudicated_full_CTC_tokens'] and scoped_whisper == report['six_plus_twelve_adjudicated_full_Whisper_tokens'], 'Actual scoped lexical transcripts changed')
    reference=tokens(source); norm=lambda seq:[ALIASES.get(t,t) for t in seq]
    pairs={'literal_current_CTC':(reference,raw_ctc),'six_owner_adjudicated_CTC':(reference,six_ctc),'six_plus_twelve_scoped_current_CTC':(reference,scoped_ctc),'six_plus_twelve_CTC_standard_spoken_comparator':(norm(reference),norm(scoped_ctc)), 'literal_full_current_Whisper_projection':(reference,raw_whisper),'six_plus_twelve_scoped_full_Whisper':(reference,scoped_whisper),'six_plus_twelve_full_Whisper_standard_spoken_comparator':(norm(reference),norm(scoped_whisper))}
    for name,(a,b) in pairs.items():
        errors=edit_distance(a,b); q=report['aggregate_metrics'][name]
        require(q['reference_tokens']==len(a) and q['recognized_tokens']==len(b) and q['levenshtein_edits']==errors
                and abs(q['score_0_to_10']-10*(1-errors/len(a))) < 1e-12, 'ASR metric arithmetic mismatch')
    require(len(reference)==1219 and all(x[:5] == reference[:5] and x[-5:] == reference[-5:] for x in [raw_ctc,raw_whisper]), 'Literal raw first/last words')
    metrics = {}
    for name,seq in [('CTC',scoped_ctc),('Whisper',scoped_whisper)]:
        errors=edit_distance(reference,seq); matched=ordered_matches(reference,seq)
        require(errors == 26 and matched == 1195 and 10*(1-errors/1219) >= 9.7 and matched/1219 >= .98, 'Literal scoped ASR/ordered coverage below policy')
        metrics[name]={'raw_score':10*(1-edit_distance(reference,raw_ctc if name=='CTC' else raw_whisper)/1219), 'scoped_score':10*(1-errors/1219),'ordered_matches':matched,'reference_tokens':1219,'coverage':matched/1219}
    return metrics

def verify_evidence(adoption):
    policy=adoption['active_policy_provenance']
    require(policy['path']=='internal/earnalism_intelligence/platform_audiobook_acceptance_v4_89_policy_decision.json'
            and policy['sha256']=='561fb5c5bfbc0fe58d7706af141ee1ff603fb3e7c7fe7333a66fd27182666c55'
            and sha((common.ROOT/policy['path']).read_bytes())==policy['sha256'], 'Active all-language owner policy provenance')
    evidence=Evidence(adoption['evidence_index_sha256'])
    final=evidence.json(FINAL_MANIFEST_SHA)
    require(len(final['files'])==18, 'Exact frozen eighteen-reference handoff')
    for ref in final['files'].values():
        raw=evidence.raw(ref['sha256']); require(len(raw)==ref['bytes'], 'Frozen handoff reference size')
    manifest=evidence.file('MANIFEST.PROPOSED.json'); descriptor=evidence.file('release-descriptor.PROPOSED.json')
    require(sha(canonical(descriptor))==DESCRIPTOR_SHA and manifest['descriptor_canonical_sha256']==DESCRIPTOR_SHA, 'Frozen exact descriptor')
    require(len(manifest['evidence'])==32 and len(manifest['assets'])==4, 'Complete 36-reference source packet')
    for role,ref in manifest['evidence'].items():
        if role != 'actual_lossless_master': require(sha(evidence.raw(ref['sha256']))==descriptor['evidence_sha256'][role], 'Descriptor evidence changed')
        else: require(ref['sha256']==SOURCE['master_wav_sha256'], 'Exact lossless master binding')
    source=(DATA/'frozen-v5/manuscript.txt').read_text()
    current_chapter=common.ROOT/'backend/data/controlled_publications/the-open-window/chapters/chapter-001.json'
    require(sha(current_chapter.read_bytes())==descriptor['evidence_sha256']['reader_chapter'], 'Current authoritative Reader source changed')
    require(sha(source.encode())==SOURCE['manuscript_sha256'] and len(source.split())==WORDS, 'Authoritative complete manuscript')
    require(sha(common.READER_CONTENT.read_bytes())==descriptor['evidence_sha256']['reader_renderer'], 'Actual supported Reader renderer changed')
    reader=common.reader_paragraph_map(source)
    require(reader==evidence.file('evidence/ACTUAL-SUPPORTED-READER-PARAGRAPH-MAP.json') and len(reader['paragraphs'])==21, 'Actual 21 semantic Reader paragraphs required')
    timing=evidence.file('evidence/21-SUPPORTED-READER-MEASURED-CANDIDATE.json')
    require(timing['auto_estimated_sync'] is False and timing['word_highlighting'] is False and timing['audio_sha256']==SOURCE['master_mp3_sha256'], 'Measured-only paragraph timing')
    groups={x['source_char_start']:x for x in timing['original29_measured_groups']}
    require(len(groups)==29 and len(timing['paragraphs'])==21, 'Measured source groups distinct from Reader paragraphs')
    side=evidence.file('assets/chapter-001-full.timestamps.json')
    cues=builder._validated_cues(side,slug=SOURCE['slug'],audio_sha256=SOURCE['master_mp3_sha256'],manuscript_sha256=SOURCE['manuscript_sha256'],duration_seconds=FRAMES/48000)
    require(len(cues)==21 and ' '.join(' '.join(x['text'] for x in cues).split())==' '.join(source.split()), 'Full measured cue text/order')
    for i,(p,row) in enumerate(zip(reader['paragraphs'],timing['paragraphs'])):
        end=timing['paragraphs'][i+1]['start_ms'] if i<20 else DURATION
        require(row['source_char_start']==p['source_start'] and row['source_char_end']==p['source_end'] and row['start_ms']==groups[p['source_start']]['start_ms']
                and row['end_ms']==end and side['cues'][i]['start_ms']==row['start_ms'] and side['cues'][i]['end_ms']==end, 'Cue boundary must equal actual measured Reader group')
    owner=evidence.json(OWNER_SHA)
    require(owner['answer_verbatim']=='All three confirmed; no defects.' and owner['listened_mp3']['sha256']==LISTENED_SHA
            and owner['ratings_0_to_10']==adoption['human_scores'] and owner['confidence_0_to_1']==adoption['confidence']==.97
            and min(owner['ratings_0_to_10'].values())>=8.9 and len(owner['ratings_0_to_10'])==10, 'Genuine complete scored owner listening')
    clock=evidence.json(descriptor['evidence_sha256']['actual_clock_transfer'])
    require(clock['publication_mp3_sha256']==SOURCE['master_mp3_sha256'] and clock['lossless_scored_wav_sha256']==SOURCE['master_wav_sha256']
            and clock['exact_lossless_and_decoded_frame_count']==FRAMES and clock['sample_rate']==48000 and clock['channels']==2
            and len(clock['checks'])==clock['check_count']==48 and clock['minimum_correlation']>.99 and clock['maximum_absolute_best_lag_seconds']==0, 'Actual full-delivery measured clock transfer')
    require(min(x['correlation'] for x in clock['checks'])==clock['minimum_correlation'] and max(abs(x['best_lag_seconds']) for x in clock['checks'])==clock['maximum_absolute_best_lag_seconds']
            and all(0 <= x['window_start_frame'] < x['window_end_frame'] <= FRAMES and x['best_lag_at_3000Hz_samples']==0 for x in clock['checks']), 'Clock check arithmetic/frame ranges')
    proof=evidence.json(descriptor['evidence_sha256']['metadata_audio_reuse'])
    media.validate_container_reuse(proof,listened=LISTENED_SHA,published=SOURCE['master_mp3_sha256'],frames=FRAMES)
    require(clock['canonical_decoded_mp3_f32le_sha256']==proof['items']['delivery']['canonical_decoded_PCM']['sha256']
            and {r['start_sample']*2 for r in groups.values()}.issubset({r['source_frame'] for r in clock['checks']}), 'Full clock proof must cover all actual 29 measured source starts')
    metrics=recognize(evidence,source)
    require(metrics==adoption['recognition_metrics'], 'No custody1.0 or invented raw/derived metrics')
    return evidence,descriptor,metrics

def validate(descriptor,package,controlled_language,downstream_gates):
    try:
        require(controlled_language.lower() in ('en','eng','english') and sha(canonical(descriptor))==DESCRIPTOR_SHA, 'Exact English scored retained descriptor required')
        require(descriptor.get('generation')==GENERATION and all(descriptor.get(k)==v for k,v in SOURCE.items()), 'No old dry/Cedar/model substitution')
        require(downstream_gates==common.DOWNSTREAM and descriptor.get('known_release_blockers',[])[-4:]==common.DOWNSTREAM
                and descriptor.get('publication_approved') is False and descriptor['release_candidate_evidence']['all_release_gates_passed'] is False, 'Source QA never grants release')
        adoption=load_adoption(); evidence, submitted, _=verify_evidence(adoption)
        require(descriptor==submitted, 'Immutable submitted descriptor')
        common.validate_topology(package,expected_sync_tier=SYNC)
        require(package.get('slug')==SOURCE['slug'] and package.get('source_sha256')==SOURCE['controlled_source_sha256'] and package.get('manuscript_sha256')==SOURCE['manuscript_sha256']
                and package.get('release_descriptor_sha256')==DESCRIPTOR_SHA and package.get('release_evidence_version')==POLICY
                and [package.get(k) for k in ('duration_ms','segment_count','word_count','paragraph_count')]==[DURATION,1,WORDS,PARAGRAPHS]
                and common.mapping(package)==descriptor['chunk_mapping_sha256'], 'Exact whole-book scored delivery topology')
        if 'package_version' in package:
            validate_audiobook_package(package,expected_slug=SOURCE['slug'],expected_source_sha256=SOURCE['controlled_source_sha256'],expected_manuscript_sha256=SOURCE['manuscript_sha256'],expected_release_descriptor_sha256=DESCRIPTOR_SHA)
        rights=adoption['audio_use_decision']; accepted,revoked=load_production_registry()
        components={'source_file':SOURCE['controlled_source_sha256'],'selected_manuscript':SOURCE['manuscript_sha256'],'master_wav':SOURCE['master_wav_sha256'],'master_mp3':SOURCE['master_mp3_sha256'],'audio_component_bindings':descriptor['chunk_mapping_sha256'],'listened_master_mp3':LISTENED_SHA,'music_rights':descriptor['evidence_sha256']['music_binding'],'model_voice_licence':descriptor['evidence_sha256']['open-window-rights-specific-resolution.json'],'container_metadata_reuse':descriptor['evidence_sha256']['metadata_audio_reuse'],'source_qa_descriptor':DESCRIPTOR_SHA}
        verdict=evaluate_accepted_record(rights,edition_id=SOURCE['slug'],operator_id='reo-enterprise',country='IN',country_trusted=True,use='audio_stream',required_components=components,accepted_records=accepted,revoked_decision_ids=revoked,now=datetime.now(timezone.utc))
        binding=load_audio_package_binding(SOURCE['slug'],DESCRIPTOR_SHA)
        require(verdict.passed and rights['territories']==['IN'] and rights['uses']==['audio_stream'] and binding is not None
                and binding['decision_id']==rights['decision_id'] and binding['record_sha256']==record_sha256(rights), 'Exact committed IN audio-use trust/binding required')
        return copy.deepcopy(descriptor)
    except Error:
        raise
    except (KeyError,TypeError,AttributeError,OSError,ValueError) as exc:
        raise Error('Incomplete scored retained source evidence: '+str(exc)) from None

def validate_publication_tags(info):
    tags=info.get('format',{}).get('tags',{}); text=' '.join(str(v) for v in tags.values())
    require(tags.get('title')=='The Open Window' and tags.get('author')=='Saki'
            and tags.get('artist')=='Earnalism; AI narration: stock Ryan (Qwen3-TTS CustomVoice)', 'Correct public title/author/narrator tags')
    require(all(s in text for s in ['Ryan','Qwen3-TTS','Heartwarming','Heartbreaking','Kevin MacLeod','https://creativecommons.org/licenses/by/4.0/']), 'Public AI and exact music credits required')
    require(not re.search(r'\b(private|draft|pending|review|proposed)\b|/Users/|/private/|/tmp/|[A-Z]:\\|X-Amz-|[?&](?:token|signature|credential)=',text,re.I), 'Private/draft/path/credential metadata forbidden')
    require(all(s.get('tags',{}) in ({},{'encoder':'Lavf'}) for s in info.get('streams',[])), 'Unexpected audio-stream metadata')
    return tags

def publication_tags(path):
    result=subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-f','mp3','-show_entries','format_tags:stream_tags','-of','json',str(path)],capture_output=True,text=True,timeout=20,check=True)
    return validate_publication_tags(json.loads(result.stdout))

def prepare(bundle_path,output_dir):
    """Read exact frozen local media once; emit only local standard package inputs."""
    bundle=load(bundle_path)
    require(bundle.get('schema')=='earnalism.open-window-scored-local-package.v1', 'Scored bundle schema')
    out=Path(output_dir); require(not out.exists(),'Output exists; preserve completed preparation')
    adoption=load_adoption(); evidence,descriptor,_=verify_evidence(adoption)
    package=evidence.file('package-identity.PROPOSED.json')
    package.pop('package_version'); package.pop('proposal_status')
    validate(descriptor,package,'en',common.DOWNSTREAM)
    def exact_file(role,expected):
        p=Path(bundle[role]).resolve(); require(p.is_file() and not p.is_symlink(),'Actual media missing')
        require(sha(p.read_bytes())==expected,'Actual local media bytes changed: '+role); return p
    wav=exact_file('master_wav',SOURCE['master_wav_sha256']); facts=media.wav_identity(wav.read_bytes())
    require(facts['frames']==FRAMES,'Actual lossless frame truth')
    listened=exact_file('listened_master_mp3',LISTENED_SHA); delivery=exact_file('master_mp3',SOURCE['master_mp3_sha256'])
    publication_tags(delivery)
    prior=media.decoded_pcm_identity(listened); current=media.decoded_pcm_identity(delivery)
    proof=evidence.json(descriptor['evidence_sha256']['metadata_audio_reuse'])
    require(prior==current and prior['frames']==FRAMES and prior['sha256']==proof['items']['delivery']['canonical_decoded_PCM']['sha256']
            and prior['packet_sha256']==proof['items']['delivery']['elementary_encoded_audio_packets']['sha256']
            and prior['packet_bytes']==proof['items']['delivery']['elementary_encoded_audio_packets']['bytes'], 'Actual unchanged listened PCM/packets required')
    plan=evidence.file('upload-plan.PROPOSED-NOT-AUTHORIZED.json')
    for row in plan['assets']:
        role=row['asset_id'].rsplit('-',1)[-1]
        p=delivery if role=='audio' else DATA/'frozen-v5/assets'/Path(row['local_path']).name
        raw=p.read_bytes(); require(sha(raw)==row['sha256'] and len(raw)==row['size_bytes'],'Actual delivery asset bytes')
        row['local_path']=str(p)
    require(sum(x['size_bytes'] for x in plan['assets'])==11824717,'Exact four-asset transfer bytes')
    tracks=[]
    for track in package['tracks']:
        chunks=[{**{k:v for k,v in ch.items() if k!='assets'},'asset_ids':{r:ch['segment_id']+'-'+r for r in ch['assets']}} for ch in track['chunks']]
        tracks.append({**{k:v for k,v in track.items() if k!='chunks'},'chunks':chunks})
    semantics={k:v for k,v in package.items() if k not in ('tracks','schema_version')}
    semantics.update(schema_version='audiobook_package_semantics.v2',package_schema_version='audiobook_package_manifest.v2',tracks=tracks)
    out=Path(output_dir); require(not out.exists(),'Output exists; preserve completed preparation')
    out.mkdir(parents=True)
    for name,value in [('release-descriptor.json',descriptor),('package-semantics.json',semantics),('upload-plan.json',plan)]:
        with (out/name).open('x') as f: json.dump(value,f,ensure_ascii=False,indent=2)
    return {'status':'LOCAL_RETAINED_SCORED_SOURCE_QA_PREPARED_STORAGE_PENDING','descriptor_sha256':DESCRIPTOR_SHA,'asset_bytes_per_store':11824717,'output_dir':str(out),'uploads':False,'public_release_approved':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--bundle',required=True); parser.add_argument('--output-dir',required=True); args=parser.parse_args()
    try: print(json.dumps(prepare(args.bundle,args.output_dir),sort_keys=True))
    except (Error,ValueError,OSError,subprocess.SubprocessError) as exc: parser.exit(2,str(exc)+'\n')
if __name__=='__main__': main()
