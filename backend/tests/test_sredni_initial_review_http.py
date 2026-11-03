"""Actual ASGI finder/merge/serialization/service; synthetic Auth/DB/storage only.

No actual account, network, member authority, storage bytes or customer debit.
"""
import asyncio,copy,importlib,json,os,sys,shutil
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pytest,httpx
from fastapi import Response

from backend import server,catalog_truth as truth,reading_pass_service as service_module
from backend import sredni_initial_review_scope as scoped,sredni_initial_review_profile as profile
from backend.reading_pass_service import ReadingPassService
from backend.domain.reading_pass import ReadingPassConfig
from backend.release_proxy_auth import request_signature
from backend.tests.test_reading_pass_service_concurrency import Database,Collection
from test_sredni_initial_review_domain import seeded,Client
SECRET='SYNTHETIC-sredni-proxy-secret-over-thirty-two-chars'
CANONICAL=Path(truth.__file__).resolve().parents[1]


def signed(method,path,country='IN'):
    stamp=int(datetime.now(timezone.utc).timestamp())
    return {'x-earnalism-release-scope':'PUBLIC','x-earnalism-release-country':country,
        'x-earnalism-release-timestamp':str(stamp),'x-earnalism-release-signature':request_signature(SECRET,method,path,'PUBLIC',stamp,country)}


@pytest.fixture
def composed(tmp_path,monkeypatch):
    root=tmp_path/'owned';root.mkdir()
    fixture=json.loads((Path(__file__).parent/'fixtures/sredni-initial-sourceqa-staged-book.json').read_text())
    for side in ['data','backend/data']:
        shutil.copytree(CANONICAL/side/'controlled_publications'/profile.SLUG,root/side/'controlled_publications'/profile.SLUG)
        for config in ['controlled_launch.json','catalog_exclusions.json']:
            if (CANONICAL/side/config).is_file():shutil.copyfile(CANONICAL/side/config,root/side/config)
        # Test the immutable real source-stage fixture regardless of mutable
        # canonical source-state advances; complete original chapters remain.
        (root/side/'controlled_publications'/profile.SLUG/'public_book.json').write_text(json.dumps(fixture))
    for loaded in {truth,importlib.import_module(server.load_controlled_artifact_book.__module__)}:
        monkeypatch.setattr(loaded,'ROOT',root);monkeypatch.setattr(loaded,'MODULE_DIR',root/'backend')
        monkeypatch.setattr(loaded,'CONTROLLED_PUBLICATIONS_DIR',root/'data/controlled_publications');loaded.clear_controlled_artifact_caches()
    clock=[datetime.now(timezone.utc)];db,w,g=seeded(clock[0]);db.books=Collection([])
    accepted={'schema':scoped.AUTHORITY_SCHEMA,'accepted':[{'owner_receipt_sha256':g['owner_receipt_sha256'],'identity_binding_sha256':g['identity_binding_sha256']}]}
    # Package/top-level aliases of the same physical source can coexist under
    # existing tests. Patch only this synthetic authority seam on each actual
    # loaded alias, never a package finder or response builder.
    for loaded in list(sys.modules.values()):
        if getattr(loaded,'__file__',None) and Path(loaded.__file__).resolve()==Path(scoped.__file__).resolve():
            monkeypatch.setattr(loaded,'load_authority',lambda:copy.deepcopy(accepted));monkeypatch.setattr(loaded,'_now',lambda:clock[0])
    monkeypatch.setattr(service_module,'_now',lambda:clock[0])
    service=ReadingPassService(db=db,client=Client(db),config=ReadingPassConfig(),token_secret='SYNTHETIC-sredni-lease')
    monkeypatch.setattr(server,'db',db);monkeypatch.setattr(server,'reading_pass_service',service)
    monkeypatch.setattr(server,'READING_PASS_V2_ENABLED',True);monkeypatch.setattr(server,'ENVIRONMENT','test');monkeypatch.setattr(server,'_redis_client',None)
    monkeypatch.setenv('EARNALISM_RELEASE_PROXY_SECRET',SECRET)
    async def no_cache(*a,**k):return None
    for name in ['_redis_cache_get','_redis_cache_set','_invalidate_user_cache','_set_user_wallet_cache']:
        monkeypatch.setattr(server,name,no_cache)
    user={'id':'user-1','role':'user','session_id':'auth-1','status':'active'}
    async def principal():return user
    server.app.dependency_overrides[server.require_user]=principal;server.app.dependency_overrides[server.optional_principal]=principal
    seen=[]
    async def storage(slug,key,url,request,*,extra_headers=None,version_id=''):
        seen.append((slug,key,version_id));return Response(b'SYNTHETIC_STORAGE_NOT_ACTUAL_AUDIO',status_code=206 if request.headers.get('range') else 200,headers=extra_headers)
    monkeypatch.setattr(server,'_stream_audiobook_asset_url',storage)
    primary=fixture['audiobook_packages'][profile.DESCRIPTOR]['tracks'][0]['chunks'][0]['assets']['audio']['storage']
    monkeypatch.setattr(server,'_b2_storage_configs',lambda:[{'name':'prod','bucket':primary['bucket'],'endpoint':'https://synthetic-storage.invalid'}])
    yield {'root':root,'clock':clock,'db':db,'w':w,'g':g,'user':user,'seen':seen,'service':service,'fixture':fixture}
    server.app.dependency_overrides.clear()
    for loaded in {truth,importlib.import_module(server.load_controlled_artifact_book.__module__)}:loaded.clear_controlled_artifact_caches()


def start_body():return {'content_type':'audio','content_id':profile.SLUG,'device_id':'synthetic-device','device_label':'SYNTHETIC','media_position_seconds':31}


def test_actual_reader_private_credit_metadata_no_lease_or_debit_and_real_finder_precedence(composed):
    async def run():
        c=composed;artifact=server._controlled_artifact_doc(profile.SLUG,include_content=False);assert artifact is not None
        # A fully populated stale DB audio record must never replace canonical
        # exact package/rights nor supply an older public narration disclosure.
        c['db'].books.rows.append({**copy.deepcopy(artifact),'audiobook_url':'https://stale.invalid/old.mp3','audio_enabled':True,
            'audiobook_enabled':True,'narration_disclosure':'Old Cedar','audiobook_release_conveyor':{
                'schema_version':'earnalism.audiobook_release_conveyor.v1','audio_release_approved':True}})
        selected=await server._reader_audio_package_book_for_slug(profile.SLUG)
        assert selected[profile.FIELD]==artifact[profile.FIELD]
        merged=server._merge_controlled_publication_truth(c['db'].books.rows[0],artifact,slug=profile.SLUG)
        assert merged['audio_enabled'] is False and merged['audiobook_assets']=={} and merged[profile.FIELD]==artifact[profile.FIELD]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            p=f'/api/reader/book/{profile.SLUG}/manifest'
            ordinary=await client.get(p,headers=signed('GET',p));assert ordinary.status_code==200,ordinary.text
            assert ordinary.json()['audio']['enabled'] is False and ordinary.json()['audio']['narration_disclosure']==''
            r=await client.get(p+'?transport_canary=1',headers=signed('GET',p));assert r.status_code==200,r.text
            audio=r.json()['audio'];private=audio['transport_canary']
            assert private['package_version']==profile.PACKAGE and private['narration_disclosure']==profile.DISCLOSURE
            assert audio['enabled'] is False
            text=r.text;assert 'backblazeb2.com' not in text and 'Old Cedar' not in text and profile.FIELD not in text
            export=os.environ.get('SREDNI_SYNTHETIC_READER_EXPORT')
            if export:
                # Actual FastAPI serialized response, synthetic account only.
                # Headers/cookies/leases/provider origins/text are excluded.
                needled=['SYNTHETIC-sredni-proxy','auth-1','user-1','lease_token','backblazeb2.com']
                assert not any(value in text for value in needled)
                with Path(export).open('x') as output:output.write(text+'\n')
        assert not c['db'].reading_pass_sessions.rows and not c['db'].wallet_ledger.rows and not c['db'].wallet_transactions.rows
        assert c['w']['starts_used']==c['w']['used_credit_seconds']==c['w']['used_microseconds']==0 and not c['seen']
    asyncio.run(run())


def test_normal_start_real_lease_package_fastapi_serialization_and_protected_assets(composed):
    async def run():
        c=composed
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            p='/api/reading-pass/sessions/start';r=await client.post(p,json=start_body(),headers=signed('POST',p));assert r.status_code==200,r.text
            assert c['db'].reading_pass_sessions.rows[0]['scope'][scoped.SCOPE_KEY]==c['g']['_id']
            p=f'/api/reader/book/{profile.SLUG}/audiobook/manifest';r=await client.get(p,headers=signed('GET',p));assert r.status_code==200,r.text
            assert r.json()['package_version']==profile.PACKAGE and r.headers['cache-control']=='private, no-store'
            assert 'backblazeb2.com' not in r.text and 'version_id' not in r.text
            segment=c['fixture']['audiobook_packages'][profile.DESCRIPTOR]['tracks'][0]['chunks'][0]['segment_id']
            for suffix in ['', '/timestamps','/vtt','/metadata']:
                p=f'/api/reader/book/{profile.SLUG}/audiobook/packages/{profile.PACKAGE}/segments/{segment}'+suffix
                r=await client.get(p,headers={**signed('GET',p),'range':'bytes=0-99'});assert r.status_code==206,r.text
        assert len(c['seen'])==4 and c['w']['starts_used']==1
        assert not c['db'].wallet_ledger.rows and 'reader_acceptance_budget' not in c['db'].users.rows[0]
    asyncio.run(run())


def test_metadata_at_three_starts_retains_exact_credits_but_fourth_normal_start_denied(composed):
    async def run():
        c=composed
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            start='/api/reading-pass/sessions/start';end='/api/reading-pass/sessions/end'
            for index in range(3):
                response=await client.post(start,json=start_body(),headers=signed('POST',start));assert response.status_code==200,response.text
                lease=response.json()
                if index<2:
                    stopped=await client.post(end,json={'session_id':lease['session_id']},headers=signed('POST',end));assert stopped.status_code==200,stopped.text
            assert c['w']['starts_used']==3
            path=f'/api/reader/book/{profile.SLUG}/manifest'
            r=await client.get(path+'?transport_canary=1',headers=signed('GET',path));assert r.status_code==200,r.text
            assert r.json()['audio']['transport_canary']['narration_disclosure']==profile.DISCLOSURE
            stopped=await client.post(end,json={'session_id':lease['session_id']},headers=signed('POST',end));assert stopped.status_code==200,stopped.text
            path=start;r=await client.post(path,json=start_body(),headers=signed('POST',path))
            assert r.status_code==403,r.text
        assert c['w']['starts_used']==3 and c['w']['used_credit_seconds']==c['w']['used_microseconds']==0
        assert len(c['db'].reading_pass_sessions.rows)==3 and all(row['status']=='ended' for row in c['db'].reading_pass_sessions.rows)
        assert not c['db'].wallet_ledger.rows and not c['seen']
    asyncio.run(run())


@pytest.mark.parametrize('kind',['missing','expired','other-member','wrong-SID','non-IN','old120','guest'])
def test_missing_changed_private_authority_no_media_debit_or_unscoped_start(composed,kind):
    async def run():
        c=composed;country='IN'
        if kind=='missing':c['db'][scoped.GRANTS].rows.clear()
        elif kind=='expired':c['g']['expires_at']=c['clock'][0]-timedelta(seconds=1)
        elif kind=='other-member':c['user']['id']='other-user'
        elif kind=='wrong-SID':c['user']['session_id']='other-login'
        elif kind=='non-IN':country='US'
        elif kind=='old120':
            c['db'][scoped.GRANTS].rows.clear();c['db'].users.rows[0]['reader_acceptance_budget']={'maximum_seconds':120,'native_replacement_authorization':{}}
        else:
            async def no_principal():return None
            server.app.dependency_overrides[server.optional_principal]=no_principal
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            p=f'/api/reader/book/{profile.SLUG}/manifest';r=await client.get(p+'?transport_canary=1',headers=signed('GET',p,country));assert r.status_code in [200,451],r.text
            if r.status_code==200:assert not r.json()['audio'].get('transport_canary') and r.json()['audio']['narration_disclosure']==''
            if kind!='guest':
                p='/api/reading-pass/sessions/start';r=await client.post(p,json=start_body(),headers=signed('POST',p,country));assert r.status_code in [403,451],r.text
        assert not c['seen'] and not c['db'].reading_pass_sessions.rows and not c['db'].wallet_ledger.rows
    asyncio.run(run())


@pytest.mark.parametrize('kind',['invalid-package','explicit-canonical-deny'])
def test_invalid_canonical_candidate_no_stale_approved_DB_fallback(composed,kind):
    async def run():
        c=composed;artifact=server._controlled_artifact_doc(profile.SLUG,include_content=False)
        c['db'].books.rows.append({**copy.deepcopy(artifact),'audio_enabled':True,'audiobook_enabled':True,
            'audiobook_url':'https://stale.invalid/approved.mp3','audiobook_release_conveyor':{
                'schema_version':'earnalism.audiobook_release_conveyor.v1','audio_release_approved':True}})
        for side in ['data','backend/data']:
            path=c['root']/side/'controlled_publications'/profile.SLUG/'public_book.json';doc=json.loads(path.read_text())
            if kind=='invalid-package':doc['audiobook_packages'][profile.DESCRIPTOR]['duration_ms']+=1
            else:doc[profile.FIELD]['status']='DENIED_CANONICAL_PRIVATE_STAGE'
            path.write_text(json.dumps(doc))
        for loaded in {truth,importlib.import_module(server.load_controlled_artifact_book.__module__)}:loaded.clear_controlled_artifact_caches()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            p='/api/reading-pass/sessions/start';r=await client.post(p,json=start_body(),headers=signed('POST',p));assert r.status_code==404,r.text
        assert not c['seen'] and not c['db'].reading_pass_sessions.rows and not c['db'].wallet_ledger.rows
    asyncio.run(run())
