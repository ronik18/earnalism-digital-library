import asyncio
import pytest
from backend.tests.test_reading_pass_service_concurrency import Database, Client
from backend.reading_pass_service import ReadingPassService
from backend.domain.reading_pass import ReadingPassConfig, ReadingPassError

@pytest.mark.parametrize('first_kind',['text','audio'])
@pytest.mark.parametrize('second_kind',['text','audio'])
@pytest.mark.parametrize('client_case', ['same_tab','same_profile_tab','same_device_browser','same_device_app','different_device'])
def test_account_lock_spans_client_and_content_combinations(first_kind, second_kind, client_case):
 async def run():
  db=Database(balance=120)
  svc=ReadingPassService(db=db,client=Client(),config=ReadingPassConfig(),token_secret='dummy-matrix-test-secret-over-32-bytes')
  original=await svc.start_session(user_id='user-1',auth_session_id='auth-a',device_id='device-a',device_label='Synthetic',content_type=first_kind,content_id='book-1',scope={})
  same_auth=client_case in ['same_tab','same_profile_tab']
  same_device=client_case in ['same_tab','same_profile_tab','same_device_app']
  with pytest.raises(ReadingPassError) as denied:
   await svc.start_session(user_id='user-1',auth_session_id='auth-a' if same_auth else 'auth-b',device_id='device-a' if same_device else 'device-b',device_label='Synthetic second',content_type=second_kind,content_id='book-2',scope={})
  assert denied.value.code=='SESSION_ACTIVE_ELSEWHERE'
  assert len(db.reading_pass_sessions.rows)==1
  assert db.users.rows[0]['reading_seconds_balance']==120
  assert db.wallet_ledger.rows==[]
  await svc.end_session(user_id='user-1',auth_session_id='auth-a',session_id=original['session_id'])
 asyncio.run(run())

def test_fractional_renewals_conserve_billable_time(monkeypatch):
 from datetime import datetime,timedelta,timezone
 async def run():
  db=Database(balance=120)
  clock=[datetime(2026,1,1,tzinfo=timezone.utc)]
  class Clock(datetime):
   @classmethod
   def now(cls,tz=None): return clock[0]
  monkeypatch.setattr('backend.reading_pass_service.datetime',Clock)
  svc=ReadingPassService(db=db,client=Client(),config=ReadingPassConfig(),token_secret='dummy-matrix-test-secret-over-32-bytes')
  lease=await svc.start_session(user_id='user-1',auth_session_id='auth-a',device_id='device-a',device_label='Synthetic',content_type='audio',content_id='book-1',scope={})
  total=0
  for seq in range(1,22):
   if seq>1: clock[0]+=timedelta(milliseconds=900)
   lease=await svc.renew_lease(user_id='user-1',auth_session_id='auth-a',session_id=lease['session_id'],lease_token=lease['lease_token'],lease_version=lease['lease_version'],sequence=seq,idempotency_key=f'fraction-{seq}',active=True,playback_state='playing')
   total+=lease['deducted_seconds']
  # Twenty 900ms intervals must conserve eighteen billable seconds.
  assert total==18
  assert db.users.rows[0]['reading_seconds_balance']==102
 asyncio.run(run())

@pytest.mark.parametrize('kind',['text','audio'])
def test_account_fraction_carry_survives_session_boundaries(monkeypatch,kind):
 from datetime import datetime,timedelta,timezone
 async def run():
  db=Database(balance=120);clock=[datetime(2026,1,1,tzinfo=timezone.utc)]
  class Clock(datetime):
   @classmethod
   def now(cls,tz=None):return clock[0]
  monkeypatch.setattr('backend.reading_pass_service.datetime',Clock)
  svc=ReadingPassService(db=db,client=Client(),config=ReadingPassConfig(),token_secret='dummy-matrix-test-secret-over-32-bytes')
  for iteration in range(2):
   lease=await svc.start_session(user_id='user-1',auth_session_id='auth-a',device_id='device-a',device_label='Synthetic',content_type=kind,content_id='book-1',scope={})
   if kind=='audio':
    lease=await svc.renew_lease(user_id='user-1',auth_session_id='auth-a',session_id=lease['session_id'],lease_token=lease['lease_token'],lease_version=lease['lease_version'],sequence=1,idempotency_key='play-'+str(iteration),active=True,playback_state='playing')
   clock[0]+=timedelta(milliseconds=600)
   await svc.end_session(user_id='user-1',auth_session_id='auth-a',session_id=lease['session_id'])
   clock[0]+=timedelta(seconds=30)
  assert db.users.rows[0]['reading_seconds_balance']==119
  assert db.users.rows[0]['reading_fractional_microseconds']==200000
  await svc.end_session(user_id='user-1',auth_session_id='auth-a',session_id=lease['session_id'])
  assert db.users.rows[0]['reading_seconds_balance']==119
 asyncio.run(run())
