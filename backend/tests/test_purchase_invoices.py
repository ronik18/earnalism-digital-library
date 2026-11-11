"""Synthetic billing only. SMTP is always injected/mocked; no real email/payment."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend import purchase_invoices as invoices, purchase_invoice_email as mail
from backend.domain.reading_pass import ReadingPassConfig
from backend.reading_pass_service import ReadingPassService
from backend.tests.test_reading_pass_service_concurrency import Database, Client

NOW = datetime(2026, 11, 11, 6, tzinfo=timezone.utc)


def purchase(**change):
    return dict(id=str(uuid4()), user_id='user-1', user_email='reader@example.com',
        minutes=30, amount_paise=4900, currency='INR', pack_id='30m',
        mode='live', status='created', **change)


def test_concurrent_verify_webhook_create_one_credit_and_invoice():
    async def run():
        db = Database(balance=0)
        intent = purchase()
        db.topup_intents.rows.append(deepcopy(intent))
        service = ReadingPassService(db=db, client=Client(), config=ReadingPassConfig(),
                                     token_secret='synthetic', invoice_email_enabled=True)
        await asyncio.gather(*[service.credit_verified_payment(intent=intent,
            payment_id='pay_synthetic', source='verify' if n % 2 else 'webhook') for n in range(10)])
        assert db.users.rows[0]['wallet_seconds'] == db.users.rows[0]['reading_seconds_balance'] == 1800
        assert len(db.wallet_ledger.rows) == len(db.wallet_transactions.rows) == 1
        rows = db['purchase_invoices'].rows
        assert len(rows) == 1 and rows[0]['delivery_status'] == 'pending'
        assert rows[0]['transaction_id'] == db.wallet_transactions.rows[0]['id']
        assert rows[0]['amount_paise'] == 4900 and rows[0]['recipient'] == 'reader@example.com'
    asyncio.run(run())


def test_legacy_credited_payment_is_not_backfilled_or_emailed():
    async def run():
        db = Database(balance=1800)
        intent = purchase(); intent['status'] = 'credited'
        db.topup_intents.rows.append(intent)
        service = ReadingPassService(db=db, client=Client(), config=ReadingPassConfig(),
                                     token_secret='synthetic', invoice_email_enabled=True)
        await service.credit_verified_payment(intent=intent, payment_id='pay_synthetic', source='webhook')
        assert not db['purchase_invoices'].rows and db.users.rows[0]['wallet_seconds'] == 1800
    asyncio.run(run())


def test_bad_invoice_recipient_does_not_withhold_paid_credit():
    async def run():
        db=Database(balance=0);intent=purchase();intent['user_email']='not-an-email'
        db.topup_intents.rows.append(deepcopy(intent))
        service=ReadingPassService(db=db,client=Client(),config=ReadingPassConfig(),
            token_secret='synthetic',invoice_email_enabled=True)
        result=await service.credit_verified_payment(intent=intent,payment_id='pay_fixture',source='verify')
        assert result['status']=='credited' and db.users.rows[0]['wallet_seconds']==1800
        assert db['purchase_invoices'].rows[0]['delivery_status']=='review_required'
    asyncio.run(run())


@pytest.mark.parametrize('change', [{'user_email':'bad\r\nBcc: other@example.com'},
    {'amount_paise':True}, {'amount_paise':-1}, {'currency':'GBP'}, {'minutes':False}])
def test_invalid_invoice_data_is_held(change):
    intent = purchase(); intent.update(change)
    row = invoices.invoice_record(intent, payment_id='pay_fixture', transaction_id='tx', now=NOW)
    assert row['delivery_status'] == 'review_required'


def test_test_payment_is_never_queued_and_html_is_self_contained():
    intent = purchase(); intent['mode'] = 'test'
    row = invoices.invoice_record(intent, payment_id='pay_<script>alert(1)</script>', transaction_id='tx', now=NOW)
    assert row['delivery_status'] == 'suppressed_test'
    assert '<script>' not in row['html'] and '&lt;script&gt;' in row['html']
    assert 'INR 49.00' in row['html'] and 'GST is not charged' in row['html']
    assert '<img' not in row['html']


def test_mail_contains_printable_invoice_and_stable_identity():
    row = invoices.invoice_record(purchase(), payment_id='pay_fixture', transaction_id='tx', now=NOW)
    config = mail.SMTPConfig(username=invoices.SUPPORT, password='a'*16)
    first, second = mail.message_for(row, config), mail.message_for(row, config)
    assert first['Message-ID'] == second['Message-ID']
    attachment, = first.iter_attachments()
    assert attachment.get_filename().endswith('.html')
    assert attachment.get_payload(decode=True).decode() == row['html']
    assert first['To'] == 'reader@example.com'


def test_disabled_config_has_no_secret_requirement_and_enabled_config_requires_app_password():
    assert mail.configuration({}) is None
    with pytest.raises(ValueError): mail.configuration({'PURCHASE_INVOICE_EMAIL_ENABLED':'true'})
    config = mail.configuration({'PURCHASE_INVOICE_EMAIL_ENABLED':'true',
        'PURCHASE_INVOICE_SMTP_PASSWORD':'abcd efgh ijkl mnop'})
    assert config.password == 'abcdefghijklmnop' and config.password not in repr(config)


def test_smtp_requires_tls_before_login_and_sends_once(monkeypatch):
    calls = []
    class SMTP:
        def __init__(self, host, port, timeout):
            assert (host,port,timeout) == ('smtp.gmail.com',587,5)
        def ehlo(self): calls.append('ehlo')
        def starttls(self, context): assert context.check_hostname; calls.append('tls')
        def auth(self, mechanism, callback, *, initial_response_ok):
            assert mechanism=='PLAIN' and initial_response_ok is True
            assert callback()=='\0'+invoices.SUPPORT+'\0'+'a'*16
            calls.append('auth_once')
        def send_message(self, message): calls.append('send'); return {}
        def quit(self): calls.append('quit')
        def close(self): calls.append('close')
    monkeypatch.setattr(mail.smtplib,'SMTP',SMTP)
    row = invoices.invoice_record(purchase(),payment_id='pay_fixture',transaction_id='tx',now=NOW)
    mail.send_invoice(row,mail.SMTPConfig(username=invoices.SUPPORT,password='a'*16))
    assert calls == ['ehlo','tls','ehlo','auth_once','send','quit']
    calls.clear()
    mail.verify_smtp(mail.SMTPConfig(username=invoices.SUPPORT,password='a'*16))
    assert calls == ['ehlo','tls','ehlo','auth_once','quit']


@pytest.mark.parametrize('attempts,expected', [(1,'pending'),(3,'failed')])
def test_email_failure_only_changes_delivery_state_and_redacts_details(attempts,expected,caplog):
    class Queue:
        async def find_one_and_update(self,*a,**k):
            self.row=invoices.invoice_record(purchase(),payment_id='pay_fixture',transaction_id='tx',now=NOW)
            self.row.update(attempts=attempts,delivery_status='sending')
            return deepcopy(self.row)
        async def update_one(self,query,update):
            assert query['_id']==self.row['_id'] and query['attempts']==attempts
            self.update=update
    class DB:
        def __getitem__(self,name): assert name=='purchase_invoices';return queue
    def refused(*a): raise ValueError('private-customer@example.com secret-provider-detail')
    async def run():
        await mail.deliver_one(DB(),mail.SMTPConfig(username=invoices.SUPPORT,password='a'*16),
                              send=refused,now=NOW)
    queue=Queue();asyncio.run(run())
    assert queue.update['$set']['delivery_status']==expected
    assert queue.update['$set']['last_error_code']=='ValueError'
    assert 'private-customer' not in caplog.text and 'secret-provider-detail' not in caplog.text


@pytest.mark.skipif(__import__('os').environ.get('READER_SEGMENT_MONGO_INTEGRATION') != '1',
                   reason='requires existing disposable loopback Mongo fixture')
@pytest.mark.parametrize('rollback', [False, True])
def test_real_mongo_credit_invoice_atomicity_and_multi_worker_claim(monkeypatch, rollback):
    from scripts.uat_mongo_fixture import isolated_database
    async def run():
        async with isolated_database('rpadmit_it_') as (client, db):
            await db.users.insert_one(dict(id='user-1',role='user',status='active',
                reading_seconds_balance=0,wallet_seconds=0))
            await db.wallet_ledger.create_index('idempotency_key',unique=True)
            await mail.prepare_outbox(db)
            intent=purchase(); await db.topup_intents.insert_one(deepcopy(intent))
            service=ReadingPassService(db=db,client=client,config=ReadingPassConfig(),
                token_secret='synthetic',invoice_email_enabled=True)
            if rollback:
                # Raise after the wallet/ledger writes but before commit.
                import backend.reading_pass_service as module
                def fail(*a,**kw): raise ValueError('synthetic invoice persistence boundary')
                monkeypatch.setattr(module,'invoice_record',fail)
                with pytest.raises(ValueError):
                    await service.credit_verified_payment(intent=intent,payment_id='pay_fixture',source='webhook')
                assert (await db.users.find_one({'id':'user-1'}))['wallet_seconds']==0
                assert await db.wallet_ledger.count_documents({})==await db.purchase_invoices.count_documents({})==0
                assert (await db.topup_intents.find_one({'id':intent['id']}))['status']=='created'
                return
            await asyncio.gather(*[service.credit_verified_payment(intent=intent,
                payment_id='pay_fixture',source='webhook') for _ in range(6)])
            assert (await db.users.find_one({'id':'user-1'}))['wallet_seconds']==1800
            assert await db.purchase_invoices.count_documents({})==await db.wallet_ledger.count_documents({})==1
            sent=[]
            def fake_send(row,config): sent.append(row['_id'])
            config=mail.SMTPConfig(username=invoices.SUPPORT,password='a'*16)
            await asyncio.gather(*[mail.deliver_one(db,config,send=fake_send) for _ in range(5)])
            assert len(sent)==1
            row=await db.purchase_invoices.find_one({})
            assert row['delivery_status']=='sent' and row['attempts']==1
    asyncio.run(run())


def test_disabled_invoice_config_starts_no_invoice_work_during_containment():
    from types import SimpleNamespace
    from backend.tests.test_reading_pass_admission_wiring import namespace
    async def run():
        events=[];ns=namespace(events)
        async def forbidden(*a): raise AssertionError('invoice work under containment')
        ns.update(purchase_invoice_email=SimpleNamespace(
            prepare_outbox=forbidden,delivery_loop=forbidden))
        async with ns['context'](None): pass
        assert events[-1]=='raw_close'
    asyncio.run(run())


@pytest.mark.parametrize('contained', [False, True])
def test_invoice_worker_cancels_before_database_shutdown(contained):
    from types import SimpleNamespace
    from backend.tests.test_reading_pass_admission_wiring import namespace
    async def run():
        events=[];ns=namespace(events);started=asyncio.Event()
        async def reader(): events.append('reader_publication')
        async def maintenance(): events.append('general_maintenance')
        async def prepare(db): events.append('invoice_prepare')
        async def worker(db,config):
            started.set()
            try: await asyncio.Event().wait()
            finally: events.append('invoice_cancelled')
        ns.update(PURCHASE_INVOICE_CONFIG=object(),_acceptance_release_containment=lambda:contained,
            ENABLE_STARTUP_DB_MAINTENANCE=True,_run_startup_database_maintenance=maintenance,
            _initialize_authorized_reader_release=reader,purchase_invoice_email=SimpleNamespace(
                prepare_outbox=prepare,delivery_loop=worker))
        async with ns['context'](None): await asyncio.wait_for(started.wait(),1)
        assert ('reader_publication' in events) is (not contained)
        assert ('general_maintenance' in events) is (not contained)
        assert events.index('invoice_prepare')<events.index('invoice_cancelled')
        assert events.index('invoice_cancelled')<events.index('close_backends')<events.index('raw_close')
    asyncio.run(run())


@pytest.mark.parametrize('contained', [False, True])
def test_invoice_index_startup_failure_still_closes_database_and_preserves_error(contained):
    from types import SimpleNamespace
    from backend.tests.test_reading_pass_admission_wiring import namespace
    async def run():
        events=[];ns=namespace(events);error=PermissionError('synthetic index denial')
        async def reader(): pass
        async def prepare(db): raise error
        async def forbidden(*a): raise AssertionError('worker must not start')
        ns.update(PURCHASE_INVOICE_CONFIG=object(),_acceptance_release_containment=lambda:contained,
            _initialize_authorized_reader_release=reader,purchase_invoice_email=SimpleNamespace(
                prepare_outbox=prepare,delivery_loop=forbidden))
        with pytest.raises(PermissionError) as got:
            async with ns['context'](None): raise AssertionError('startup must not yield')
        assert got.value is error
        assert events.index('close_backends')<events.index('raw_close')
    asyncio.run(run())


def test_startup_auth_failure_uses_one_mechanism_and_never_claims_queue(monkeypatch, caplog):
    calls=[]
    class SMTP:
        def __init__(self,*a,**kw): calls.append('connect')
        def ehlo(self): calls.append('ehlo')
        def starttls(self,context): assert context.check_hostname;calls.append('tls')
        def auth(self,mechanism,callback,*,initial_response_ok):
            assert mechanism=='PLAIN' and initial_response_ok
            calls.append('auth_once')
            raise mail.smtplib.SMTPAuthenticationError(535,b'private-provider-text secret-password')
        def close(self): calls.append('close')
    class ForbiddenDB:
        def __getitem__(self,key): raise AssertionError('queue must remain unclaimed')
    monkeypatch.setattr(mail.smtplib,'SMTP',SMTP)
    async def run():
        await asyncio.wait_for(mail.delivery_loop(ForbiddenDB(),mail.SMTPConfig(
            username=invoices.SUPPORT,password='a'*16)),1)
    asyncio.run(run())
    assert calls==['connect','ehlo','tls','ehlo','auth_once','close']
    assert 'stage=AUTH code=535; delivery held' in caplog.text
    assert 'private-provider-text' not in caplog.text and 'secret-password' not in caplog.text


def test_tls_failure_never_authenticates_and_identifies_safe_stage(monkeypatch):
    calls=[]
    class SMTP:
        def __init__(self,*a,**kw): pass
        def ehlo(self): calls.append('ehlo')
        def starttls(self,context): raise mail.ssl.SSLError('synthetic TLS denial')
        def auth(self,*a,**kw): raise AssertionError('no auth before TLS')
        def close(self): calls.append('close')
    monkeypatch.setattr(mail.smtplib,'SMTP',SMTP)
    with pytest.raises(mail.ssl.SSLError) as got:
        mail.verify_smtp(mail.SMTPConfig(username=invoices.SUPPORT,password='a'*16))
    assert mail._failure_stage(got.value)=='STARTTLS' and calls==['ehlo','close']
