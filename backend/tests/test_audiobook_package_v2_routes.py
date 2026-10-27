"""Current protected-package routes: real Request/Response and immutable binding.

No database, provider access, paid sessions or legacy MP3 publication are needed.
"""
import asyncio
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

@pytest.fixture
def server(monkeypatch):
    monkeypatch.setenv('MONGODB_URL', 'mongodb://localhost:27017/earnalism_test')
    monkeypatch.setenv('JWT_SECRET', 'isolated-package-route-test')
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    value=importlib.import_module('server')
    monkeypatch.setattr(value,'READING_PASS_V2_ENABLED',True)
    return value

@pytest.fixture
def book(server):
    return server._controlled_artifact_doc('the-open-window', include_content=False)

def request(method='GET', headers=None):
    return Request({'type':'http','method':method,'path':'/api/reader/book/the-open-window/audiobook/manifest','headers':[(k.encode(),v.encode()) for k,v in (headers or {}).items()],'query_string':b''})

def test_exact_accepted_package_selection_is_deterministic(server,book):
    first=server._selected_audiobook_package(book,'the-open-window',request())[0]
    second=server._selected_audiobook_package(book,'the-open-window',request())[0]
    assert first and first['package_version']==second['package_version']
    assert first['segment_count']==29 and first['duration_ms']==491436
    assert not book.get('audiobook_assets',{}).get('mp3')

@pytest.mark.parametrize('method',['GET','HEAD'])
def test_manifest_current_response_and_method_contract(server,book,monkeypatch,method):
    async def resolve(slug):return book
    async def authorized(req,principal,slug):return {'session_id':'synthetic-only'}
    monkeypatch.setattr(server,'_reader_audio_package_book_for_slug',resolve)
    monkeypatch.setattr(server,'_authorize_reading_pass_audio',authorized)
    result=asyncio.run(server.reader_book_audiobook_package_manifest('the-open-window',request(method),None))
    assert isinstance(result,Response) and result.status_code==200
    assert result.headers['cache-control']=='private, no-store'
    if method=='HEAD':assert result.body==b'' and int(result.headers['content-length'])>0
    else:
        manifest=json.loads(result.body)
        assert 'backblaze' not in result.body.decode().lower()
        assert manifest['package_version']==server._selected_audiobook_package(book,'the-open-window',request())[0]['package_version']

@pytest.mark.parametrize('code',[401,403])
@pytest.mark.parametrize('kind',['manifest','segment'])
def test_denial_happens_before_package_or_storage_resolution(server,monkeypatch,code,kind):
    async def deny(*args):raise HTTPException(status_code=code,detail='synthetic denial')
    async def forbidden(*args):raise AssertionError('denied request reached package/storage')
    monkeypatch.setattr(server,'_authorize_reading_pass_audio',deny)
    monkeypatch.setattr(server,'_reader_audio_package_book_for_slug',forbidden)
    with pytest.raises(HTTPException) as error:
        if kind=='manifest':asyncio.run(server.reader_book_audiobook_package_manifest('the-open-window',request(),None))
        else:asyncio.run(server.reader_book_audiobook_package_segment('the-open-window','wrong','unknown',request(),None))
    assert error.value.status_code==code

def test_missing_lease_actual_authorizer_fails_closed(server):
    with pytest.raises(HTTPException) as error:asyncio.run(server._authorize_reading_pass_audio(request(),None,'the-open-window'))
    assert error.value.status_code==401

@pytest.mark.parametrize('mutation',['version','segment'])
def test_unknown_package_identity_never_reaches_storage(server,book,monkeypatch,mutation):
    async def resolve(slug):return book
    async def forbidden(*args,**kwargs):raise AssertionError('invalid package reached storage')
    monkeypatch.setattr(server,'_reader_audio_package_book_for_slug',resolve)
    monkeypatch.setattr(server,'_stream_audiobook_asset_url',forbidden)
    p=server._selected_audiobook_package(book,'the-open-window',request())[0]
    sid=p['tracks'][0]['chunks'][0]['segment_id']
    with pytest.raises(HTTPException) as error:asyncio.run(server._reader_book_audiobook_package_segment('the-open-window','invalid' if mutation=='version' else p['package_version'],'invalid' if mutation=='segment' else sid,'mp3',request()))
    assert error.value.status_code==404

@pytest.mark.parametrize('asset',['mp3','timestamps','vtt','metadata'])
@pytest.mark.parametrize('method',['GET','HEAD'])
def test_segment_passes_immutable_object_version_and_real_request(server,book,monkeypatch,asset,method):
    async def resolve(slug):return book
    calls=[]
    async def stream(slug,key,url,req,**kwargs):
        calls.append((key,req.method,kwargs));return Response(b'' if req.method=='HEAD' else b'synthetic bytes')
    monkeypatch.setattr(server,'_reader_audio_package_book_for_slug',resolve)
    monkeypatch.setattr(server,'_stream_audiobook_asset_url',stream)
    monkeypatch.setattr(server,'_audio_package_storage_url',lambda storage:'https://storage.example.invalid/immutable')
    p=server._selected_audiobook_package(book,'the-open-window',request())[0]
    sid=p['tracks'][0]['chunks'][0]['segment_id']
    result=asyncio.run(server._reader_book_audiobook_package_segment('the-open-window',p['package_version'],sid,asset,request(method)))
    assert result.status_code==200 and len(calls)==1
    assert calls[0][1]==method and calls[0][2]['version_id']
    assert calls[0][2]['extra_headers']['X-Audiobook-Package-Version']==p['package_version']

@pytest.mark.parametrize('value',['bytes=-','bytes=200-300'])
def test_unsatisfiable_or_malformed_range_remains_416(server,monkeypatch,value):
    storage={'bucket':'synthetic'}
    monkeypatch.setattr(server,'_b2_storage_for_url',lambda url:storage)
    monkeypatch.setattr(server,'_b2_key_from_url',lambda url,store:'synthetic.mp3')
    monkeypatch.setattr(server,'_b2_client',lambda store:object())
    async def head(*args,**kwargs):return {'ContentLength':100,'ContentType':'audio/mpeg'}
    async def get(*args,**kwargs):
        error=Exception('synthetic range');error.response={'ResponseMetadata':{'HTTPStatusCode':416}};raise error
    monkeypatch.setattr(server,'_b2_head_object',head);monkeypatch.setattr(server,'_b2_get_object',get)
    result=asyncio.run(server._stream_audiobook_asset_url('the-open-window','mp3','https://example.invalid/private',request(headers={'range':value}),version_id='immutable'))
    assert result.status_code==416 and result.headers['content-range']=='bytes */100'
