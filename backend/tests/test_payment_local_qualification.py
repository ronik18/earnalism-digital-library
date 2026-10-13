"""Provider-free handler regressions against an explicitly isolated replica set."""
import asyncio
import pytest
import os

pytestmark = pytest.mark.skipif(os.environ.get("READER_SEGMENT_MONGO_INTEGRATION") != "1", reason="requires explicit isolated loopback replica set")
from fastapi import HTTPException
from backend import server
from backend.tests.test_reading_pass_text_admission_mongo_integration import _isolated_database

async def seed(db, status='created'):
    await db.users.insert_one({'id':'payment-user','role':'user','reading_seconds_balance':120,'wallet_seconds':120})
    intent={'id':'intent-local','user_id':'payment-user','status':status,'minutes':60,'pack_id':'1h','amount_paise':8900,'currency':'INR','razorpay_order_id':'order_local','razorpay_payment_id':None,'created_at':server.now_iso()}
    await db.topup_intents.insert_one(intent)
    return intent

async def noop(*a, **kw): pass

def test_reconcile_requires_captured_payment(monkeypatch):
    async def scenario():
        async with _isolated_database() as db:
            await seed(db)
            with pytest.raises(HTTPException) as failure:
                await server.admin_reconcile_intent('intent-local',server.PaymentReconcileIn(note='fixture'),admin={'email':'fixture'})
            assert failure.value.status_code == 409
            assert (await db.users.find_one({'id':'payment-user'}))['reading_seconds_balance']==120
            assert await db.wallet_ledger.count_documents({})==0
    asyncio.run(scenario())

def test_bad_signature_cannot_downgrade_credited(monkeypatch):
    monkeypatch.setattr(server,'_public_paid_commerce_enabled_or_404',lambda:None)
    monkeypatch.setattr(server,'razorpay_keys_configured',lambda:True)
    monkeypatch.setattr(server,'RAZORPAY_KEY_SECRET','synthetic-only')
    monkeypatch.setattr(server,'_invalidate_user_cache',noop)
    async def scenario():
        async with _isolated_database() as db:
            await seed(db,'credited')
            with pytest.raises(HTTPException) as failure:
                await server.payments_verify(server.PaymentVerifyIn(razorpay_order_id='order_local',razorpay_payment_id='pay_local',razorpay_signature='bad'),user={'id':'payment-user'})
            assert failure.value.status_code==400
            assert (await db.topup_intents.find_one({'id':'intent-local'}))['status']=='credited'
    asyncio.run(scenario())

def test_refund_failure_rolls_back_every_write(monkeypatch):
    async def fail(*a, **kw): raise RuntimeError('injected ledger failure')
    monkeypatch.setattr(server,'_record_wallet_ledger',fail)
    async def scenario():
        async with _isolated_database() as db:
            await seed(db)
            await db.wallet_refunds.create_index('candidate_id',unique=True)
            tx={'id':'consume-local','user_id':'payment-user','type':'consume','seconds':-120,'created_at':server.now_iso(),'session_id':'session-local'}
            await db.wallet_transactions.insert_one(tx)
            candidate=server._wallet_refund_candidates([tx])[0]['candidate_id']
            with pytest.raises(RuntimeError,match='injected ledger failure'):
                await server.admin_wallet_refund_approve('payment-user',server.WalletRefundApproveIn(candidate_ids=[candidate],note='test'),admin={'email':'fixture'})
            assert (await db.users.find_one({'id':'payment-user'}))['reading_seconds_balance']==120
            assert await db.wallet_refunds.count_documents({})==0
    asyncio.run(scenario())

def test_captured_payment_binding_rejects_mismatches():
    intent={'razorpay_order_id':'order_local','amount_paise':8900,'currency':'INR'}
    payment={'id':'pay_local','order_id':'order_local','amount':8900,'currency':'INR','status':'captured','captured':True}
    assert server._razorpay_payment_matches_intent(payment,intent)
    for key,value in [('order_id','other'),('amount',1),('currency','USD'),('status','authorized'),('id','')]:
        bad={**payment,key:value}
        assert not server._razorpay_payment_matches_intent(bad,intent)

def test_credit_race_commits_once(monkeypatch):
    async def scenario():
        async with _isolated_database() as db:
            intent=await seed(db)
            results = await asyncio.gather(*[server.reading_pass_service.credit_verified_payment(intent=intent,payment_id='pay_local',source=source) for source in ['verify','webhook','reconcile']], return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    assert getattr(result, 'has_error_label', lambda _: False)('TransientTransactionError')
                    await server.reading_pass_service.credit_verified_payment(intent=intent,payment_id='pay_local',source='retry')
            assert (await db.users.find_one({'id':'payment-user'}))['reading_seconds_balance']==3720
            assert await db.wallet_ledger.count_documents({'action':'topup_credit'})==1
            assert await db.wallet_transactions.count_documents({})==1
    asyncio.run(scenario())

def test_refund_concurrent_approval_credits_once(monkeypatch):
    monkeypatch.setattr(server,'_invalidate_user_cache',noop)
    async def scenario():
        async with _isolated_database() as db:
            await seed(db)
            await db.wallet_refunds.create_index('candidate_id',unique=True)
            tx={'id':'consume-local','user_id':'payment-user','type':'consume','seconds':-120,'created_at':server.now_iso(),'session_id':'session-local'}
            await db.wallet_transactions.insert_one(tx)
            candidate=server._wallet_refund_candidates([tx])[0]
            async def approve():
                try:
                    return await server.admin_wallet_refund_approve('payment-user',server.WalletRefundApproveIn(candidate_ids=[candidate['candidate_id']],note='test'),admin={'email':'fixture'})
                except HTTPException as exc:
                    assert exc.status_code==409
            await asyncio.gather(approve(),approve())
            assert (await db.users.find_one({'id':'payment-user'}))['reading_seconds_balance']==120+candidate['refundable_seconds']
            assert await db.wallet_ledger.count_documents({'action':'refund_credit'})==1
            assert (await db.wallet_refunds.find_one({}))['credited'] is True
    asyncio.run(scenario())

def test_reconcile_verified_capture_and_replay(monkeypatch):
    calls=[]
    def captured(intent,payment_id):
        calls.append(payment_id)
        return {'id':payment_id}
    monkeypatch.setattr(server,'_fetch_captured_razorpay_payment',captured)
    monkeypatch.setattr(server,'_invalidate_user_cache',noop)
    monkeypatch.setattr(server,'_set_user_wallet_cache',noop)
    async def scenario():
        async with _isolated_database() as db:
            await seed(db)
            await db.topup_intents.update_one({'id':'intent-local'},{'$set':{'razorpay_payment_id':'pay_local'}})
            payload=server.PaymentReconcileIn(note='fixture')
            first=await server.admin_reconcile_intent('intent-local',payload,admin={'email':'fixture'})
            second=await server.admin_reconcile_intent('intent-local',payload,admin={'email':'fixture'})
            assert first['intent']['status']=='credited' and second['duplicate'] is True
            assert calls==['pay_local']
            assert (await db.users.find_one({'id':'payment-user'}))['reading_seconds_balance']==3720
            assert await db.wallet_ledger.count_documents({})==1
    asyncio.run(scenario())

def test_provider_returned_payment_id_must_match_request(monkeypatch):
    from types import SimpleNamespace
    intent={'razorpay_order_id':'order_local','amount_paise':8900,'currency':'INR'}
    wrong={'id':'pay_other','order_id':'order_local','amount':8900,'currency':'INR','status':'captured'}
    monkeypatch.setattr(server,'get_razorpay_client',lambda: SimpleNamespace(payment=SimpleNamespace(fetch=lambda _:wrong)))
    with pytest.raises(HTTPException) as denied:
        server._fetch_captured_razorpay_payment(intent,'pay_local')
    assert denied.value.status_code==409

def test_verify_signed_webhook_reconcile_handler_race(monkeypatch):
    import hashlib,hmac,json
    from starlette.requests import Request
    from types import SimpleNamespace
    secret='synthetic-local-handler-secret'
    payment={'id':'pay_local','order_id':'order_local','amount':8900,'currency':'INR','status':'captured'}
    monkeypatch.setattr(server,'_public_paid_commerce_enabled_or_404',lambda:None)
    monkeypatch.setattr(server,'razorpay_keys_configured',lambda:True)
    monkeypatch.setattr(server,'RAZORPAY_KEY_SECRET',secret)
    monkeypatch.setattr(server,'RAZORPAY_WEBHOOK_SECRET',secret)
    monkeypatch.setattr(server,'get_razorpay_client',lambda:SimpleNamespace(payment=SimpleNamespace(fetch=lambda _:payment)))
    for name in ['_invalidate_user_cache','_set_user_wallet_cache','_record_purchase_conversion']:
        monkeypatch.setattr(server,name,noop)
    async def wallet(_): return 3720
    monkeypatch.setattr(server,'_cached_user_wallet_seconds',wallet)
    raw=json.dumps({'event':'payment.captured','payload':{'payment':{'entity':payment}}}).encode()
    signature=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    def request():
        async def receive(): return {'type':'http.request','body':raw,'more_body':False}
        return Request({'type':'http','headers':[(b'x-razorpay-signature',signature.encode()),(b'x-razorpay-event-id',b'event_local')]},receive)
    async def scenario():
        async with _isolated_database() as db:
            await seed(db)
            await db.topup_intents.update_one({'id':'intent-local'},{'$set':{'razorpay_payment_id':'pay_local'}})
            browser_signature=hmac.new(secret.encode(),b'order_local|pay_local',hashlib.sha256).hexdigest()
            async def verify():
                return await server.payments_verify(server.PaymentVerifyIn(razorpay_order_id='order_local',razorpay_payment_id='pay_local',razorpay_signature=browser_signature),user={'id':'payment-user'})
            async def webhook(): return await server.payments_webhook(request())
            async def reconcile(): return await server.admin_reconcile_intent('intent-local',server.PaymentReconcileIn(note='fixture'),admin={'email':'fixture'})
            operations=[verify,webhook,reconcile]
            results=await asyncio.gather(*[op() for op in operations],return_exceptions=True)
            for op,result in zip(operations,results):
                if isinstance(result,Exception):
                    assert getattr(result,'has_error_label',lambda _:False)('TransientTransactionError')
                    await op()
            assert (await db.users.find_one({'id':'payment-user'}))['reading_seconds_balance']==3720
            assert await db.wallet_ledger.count_documents({'action':'topup_credit'})==1
            assert await db.wallet_transactions.count_documents({})==1
            assert (await server.payments_webhook(request()))['duplicate'] is True
    asyncio.run(scenario())
