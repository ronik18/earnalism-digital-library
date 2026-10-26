"""Mounted renewal route plus native lease/accounting, synthetic account only."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from datetime import timedelta

import httpx
import pytest
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from backend.domain.reading_pass import ReadingPassError, ReadingPassConfig
from backend.tests.test_open_window_audio_acceptance_budget import fixture, start


class Renewal(BaseModel):
    session_id: str
    lease_version: int
    sequence: int
    idempotency_key: str
    active: bool
    playback_state: str
    text_phase: str = ''


def application(db,service,secure):
    async def user():return {'id':'user-1','session_id':'auth-1'}
    ns=dict(Depends=Depends,require_user=user,ReadingPassLeaseRenewIn=Renewal,
        Request=Request,Response=Response,HTTPException=HTTPException,
        _reading_pass_enabled_or_404=lambda:None,db=db,reading_pass_service=service,
        _invalidate_user_cache=AsyncMock(),_set_user_wallet_cache=AsyncMock(),
        ReadingPassError=ReadingPassError,_reading_pass_http_error=lambda e:HTTPException(e.status_code,e.payload()),
        COOKIE_SECURE=secure,READING_PASS_CONFIG=ReadingPassConfig())
    source=Path(__file__).resolve().parents[1]/'server.py'
    names={'_set_reading_pass_media_cookies','_clear_reading_pass_media_cookies','_reading_pass_lease_headers','reading_pass_lease_renew'}
    nodes=[n for n in ast.parse(source.read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    for n in nodes:n.decorator_list=[]
    tree=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree),str(source),'exec'),ns)
    app=FastAPI();app.post('/api/reading-pass/leases/renew')(ns['reading_pass_lease_renew'])
    @app.get('/test/start')
    async def begin(response:Response):
        lease=await start(service);ns['_set_reading_pass_media_cookies'](response,lease)
        return {k:v for k,v in lease.items() if k not in ('lease_token',)}
    @app.get('/api/reader/book/the-open-window/audiobook/test-segment')
    async def segment(request:Request):
        sid,token=ns['_reading_pass_lease_headers'](request)
        if not sid or not token:raise HTTPException(401,{'code':'AUTH_REQUIRED'})
        try:await service.authorize_media_credential(session_id=sid,lease_token=token,content_type='audio',content_id='the-open-window')
        except ReadingPassError as error:raise HTTPException(error.status_code,error.payload())
        return Response(b'synthetic',status_code=206)
    return app


@pytest.mark.parametrize('secure',[False,True])
def test_paused_renewal_retains_media_access_then_resumes_with_native_accounting(monkeypatch,secure):
    async def run():
        clock,db,_,service=fixture(monkeypatch)
        db.users.rows[0].pop('reader_acceptance_budget') # normal Reading Pass, no custom cap
        app=application(db,service,secure)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test' if secure else 'http://test') as client:
            lease=(await client.get('/test/start')).json()
            assert (await client.get('/api/reader/book/the-open-window/audiobook/test-segment')).status_code==206
            async def renew(seq,active,state):
                return await client.post('/api/reading-pass/leases/renew',json=dict(session_id=lease['session_id'],lease_version=seq,sequence=seq,idempotency_key=f'test-{seq}',active=active,playback_state=state))
            clock[0]+=timedelta(seconds=10)
            paused=await renew(1,False,'paused');assert paused.status_code==200
            assert paused.json()['status']=='Paused' and paused.json()['deducted_seconds']==0
            assert (await client.get('/api/reader/book/the-open-window/audiobook/test-segment')).status_code==403
            headers=paused.headers.get_list('set-cookie');assert len(headers)==2
            assert all('HttpOnly' in h and 'Path=/api' in h for h in headers)
            assert all(('Secure' in h)==secure for h in headers)
            assert all(('SameSite=none' if secure else 'SameSite=lax') in h for h in headers)
            resumed=await renew(2,True,'playing');assert resumed.status_code==200
            assert (await client.get('/api/reader/book/the-open-window/audiobook/test-segment')).status_code==206
            clock[0]+=timedelta(seconds=10)
            billed=await renew(3,True,'playing');assert billed.json()['deducted_seconds']==10
            assert sum(x['debit'] for x in db.wallet_ledger.rows)==10
            assert db.users.rows[0]['reading_seconds_balance']==db.users.rows[0]['wallet_seconds']==990
            clock[0]+=timedelta(seconds=60)
            expired=await renew(4,True,'playing');assert expired.status_code==403
            assert (await client.get('/api/reader/book/the-open-window/audiobook/test-segment')).status_code==403
    asyncio.run(run())

@pytest.mark.parametrize('state',['Expired','Exhausted','Ended'])
def test_terminal_audio_renewal_still_clears_cookies(monkeypatch,state):
    async def run():
        _,db,_,service=fixture(monkeypatch)
        service.renew_lease=AsyncMock(return_value={'status':state,'content_type':'audio','balance_seconds':1000})
        app=application(db,service,True)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as client:
            await client.get('/test/start')
            response=await client.post('/api/reading-pass/leases/renew',json=dict(session_id='test',lease_version=1,sequence=1,idempotency_key='terminal',active=False,playback_state='paused'))
            assert response.status_code==200
            assert len(response.headers.get_list('set-cookie'))==2
            assert all('Max-Age=0' in h for h in response.headers.get_list('set-cookie'))
    asyncio.run(run())
