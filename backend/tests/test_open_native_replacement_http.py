"""Actual ASGI/Reader/service seams with SYNTHETIC Auth/storage/DB only.

This is neither a real-owner grant nor production playback/real Auth proof.
Immutable adopted source QA was actually rerun by the separate25 lifecycle/
bridge cases; only its unchanged evidence verification is cached here, while
current adoption/rights/package/route checks execute each time.
"""
import asyncio,copy,importlib,json
from datetime import datetime,timedelta,timezone
import pytest,httpx
from backend.tests import test_native_audiobook_replacement_http as inherited
from backend.tests.test_native_audio_review_scope import seeded,Client
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'internal/audiobook_lab/scripts'))
from test_open_window_replacement_release import synthetic_only_open_storage_binding
import test_open_window_replacement_release as source_fixtures

from backend import native_audio_review_scope as scoped
from backend import native_audio_review_authority as authority
from backend import open_window_audiobook_replacement as opened
server=inherited.server;truth=inherited.truth

@pytest.fixture
def composed(tmp_path,monkeypatch):
    monkeypatch.setattr(inherited,'native',opened)
    monkeypatch.setattr(inherited,'source_fixtures',source_fixtures)
    generator=inherited.composed.__wrapped__(tmp_path,monkeypatch);c=next(generator)
    # Fictional setup only: convert the inherited fixture to the scoped metadata path.
    c['db'].users.rows[0].pop('reader_acceptance_budget')
    _,w,g=seeded(c['clock'][0]);w['owner_scope_sha256']=g['owner_scope_sha256']=authority.ORIGINAL_OWNER_RECEIPT_SHA256
    g.update(_id='open-window-SYNTHETIC',slug=opened.SLUG,descriptor_sha256=opened.DESCRIPTOR,
        package_version=c['package']['package_version'],continuation_sha256=authority.BOTH_TITLES_RECEIPT_SHA256)
    c['db'][scoped.WORKFLOWS].rows=[w];c['db'][scoped.GRANTS].rows=[g];c['service'].client=Client(c['db'])
    yield c
    try:next(generator)
    except StopIteration:pass


def test_open_actual_reader_manifest_range_and_counter_scope_ordinary_predecessor_preserved(composed):
    async def run():
        c=composed;book=server._controlled_artifact_doc(opened.SLUG,include_content=False)
        old,desc,_=server._selected_audiobook_package(book,opened.SLUG);assert desc==opened.PREDECESSOR
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            lease=await inherited.start(client)
            path=f'/api/reader/book/{opened.SLUG}/audiobook/manifest'
            r=await client.get(path,headers=inherited.signed('GET',path));assert r.status_code==200,r.text
            assert r.json()['package_version']==c['package']['package_version']
            assert c['db'].reading_pass_sessions.rows[0]['scope'][scoped.SCOPE_KEY]=='open-window-SYNTHETIC'
            assert 'reader_acceptance_budget' not in c['db'].users.rows[0]
            for suffix in ('','/timestamps','/vtt','/metadata'):
                p=f'/api/reader/book/{opened.SLUG}/audiobook/packages/{c["package"]["package_version"]}/segments/chapter-001-full'+suffix
                response=await client.get(p,headers={**inherited.signed('GET',p),'range':'bytes=0-99'})
                assert response.status_code==206,response.text
            assert len(c['seen'])==4
        assert c['db'][scoped.WORKFLOWS].rows[0]['used_credit_seconds']==61
    asyncio.run(run())


def test_open_same_retained_counter_after_actual_synthetic_proof_promotion_uses_public_presentation(composed):
    async def run():
        c=composed;before=copy.deepcopy(c['db'][scoped.GRANTS].rows)
        source_fixtures.release.promote(c['root'],snapshot_record=c['source_snapshot'],
            decision_id='india-fixture-the-open-window-scoped-public-carry',approved_by='SYNTHETIC_FIXTURE_ONLY',
            generated_at=datetime.now(timezone.utc).isoformat(),apply=True,
            **__import__('test_open_window_continuous_acceptance').arguments(c['package']))
        for loaded in {truth,importlib.import_module(server.load_controlled_artifact_book.__module__)}:loaded.clear_controlled_artifact_caches()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            await inherited.start(client)
            p=f'/api/reader/book/{opened.SLUG}/audiobook/manifest';r=await client.get(p,headers=inherited.signed('GET',p))
            assert r.status_code==200,r.text
            assert r.json()['package_version']==c['package']['package_version'] and r.json().get('transport_canary') is None
        after=c['db'][scoped.GRANTS].rows;assert len(after)==1 and after[0]['_id']==before[0]['_id'] and after[0]['workflow_id']==before[0]['workflow_id']
        assert c['db'][scoped.WORKFLOWS].rows[0]['used_credit_seconds']==61
    asyncio.run(run())


def test_open_expired_retained_open_grant_denies_normal_start_before_new_lease_billing_or_storage(composed):
    async def run():
        c=composed;g=c['db'][scoped.GRANTS].rows[0];now=datetime.now(timezone.utc)
        g.update(created_at=now-timedelta(minutes=2),expires_at=now-timedelta(seconds=1))
        counters=copy.deepcopy(c['db'][scoped.WORKFLOWS].rows)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            p='/api/reading-pass/sessions/start';r=await client.post(p,json=inherited.start_body(),headers=inherited.signed('POST',p))
            assert r.status_code==403 and r.json()['detail']['code']=='NATIVE_REPLACEMENT_SCOPE_DENIED'
        assert not c['db'].reading_pass_sessions.rows and not c['seen'] and not c['db'].wallet_ledger.rows
        assert c['db'][scoped.WORKFLOWS].rows==counters and c['db'].users.rows[0]['reading_seconds_balance']==300
    asyncio.run(run())


@pytest.mark.parametrize('cap',[None,{'status':'disabled','maximum_seconds':600},{'status':'enabled','maximum_seconds':600}])
def test_open_native_scope_never_bypasses_any_retained_user_cap(composed,cap):
    async def run():
        c=composed;c['db'].users.rows[0]['reader_acceptance_budget']=cap
        before=copy.deepcopy(c['db'][scoped.WORKFLOWS].rows)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://fixture') as client:
            p='/api/reading-pass/sessions/start';r=await client.post(p,json=inherited.start_body(),headers=inherited.signed('POST',p))
            assert r.status_code==403 and r.json()['detail']['code']=='NATIVE_REPLACEMENT_SCOPE_DENIED'
        assert not c['db'].reading_pass_sessions.rows and not c['seen'] and not c['db'].wallet_ledger.rows
        assert c['db'][scoped.WORKFLOWS].rows==before and c['db'].users.rows[0]['reading_seconds_balance']==300
    asyncio.run(run())
