"""Composed ASGI/ReadingPass tests. Only local synthetic users/storage/proofs.

Uses the actual controlled artifact loader and merge, actual lease/finance
service, signed IN proxy requests and all real package routes. No network.
"""
import asyncio,copy,importlib,json,os,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pytest,httpx
from fastapi import Response
os.environ.setdefault('JWT_SECRET','isolated-native-replacement-fixture')
os.environ.setdefault('MONGO_URL','mongodb://127.0.0.1:27017')
os.environ.setdefault('DB_NAME','isolated_native_no_network')
os.environ.setdefault('ENVIRONMENT','test')
ROOT=Path(__file__).resolve().parents[2];SCRIPTS=ROOT/'internal/audiobook_lab/scripts'
sys.path.insert(0,str(SCRIPTS))
import test_native_replacement_release as source_fixtures
from backend import server, catalog_truth as truth, reading_pass_service as service_module
from backend import native_audiobook_replacement as native
from backend.reading_pass_service import ReadingPassService
from backend.domain.reading_pass import ReadingPassConfig
from backend.tests.test_reading_pass_service_concurrency import Database,Collection,Client
from backend.release_proxy_auth import request_signature
from backend import protected_package_publication as publication
SECRET='synthetic-native-proxy-secret-over-thirty-two-chars'


def carried_budget(package,now):
    # Fictional60 reserved, maximum67. This is NOT the owner's current balance.
    return dict(schema='reader-acceptance-budget.v1',user_id='user-1',content_type='audio',content_id=native.SLUG,
        test_id=native.TEST_ID,status='enabled',maximum_seconds=67,consumed_seconds=60,
        manifest_version=package['package_version'],segmentation_version=native.DESCRIPTOR,
        created_at=now-timedelta(seconds=1),expires_at=now+timedelta(minutes=10),
        native_replacement_authorization=dict(schema='earnalism.native_replacement_member_grant.v1',authorization_id='SYNTHETIC-carried-grant',
            original_ceiling_seconds=120,lineage_status='CONSERVATIVE_RESERVATION',inherited_reserved_seconds=60,
            usage_lineage_sha256='1'*64,owner_scope_sha256='2'*64,expires_at=now+timedelta(minutes=10)))


def signed(method,path,country='IN'):
    now=int(datetime.now(timezone.utc).timestamp())
    return {'x-earnalism-release-scope':'PUBLIC','x-earnalism-release-country':country,
        'x-earnalism-release-timestamp':str(now),'x-earnalism-release-signature':request_signature(SECRET,method,path,'PUBLIC',now,country)}


@pytest.fixture
def composed(tmp_path,monkeypatch):
    source_fixtures.clone(tmp_path);package,descriptor=source_fixtures.finalized_package()
    snap=source_fixtures.release.snapshot(tmp_path)
    source_fixtures.release.stage(tmp_path,**source_fixtures.stage_args(package,descriptor,snap),apply=True)
    # Route actual path lookup to the full, byte-identical current-public clone.
    for loaded_truth in {truth, importlib.import_module(server.load_controlled_artifact_book.__module__)}:
        monkeypatch.setattr(loaded_truth,'ROOT',tmp_path);monkeypatch.setattr(loaded_truth,'MODULE_DIR',tmp_path/'backend')
        monkeypatch.setattr(loaded_truth,'CONTROLLED_PUBLICATIONS_DIR',tmp_path/'data/controlled_publications')
        loaded_truth.clear_controlled_artifact_caches()
    now=datetime.now(timezone.utc);clock=[now]
    monkeypatch.setattr(service_module,'_now',lambda:clock[0])
    db=Database(balance=300);db.books=Collection([])
    db.users.rows[0]['reader_acceptance_budget']=carried_budget(package,now)
    db.user_sessions.rows.append(dict(id='auth-1',user_id='user-1',status='active',idle_expires_at=now+timedelta(hours=1),absolute_expires_at=now+timedelta(hours=1)))
    service=ReadingPassService(db=db,client=Client(),config=ReadingPassConfig(),token_secret='SYNTHETIC-lease-secret')
    monkeypatch.setattr(server,'db',db);monkeypatch.setattr(server,'reading_pass_service',service)
    monkeypatch.setattr(server,'READING_PASS_V2_ENABLED',True)
    monkeypatch.setattr(server,'ENVIRONMENT','test')
    monkeypatch.setattr(server,'_redis_client',None)
    monkeypatch.setenv('EARNALISM_RELEASE_PROXY_SECRET',SECRET)
    async def no_cache(*a,**kw):return None
    for key in ('_redis_cache_get','_redis_cache_set','_invalidate_user_cache','_set_user_wallet_cache'):
        monkeypatch.setattr(server,key,no_cache)
    user={'id':'user-1','role':'user','session_id':'auth-1','status':'active'}
    async def principal():return user
    server.app.dependency_overrides[server.require_user]=principal
    server.app.dependency_overrides[server.optional_principal]=principal
    seen=[]
    async def storage(slug,asset_key,asset_url,request,*,extra_headers=None,version_id=''):
        seen.append((asset_key,asset_url,version_id))
        return Response(b'SYNTHETIC-storage-body-not-real-audio',status_code=206 if request.headers.get('range') else 200,headers=extra_headers)
    monkeypatch.setattr(server,'_stream_audiobook_asset_url',storage)
    monkeypatch.setattr(server,'_b2_storage_configs',lambda:[dict(name='prod',bucket='prod-bucket',endpoint='https://storage-fixture.invalid')])
    yield dict(root=tmp_path,package=package,clock=clock,db=db,service=service,user=user,seen=seen,source_snapshot=snap)
    server.app.dependency_overrides.clear();truth.clear_controlled_artifact_caches()


def start_body():return dict(content_type='audio',content_id=native.SLUG,device_id='device-1',device_label='SYNTHETIC',media_position_seconds=31)


async def start(client):
    path='/api/reading-pass/sessions/start';response=await client.post(path,json=start_body(),headers=signed('POST',path))
    assert response.status_code==200,response.text
    return response.json()


def test_real_artifact_finder_public_old_private_member_and_lease_selected_exactly(composed):
    async def run():
        c=composed;artifact=server._controlled_artifact_doc(native.SLUG,include_content=False)
        assert artifact is not None and artifact[native.FIELD]['status']=='STAGED_PRIVATE'
        # Real merge cannot promote a stale database candidate or URL.
        c['db'].books.rows.append({**copy.deepcopy(artifact),'audiobook_native_replacement':{'status':'MALICIOUS'},'audiobook_url':'https://stale.invalid/x'})
        actual=await server._reader_audio_package_book_for_slug(native.SLUG)
        assert actual[native.FIELD]==artifact[native.FIELD]
        old,descriptor,_=server._selected_audiobook_package(actual,native.SLUG)
        assert descriptor==native.PREDECESSOR
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            lease=await start(client)
            assert c['db'].reading_pass_sessions.rows[0]['scope']['release_descriptor_sha256']==native.DESCRIPTOR
            path=f'/api/reader/book/{native.SLUG}/audiobook/manifest'
            result=await client.get(path,headers=signed('GET',path));assert result.status_code==200,result.text
            body=result.json();assert body['package_version']==c['package']['package_version']
            assert 'storage-fixture' not in result.text and 'SYNTHETIC-prod' not in result.text
            assert result.headers['cache-control']=='private, no-store'
            assert 'ear_audiobook_rollout' not in result.headers.get('set-cookie','')
            for suffix in ('','/timestamps','/vtt','/metadata'):
                p=f"/api/reader/book/{native.SLUG}/audiobook/packages/{c['package']['package_version']}/segments/{c['package']['tracks'][0]['chunks'][0]['segment_id']}"+suffix
                r=await client.get(p,headers={**signed('GET',p),'range':'bytes=0-99'})
                assert r.status_code==206,r.text
            assert len(c['seen'])==4 and all('SYNTHETIC-prod-' in row[2] for row in c['seen'])
            wrong=await client.get(p.replace(c['package']['package_version'],old['package_version']),headers=signed('GET',p.replace(c['package']['package_version'],old['package_version'])))
            assert wrong.status_code==404
        assert c['db'].users.rows[0]['reading_seconds_balance']==300
        assert c['db'].users.rows[0]['reader_acceptance_budget']['consumed_seconds']==60
    asyncio.run(run())


@pytest.mark.parametrize('mutation',['missing-grant','changed-id','expired','wrong-package','revoked-rights','country-US','bad-signature','other-member'])
def test_actual_media_denies_changed_private_authority_before_storage(composed,mutation,monkeypatch):
    async def run():
        c=composed
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            await start(client);budget=c['db'].users.rows[0]['reader_acceptance_budget'];path=f'/api/reader/book/{native.SLUG}/audiobook/manifest'
            headers=signed('GET',path)
            if mutation=='missing-grant':budget.pop('native_replacement_authorization')
            elif mutation=='changed-id':budget['native_replacement_authorization']['authorization_id']='DIFFERENT'
            elif mutation=='expired':budget['expires_at']=datetime.now(timezone.utc)-timedelta(seconds=1)
            elif mutation=='wrong-package':budget['manifest_version']='sha256-'+'f'*64
            elif mutation=='revoked-rights':
                original=native.load_production_registry
                def revoked():
                    accepted,ids=original();return accepted,frozenset(set(ids)|{'india-20261102-the-selfish-giant-cedar-scored-audio'})
                monkeypatch.setattr(native,'load_production_registry',revoked)
            elif mutation=='country-US':headers=signed('GET',path,'US')
            elif mutation=='bad-signature':headers['x-earnalism-release-signature']='0'*64
            else:
                async def other():return {'id':'other','role':'user','session_id':'other-auth'}
                server.app.dependency_overrides[server.optional_principal]=other
            response=await client.get(path,headers=headers);assert response.status_code in (401,403),response.text
            assert not c['seen'] and c['db'].users.rows[0]['reading_seconds_balance']==300
    asyncio.run(run())


def test_native_cookie_rebinds_current_login_and_guest_query_cannot_choose_candidate(composed):
    async def run():
        c=composed
        async def guest():return None
        server.app.dependency_overrides[server.optional_principal]=guest
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            p=f'/api/reader/book/{native.SLUG}/audiobook/manifest'
            r=await client.get(p+'?package_version='+c['package']['package_version']+'&transport_canary=1',headers=signed('GET',p));assert r.status_code==401
            await start(client)
            r=await client.get(p,headers=signed('GET',p));assert r.status_code==200
            c['db'].user_sessions.rows[0]['status']='revoked'
            r=await client.get(p,headers=signed('GET',p));assert r.status_code==401
    asyncio.run(run())


def test_native_transfer_denied_and_transaction_rechecks_grant_without_wallet_change(composed):
    async def run():
        c=composed
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            p='/api/reading-pass/sessions/transfer';r=await client.post(p,json=start_body(),headers=signed('POST',p));assert r.status_code==403
            lease=await start(client)
            c['db'].users.rows[0]['reader_acceptance_budget']['native_replacement_authorization']['authorization_id']='SWAPPED'
            c['clock'][0]+=timedelta(seconds=4)
            p='/api/reading-pass/leases/renew';r=await client.post(p,json=dict(session_id=lease['session_id'],lease_version=1,sequence=1,idempotency_key='fixture-1',active=True,playback_state='playing'),headers=signed('POST',p))
            assert r.status_code==403 and c['db'].users.rows[0]['reading_seconds_balance']==300
            assert not c['db'].wallet_ledger.rows
    asyncio.run(run())


def test_real_carried_budget_cumulative_debit_pause_fraction_and_terminal_are_unchanged(composed):
    async def run():
        c=composed
        c['db'].users.rows[0]['reading_fractional_microseconds']=250000
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            lease=await start(client)
            async def renewal(seq,state):
                path='/api/reading-pass/leases/renew'
                r=await client.post(path,json=dict(session_id=lease['session_id'],lease_version=seq,sequence=seq,
                    idempotency_key='carried-fixture-'+str(seq),active=state=='playing',playback_state=state),headers=signed('POST',path))
                assert r.status_code==200,r.text
                return r.json()
            first=await renewal(1,'playing');assert first['deducted_seconds']==0
            c['clock'][0]+=timedelta(seconds=2.4)
            second=await renewal(2,'playing');assert second['deducted_seconds']==2
            assert c['db'].users.rows[0]['reading_fractional_microseconds']==650000
            c['clock'][0]+=timedelta(seconds=2.6)
            third=await renewal(3,'paused');assert third['deducted_seconds']==3
            assert c['db'].users.rows[0]['reading_fractional_microseconds']==250000
            c['clock'][0]+=timedelta(seconds=1)
            fourth=await renewal(4,'playing');assert fourth['deducted_seconds']==0
            c['clock'][0]+=timedelta(seconds=2)
            endpath='/api/reading-pass/sessions/end'
            ended=await client.post(endpath,json=dict(session_id=lease['session_id'],reason='fixture_complete'))
            assert ended.status_code==200,ended.text
            user=c['db'].users.rows[0]
            assert user['reader_acceptance_budget']['consumed_seconds']==67
            assert user['reading_seconds_balance']==user['wallet_seconds']==293
            assert sum(r['debit'] for r in c['db'].wallet_ledger.rows)==7
            assert user['reading_fractional_microseconds']==250000
            assert user['reader_acceptance_budget']['native_replacement_authorization']['inherited_reserved_seconds']==60
            assert not any(r.get('status')=='active' for r in c['db'].reading_pass_sessions.rows)
    asyncio.run(run())


def test_actual_listener_presentation_is_private_member_only_with_old_public_catalog(composed):
    async def run():
        c=composed;p=f'/api/reader/book/{native.SLUG}/manifest'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            r=await client.get(p+'?transport_canary=1',headers=signed('GET',p));assert r.status_code==200,r.text
            canary=r.json()['audio']['transport_canary']
            assert canary['scope']==native.PRIVATE_SCOPE and canary['package_version']==c['package']['package_version']
            assert 'rollout_percentage' not in canary and native.FIELD not in r.text
            async def other():return {'id':'other','role':'user','status':'active','session_id':'other-auth'}
            server.app.dependency_overrides[server.optional_principal]=other
            r=await client.get(p+'?transport_canary=1',headers=signed('GET',p));assert r.status_code==200,r.text
            assert 'transport_canary' not in r.json()['audio']
            projected=server.public_book_projection(server._controlled_artifact_doc(native.SLUG,include_content=False))
            assert native.FIELD not in projected
            old,selected,_=server._selected_audiobook_package(await server._reader_audio_package_book_for_slug(native.SLUG),native.SLUG)
            assert selected==native.PREDECESSOR and old['package_version']!=c['package']['package_version']
    asyncio.run(run())


@pytest.mark.parametrize('mutation',['reset-reserve','maximum-expanded','counter-below-reservation','not-reconciled','expired-scope','wrong-descriptor','boolean-counter'])
def test_native_carried_grant_rejects_reset_broader_or_malformed_authority(composed,mutation):
    c=composed;budget=c['db'].users.rows[0]['reader_acceptance_budget'];grant=budget['native_replacement_authorization']
    if mutation=='reset-reserve':grant['inherited_reserved_seconds']=0
    elif mutation=='maximum-expanded':budget['maximum_seconds']=121
    elif mutation=='counter-below-reservation':budget['consumed_seconds']=59
    elif mutation=='not-reconciled':grant['lineage_status']='NOMINAL_69_ASSUMPTION'
    elif mutation=='expired-scope':grant['expires_at']=c['clock'][0]-timedelta(seconds=1)
    elif mutation=='wrong-descriptor':budget['segmentation_version']='f'*64
    else:budget['consumed_seconds']=True
    with pytest.raises(ValueError):native.validate_carried_grant(budget,'user-1',now=c['clock'][0],package_version=c['package']['package_version'])


def test_composed_production_rights_middleware_uses_new_coherent_reader_binding(composed,monkeypatch):
    async def run():
        c=composed
        # Real production middleware and actual rights evaluator; only the
        # deployment's filesystem/registry inputs point at the isolated clone.
        monkeypatch.chdir(c['root']);monkeypatch.setattr(server,'ENVIRONMENT','production')
        module=importlib.import_module(server.load_production_registry.__module__)
        monkeypatch.setattr(server,'load_production_registry',lambda:module.load_production_registry(c['root']/'backend/data/rights_decision_registry.json'))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            await start(client);path=f'/api/reader/book/{native.SLUG}/audiobook/manifest'
            r=await client.get(path,headers=signed('GET',path));assert r.status_code==200,r.text
            assert r.json()['package_version']==c['package']['package_version']
            denied=await client.get(path,headers=signed('GET',path,'US'))
            assert denied.status_code in (403,451),denied.text
    asyncio.run(run())


def test_actual_bson_utc_roundtrip_grant_works_without_mutating_retained_cas_document(composed):
    from bson import BSON
    async def run():
        c=composed;budget=c['db'].users.rows[0]['reader_acceptance_budget']
        decoded=BSON.encode(budget).decode()
        assert decoded['created_at'].tzinfo is None and decoded['native_replacement_authorization']['expires_at'].tzinfo is None
        c['db'].users.rows[0]['reader_acceptance_budget']=decoded;before=copy.deepcopy(decoded)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            await start(client);path=f'/api/reader/book/{native.SLUG}/audiobook/manifest'
            r=await client.get(path,headers=signed('GET',path));assert r.status_code==200,r.text
        assert c['db'].users.rows[0]['reader_acceptance_budget']==before
        assert c['db'].users.rows[0]['reading_seconds_balance']==300
    asyncio.run(run())


# Actual require_user dependency coverage: all keys/identities are synthetic;
# only cache/device inputs are isolated, not the authentication dependency.
def _use_real_require_user(composed, monkeypatch):
    c = composed
    server.app.dependency_overrides.pop(server.require_user, None)
    user = c['db'].users.rows[0]
    user['active_user_session_id'] = 'auth-1'
    c['db'].user_sessions.rows[0]['last_seen_at'] = datetime.now(timezone.utc)
    async def cached_user(user_id):
        row = next((r for r in c['db'].users.rows if r['id'] == user_id), None)
        return copy.deepcopy(row) if row else None
    async def cached_session(session_id, user_id):
        row = next((r for r in c['db'].user_sessions.rows
                    if r['id'] == session_id and r['user_id'] == user_id), None)
        return copy.deepcopy(row) if row else None
    monkeypatch.setattr(server, '_cached_user_doc', cached_user)
    monkeypatch.setattr(server, '_cached_user_session', cached_session)
    monkeypatch.setattr(server, '_device_fingerprint', lambda request: 'SYNTHETIC-fingerprint')
    token = server.create_user_token('user-1', 'synthetic@example.invalid', 'auth-1', 'SYNTHETIC-fingerprint')
    return {'Authorization': 'Bearer ' + token}


def _renewal_body(lease):
    return dict(session_id=lease['session_id'], lease_version=1, sequence=1,
                idempotency_key='SYNTHETIC-real-auth-renewal', active=True, playback_state='playing')


def test_real_require_user_native_renewal_checks_authority_and_preserves_cached_body(composed, monkeypatch):
    async def run():
        c = composed
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url='https://fixture') as client:
            lease = await start(client)
            headers = _use_real_require_user(c, monkeypatch)
            calls = []
            original = server._native_replacement_renewal_authority
            async def observe(request, user_id):
                calls.append((request.url.path, user_id))
                return await original(request, user_id)
            monkeypatch.setattr(server, '_native_replacement_renewal_authority', observe)
            path = '/api/reading-pass/leases/renew'
            response = await client.post(path, json=_renewal_body(lease), headers={**signed('POST', path), **headers})
            assert response.status_code == 200, response.text
            assert calls == [(path, 'user-1')]
            assert response.json()['deducted_seconds'] == 0
            assert c['db'].users.rows[0]['reader_acceptance_budget']['consumed_seconds'] == 60
    asyncio.run(run())


@pytest.mark.parametrize('mutation', ['missing-grant', 'changed-id', 'revoked-rights', 'country-US', 'expired-grant'])
def test_real_require_user_native_renewal_denies_changed_authority_before_finance(composed, monkeypatch, mutation):
    async def run():
        c = composed
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url='https://fixture') as client:
            lease = await start(client)
            headers = _use_real_require_user(c, monkeypatch)
            if mutation == 'missing-grant':
                del c['db'].users.rows[0]['reader_acceptance_budget']
            elif mutation == 'changed-id':
                c['db'].users.rows[0]['reader_acceptance_budget']['native_replacement_authorization']['authorization_id'] = 'SYNTHETIC-changed'
            elif mutation == 'expired-grant':
                now = datetime.now(timezone.utc)
                budget = c['db'].users.rows[0]['reader_acceptance_budget']
                budget['created_at'] = now - timedelta(minutes=2)
                budget['expires_at'] = now - timedelta(seconds=1)
                budget['native_replacement_authorization']['expires_at'] = budget['expires_at']
            elif mutation == 'revoked-rights':
                original = native.load_production_registry
                def revoked():
                    accepted, prior = original()
                    return accepted, prior | frozenset(['india-20261102-the-selfish-giant-cedar-scored-audio'])
                monkeypatch.setattr(native, 'load_production_registry', revoked)
            before = copy.deepcopy((c['db'].reading_pass_sessions.rows, c['db'].wallet_ledger.rows,
                                    c['db'].users.rows[0]['reading_seconds_balance']))
            path = '/api/reading-pass/leases/renew'
            response = await client.post(path, json=_renewal_body(lease), headers={**signed('POST', path, 'US' if mutation == 'country-US' else 'IN'), **headers})
            assert response.status_code == 403, response.text
            after = (c['db'].reading_pass_sessions.rows, c['db'].wallet_ledger.rows,
                     c['db'].users.rows[0]['reading_seconds_balance'])
            assert before == after
    asyncio.run(run())


def test_real_require_user_missing_bearer_never_reaches_native_renewal_hook(composed, monkeypatch):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url='https://fixture') as client:
            lease = await start(client)
            _use_real_require_user(composed, monkeypatch)
            calls = []
            async def forbidden(*args):
                calls.append(True)
                raise AssertionError('Unauthenticated request reached native authority')
            monkeypatch.setattr(server, '_native_replacement_renewal_authority', forbidden)
            path = '/api/reading-pass/leases/renew'
            response = await client.post(path, json=_renewal_body(lease), headers=signed('POST', path))
            assert response.status_code == 401, response.text
            assert calls == []
    asyncio.run(run())


def test_real_require_user_normal_renewal_does_not_enter_private_candidate_authority(composed, monkeypatch):
    async def run():
        c = composed
        del c['db'].users.rows[0]['reader_acceptance_budget']
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url='https://fixture') as client:
            lease = await start(client)
            headers = _use_real_require_user(c, monkeypatch)
            async def forbidden(*args, **kwargs):
                raise AssertionError('Normal lease entered native candidate authority')
            monkeypatch.setattr(server, '_native_replacement_member_scope', forbidden)
            path = '/api/reading-pass/leases/renew'
            response = await client.post(path, json=_renewal_body(lease), headers={**signed('POST', path), **headers})
            assert response.status_code == 200, response.text
            assert response.json()['deducted_seconds'] == 0
            assert 'reader_acceptance_budget' not in c['db'].users.rows[0]
    asyncio.run(run())


@pytest.mark.parametrize('mutation', ['blocked', 'expired-auth', 'revoked-auth', 'device-mismatch', 'invalid-token'])
def test_real_auth_rejection_precedes_native_lookup_and_finance(composed, monkeypatch, mutation):
    async def run():
        c = composed
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url='https://fixture') as client:
            lease = await start(client)
            headers = _use_real_require_user(c, monkeypatch)
            if mutation == 'blocked':
                c['db'].users.rows[0]['status'] = 'blocked'
            elif mutation == 'expired-auth':
                c['db'].user_sessions.rows[0]['idle_expires_at'] = datetime.now(timezone.utc) - timedelta(seconds=1)
            elif mutation == 'revoked-auth':
                c['db'].user_sessions.rows[0]['status'] = 'revoked'
            elif mutation == 'device-mismatch':
                monkeypatch.setattr(server, '_device_fingerprint', lambda request: 'SYNTHETIC-wrong-device')
            else:
                headers = {'Authorization': 'Bearer SYNTHETIC-invalid-token'}
            calls = []
            async def forbidden(*args):
                calls.append(True)
                raise AssertionError('Failed normal auth reached native preflight')
            monkeypatch.setattr(server, '_native_replacement_renewal_authority', forbidden)
            before = copy.deepcopy((c['db'].reading_pass_sessions.rows, c['db'].wallet_ledger.rows,
                                    c['db'].users.rows[0]['reading_seconds_balance']))
            path = '/api/reading-pass/leases/renew'
            response = await client.post(path, json=_renewal_body(lease), headers={**signed('POST', path), **headers})
            assert response.status_code in (401, 403), response.text
            assert calls == []
            assert before == (c['db'].reading_pass_sessions.rows, c['db'].wallet_ledger.rows,
                              c['db'].users.rows[0]['reading_seconds_balance'])
    asyncio.run(run())


def test_real_auth_unrelated_endpoint_does_not_lookup_renewal_scope(composed, monkeypatch):
    async def run():
        c = composed
        headers = _use_real_require_user(c, monkeypatch)
        async def forbidden(*args, **kwargs):
            raise AssertionError('Unrelated endpoint attempted native/session lookup')
        monkeypatch.setattr(server, '_native_replacement_renewal_authority', forbidden)
        monkeypatch.setattr(c['db'].reading_pass_sessions, 'find_one', forbidden)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url='https://fixture') as client:
            response = await client.get('/api/users/me/wallet', headers=headers)
            assert response.status_code == 200, response.text
            assert response.json()['wallet_seconds'] == 300
    asyncio.run(run())


@pytest.mark.parametrize("case", ["none", "other", "missing", "malformed", "stale", "wrong-descriptor", "wrong-schema"])
@pytest.mark.parametrize("native_bound", [False, True])
def test_unrelated_or_missing_native_candidate_never_reads_member_data(monkeypatch, case, native_bound):
    from types import SimpleNamespace
    marker = {"schema_version": native.SCHEMA, "status": "STAGED_PRIVATE",
              "candidate_descriptor_sha256": native.DESCRIPTOR}
    book = {"slug": native.SLUG, native.FIELD: marker}
    if case == "none": book = None
    elif case == "other": book["slug"] = "another-book"
    elif case == "missing": del book[native.FIELD]
    elif case == "malformed": book[native.FIELD] = "not-a-marker"
    elif case == "stale": marker["status"] = "REMOVED"
    elif case == "wrong-descriptor": marker["candidate_descriptor_sha256"] = "f" * 64
    else: marker["schema_version"] = "unreviewed-schema"
    async def forbidden(*args, **kwargs):
        raise AssertionError("Inapplicable candidate queried private member data")
    monkeypatch.setattr(server, "db", SimpleNamespace(users=SimpleNamespace(find_one=forbidden)))
    scope = {"native_replacement_authorization_id": "SYNTHETIC-retained-grant"} if native_bound else None
    async def run():
        if native_bound:
            with pytest.raises(server.HTTPException) as error:
                await server._native_replacement_member_scope(book, "user-1", None, session_scope=scope)
            assert error.value.status_code == 403
            assert error.value.detail["code"] == "NATIVE_REPLACEMENT_SCOPE_DENIED"
        else:
            assert await server._native_replacement_member_scope(book, "user-1", None) is None
    asyncio.run(run())
