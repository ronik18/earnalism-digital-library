"""Renewal-only admitted dependency composition on unchanged native accounting.

Synthetic rows and explicit inert transactions only. This does not qualify real
Mongo atomicity, owner allowance, provider activity or production activation.
"""
import pytest
from backend.reading_pass_admission import ScopedAdmission
from backend.reading_pass_service import ReadingPassService
from backend.tests import test_native_audio_review_scope as cases
from backend.tests.test_native_audio_review_operator import synthetic_owner_pin


@pytest.fixture
def admitted_native_renewal(monkeypatch):
    original = ReadingPassService.__init__
    function = ReadingPassService.renew_lease
    adapters = []

    def initialize(self, *, db, client, config, token_secret):
        original(self, db=db, client=client, config=config, token_secret=token_secret)
        assert db.client is client
        admission = ScopedAdmission(client, _inert_test_client=True)
        view = object.__new__(ReadingPassService)
        original(view, db=admission.database(db), client=admission,
                 config=config, token_secret=token_secret)
        self.renew_lease = function.__get__(view, ReadingPassService)
        assert self.db is db and self.client is client
        adapters.append(admission)

    monkeypatch.setattr(ReadingPassService, '__init__', initialize)
    yield
    for admission in adapters:
        assert not admission.permits
        assert not admission.sessions
        assert not admission.background
        assert not admission.errors


@pytest.mark.parametrize('case', [
    'test_actual_service_native_fraction_credit_idempotency_and_terminal',
    'test_native_interval_then_failed_wallet_cas_rolls_back_all_metadata',
    'test_ordinary_audio_start_and_debit_do_not_touch_review_metadata',
    'test_actual_native_debits_preexisting_and_ordinary_moved_fraction_without_reset',
])
def test_native_accounting_through_admitted_renewal(case, monkeypatch, admitted_native_renewal):
    # Keep every original wallet, grant, workflow, CAS, carry and ledger assertion.
    getattr(cases, case)(monkeypatch)


def test_open_native_shared_counter_through_admitted_renewal(monkeypatch, admitted_native_renewal):
    from backend.tests import test_open_native_review_scope as opened
    opened.test_actual_shared_service_open_fraction_credit_idempotency_and_ordinary_carry(monkeypatch)
