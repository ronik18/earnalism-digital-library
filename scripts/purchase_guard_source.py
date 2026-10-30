"""Source-only contract; reads explicit Git blobs, never providers or settings."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

SCHEMA = 'earnalism.purchase-guard-source.v1'
SUCCESSOR_SCHEMA = 'earnalism.purchase-guard-source.v2'
PATH = 'internal/legal/purchase_guard_source.json'
ANCHOR = '    if ENVIRONMENT == "production" and request.method == "POST" and request.url.path == COMMERCE_ORDER_PATH:\n        commerce = commerce_territory_verdict('
BRANCH = '\n    if ENVIRONMENT == "production" and request.method == "POST" and request.url.path == COMMERCE_ORDER_PATH:\n        return JSONResponse(status_code=503, content={"detail": {"code": "PURCHASE_INITIATION_CLOSED", "message": "New Reading Pass purchases are temporarily paused. Existing reading and listening access remains available."}}, headers={"Cache-Control": "no-store"})\n'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def guard_only_server(approved_base, base):
    if not re.fullmatch('[0-9a-f]{64}', approved_base) or sha(base) != approved_base:
        raise ValueError('Approved base bytes required')
    text = base.decode('utf-8')
    if text.count(ANCHOR) != 1 or 'PURCHASE_INITIATION_CLOSED' in text:
        raise ValueError('Exact unguarded anchor required')
    return text.replace(ANCHOR, BRANCH + ANCHOR, 1).encode('utf-8')

def exact_git_server(repo, ref):
    if not re.fullmatch('[0-9a-f]{40}', ref):
        raise ValueError('Exact Git source SHA required, not placeholder')
    return subprocess.check_output(['git','-c','remote.origin.promisor=false','show',ref+':backend/server.py'],cwd=repo,env={**__import__('os').environ,'GIT_NO_LAZY_FETCH':'1'},timeout=10)

def _preserved_purchase_handlers(historical, application):
    """A successor is not a new financial or territorial policy approval."""
    names = {'enforce_public_release_country', 'payments_create_topup',
             'payments_verify', 'payments_webhook', '_credit_wallet_for_intent',
             'admin_wallet_adjust', 'admin_wallet_refund_review',
             'admin_wallet_refund_approve', 'reading_pass_lease_renew'}
    def functions(source):
        return {n.name: ast.dump(n, include_attributes=False)
                for n in ast.parse(source).body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names}
    old, new = functions(historical), functions(application)
    if set(old) != names or old != new:
        raise ValueError('Successor changes protected purchase, financial or lease handlers')


def validate(repo, *, base_reader=exact_git_server):
    repo=Path(repo); m=json.loads((repo/PATH).read_text())
    expected={'schema','state','approved_merged_584_sha','approved_base_server_sha256','closed_server_sha256','owner_receipt_path','owner_receipt_sha256'}
    successor = m.get('schema') == SUCCESSOR_SCHEMA
    if successor:
        expected |= {'application_source_sha', 'application_server_sha256', 'application_closed_server_sha256'}
    if set(m)!=expected or m['schema'] not in {SCHEMA, SUCCESSOR_SCHEMA} or m['state'] not in {'OPEN','CLOSED'}:
        raise ValueError('Operational source contract malformed')
    if not re.fullmatch('[0-9a-f]{40}',m['approved_merged_584_sha']):raise ValueError('Unknown actual merged base')
    # Fixed reviewed receipt destination only: arbitrary private paths are forbidden.
    if m['owner_receipt_path']!='internal/legal/purchase_guard_owner_acceptance.json':raise ValueError('Unexpected approval path')
    receipt=(repo/m['owner_receipt_path']).read_bytes()
    if sha(receipt)!=m['owner_receipt_sha256']:raise ValueError('Owner receipt differs')
    approval=json.loads(receipt)
    scope=approval.get('scope',{})
    if approval.get('answer')!='Approve temporary purchase pause' or not all(scope.get(k) is True for k in ('guarded_recovery_bootstrap_on_existing_backend','temporary_new_pass_purchase_pause','reopen_after_verified_final_rollout','remain_closed_if_safe_recovery_not_complete','existing_reader_listener_preserved','verify_refund_webhook_code_preserved')):
        raise ValueError('Required actual owner scope missing')
    base=base_reader(repo,m['approved_merged_584_sha'])
    closed=guard_only_server(m['approved_base_server_sha256'],base)
    if sha(closed)!=m['closed_server_sha256']:raise ValueError('Closed server binding differs')
    if successor:
        application = base_reader(repo, m['application_source_sha'])
        if sha(application) != m['application_server_sha256']:
            raise ValueError('Application source binding differs')
        _preserved_purchase_handlers(base, application)
        closed = guard_only_server(m['application_server_sha256'], application)
        if sha(closed) != m['application_closed_server_sha256']:
            raise ValueError('Successor closed source binding differs')
        base = application
    actual=(repo/'backend/server.py').read_bytes()
    if actual != (closed if m['state']=='CLOSED' else base):raise ValueError('Whole server equality failed')
    return m,base,closed

def normal_guard_source(repo):
    """Signed-country tests inspect the exact bound underlying application."""
    _,base,_=validate(repo)
    return base.decode('utf-8')
