"""Exact one-file native evidence bridge; never claims full production playing.

Full source/listening QA is reused only through independently adopted exact
bytes. This narrow path additionally requires authenticated complete served
bytes/decode and new bounded runtime/accounting observations. The legacy
whole-segment validator is unchanged.
"""
from __future__ import annotations
import hashlib,json,math,re
try:
    from backend.native_audiobook_replacement import SLUG,DESCRIPTOR,AUDIO,digest,need,SHA
except ImportError:  # Script entry from the existing release manager.
    from native_audiobook_replacement import SLUG,DESCRIPTOR,AUDIO,digest,need,SHA
from native_scored_metadata import metadata_for_package

MODE='single_continuous_identical_native_asset.v1'
OWNER='ebb1fea766be347cb35526dba9e18b082fec5cf25fc3be3ed5bd0b920079973f'
CONTENT='663fe88e0667a2f0fcb7b652fa4de05dd788eb5e9c9e778d656592e051b445da'
REUSE='d5b645742e0e8a3341291a5526a53a82e08a37744b21ffa6b0c5cf764a3773cd'
PCM='e6043c9b4580d0a53b3619bf94a6aafa80e44530735b0d49f98dbed84b1d5e8b'
PACKETS='de42ed2665d057c35570814d681eff01939ae0ed0f69c05081ba45c4fd135fd6'
CUES='3c4d0f5d44e62416d0eb8d85d585788d08281d146ff740a1ecf321c4103da69e'
CONTROLS=('start','audible_narration_and_score','pause','resume','seek_middle','seek_end','ended','lease_renewal','native_cookie_auth','explicit_session_end','ordinary_predecessor_still_public')


def _proofs(blobs,hashes):
    need(isinstance(hashes,dict) and set(hashes)==set(blobs),'Exact native production proof identities required')
    result={}
    for role,value in blobs.items():
        need(isinstance(hashes[role],str) and SHA.fullmatch(hashes[role]) and hashlib.sha256(value).hexdigest()==hashes[role],'Native production proof hash changed')
        result[role]=json.loads(value);need(isinstance(result[role],dict),'Native production proof object required')
    return result


def validate(package,*,playback_bytes,business_bytes,accounting_bytes,expected_proof_hashes):
    need(metadata_for_package(package,DESCRIPTOR,'en') is not None,'Independent native adoption/sourceQA profile required')
    need(package['segment_count']==1 and package['release_descriptor_sha256']==DESCRIPTOR,'Single exact native successor required')
    chunk=package['tracks'][0]['chunks'][0];asset=chunk['assets']['audio'];version=package['package_version']
    need(asset['sha256']==AUDIO and asset['size_bytes']==13005786 and package['duration_ms']==541807,'Native continuous bytes changed')
    rows=_proofs({'playback':playback_bytes,'business':business_bytes,'accounting':accounting_bytes},expected_proof_hashes)
    p,b,a=(rows[k] for k in ('playback','business','accounting'))
    for proof in (p,b,a):
        need(proof.get('descriptor')==DESCRIPTOR and proof.get('packageVersion')==version,'Runtime proof belongs to another edition')
    need(p.get('schema_version')=='earnalism.native_continuous_runtime_acceptance.v1' and p.get('evidence_mode')==MODE
         and p.get('durationMs')==541807 and p.get('segmentId')==chunk['segment_id']
         and p.get('full_production_listen')=='UNPERFORMED'
         and p.get('continuous_full_duration_production_playback')=='UNPERFORMED','Native bounded/full listening truth must remain explicit')
    expected_reuse={'status':'REUSED_IDENTICAL_DECODED_AUDIO','owner_complete_listening_sha256':OWNER,
        'adjudicated_complete_content_sha256':CONTENT,'publication_container_audio_reuse_sha256':REUSE,
        'measured_paragraph_timestamps_sha256':CUES,'confidence':0.96,'paragraph_count':23,'estimated_sync':False}
    need(p.get('source_full_qa')==expected_reuse,'Exact complete source/listening/paragraph evidence reuse required')
    path=f'/api/reader/book/{SLUG}/audiobook/packages/{version}/segments/{chunk["segment_id"]}'
    served=p.get('full_authenticated_asset_read') or {}
    need(served.get('http_status') in (200,206) and served.get('method')=='GET' and served.get('path')==path
         and served.get('package_version')==version and served.get('object_version_id')==asset['storage']['version_id']
         and served.get('received_bytes')==asset['size_bytes'] and served.get('sha256')==AUDIO
         and served.get('authenticated_exact_member_lease') is True and served.get('complete_body_read') is True
         and served.get('request_country')=='IN' and served.get('signed_proxy_verified') is True,'Complete authenticated exact served-body proof required')
    if served['http_status']==206:need(served.get('content_range')=='bytes 0-13005785/13005786','Partial Range is not a complete served-body proof')
    decoded=p.get('served_body_decode') or {}
    need(decoded=={'input_sha256':AUDIO,'full_decode_completed':True,'sample_format':'f32le','sample_rate':48000,
        'channels':2,'frame_count':26006746,'pcm_sha256':PCM,'elementary_mp3_packets_sha256':PACKETS,'decode_error_count':0},'Actual full served-byte decode/frame/PCM/packet proof required')
    scope=p.get('private_scope') or {}
    need(all(isinstance(scope.get(k),str) and SHA.fullmatch(scope[k]) for k in ('account_sha256','session_sha256','authorization_sha256','usage_lineage_sha256'))
         and scope.get('release_country')=='IN' and scope.get('package_version')==version and scope.get('descriptor')==DESCRIPTOR
         and scope.get('only_authorized_account_selected') is True
         and scope.get('guest_other_member_stale_grant_wrong_version_denied') is True,'Actual private identity/expiry/package/IN negative proof required')
    for other in (served,b,a):
        need(other.get('account_sha256')==scope['account_sha256'] and other.get('session_sha256')==scope['session_sha256'], 'Runtime proofs belong to different member/session')
    begin,end=p.get('observation_start_utc_ms'),p.get('observation_end_utc_ms')
    created,expiry=scope.get('grant_created_utc_ms'),scope.get('grant_expires_utc_ms')
    need(all(type(v) is int for v in (begin,end,created,expiry)) and created<=begin<end<=expiry
         and 0<expiry-created<=900000,'Actual private grant/observation expiry binding required')
    need(type(served.get('started_utc_ms')) is int and type(served.get('completed_utc_ms')) is int
         and begin<=served['started_utc_ms']<served['completed_utc_ms']<=end,'Authenticated full read occurred outside bounded authority')
    events=p.get('controls')
    need(isinstance(events,list) and len(events)==len(CONTROLS) and {e.get('case') for e in events}==set(CONTROLS)
         and all(e.get('observed') is True and type(e.get('monotonic_ms')) is int and 0<=e['monotonic_ms']<=end-begin for e in events)
         and [e['monotonic_ms'] for e in events]==sorted(e['monotonic_ms'] for e in events),'Genuine bounded browser controls/events required')
    event_times={row['case']:row['monotonic_ms'] for row in events}
    points=p.get('position_observations') or {}
    need(set(points)=={'start','middle','end'},'Actual start/middle/end observations required')
    for key,lo,hi in [('start',0,5000),('middle',216722,325085),('end',514716,541808)]:
        row=points[key];need(type(row.get('media_position_ms')) is int and lo<=row['media_position_ms']<hi
            and row.get('playing_observed') is True and row.get('narration_and_music_intelligible') is True
            and row.get('chapter_navigation_correct') is True,'Bounded start/middle/end/music/navigation observation missing')
    intervals=p.get('measured_playing_intervals');need(isinstance(intervals,list) and intervals,'Actual measured playing intervals required')
    total=0;last_end=-1;rates=set()
    for row in intervals:
        start,end=row.get('start_monotonic_ms'),row.get('end_monotonic_ms');rate=row.get('playback_rate')
        need(type(start) is int and type(end) is int and last_end<=start<end and rate in (1,1.25,1.5) and end<=p['observation_end_utc_ms']-p['observation_start_utc_ms'],'Playing intervals overlap/unmeasured/invalid')
        need(type(row.get('media_start_ms')) is int and type(row.get('media_end_ms')) is int
             and 0<=row['media_start_ms']<row['media_end_ms']<=541808,'Actual playing media boundaries required')
        expected=(end-start)*rate
        need(abs((row['media_end_ms']-row['media_start_ms'])-expected)<=max(300,expected*0.1),'Seek/duration cannot masquerade as measured playing')
        total+=end-start;last_end=end;rates.add(rate)
    for key,row in points.items():
        observed=row.get('monotonic_ms')
        need(type(observed) is int and any(interval['start_monotonic_ms']<=observed<=interval['end_monotonic_ms']
            and abs(row['media_position_ms']-(interval['media_start_ms']+(observed-interval['start_monotonic_ms'])*interval['playback_rate']))<=300 for interval in intervals),
            'Observed media position must match measured playing time/rate within300ms, never just fall in the same segment')
    need(event_times['start']<=intervals[0]['start_monotonic_ms']
         and event_times['ended']>=intervals[-1]['end_monotonic_ms']
         and event_times['explicit_session_end']>=event_times['ended']
         and event_times['pause']<=event_times['resume']
         and event_times['seek_middle']<=points['middle']['monotonic_ms']
         and event_times['seek_end']<=points['end']['monotonic_ms']
         and all(not (interval['start_monotonic_ms']<event_times['resume'] and interval['end_monotonic_ms']>event_times['pause']) for interval in intervals),
         'Measured playing/events conflict with pause, seeks, ending or session settlement')
    need(p.get('actual_played_wall_ms')==total and 0<total<120000 and rates=={1,1.25,1.5},'Bounded actual playing total/rates invalid')
    requests=p.get('requests') or []
    need(any(r.get('path')==path and r.get('http')==206 and r.get('package_version')==version and r.get('object_version_id')==asset['storage']['version_id'] for r in requests)
         and any(r.get('path')==path+'/timestamps' and r.get('http')==200 and r.get('sha256')==chunk['assets']['timestamps']['sha256'] for r in requests),'New exact Range and measured-sidecar responses required')
    credit=p.get('credit_settlement') or {}
    need(credit.get('original_ceiling_seconds')==120 and credit.get('all_prior_sessions_terminal') is True
         and credit.get('fractional_lineage_reconciled_or_conservatively_reserved') is True
         and credit.get('usage_lineage_sha256')==scope['usage_lineage_sha256']
         and credit.get('existing_open_window_600_lineage_unchanged') is True
         and type(credit.get('inherited_reserved_seconds')) is int and 51<=credit['inherited_reserved_seconds']<120
         and type(credit.get('cumulative_before_seconds')) is int and credit['inherited_reserved_seconds']<=credit['cumulative_before_seconds']<120
         and type(credit.get('actual_debited_seconds')) is int and 0<credit['actual_debited_seconds']<=math.ceil(total/1000)+1
         and credit.get('cumulative_after_seconds')==credit['cumulative_before_seconds']+credit['actual_debited_seconds']<=120
         and total<=1000*(120-credit['cumulative_before_seconds'])
         and credit.get('current_session_terminal') is True,'Reconciled original cumulative authority/server settlement required')
    billing=p.get('server_billing_intervals')
    alignment=p.get('server_client_clock_alignment') or {}
    need(isinstance(billing,list) and billing and type(alignment.get('maximum_error_microseconds')) is int
         and 0<=alignment['maximum_error_microseconds']<=250000
         and isinstance(alignment.get('measurement_sha256'),str) and SHA.fullmatch(alignment['measurement_sha256']),
         'Measured server/client clock alignment and numeric server intervals required')
    error=alignment['maximum_error_microseconds'];seen=set();billable_total=0;debit_total=0
    carry=credit.get('carry_before_microseconds')
    need(type(carry) is int and 0<=carry<1000000,'Actual account fractional carry before session required')
    for row in billing:
        values=[row.get(k) for k in ('last_billed_utc_us','server_now_utc_us','lease_expires_utc_us','billable_microseconds','debit_seconds','carry_before_microseconds','carry_after_microseconds')]
        need(all(type(v) is int for v in values) and row.get('billing_active') in (True,False)
             and type(row.get('billing_active')) is bool
             and isinstance(row.get('server_transition_sha256'),str) and SHA.fullmatch(row['server_transition_sha256']),
             'Actual numeric server transition/carry fields required')
        start,now,expiry,micros,debit,before,after=values
        stop=min(now,expiry);expected=min(max(0,stop-start),20000000) if row['billing_active'] else 0
        need(micros==expected and debit>=0 and before==carry and 0<=after<1000000
             and debit*1000000+after==before+micros,'Server-clock debit and global fractional carry do not conserve usage')
        index=row.get('playing_interval_index')
        if row['billing_active']:
            need(type(index) is int and 0<=index<len(intervals) and index not in seen,'Server interval must map once to actual measured playing')
            interval=intervals[index];seen.add(index)
            need(abs(start-(p['observation_start_utc_ms']*1000+interval['start_monotonic_ms']*1000))<=error
                 and abs(stop-(p['observation_start_utc_ms']*1000+interval['end_monotonic_ms']*1000))<=error,
                 'Numeric server interval does not match the measured active wall interval')
        else:need(index is None and micros==0 and debit==0 and after==before,'Paused/nonplaying interval cannot create usage')
        billable_total+=micros;debit_total+=debit;carry=after
    need(seen==set(range(len(intervals))) and credit.get('server_billable_microseconds')==billable_total
         and credit.get('carry_after_microseconds')==carry and credit['actual_debited_seconds']==debit_total
         and b.get('server_billable_microseconds')==a.get('server_billable_microseconds')==billable_total
         and b.get('carry_before_microseconds')==a.get('carry_before_microseconds')==credit['carry_before_microseconds']
         and b.get('carry_after_microseconds')==a.get('carry_after_microseconds')==carry
         and type(b.get('wallet_before_seconds')) is int and type(b.get('wallet_after_seconds')) is int
         and b['wallet_before_seconds']>=debit_total and b['wallet_after_seconds']>=0
         and b['wallet_before_seconds']-b['wallet_after_seconds']==debit_total
         and b.get('wallet_ledger_debit_seconds')==a.get('wallet_ledger_debit_seconds')==debit_total,
         'Numeric interval, fractional carry, wallet, ledger and cumulative settlement must agree exactly')
    # Existing business/accounting requirements remain, with new exact package
    # and account/session/source/deployed bindings above and below.
    need(b.get('status')=='PRODUCTION_SPEED_CONCURRENCY_AND_SERVER_BILLING_PASS'
        and b.get('speedsObserved')==[1,1.25,1.5]
        and b.get('secondClientStart')=={'http':409,'code':'SESSION_ACTIVE_ELSEWHERE'}
        and all(b.get(k) is True for k in ('allServerClockIntervalsMatch','pausedIntervalsDebitZero','nonPlayingPriorIntervalsDebitZero','balanceDifferenceMatchesDebit','ended'))
        and b.get('endHTTP')==200 and b.get('simultaneousPaidPlayback') is False
        and b.get('actual_debited_seconds')==credit['actual_debited_seconds'],'New production speed/conflict/billing proof required')
    commit=a.get('sourceCommit')
    need(a.get('status')=='DEPLOYED_ACCOUNTING_AND_AUTHENTICATED_USAGE_VERIFIED'
         and a.get('fractionalRenewalRegressionPass') is True and a.get('authenticatedUsagePaginationPass') is True
         and isinstance(commit,str) and re.fullmatch(r'[a-f0-9]{40}',commit) and a.get('deployedCommit')==commit
         and p.get('sourceCommit')==p.get('deployedCommit')==commit and b.get('sourceCommit')==b.get('deployedCommit')==commit
         and isinstance(a.get('runtime_manifest_sha256'),str) and SHA.fullmatch(a['runtime_manifest_sha256'])
         and p.get('runtime_manifest_sha256')==b.get('runtime_manifest_sha256')==a['runtime_manifest_sha256']
         and a.get('actual_debited_seconds')==credit['actual_debited_seconds'],'Exact deployed accounting/source/runtime/usage proof required')
    return {'schema_version':'audiobook_public_package_acceptance.v1','release_descriptor_sha256':DESCRIPTOR,
        'package_version':version,'duration_ms':541807,'segment_count':1,'production_proof_sha256':dict(expected_proof_hashes),
        'accounting_commit':commit,'public_activation_performed':False,'evidence_mode':MODE,
        'source_full_qa':expected_reuse,'full_production_listen':'UNPERFORMED',
        'continuous_full_duration_production_playback':'UNPERFORMED','actual_played_wall_ms':total,
        'actual_debited_seconds':credit['actual_debited_seconds'],'full_served_asset_integrity':'COMPLETE_AUTHENTICATED_BODY_AND_DECODE_VERIFIED',
        'runtime_bounded_playback':'VERIFIED_ONLY_OBSERVED_CASES'}
