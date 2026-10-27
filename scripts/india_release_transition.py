"""Validate a future transition plan. No provider execution capability is present."""
import argparse
import json
from pathlib import Path


# These are evidence requirements, not new owner approval ceremonies. Reuse the
# existing protected environment/config/rollback gate at future execution time.
STAGES = (
    ('source', (), ('exact_reviewed_source', 'controller_ci')),
    ('provider_preflight', ('source',), ('current_provider_identity', 'auto_deploy_off',
                                      'secret_compatibility', 'rollback_qualified')),
    ('stage_frontend', ('provider_preflight',), ('protected_release_approval',)),
    ('qualify_frontend', ('stage_frontend',), ('production_candidate_no_domains',
                                           'candidate_health_book', 'guest_manifest_401',
                                           'old_backend_signed_purchase_compatibility')),
    ('promote_frontend', ('qualify_frontend',), ('exact_tested_candidate', 'both_aliases')),
    ('release_backend', ('promote_frontend',), ('current_frontend_signs_purchase',
                                             'fresh_startup_database', 'exact_backend_source')),
    ('qualify_combined', ('release_backend',), ('actual_serving_source', 'india_admission',
                                             'non_india_denial', 'verify_refund_webhook_preserved',
                                             'reader_entitlements_preserved', 'no_free_audio')),
)


def validate_plan(plan):
    if plan.get('schema') != 'earnalism-india-transition-preparation.v1':
        raise ValueError('Unknown transition schema')
    if plan.get('execution_enabled') is not False:
        raise ValueError('Execution is outside preparation scope')
    if plan.get('territories') != ['IN'] or plan.get('paid_sessions') is not False:
        raise ValueError('Scope expansion rejected')
    if plan.get('order') != [name for name, _, _ in STAGES]:
        raise ValueError('Backend-first or incomplete sequence rejected')
    rollback = plan.get('rollback', {})
    if rollback.get('restore_unguarded_backend') is not False:
        raise ValueError('Unguarded backend rollback rejected')
    if rollback.get('restore_unsigned_frontend_against_guarded_backend') is not False:
        raise ValueError('Incompatible frontend rollback rejected')
    if rollback.get('preserve_verification_refund_webhook') is not True:
        raise ValueError('Settlement lifecycle must remain available')
    if plan.get('unknown_write_outcome') != 'STOP_AND_READ_ONLY_RECONCILE':
        raise ValueError('Unknown writes may not be retried')
    if plan.get('automatic_retry') is not False:
        raise ValueError('Automatic provider retries rejected')
    return plan


def next_stage(plan, completed, evidence):
    """Pure dry-run: return a proposed stage and missing evidence; execute nothing.

    Evidence input is a readiness simulation only. It cannot establish actual
    provider authenticity, create approval, or override current no-deploy scope.
    """
    validate_plan(plan)
    names = [name for name, _, _ in STAGES]
    if completed != names[:len(completed)]:
        raise ValueError('Out-of-order or unknown completion state')
    if len(completed) > len(names):
        raise ValueError('Invalid completion count')
    if evidence.get('unknown_write_outcome'):
        return {'proposed_stage': None, 'hold': ['read_only_reconciliation'], 'execution_enabled': False}
    if len(completed) == len(names):
        return {'proposed_stage': None, 'hold': [], 'execution_enabled': False,
                'status': 'SIMULATION_COMPLETE_NOT_PRODUCTION_ACCEPTANCE'}
    name, parents, required = STAGES[len(completed)]
    assert all(p in completed for p in parents)
    missing = [r for r in required if evidence.get(r) is not True]
    return {'proposed_stage': name, 'hold': missing, 'execution_enabled': False,
            'status': 'PREPARATION_ONLY'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    plan = validate_plan(json.loads(args.plan.read_text()))
    print(json.dumps(next_stage(plan, [], {}), indent=2))


if __name__ == '__main__':
    main()
