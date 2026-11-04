"""Read-only startup proof contract; no provider, policy or database writes.

The actual protected observer must run the unchanged startup guard against its
authorized current data. A compatibility label is not that qualification.
"""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _hash(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) and value != '0' * 64


def validate_startup_qualification(binding, approval, actual, now):
    """Validate an actual observer receipt, never manufacture its authority."""
    proof = actual.get('startup_data_qualification')
    fields = {'schema', 'scope', 'phase', 'source_sha', 'source_delivery_sha256',
              'config_sha256', 'policy_sha256', 'guard_source_sha256',
              'marker_identity_sha256', 'markers_sha256', 'marker_count',
              'context_sha256', 'method', 'snapshot_sha256', 'observed_at', 'guard_verified'}
    if not isinstance(proof, dict) or set(proof) != fields:
        raise ValueError('Actual startup data qualification receipt required')
    if (proof['schema'] != 'earnalism.startup-data-dispatch-qualification.v1'
            or proof['scope'] != 'ACTUAL_STARTUP_POLICY_AND_CANARIES'
            or proof['phase'] != 'INSTALLED_POLICY_BEFORE_BACKEND_DISPATCH'
            or proof['guard_verified'] is not True
            or type(proof['marker_count']) is not int or not 2 <= proof['marker_count'] <= 4):
        raise ValueError('Actual installed startup guard qualification required')
    if (proof['method'] not in {'DIRECT_AUTHORIZED_METADATA_READ', 'UNCHANGED_GUARD_OVER_AUTHORIZED_BOUNDED_SNAPSHOT'}
            or (proof['method'] == 'DIRECT_AUTHORIZED_METADATA_READ' and proof['snapshot_sha256'] is not None)
            or (proof['method'] == 'UNCHANGED_GUARD_OVER_AUTHORIZED_BOUNDED_SNAPSHOT' and not _hash(proof['snapshot_sha256']))):
        raise ValueError('Explicit direct-read or bounded-snapshot method required')
    for key in fields & {'source_delivery_sha256', 'config_sha256', 'policy_sha256',
                         'guard_source_sha256', 'marker_identity_sha256', 'markers_sha256', 'context_sha256'}:
        if not _hash(proof[key]):
            raise ValueError('Invalid startup qualification digest')
    expected = {'source_sha': binding.get('source_sha'),
                'source_delivery_sha256': binding.get('source_delivery_sha256'),
                'config_sha256': approval.get('config_sha256'),
                'policy_sha256': binding.get('startup_policy_sha256'),
                'guard_source_sha256': binding.get('startup_guard_source_sha256'),
                'marker_identity_sha256': binding.get('startup_marker_identity_sha256'),
                'context_sha256': binding.get('startup_context_sha256')}
    if any(proof[key] != value for key, value in expected.items()):
        raise ValueError('Startup policy/source/config/marker binding differs')
    if actual.get('startup_policy_sha256') != proof['policy_sha256']:
        raise ValueError('Actual installed provider policy observation required')
    if (not _hash(binding.get('startup_data_receipt_sha256'))
            or digest(proof) != binding['startup_data_receipt_sha256']):
        raise ValueError('Exact startup qualification receipt differs')
    try:
        observed = datetime.fromisoformat(proof['observed_at'])
        if now.tzinfo is None or observed.tzinfo is None or not timedelta(0) <= now - observed <= timedelta(minutes=15):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('Stale/future/naive startup qualification') from None
    return proof


async def collect_startup_qualification(client, db, raw_policy, *, source_sha,
                                        source_delivery_sha256, config_sha256,
                                        guard_source_sha256, context_sha256, clock,
                                        method='DIRECT_AUTHORIZED_METADATA_READ', snapshot_sha256=None,
                                        snapshot_observed_at=None):
    """Use the actual unchanged guard; existing authorized read context only.

    The caller must bind the source/config to genuine protected observations.
    Raw policy, principal, role and database values never enter this receipt.
    This function does not acquire access or authorize even read operations.
    """
    from backend import startup_data_guard as guard
    if (not isinstance(source_sha, str) or not re.fullmatch('[0-9a-f]{40}', source_sha)
            or not all(_hash(x) for x in (source_delivery_sha256, config_sha256, guard_source_sha256, context_sha256))):
        raise ValueError('Exact startup source/config bindings required')
    if (method not in {'DIRECT_AUTHORIZED_METADATA_READ', 'UNCHANGED_GUARD_OVER_AUTHORIZED_BOUNDED_SNAPSHOT'}
            or (method == 'DIRECT_AUTHORIZED_METADATA_READ' and snapshot_sha256 is not None)
            or (method == 'UNCHANGED_GUARD_OVER_AUTHORIZED_BOUNDED_SNAPSHOT' and not _hash(snapshot_sha256))):
        raise ValueError('Explicit authorized read method required')
    # Replay time cannot refresh captured evidence. The trusted collector must
    # carry the original capture timestamp and exact snapshot digest together.
    captured = None
    if method == 'UNCHANGED_GUARD_OVER_AUTHORIZED_BOUNDED_SNAPSHOT':
        try:
            captured = datetime.fromisoformat(snapshot_observed_at)
            now = clock()
            if (captured.tzinfo is None or now.tzinfo is None
                    or not timedelta(0) <= now - captured <= timedelta(minutes=15)):
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError('Fresh original snapshot capture time required') from None
    elif snapshot_observed_at is not None:
        raise ValueError('Direct-read receipt cannot carry a snapshot time')
    if hashlib.sha256(Path(guard.__file__).read_bytes()).hexdigest() != guard_source_sha256:
        raise ValueError('Actual startup guard implementation differs')
    policy = guard.parse_policy(raw_policy)
    await guard.verify_startup_data(client, db, raw_policy)
    verified = clock()
    observed = captured or verified
    if (verified.tzinfo is None or not timedelta(0) <= verified - observed <= timedelta(minutes=15)):
        raise ValueError('Aware observation time required')
    return {'schema': 'earnalism.startup-data-dispatch-qualification.v1',
            'scope': 'ACTUAL_STARTUP_POLICY_AND_CANARIES',
            'phase': 'INSTALLED_POLICY_BEFORE_BACKEND_DISPATCH',
            'source_sha': source_sha, 'source_delivery_sha256': source_delivery_sha256,
            'config_sha256': config_sha256,
            'policy_sha256': hashlib.sha256(raw_policy.encode()).hexdigest(),
            'guard_source_sha256': guard_source_sha256,
            'context_sha256': context_sha256, 'method': method, 'snapshot_sha256': snapshot_sha256,
            'marker_identity_sha256': digest([{'uuid': m['uuid'], 'slug': m['slug']} for m in policy['markers']]),
            'markers_sha256': digest(policy['markers']), 'marker_count': len(policy['markers']),
            'observed_at': observed.isoformat(), 'guard_verified': True}


def bind_retained_startup_projection(binding, captured, *, clock):
    """Bind an already captured, authorized phase receipt; never capture or refresh.

    The existing bounded capture operator owns read authority and durable usage.
    This pure callback has no database/provider channel. Repeated source checks
    reuse original capture time; stale evidence fails without another read.
    """
    if not isinstance(captured, dict) or set(captured) != {'startup_policy_sha256', 'startup_data_qualification'}:
        raise ValueError('Exact retained startup projection required')
    binding_bytes = json.dumps(binding, sort_keys=True, separators=(',', ':'))
    receipt_bytes = json.dumps(captured, sort_keys=True, separators=(',', ':'))
    expected = json.loads(binding_bytes)
    validate_startup_qualification(expected, {'config_sha256': expected.get('config_sha256')},
                                   json.loads(receipt_bytes), clock())

    def read(selected):
        if json.dumps(selected, sort_keys=True, separators=(',', ':')) != binding_bytes:
            raise ValueError('Retained startup phase binding differs')
        retained = json.loads(receipt_bytes)
        validate_startup_qualification(expected, {'config_sha256': expected.get('config_sha256')},
                                       retained, clock())
        return retained
    return read
