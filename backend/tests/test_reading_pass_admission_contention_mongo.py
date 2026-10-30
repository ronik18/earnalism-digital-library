"""Real authenticated owned-loopback admission races, no real users/payments."""
import asyncio,os,time
import pytest
from backend import server
from backend.domain.reading_pass import ReadingPassError
from backend.tests.test_reading_pass_text_admission_mongo_integration import _isolated_database,_seed_retained_content,_rows
pytestmark=pytest.mark.skipif(os.environ.get('READER_SEGMENT_MONGO_INTEGRATION')!='1',reason='explicit disposable loopback replica required')


def args(user,manifest,**extra):
    return dict(user_id=user,auth_session_id='auth-'+user,device_id='device-'+user,device_label='dummy',content_type='text',content_id='hot-book',scope={'segmentation_version':manifest['segmentation_version'],'manifest_version':manifest['version'],'authority_activation_generation':1},**extra)


@pytest.mark.parametrize("variant",["retained_base","candidate"] if os.environ.get("ADMISSION_RETAINED_BASELINE")=="1" else ["candidate"])
def test_real_parallel_same_title_grants_are_atomic_or_controlled_busy(variant):
    async def case():
        async with _isolated_database() as db:
            m=await _seed_retained_content(db,'hot-book')
            if variant=='retained_base':
                import subprocess,types
                source=subprocess.check_output(['git','-c','remote.origin.promisor=false','show','ca37aee:backend/reading_pass_service.py'],env={**os.environ,'GIT_NO_LAZY_FETCH':'1'})
                module=types.ModuleType('backend.retained_baseline');module.__package__='backend';exec(compile(source,'retained-baseline','exec'),module.__dict__)
                server.reading_pass_service=module.ReadingPassService(db=db,client=server.client,config=server.READING_PASS_CONFIG,token_secret=server.READING_PASS_TOKEN_SECRET)
            users=['dummy-'+str(i) for i in range(8)]
            await db.users.insert_many([dict(id=u,role='user',status='active',reading_seconds_balance=300,wallet_seconds=300) for u in users])
            started=time.monotonic()
            results=await asyncio.wait_for(asyncio.gather(*[server.reading_pass_service.start_session(**args(u,m)) for u in users],return_exceptions=True),20)
            accepted=[x for x in results if isinstance(x,dict)];denied=[x for x in results if not isinstance(x,dict)]
            assert accepted
            if variant=='candidate':assert all(isinstance(x,ReadingPassError) and x.code=='TRANSACTION_CONTENTION' and x.status_code==503 for x in denied)
            assert await db.reading_pass_sessions.count_documents({})==len(accepted)
            assert await db.reading_pass_devices.count_documents({})==len(accepted)
            assert await db.reading_pass_audit.count_documents({'event':'metered_session_started'})==len(accepted)
            assert await db.wallet_ledger.count_documents({})==0
            assert await db.users.count_documents({'reading_seconds_balance':300})==8
            print('ADMISSION_RESULT',{'variant':variant,'requests':8,'accepted':len(accepted),'controlled_busy':sum(isinstance(x,ReadingPassError) for x in denied),'raw_errors':sum(not isinstance(x,ReadingPassError) for x in denied),'seconds':round(time.monotonic()-started,3)})
    asyncio.run(case())


@pytest.mark.parametrize('change',['promotion','revocation'])
@pytest.mark.parametrize('transfer',[False,True])
def test_real_publication_race_aborts_all_partial_start_effects(change,transfer):
    async def case():
        async with _isolated_database() as db:
            m=await _seed_retained_content(db,'hot-book');await db.users.insert_one(dict(id='dummy',role='user',status='active',reading_seconds_balance=300,wallet_seconds=300))
            s=server.reading_pass_service
            if transfer:
                previous=args('dummy',m);previous['content_type']='audio';previous['content_id']='dummy-audio';previous['scope']={}
                await s.start_session(**previous)
            before={n:await _rows(db[n]) for n in ['users','reading_pass_sessions','reading_pass_devices','reading_pass_audit','wallet_ledger','wallet_transactions']}
            original=s._assert_text_start_authority;changed=False
            async def race(**kwargs):
                nonlocal changed
                if kwargs.get('write_fence',True) and not changed:
                    changed=True
                    if change=='promotion':update={'$inc':{'generation':1}}
                    else:update={'$set':{'text_revocation':{'status':'revoked','generation':1,'operation_id':'dummy-revoke','cutoff_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc),'activation_generation':1,'segmentation_version':m['segmentation_version'],'manifest_version':m['version']}}}
                    await db.reader_segment_activation_state.update_one({'book_slug':'hot-book'},update)
                return await original(**kwargs)
            s._assert_text_start_authority=race
            with pytest.raises(ReadingPassError) as failure:await s.start_session(**args('dummy',m,transfer=transfer,prepare_text=True))
            assert failure.value.code in {'CONTENT_AUTHORITY_UNAVAILABLE','CONTENT_REVOKED'}
            assert changed
            for n,rows in before.items():assert await _rows(db[n])==rows,n
    asyncio.run(case())


def test_real_same_user_concurrent_start_keeps_one_active_lease():
    async def case():
        async with _isolated_database() as db:
            m=await _seed_retained_content(db,'hot-book')
            await db.users.insert_one(dict(id='same-user',role='user',status='active',reading_seconds_balance=300,wallet_seconds=300))
            outcomes=await asyncio.gather(*[server.reading_pass_service.start_session(**args('same-user',m)) for _ in range(2)],return_exceptions=True)
            assert sum(isinstance(x,dict) for x in outcomes)==1
            assert all(isinstance(x,dict) or isinstance(x,ReadingPassError) and x.code in {'SESSION_ACTIVE_ELSEWHERE','TRANSACTION_CONTENTION'} for x in outcomes)
            assert await db.reading_pass_sessions.count_documents({'active_lock':'same-user'})==1
            assert await db.reading_pass_audit.count_documents({'event':'metered_session_started'})==1
            assert await db.wallet_ledger.count_documents({})==0
    asyncio.run(case())
