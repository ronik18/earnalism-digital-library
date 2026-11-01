"""Typed evidence admission with SYNTHETIC runtime values only; no production PASS."""
import copy,json,hashlib
import pytest
import native_continuous_acceptance as gate
import native_audiobook_replacement as native
import test_native_replacement_release as source_fixtures
import test_new_title_publication_acceptance as generic_fixtures


def runtime_documents(package):
    chunk=package['tracks'][0]['chunks'][0];asset=chunk['assets']['audio'];version=package['package_version']
    path=f'/api/reader/book/{native.SLUG}/audiobook/packages/{version}/segments/{chunk["segment_id"]}'
    scope=dict(account_sha256='1'*64,session_sha256='2'*64,authorization_sha256='3'*64,usage_lineage_sha256='4'*64,
        release_country='IN',package_version=version,descriptor=native.DESCRIPTOR,only_authorized_account_selected=True,
        guest_other_member_stale_grant_wrong_version_denied=True,grant_created_utc_ms=1790000000000,grant_expires_utc_ms=1790000600000)
    common=dict(descriptor=native.DESCRIPTOR,packageVersion=version,sourceCommit='c'*40,deployedCommit='c'*40,
        runtime_manifest_sha256='5'*64,account_sha256=scope['account_sha256'],session_sha256=scope['session_sha256'])
    generic=generic_fixtures.AcceptanceTests();generic.setUp()
    business={**generic.business,**common,'actual_debited_seconds':3,'server_billable_microseconds':3000000,'carry_before_microseconds':250000,'carry_after_microseconds':250000,'wallet_ledger_debit_seconds':3}
    business.update(wallet_before_seconds=300,wallet_after_seconds=297)
    accounting={**generic.accounting,**common,'actual_debited_seconds':3,'server_billable_microseconds':3000000,'carry_before_microseconds':250000,'carry_after_microseconds':250000,'wallet_ledger_debit_seconds':3}
    intervals=[dict(start_monotonic_ms=0,end_monotonic_ms=1000,playback_rate=1,media_start_ms=0,media_end_ms=1000),
        dict(start_monotonic_ms=2000,end_monotonic_ms=3000,playback_rate=1.25,media_start_ms=270000,media_end_ms=271250),
        dict(start_monotonic_ms=4000,end_monotonic_ms=5000,playback_rate=1.5,media_start_ms=540307,media_end_ms=541807)]
    playback={**common,'schema_version':'earnalism.native_continuous_runtime_acceptance.v1','evidence_mode':gate.MODE,
        'observation_start_utc_ms':1790000001000,'observation_end_utc_ms':1790000007000,'durationMs':541807,'segmentId':chunk['segment_id'],'full_production_listen':'UNPERFORMED',
        'continuous_full_duration_production_playback':'UNPERFORMED','source_full_qa':dict(status='REUSED_IDENTICAL_DECODED_AUDIO',
            owner_complete_listening_sha256=gate.OWNER,adjudicated_complete_content_sha256=gate.CONTENT,
            publication_container_audio_reuse_sha256=gate.REUSE,measured_paragraph_timestamps_sha256=gate.CUES,
            confidence=0.96,paragraph_count=23,estimated_sync=False),
        'full_authenticated_asset_read':dict(http_status=200,method='GET',path=path,package_version=version,
            object_version_id=asset['storage']['version_id'],received_bytes=13005786,sha256=native.AUDIO,
            authenticated_exact_member_lease=True,complete_body_read=True,request_country='IN',signed_proxy_verified=True,
            account_sha256=scope['account_sha256'],session_sha256=scope['session_sha256'],started_utc_ms=1790000001100,completed_utc_ms=1790000001900),
        'served_body_decode':dict(input_sha256=native.AUDIO,full_decode_completed=True,sample_format='f32le',sample_rate=48000,
            channels=2,frame_count=26006746,pcm_sha256=gate.PCM,elementary_mp3_packets_sha256=gate.PACKETS,decode_error_count=0),
        'private_scope':scope,'controls':[dict(case=k,observed=True,monotonic_ms=ms) for k,ms in [('native_cookie_auth',0),('ordinary_predecessor_still_public',0),('start',0),('audible_narration_and_score',500),('pause',1000),('lease_renewal',1500),('resume',2000),('seek_middle',2000),('seek_end',4000),('ended',5000),('explicit_session_end',5500)]],
        'position_observations':{k:dict(media_position_ms=pos,playing_observed=True,narration_and_music_intelligible=True,chapter_navigation_correct=True,monotonic_ms=ms)
            for k,pos,ms in [('start',0,0),('middle',270000,2000),('end',541000,4500)]},
        'measured_playing_intervals':intervals,'actual_played_wall_ms':3000,
        'requests':[dict(path=path,http=206,package_version=version,object_version_id=asset['storage']['version_id']),
            dict(path=path+'/timestamps',http=200,sha256=chunk['assets']['timestamps']['sha256'])],
        'credit_settlement':dict(original_ceiling_seconds=120,all_prior_sessions_terminal=True,fractional_lineage_reconciled_or_conservatively_reserved=True,
            usage_lineage_sha256=scope['usage_lineage_sha256'],existing_open_window_600_lineage_unchanged=True,inherited_reserved_seconds=60,
            cumulative_before_seconds=60,actual_debited_seconds=3,cumulative_after_seconds=63,current_session_terminal=True,carry_before_microseconds=250000,carry_after_microseconds=250000,server_billable_microseconds=3000000)}
    playback['server_client_clock_alignment']={'maximum_error_microseconds':1000,'measurement_sha256':'6'*64}
    playback['server_billing_intervals']=[dict(last_billed_utc_us=1790000001000000+row['start_monotonic_ms']*1000,
        server_now_utc_us=1790000001000000+row['end_monotonic_ms']*1000,lease_expires_utc_us=1790000021000000,
        billable_microseconds=1000000,debit_seconds=1,carry_before_microseconds=250000,carry_after_microseconds=250000,
        billing_active=True,playing_interval_index=i,server_transition_sha256=str(i+7)*64) for i,row in enumerate(intervals)]
    return playback,business,accounting


def arguments(package,documents=None):
    docs=documents or runtime_documents(package);blobs={k:json.dumps(v).encode() for k,v in zip(('playback','business','accounting'),docs)}
    return {**{k+'_bytes':v for k,v in blobs.items()},'expected_proof_hashes':{k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()}}


def test_exact_typed_fixture_admits_without_inventing_full_production_playing():
    package,_=source_fixtures.finalized_package();got=gate.validate(package,**arguments(package))
    assert got['actual_played_wall_ms']==3000 and got['full_production_listen']=='UNPERFORMED'
    assert got['continuous_full_duration_production_playback']=='UNPERFORMED'
    assert got['source_full_qa']['status']=='REUSED_IDENTICAL_DECODED_AUDIO'
    assert 'coverage' not in got and got['public_activation_performed'] is False


@pytest.mark.parametrize('mutation',['old-container-size','missing-full-read','wrong-body-hash','wrong-pcm','missing-owner-review',
    'fake-full-playing','seek-as-playing','over-original-cap','old-deployment','wrong-object-version','no-music-observation','wrong-account','playing-after-ended','playing-during-pause','consistent-undebit','inexact-position-at-time'])
def test_each_material_native_bridge_gap_fails_closed(mutation):
    package,_=source_fixtures.finalized_package();p,b,a=runtime_documents(package)
    if mutation=='old-container-size':p['full_authenticated_asset_read']['received_bytes']=13006625
    elif mutation=='missing-full-read':p['full_authenticated_asset_read']['complete_body_read']=False
    elif mutation=='wrong-body-hash':p['full_authenticated_asset_read']['sha256']='f'*64
    elif mutation=='wrong-pcm':p['served_body_decode']['pcm_sha256']='f'*64
    elif mutation=='missing-owner-review':p['source_full_qa']['owner_complete_listening_sha256']='f'*64
    elif mutation=='fake-full-playing':p['continuous_full_duration_production_playback']='PASS'
    elif mutation=='seek-as-playing':p['measured_playing_intervals'][0]['media_end_ms']=541807
    elif mutation=='over-original-cap':p['credit_settlement'].update(cumulative_before_seconds=119,cumulative_after_seconds=122)
    elif mutation=='old-deployment':a['deployedCommit']='d'*40
    elif mutation=='wrong-object-version':p['full_authenticated_asset_read']['object_version_id']='SYNTHETIC-wrong'
    elif mutation=='no-music-observation':p['position_observations']['end']['narration_and_music_intelligible']=False
    elif mutation=='wrong-account':b['account_sha256']='f'*64
    elif mutation=='playing-after-ended':next(row for row in p['controls'] if row['case']=='ended')['monotonic_ms']=4000
    elif mutation=='playing-during-pause':next(row for row in p['controls'] if row['case']=='pause')['monotonic_ms']=500
    elif mutation=='consistent-undebit':
        p['credit_settlement'].update(actual_debited_seconds=1,cumulative_after_seconds=61)
        b['actual_debited_seconds']=a['actual_debited_seconds']=1
    else:p['position_observations']['middle']['media_position_ms']=271249
    with pytest.raises((ValueError,KeyError,TypeError)):gate.validate(package,**arguments(package,(p,b,a)))


def test_generic_whole_segment_proof_cannot_qualify_native_bridge():
    package,_=source_fixtures.finalized_package()
    with pytest.raises(ValueError):gate.validate(package,**source_fixtures.proofs(package))
