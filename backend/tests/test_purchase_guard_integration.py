"""Portable repository test: actual middleware source, dummy ASGI handlers only."""
import ast
import asyncio
from pathlib import Path
import unittest
from types import SimpleNamespace
from scripts.purchase_guard_source import validate

ROOT=Path(__file__).resolve().parents[2]

class GuardedPurchaseSourceTests(unittest.TestCase):
    def test_exact_operational_source_contract(self):
        manifest,base,closed=validate(ROOT)
        from scripts.build_india_guarded_rollback import guard_only_server as canonical_guard
        self.assertEqual(closed, canonical_guard(base.decode('utf-8'), base.decode('utf-8')).encode('utf-8'))
        self.assertIn(manifest['state'],{'OPEN','CLOSED'})
        self.assertEqual((ROOT/'backend/server.py').read_bytes(),closed if manifest['state']=='CLOSED' else base)

    def test_actual_closed_middleware_asgi_never_enters_purchase_handler(self):
        from fastapi import FastAPI
        from starlette.responses import JSONResponse
        import httpx
        from backend.commerce_territory import COMMERCE_ORDER_PATH,commerce_territory_verdict
        from backend.release_proxy_auth import request_signature
        from datetime import datetime,timezone
        manifest,base,closed=validate(ROOT)
        source=(ROOT/'backend/server.py').read_text()
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='enforce_public_release_country');node.decorator_list=[]
        secret='isolated-purchase-guard-no-provider-credential'
        ns=dict(Request=object,ENVIRONMENT='production',PUBLIC_READER_EXPOSURE_ENABLED=False,COMMERCE_ORDER_PATH=COMMERCE_ORDER_PATH,commerce_territory_verdict=commerce_territory_verdict,os=SimpleNamespace(getenv=lambda *_:secret),JSONResponse=JSONResponse)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-guarded-middleware','exec'),ns)
        app=FastAPI();app.middleware('http')(ns['enforce_public_release_country']);calls=[]
        paths=[COMMERCE_ORDER_PATH,'/api/payments/verify','/api/payments/webhook','/api/admin/users/dummy/wallet/refund-approve','/api/reading-pass/leases/renew']
        for path in paths:
            async def dummy(request_path=path):calls.append(request_path);return JSONResponse({},status_code=204)
            app.post(path)(dummy)
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://isolated-dummy') as client:
                if manifest['state']=='CLOSED':
                    for headers in ({},{'x-vercel-ip-country':'IN'},{'x-earnalism-release-country':'US'}):
                        r=await client.post(COMMERCE_ORDER_PATH,headers=headers)
                        self.assertEqual(r.status_code,503);self.assertEqual(r.headers.get('cache-control'),'no-store');self.assertEqual(r.json()['detail']['code'],'PURCHASE_INITIATION_CLOSED');self.assertEqual(r.json()['detail']['message'],'New Reading Pass purchases are temporarily paused. Existing reading and listening access remains available.')
                    self.assertEqual(calls,[])
                else:
                    timestamp=int(datetime.now(timezone.utc).timestamp())
                    headers={'x-earnalism-release-scope':'PUBLIC','x-earnalism-release-country':'IN','x-earnalism-release-timestamp':str(timestamp),'x-earnalism-release-signature':request_signature(secret,'POST',COMMERCE_ORDER_PATH,'PUBLIC',timestamp,'IN')}
                    self.assertEqual((await client.post(COMMERCE_ORDER_PATH,headers=headers)).status_code,204)
                    for headers in ({},{'x-vercel-ip-country':'IN'}):self.assertEqual((await client.post(COMMERCE_ORDER_PATH,headers=headers)).status_code,451)
                    self.assertEqual(calls,[COMMERCE_ORDER_PATH]);calls.clear()
                for path in paths[1:]:self.assertEqual((await client.post(path)).status_code,204)
                self.assertEqual(calls,paths[1:])
        asyncio.run(run())

if __name__=='__main__':unittest.main()
