"""Late title-fence ordering and bounded known-conflict outcomes; dummy only."""
import asyncio
import pytest
from backend.reading_pass_service import ReadingPassService
from backend.domain.reading_pass import ReadingPassConfig, ReadingPassError
from backend.tests.test_reading_pass_service_concurrency import Database, ExplicitCommitClient, LabeledTransactionError


def service(client):
    return ReadingPassService(db=Database(), client=client, config=ReadingPassConfig(), token_secret='dummy')


def test_exhausted_known_transient_is_controlled_503():
    async def case():
        c=ExplicitCommitClient();s=service(c);calls=[]
        async def conflict(_session):
            calls.append(1);raise LabeledTransactionError('TransientTransactionError')
        with pytest.raises(ReadingPassError) as failure:await s._transaction(conflict)
        assert failure.value.code=='TRANSACTION_CONTENTION' and failure.value.status_code==503
        assert len(calls)==3
    asyncio.run(case())


def test_exhausted_unknown_commit_never_replays_callback_or_claims_retryable():
    async def case():
        c=ExplicitCommitClient();s=service(c);calls=[]
        async def unknown():raise LabeledTransactionError('UnknownTransactionCommitResult')
        c.session.commit_transaction=unknown
        async def operation(_session):calls.append(1);return {'dummy':True}
        with pytest.raises(LabeledTransactionError):await s._transaction(operation)
        assert calls==[1]
    asyncio.run(case())


def test_early_authority_read_then_final_fence_after_all_session_writes():
    async def case():
        s=service(ExplicitCommitClient());events=[]
        async def authority(**kwargs):
            events.append('fence' if kwargs.get('write_fence',True) else 'read')
            if kwargs.get('write_fence',True):
                assert len(s.db.reading_pass_sessions.rows)==1
                assert len(s.db.reading_pass_devices.rows)==1
                assert s.db.reading_pass_audit.rows
        s._assert_text_start_authority=authority
        result=await s.start_session(user_id='user-1',auth_session_id='auth',device_id='dummy',device_label='dummy',content_type='text',content_id='book',scope={})
        assert result['session_id'] and events==['read','fence']
    asyncio.run(case())


def test_exhausted_known_transient_commit_is_controlled_and_dual_unknown_is_not_replayed():
    async def case(unknown):
        c=ExplicitCommitClient();s=service(c);calls=[];commits=[]
        class CommitFailure(Exception):
            def has_error_label(self,label):
                return label=='TransientTransactionError' or unknown and label=='UnknownTransactionCommitResult'
        async def fail_commit():commits.append(1);raise CommitFailure()
        c.session.commit_transaction=fail_commit
        async def operation(_session):calls.append(1);return {'dummy':True}
        with pytest.raises(CommitFailure if unknown else ReadingPassError) as failure:
            await s._transaction(operation)
        assert len(commits)==3 and len(calls)==(1 if unknown else 3)
        if not unknown:assert failure.value.code=='TRANSACTION_CONTENTION'
    asyncio.run(case(False));asyncio.run(case(True))
