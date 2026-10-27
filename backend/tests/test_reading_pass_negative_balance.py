import os
os.environ.setdefault("MONGODB_URL", "mongodb://127.0.0.1:1/offline_dummy")
os.environ.setdefault("JWT_SECRET", "negative-balance-dummy-test-secret")
import asyncio
import pytest
from fastapi.testclient import TestClient
from backend import server
from backend.domain.reading_pass import ReadingPassConfig, ReadingPassError
from backend.tests import test_reading_pass_service_concurrency as fixtures
from backend import reading_pass_service as candidate
USER={'id':'user-1','role':'user','status':'active','session_id':'auth-1'}

@pytest.mark.parametrize('balance',[-1,-100])
@pytest.mark.parametrize('route',['wallet','sessions/start','sessions/transfer'])
def test_negative_balance_http_returns_safe_503_without_mutation(monkeypatch,balance,route):
    db=fixtures.Database(balance=balance)
    svc=candidate.ReadingPassService(db=db,client=fixtures.Client(),config=ReadingPassConfig(),token_secret='dummy')
    async def approved(slug): return {'slug':slug}
    monkeypatch.setattr(server,'READING_PASS_V2_ENABLED',True)
    monkeypatch.setattr(server,'reading_pass_service',svc)
    monkeypatch.setattr(server,'_reader_audio_package_book_for_slug',approved)
    server.app.dependency_overrides[server.require_user]=lambda:USER
    client=TestClient(server.app,raise_server_exceptions=False)
    try:
        if route=='wallet': result=client.get('/api/reading-pass/wallet')
        else: result=client.post('/api/reading-pass/'+route,json={'device_id':'dummy-device-001','content_type':'audio','content_id':'dummy','media_position_seconds':0})
        assert result.status_code==503,result.text
        assert result.json()['detail']['code']=='BALANCE_UNAVAILABLE'
        assert 'safe integer' not in result.text
        assert not result.headers.get('set-cookie')
        assert db.users.rows[0]['reading_seconds_balance']==balance
        for name in ('wallet_ledger','wallet_transactions','reading_pass_sessions','reading_pass_devices','reading_pass_audit'):
            assert getattr(db,name).rows==[]
    finally:
        server.app.dependency_overrides.pop(server.require_user,None);client.close()

@pytest.mark.parametrize('slug',['a-ghost-story','the-tell-tale-heart','radharani'])
def test_legitimate_free_reader_entitlements_preserved(monkeypatch,slug):
    monkeypatch.setattr(fixtures,'ReadingPassService',candidate.ReadingPassService)
    fixtures.test_free_india_pilot_lease_reads_beyond_preview_without_wallet_debit(slug)

@pytest.mark.parametrize('kind',['text','audio'])
def test_zero_balance_remains_pass_required(kind):
    async def scenario():
        db=fixtures.Database(balance=0)
        svc=candidate.ReadingPassService(db=db,client=fixtures.Client(),config=ReadingPassConfig(),token_secret='dummy')
        with pytest.raises(ReadingPassError) as denied:
            await svc.start_session(user_id='user-1',auth_session_id='auth-1',device_id='dummy-device-001',device_label='Dummy',content_type=kind,content_id='dummy',scope={'canonical_page_index':4})
        assert denied.value.code=='PASS_REQUIRED'
        assert db.wallet_ledger.rows==db.reading_pass_sessions.rows==[]
    asyncio.run(scenario())
