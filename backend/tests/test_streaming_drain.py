"""Actual ASGI response lifecycle; no listener, provider or customer session."""
import ast
import asyncio
import json
import logging
from pathlib import Path
import time
import unittest
import uuid

from fastapi import FastAPI
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from backend.utils.streaming_drain import StreamingDrainMiddleware

SERVER = Path(__file__).resolve().parents[1] / 'server.py'
SCOPE = {'type':'http','asgi':{'version':'3.0'},'method':'GET','path':'/fixture',
         'raw_path':b'/fixture','query_string':b'','headers':[],'scheme':'http',
         'server':('dummy.invalid',80),'client':('127.0.0.1',1),'http_version':'1.1'}

async def receive_forever():
    await asyncio.Event().wait()

class StreamingDrainTests(unittest.IsolatedAsyncioTestCase):
    async def test_counts_until_final_send_and_cleanup(self):
        state={'inflight':0};messages=[];release=asyncio.Event();seen=asyncio.Event()
        async def app(scope,receive,send):
            await send({'type':'http.response.start','status':206,'headers':[(b'content-range',b'bytes 0-1/2')]})
            await send({'type':'http.response.body','body':b'a','more_body':True})
            seen.set();await release.wait()
            await send({'type':'http.response.body','body':b'b'})
            self.assertEqual(state['inflight'],1)  # include background cleanup
        async def send(m):messages.append(m)
        task=asyncio.create_task(StreamingDrainMiddleware(app,state)(dict(SCOPE),receive_forever,send))
        try:
            await asyncio.wait_for(seen.wait(),2)
            self.assertEqual(state['inflight'],1)
            self.assertEqual(messages[0]['headers'],[(b'content-range',b'bytes 0-1/2')])
        finally:release.set();await asyncio.wait_for(task,2)
        self.assertEqual(state['inflight'],0)
        self.assertEqual(b''.join(m.get('body',b'') for m in messages),b'ab')

    async def test_send_failure_before_and_after_headers(self):
        for failure_type in ('http.response.start','http.response.body'):
            with self.subTest(failure_type=failure_type):
                state={'inflight':0}
                async def app(scope,receive,send):
                    await send({'type':'http.response.start','status':200,'headers':[]})
                    await send({'type':'http.response.body','body':b'dummy'})
                async def send(m):
                    if m['type']==failure_type:raise OSError('dummy send failure')
                with self.assertRaises(OSError):await StreamingDrainMiddleware(app,state)(dict(SCOPE),receive_forever,send)
                self.assertEqual(state['inflight'],0)

    async def test_cancellation_and_iterator_failure_release_once(self):
        for kind in ('cancel','iterator'):
            with self.subTest(kind=kind):
                state={'inflight':0};started=asyncio.Event()
                async def app(scope,receive,send):
                    started.set()
                    if kind=='iterator':raise ValueError('dummy iterator failure')
                    await asyncio.Event().wait()
                async def send(m):pass
                task=asyncio.create_task(StreamingDrainMiddleware(app,state)(dict(SCOPE),receive_forever,send))
                await asyncio.wait_for(started.wait(),2)
                if kind=='cancel':
                    self.assertEqual(state['inflight'],1);task.cancel()
                    with self.assertRaises(asyncio.CancelledError):await task
                else:
                    with self.assertRaises(ValueError):await task
                self.assertEqual(state['inflight'],0)

    async def test_non_http_unchanged(self):
        state={'inflight':3};seen=[]
        async def app(scope,receive,send):seen.append(scope['type'])
        await StreamingDrainMiddleware(app,state)({'type':'lifespan'},None,None)
        self.assertEqual(state['inflight'],3);self.assertEqual(seen,['lifespan'])

    async def test_concurrent_requests_account_independently(self):
        state={'inflight':0};release=[asyncio.Event(),asyncio.Event()];started=[asyncio.Event(),asyncio.Event()]
        async def app(scope,receive,send):
            i=scope['test_id'];started[i].set();await release[i].wait()
        async def send(m):pass
        wrapped=StreamingDrainMiddleware(app,state)
        tasks=[asyncio.create_task(wrapped(dict(SCOPE,test_id=i),receive_forever,send)) for i in range(2)]
        try:
            await asyncio.gather(*(asyncio.wait_for(e.wait(),2) for e in started))
            self.assertEqual(state['inflight'],2)
            release[0].set();await tasks[0];self.assertEqual(state['inflight'],1)
        finally:
            for e in release:e.set()
            await asyncio.gather(*tasks)
        self.assertEqual(state['inflight'],0)

    async def test_exact_server_middleware_stream_and_drain_denial(self):
        tree=ast.parse(SERVER.read_text());node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='production_hardening_middleware');node.decorator_list=[]
        state={'draining':False,'inflight':0}
        async def rate_limit(request):return None
        ns={'Request':Request,'uuid':uuid,'time':time,'_shutdown_state':state,'_rate_limit_retry_after':rate_limit,
            '_security_headers':lambda r:None,'_is_public_anonymous_cacheable_response':lambda *a:False,
            'logger':logging.getLogger(__name__),'_json':json,'_client_ip':lambda r:'DUMMY',
            '_json_error_response':lambda request,status_code,message,headers=None:JSONResponse({'detail':message},status_code=status_code,headers=headers)}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(SERVER),'exec'),ns)
        app=FastAPI();app.middleware('http')(ns['production_hardening_middleware'])
        opened=asyncio.Event();release=asyncio.Event();cleanup=asyncio.Event();body_seen=asyncio.Event();messages=[]
        async def background():
            self.assertEqual(state['inflight'],1);cleanup.set()
        @app.get('/fixture')
        async def fixture():
            async def body():
                opened.set();yield b'first';await release.wait();yield b'last'
            return StreamingResponse(body(),headers={'Content-Range':'bytes 0-8/9'},status_code=206,background=BackgroundTask(background))
        app.add_middleware(StreamingDrainMiddleware,state=state)
        async def send(m):
            messages.append(m)
            if m['type']=='http.response.body' and m.get('body'):body_seen.set()
        task=asyncio.create_task(app(dict(SCOPE),receive_forever,send))
        try:
            await asyncio.wait_for(body_seen.wait(),2);self.assertEqual(state['inflight'],1)
            state['draining']=True;denied=[]
            async def deny_send(m):denied.append(m)
            await app(dict(SCOPE),receive_forever,deny_send)
            self.assertEqual(denied[0]['status'],503)
            self.assertEqual(state['inflight'],1)  # earlier stream is still held
        finally:release.set();await asyncio.wait_for(task,2)
        self.assertTrue(cleanup.is_set());self.assertEqual(state['inflight'],0)
        self.assertEqual(messages[0]['status'],206)
        self.assertIn((b'content-range',b'bytes 0-8/9'),messages[0]['headers'])
        self.assertEqual(b''.join(m.get('body',b'') for m in messages),b'firstlast')

    async def test_real_stream_disconnect_and_iterator_exception(self):
        for kind in ('disconnect', 'iterator'):
            with self.subTest(kind=kind):
                state={'inflight':0}; first=asyncio.Event(); cleaned=asyncio.Event()
                async def body():
                    try:
                        yield b'dummy'
                        if kind=='iterator':raise ValueError('dummy body iterator')
                        await asyncio.Event().wait()
                    finally:cleaned.set()
                response=StreamingResponse(body())
                async def receive():
                    await first.wait()
                    if kind=='disconnect':return {'type':'http.disconnect'}
                    await asyncio.Event().wait()
                async def send(message):
                    if message['type']=='http.response.body':
                        self.assertEqual(state['inflight'],1);first.set()
                wrapped=StreamingDrainMiddleware(response,state)
                if kind=='iterator':
                    with self.assertRaises(BaseExceptionGroup):
                        await asyncio.wait_for(wrapped(dict(SCOPE),receive,send),2)
                else:await asyncio.wait_for(wrapped(dict(SCOPE),receive,send),2)
                self.assertTrue(cleaned.is_set());self.assertEqual(state['inflight'],0)

    def test_registration_is_outermost_user_layer_and_old_counter_removed(self):
        tree=ast.parse(SERVER.read_text())
        calls=[n.value for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='app' and n.value.func.attr=='add_middleware']
        self.assertEqual(calls[-1].args[0].id,'StreamingDrainMiddleware')
        node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='production_hardening_middleware')
        self.assertNotIn('inflight',ast.unparse(node))

if __name__=='__main__':unittest.main()
