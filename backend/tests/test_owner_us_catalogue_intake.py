"""Actual owner acceptance is source intake, never runtime activation."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import pytest
from backend.rights_decision_gate import evaluate_accepted_record, load_production_registry, record_sha256
ROOT=Path(__file__).resolve().parents[2]
BATCH=ROOT/'internal/legal/us_rights_intake_20261028/catalogue-51'
INTAKE=json.loads((BATCH/'intake.json').read_text())
INDEX=json.loads((BATCH/'DECISION-INDEX.json').read_text())

@pytest.mark.parametrize('row',INTAKE['records'],ids=lambda r:r['decision_id'])
def test_actual_owner_accepted_exact_scope_without_runtime_grant(row):
    accepted=json.loads((BATCH/row['accepted_path']).read_text())
    source=next(r for r in INDEX['records'] if r['sha256']==row['proposal_sha256'])
    proposal_path=BATCH/'proposals'/Path(source['file']).name
    assert hashlib.sha256(proposal_path.read_bytes()).hexdigest()==row['proposal_sha256']
    proposal=json.loads(proposal_path.read_text())
    changed={k for k in proposal if proposal[k]!=accepted[k]}
    assert changed=={'status','accepted_by','conditions_satisfied','evidence_sha256'}
    assert accepted['status']=='ACCEPTED' and accepted['conditions_satisfied'] is True
    assert accepted['territories']==['US']
    assert accepted['components']==proposal['components']
    assert record_sha256(accepted)==row['accepted_record_sha256']
    assert INTAKE['owner_receipt_sha256'] in accepted['evidence_sha256']
    runtime,revoked=load_production_registry()
    assert accepted['decision_id'] not in runtime
    args=dict(edition_id=accepted['edition_id'],operator_id='reo-enterprise',country_trusted=True,required_components=accepted['components'],revoked_decision_ids=revoked,now=datetime.fromisoformat(INTAKE['actual_acceptance_recorded_at_utc']))
    trust={accepted['decision_id']:record_sha256(accepted)}
    allowed='audio_stream' if row['type']=='audio_stream' else 'reader_delivery'
    assert evaluate_accepted_record(accepted,country='US',use=allowed,accepted_records=trust,**args).passed
    assert not evaluate_accepted_record(accepted,country='US',use=allowed,accepted_records=runtime,**args).passed
    assert not evaluate_accepted_record(accepted,country='IN',use=allowed,accepted_records=trust,**args).passed
    assert not evaluate_accepted_record(accepted,country='US',use='audio_download',accepted_records=trust,**args).passed
    if allowed!='audio_stream':
        assert not evaluate_accepted_record(accepted,country='US',use='audio_stream',accepted_records=trust,**args).passed


def test_actual_receipt_and_material_edition_exception_are_preserved():
    raw=(BATCH/'OWNER-ACCEPTANCE.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==INTAKE['owner_receipt_sha256']
    receipt=json.loads(raw)
    assert receipt['owner_statement']=='Accept the exact consolidated US rights packet'
    assert receipt['question_item_id']=='call_fd63aceab7874889b48cc98744f6223e/0'
    assert hashlib.sha256((BATCH/'DECISION-INDEX.json').read_bytes()).hexdigest()=='b5045211f55905e1911483b48689073a73093da2f042ccdb6e129c64c1941cf3'
    assert len(INTAKE['records'])==51
    assert sum(r['type']=='audio_stream' for r in INTAKE['records'])==1
    assert len(INTAKE['prior_two_acceptances_reused'])==2
    assert all(r['new_decision_required'] is False for r in INTAKE['prior_two_acceptances_reused'])
    scope=json.loads((BATCH/'evidence/lokrahasya-scope.json').read_text())
    assert len(scope['chapters'])==15 and scope['total_notes_excluded']==8
    assert scope['excluded_appendix']['characters']==6657
    lok=next(r for r in INTAKE['records'] if r['slug']=='lokrahasya')
    assert lok['edition_id']=='lokrahasya-us-narrative-20261028'
    for key in ('runtime_registry_modified','existing_IN_records_modified','runtime_activation','publication_authorized','deployment_authorized','new_audio_authorized','paid_sessions_authorized'):
        assert INTAKE[key] is False
