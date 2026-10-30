"""Source-only and admitted loopback tests, never a provider/production target."""
import ast
import asyncio
from contextvars import ContextVar
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from backend import public_metadata_cache as m
from backend.tests.public_metadata_fixtures import database

ROOT=Path(__file__).resolve().parents[2]

def run(coroutine):return asyncio.run(coroutine)


def test_control_concerns_bounds_and_off_passive():
    async def case():
        db=database();c=m.Control(db)
        assert await c.begin(False) is None
        assert [x[0] for x in c.collection.calls]==['read']
        assert c.collection.options['read_concern'].document=={'level':'linearizable'}
        assert c.collection.options['write_concern'].document=={'w':'majority','j':True,'wtimeout':2000}
        assert c.collection.options['read_preference'].name=='Primary'
        assert c.collection.calls[0][2]['max_time_ms']==2000
    run(case())


def test_startup_rotates_valid_epoch_and_never_unfences():
    async def case():
        c=m.Control(database());assert await c.startup();old=(await c.read())['epoch']
        assert await c.startup();assert (await c.read())['epoch']!=old
        token=await c.begin(True);fence=await c.read()
        assert not await c.startup() and (await c.read())==fence
        with pytest.raises(ValueError):await c.begin(True)
        with pytest.raises(ValueError):await c.finish('f'*32)
        assert (await c.read())==fence
        await c.finish(token);assert (await c.read())['state']=='ACTIVE'
    run(case())


@pytest.mark.parametrize('row',[{}, {'_id':m.CONTROL_ID,'state':'ACTIVE','epoch':'bad','token':None}, {'_id':m.CONTROL_ID,'state':'FENCED','epoch':'a'*32,'token':None}])
def test_malformed_authority_is_never_reset(row):
    async def case():
        db=database();db.public_metadata_cache_control.row=row;c=m.Control(db)
        with pytest.raises(ValueError):await c.startup()
        assert not any(x[0] in {'insert','cas'} for x in c.collection.calls)
    run(case())


def test_exception_and_cancel_keep_durable_fence_across_new_control():
    async def case():
        db=database();c=m.Control(db);await c.startup()
        with pytest.raises(RuntimeError):
            async with m.mutation(db,True):raise RuntimeError('source commit unknown')
        assert (await m.Control(db).read())['state']=='FENCED'
        assert not await m.Control(db).startup()
    run(case())


def test_child_context_inheritance_does_not_bypass_fence():
    async def case():
        db=database();await m.Control(db).startup()
        async with m.mutation(db,True):
            assert m.mutation_held(db)
            async with m.mutation(db,True):pass
            async def child():
                assert not m.mutation_held(db)
                with pytest.raises(ValueError):
                    async with m.mutation(db,True):raise AssertionError('child handler entered')
            await asyncio.create_task(child())
    run(case())


@pytest.mark.parametrize('value',[b'not-json',{'x':b'private'}, {'x':float('nan')}, {'x':'data:audio/mp3;base64,AA'}, {'x':'x'*(m.MAX_STRING+1)}, {'x':1<<128}])
def test_json_type_and_size_denials(value):
    with pytest.raises(ValueError):m.encode(value)


def test_cumulative_bound_before_dumps_and_nonbmp():
    with patch.object(m.json,'dumps',side_effect=AssertionError('must reject before serialization')):
        with pytest.raises(ValueError):m.encode(['x'*m.MAX_STRING]*200)
        with pytest.raises(ValueError):m.encode(['\U0001f600'*12000])
    assert m.decode(m.encode({'value':['exact',1,None,True]}))=={'value':['exact',1,None,True]}
    with pytest.raises(ValueError):m.decode(b'x'*(m.MAX_BYTES+1))


def test_fixed_slot_count_covers_retained_epochs():
    assert len({m.slot('p',str(i)+':'+str(epoch))[0] for epoch in range(20) for i in range(1000)})<=m.SLOTS
    assert 'HSTRLEN' in m.READ and '131072' in m.FILL


def server_bindings(db):
    from backend.tests.test_public_metadata_redis import bindings
    ns=bindings(None,'resilient-offline');ns.update(db=db,metadata_cache=m,_public_metadata_source_binding=lambda:'a'*64)
    # The bindings fixture covers legacy helpers; switch explicit optional mode.
    ns.update(REDIS_CACHE_ENABLED=False,MULTI_REPLICA_ENABLED=False,REDIS_PUBLIC_METADATA_ENABLED=True)
    return ns


def test_known_success_finish_failure_preserves_result_and_fence():
    async def case():
        import functools,logging
        from fastapi import HTTPException,Response
        db=database();await m.Control(db).startup();db.public_metadata_cache_control.fail_finish=True
        ns=server_bindings(db);ns.update(wraps=functools.wraps,HTTPException=HTTPException,Response=Response,logger=logging.getLogger('dummy'))
        tree=ast.parse((ROOT/'backend/server.py').read_text())
        for name in ['_clear_local_public_metadata','_public_metadata_mutation']:
            node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-server','exec'),ns)
        calls=[]
        async def handler():calls.append('committed');return {'ok':True}
        assert await ns['_public_metadata_mutation'](handler)()=={'ok':True}
        assert calls==['committed'] and (await m.Control(db).read())['state']=='FENCED'
    run(case())


def test_default_off_and_legacy_mutation_wrapper_no_control_dependency():
    async def case():
        import functools,logging
        from fastapi import HTTPException,Response
        ns=server_bindings(object());ns.update(wraps=functools.wraps,HTTPException=HTTPException,Response=Response,logger=logging.getLogger('dummy'))
        tree=ast.parse((ROOT/'backend/server.py').read_text());node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='_public_metadata_mutation');exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-server','exec'),ns)
        async def handler():return {'ok':True}
        ns['REDIS_PUBLIC_METADATA_ENABLED']=False;assert await ns['_public_metadata_mutation'](handler)()=={'ok':True}
        ns['REDIS_PUBLIC_METADATA_ENABLED']=True;ns['REDIS_CACHE_ENABLED']=True;assert await ns['_public_metadata_mutation'](handler)()=={'ok':True}
    run(case())


def test_real_mongo_redis_cross_process_fence_restart_and_bounded_slots():
    import os,sys,subprocess,uuid
    if os.environ.get('EARNALISM_REDIS_INTEGRATION')!='1' or os.environ.get('READER_SEGMENT_MONGO_INTEGRATION')!='1':
        pytest.skip('explicit isolated Redis and authenticated Mongo fixtures required')
    from backend.tests.test_shared_redis_limiter_integration import _endpoint
    from scripts.uat_mongo_fixture import isolated_database
    async def case():
        import redis.asyncio as redis
        async with isolated_database('public_metadata_it_') as (_,db):
            c=m.Control(db);assert await c.startup()
            initial=(await c.read())['epoch']
            admissions=await asyncio.gather(c.startup(),m.Control(db).startup())
            assert any(admissions) and (await c.read())['state']=='ACTIVE'
            assert (await c.read())['epoch']!=initial
            contenders=await asyncio.gather(c.begin(True),m.Control(db).begin(True),return_exceptions=True)
            winners=[v for v in contenders if isinstance(v,str)]
            assert len(winners)==1 and sum(isinstance(v,ValueError) for v in contenders)==1
            with pytest.raises(ValueError):await c.finish('wrong-token')
            assert (await c.read())['state']=='FENCED'
            await c.finish(winners[0])
            client=redis.from_url(_endpoint(),socket_timeout=1,socket_connect_timeout=1,retry_on_timeout=False)
            prefix='durable-it-'+uuid.uuid4().hex;known=set()
            ns=server_bindings(db);ns.update(_redis_client=client,_redis_available=True,REDIS_KEY_PREFIX=prefix)
            async def get(key):return await ns['_public_cache_get'](key)
            async def put(key,value):
                slot,_=m.slot(prefix,key+':source:'+'a'*64);known.add(slot)
                await ns['_public_cache_set'](key,value)
            def worker(mode):
                result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',mode,db.name],env=os.environ,cwd=ROOT,capture_output=True,text=True,timeout=12)
                return result
            try:
                key='categories:real'
                assert await get(key) is None;await put(key,{'revision':'old'})
                assert await get(key)=={'revision':'old'}
                read=await asyncio.to_thread(worker,'read');assert read.returncode==0;assert json.loads(read.stdout)['state']=='ACTIVE'
                # Worker dies with durable fence held. Parent and fresh Control
                # see it; Redis restored stale payload cannot bypass authority.
                dead=await asyncio.to_thread(worker,'crash_fence');assert dead.returncode==17
                blocked=await c.read();assert blocked['state']=='FENCED'
                assert not await m.Control(db).startup()
                assert await get(key) is None
                await put(key,{'revision':'must-not-fill'})
                slot,logical=m.slot(prefix,key+':source:'+'a'*64)
                await client.hset(slot,mapping={'epoch':'0'*32,'key':logical,'body':m.encode({'revision':'restored-old'})})
                assert await get(key) is None
                # This is synthetic known-outcome reconciliation, not automatic
                # production recovery: no source mutation was run by the worker.
                await c.finish(blocked['token']);assert await get(key) is None
                await put(key,{'revision':'current'});assert await get(key)=={'revision':'current'}
                # A pre-invalidation ticket cannot fill after source generation.
                ns['_public_cache_ticket'](key,('durable',(await c.read())['epoch'],'a'*64))
                await c.rotate();await put(key,{'revision':'late-old'});assert await get(key) is None
                # Simulate OFF write interval; new startup rotates Mongo epoch,
                # never trusts retained Redis values or a SETNX marker.
                await put(key,{'revision':'before-disable'})
                assert await c.startup();assert await get(key) is None
                # One fixed slot can contain only its exact logical digest.
                collision={}
                pair=None
                for i in range(1000):
                    k='categories:collision'+str(i);s,_=m.slot(prefix,k+':source:'+'a'*64)
                    if s in collision:pair=(collision[s],k);break
                    collision[s]=k
                assert pair
                for k in pair:assert await get(k) is None;await put(k,{'key':k})
                assert await get(pair[0]) is None and await get(pair[1])=={'key':pair[1]}
                # Oversized restored entry is rejected in Lua before body HGET.
                slot,logical=m.slot(prefix,key+':source:'+'a'*64);known.add(slot)
                await client.hset(slot,mapping={'epoch':(await c.read())['epoch'],'key':logical,'body':b'x'*(m.MAX_BYTES+1)})
                assert await get(key) is None
                # New measured source cannot consume an old worker's payload.
                await put(key,{'revision':'source-a'});ns['_public_metadata_source_binding']=lambda:'b'*64
                assert await get(key) is None
                assert len(known)<=m.SLOTS
            finally:
                if known:await client.delete(*known)
                await client.aclose()
    run(asyncio.wait_for(case(),70))


def _worker():
    import os,re,sys
    from scripts.uat_mongo_fixture import setup_configuration
    if len(sys.argv)!=4 or sys.argv[1]!='--worker' or sys.argv[2] not in {'read','crash_fence'} or not re.fullmatch('public_metadata_it_[0-9a-f]{32}',sys.argv[3]):
        raise ValueError('Only explicit synthetic worker namespace admitted')
    if os.environ.get('EARNALISM_REDIS_INTEGRATION')!='1' or os.environ.get('READER_SEGMENT_MONGO_INTEGRATION')!='1':raise ValueError('Explicit fixtures required')
    config=setup_configuration(os.environ)
    async def case():
        from motor.motor_asyncio import AsyncIOMotorClient
        client=AsyncIOMotorClient(f"mongodb://127.0.0.1:{config['port']}/?replicaSet=earnalism-uat-rs0",username=config['principal'],password=config['password'],authSource='admin',serverSelectionTimeoutMS=2000,connectTimeoutMS=2000,socketTimeoutMS=4000)
        try:
            c=m.Control(client[sys.argv[3]])
            if sys.argv[2]=='read':print(json.dumps({'state':(await c.read())['state']}),flush=True)
            else:
                await c.begin(True,operation='inert_worker_no_source_mutation')
                os._exit(17)
        finally:client.close()
    run(case())



def test_positive_mutation_coverage_excludes_financial_and_upload_staging():
    tree=ast.parse((ROOT/'backend/server.py').read_text())
    guarded={n.name for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and any(isinstance(d,ast.Name) and d.id=='_public_metadata_mutation' for d in n.decorator_list)}
    assert guarded=={'_bootstrap_reader_segment_candidate','admin_ingest_catalogue_evidence','admin_create_book','admin_update_book','admin_update_book_audiobook','admin_release_audiobook','admin_update_home_curation','admin_delete_book','admin_import_book_template','admin_add_chapter','admin_reorder_chapters','admin_update_chapter','admin_delete_chapter','admin_promote_cover','admin_upload_chapter_file','admin_create_cat','admin_update_cat','admin_delete_cat','admin_set_social','admin_set_brand','admin_set_featured','admin_promote_reading_pass_segments','admin_bootstrap_reading_pass_segments','admin_revoke_reading_pass_text_publication'}
    for n in tree.body:
        if isinstance(n,ast.AsyncFunctionDef) and n.name in guarded and n.name.startswith('admin_'):
            assert 'Depends(require_admin)' in ast.unparse(n.args)


def test_public_optional_startup_timeout_policy_soft_failure_and_no_config():
    import logging
    from unittest.mock import patch
    async def case():
        tree=ast.parse((ROOT/'backend/server.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='initialize_replica_state_backends')
        ns=dict(ENABLE_STARTUP_DB_MAINTENANCE=False,asyncio=asyncio,REDIS_CACHE_ENABLED=False,MULTI_REPLICA_ENABLED=False,REDIS_PUBLIC_METADATA_ENABLED=True,REDIS_CACHE_FAIL_FAST=True,REDIS_URL='redis://127.0.0.1:26379/0',REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS=2,REDIS_SOCKET_TIMEOUT_SECONDS=2,_redis_available=False,_redis_client=None,logger=logging.getLogger('dummy'))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-initializer','exec'),ns)
        class Down:
            closed=False
            async def ping(self):raise TimeoutError('inert optional startup outage')
            async def aclose(self):self.closed=True
        down=Down()
        with patch('redis.asyncio.from_url',return_value=down) as construct:
            await ns['initialize_replica_state_backends']()
        assert not ns['_redis_available'] and ns['_redis_client'] is None and down.closed
        assert construct.call_args.kwargs=={'socket_connect_timeout':.25,'socket_timeout':.25,'retry_on_timeout':False}
    run(case())


def test_lookup_authority_deadline_bypasses_without_reset_or_write():
    async def case():
        db=database()
        async def blocked(*a,**kw):await asyncio.sleep(2)
        db.public_metadata_cache_control.find_one=blocked
        started=asyncio.get_running_loop().time()
        with pytest.raises((TimeoutError,asyncio.TimeoutError)):await m.Control(db).read(cache=True)
        assert asyncio.get_running_loop().time()-started<.7
        assert db.public_metadata_cache_control.row is None
    run(case())


def test_external_ingest_refuses_active_control_without_fence_before_transaction():
    async def case():
        db=database();await m.Control(db).startup()
        with pytest.raises(ValueError):await m.reject_unsupported_writer_async(db)
        async with m.mutation(db,True):await m.reject_unsupported_writer_async(db)
    run(case())



def test_unauthenticated_metadata_write_never_acquires_fence(monkeypatch):
    import os
    os.environ.setdefault('MONGODB_URL','mongodb://127.0.0.1:27018/unused_dummy')
    os.environ.setdefault('JWT_SECRET','isolated-local-source-test')
    async def case():
        from backend import server
        import httpx
        db=database();monkeypatch.setattr(server,'db',db)
        monkeypatch.setattr(server,'REDIS_PUBLIC_METADATA_ENABLED',True)
        monkeypatch.setattr(server,'REDIS_CACHE_ENABLED',False)
        monkeypatch.setattr(server,'MULTI_REPLICA_ENABLED',False)
        monkeypatch.setattr(server,'RATE_LIMIT_ENABLED',False)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://isolated-dummy') as web:
            result=await web.post('/api/admin/categories',json={'name':'dummy','slug':'dummy'})
            assert result.status_code==401
        assert db.public_metadata_cache_control.calls==[]
    run(case())


def test_real_sdk_stalled_loopback_read_is_bounded_without_retry():
    import os,socket,threading,time
    if os.environ.get('EARNALISM_REDIS_INTEGRATION')!='1':pytest.skip('explicit local runtime fixture required')
    from backend.tests.test_shared_redis_limiter_integration import _endpoint
    _endpoint()  # Opt-in itself must admit a strict loopback disposable target.
    listener=socket.socket();listener.bind(('127.0.0.1',26474));listener.listen(1);listener.settimeout(1)
    accepted=[]
    def stall():
        try:
            conn,_=listener.accept();accepted.append(True)
            with conn:time.sleep(.7)
        except OSError:pass
        finally:listener.close()
    thread=threading.Thread(target=stall,daemon=True);thread.start()
    async def case():
        import redis.asyncio as redis
        db=database();await m.Control(db).startup()
        client=redis.from_url('redis://127.0.0.1:26474/0',socket_connect_timeout=.25,socket_timeout=.25,retry_on_timeout=False)
        ns=server_bindings(db);ns.update(_redis_client=client,_redis_available=True)
        started=time.monotonic()
        try:
            assert await ns['_public_cache_get']('categories:stalled') is None
            assert time.monotonic()-started<.65
            assert ns['_cache_stats']['public-cache_read_error']==1
            assert accepted==[True]
        finally:await client.aclose()
    try:run(case())
    finally:thread.join(1.2);listener.close()



def test_actual_task_cancellation_retains_fence():
    async def case():
        db=database();await m.Control(db).startup();held=asyncio.Event()
        async def writer():
            async with m.mutation(db,True,operation='inert_cancel'):
                held.set();await asyncio.sleep(10)
        task=asyncio.create_task(writer());await held.wait();task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert (await m.Control(db).read())['state']=='FENCED'
        assert not await m.Control(db).startup()
    run(case())


def test_applied_finish_lost_reply_preserves_success_and_old_token_cannot_rewind():
    async def case():
        import functools,logging
        from fastapi import HTTPException,Response
        db=database();await m.Control(db).startup();collection=db.public_metadata_cache_control
        original=collection.find_one_and_update;tokens=[]
        async def lost(query,update,**kwargs):
            result=await original(query,update,**kwargs)
            if update['$set'].get('state')=='ACTIVE' and result:
                tokens.append(query['token']);raise TimeoutError('inert applied finish reply lost')
            return result
        collection.find_one_and_update=lost
        ns=server_bindings(db);ns.update(wraps=functools.wraps,HTTPException=HTTPException,Response=Response,logger=logging.getLogger('dummy'))
        tree=ast.parse((ROOT/'backend/server.py').read_text())
        for name in ['_clear_local_public_metadata','_public_metadata_mutation']:
            node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-server','exec'),ns)
        calls=[]
        async def handler():calls.append('committed');return {'ok':True}
        assert await ns['_public_metadata_mutation'](handler)()=={'ok':True}
        current=await m.Control(db).read();assert current['state']=='ACTIVE' and calls==['committed']
        collection.find_one_and_update=original
        with pytest.raises(ValueError):await m.Control(db).finish(tokens[0])
        assert await m.Control(db).read()==current
    run(case())

def test_background_bootstrap_is_fenced_and_maintenance_combination_rejected():
    tree=ast.parse((ROOT/'backend/server.py').read_text())
    bootstrap=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='_bootstrap_reader_segment_candidate')
    assert any(isinstance(d,ast.Name) and d.id=='_public_metadata_mutation' for d in bootstrap.decorator_list)
    node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='initialize_replica_state_backends')
    ns=dict(REDIS_PUBLIC_METADATA_ENABLED=True,REDIS_CACHE_ENABLED=False,
            MULTI_REPLICA_ENABLED=False,ENABLE_STARTUP_DB_MAINTENANCE=True)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-initializer','exec'),ns)
    with patch('redis.asyncio.from_url',side_effect=AssertionError('must reject before Redis')):
        with pytest.raises(RuntimeError,match='maintenance OFF'):
            run(ns['initialize_replica_state_backends']())


if __name__=='__main__':_worker()
