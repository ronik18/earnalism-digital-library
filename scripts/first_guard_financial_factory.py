"""Proposed post-claim diagnostic factory; no import-time SDK/profile activity."""
import hashlib
import inspect
import json
import os
import stat
from pathlib import Path

ADMISSION_PATH = '/private/tmp/pr656-native-successor-20261107/continue-after-incident.e2is7kjr/CAPTURE-ADMISSION.ACTUAL.json'
ADMISSION_SHA256 = '6744ddbee0abe7c85057015432bb62447135a64fafe3ac63d4a1e75d059db02b'
DATABASE_SHA256 = '181aecefb7a492f2446e4c81880b21cce5a539402e2315afefa72f2ebf51d9a2'
MAX_FILE_BYTES = 65536


def _need(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def _read_pinned(path, expected, private):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        _need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid(), 'PINNED_FILE_OWNER_OR_TYPE')
        if private:
            _need(stat.S_IMODE(info.st_mode) == 0o600, 'PRIVATE_FILE_MODE')
        raw = stream.read(MAX_FILE_BYTES + 1)
    _need(len(raw) <= MAX_FILE_BYTES and hashlib.sha256(raw).hexdigest() == expected, 'PINNED_FILE_HASH_OR_SIZE')
    return json.loads(raw)


def create_client(context):
    """Called once by the observer's owned factory Future after durable claim.

    Historical admission supplies immutable file references, never new authority.
    Unknown constructor state remains registered and holds the original claim.
    """
    context.assert_valid()
    runtime = context.runtime_contract
    helper_path = inspect.getsourcefile(type(context))
    _need(helper_path is not None and hashlib.sha256(Path(helper_path).read_bytes()).hexdigest()
          == runtime['source_pins']['claim_helper'], 'EXACT_CLAIM_HELPER_SOURCE_REQUIRED')
    context.require_for(runtime['source_pins']['observer'])
    source = Path(__file__).read_bytes()
    _need(hashlib.sha256(source).hexdigest() == runtime['source_pins']['client_factory'], 'EXACT_FACTORY_SOURCE_REQUIRED')
    context.begin_client_factory(runtime['source_pins']['client_factory'])
    actual = runtime['required_actual_before_any_claim']
    _need(actual['actual_client_factory_source_sha256'] == runtime['source_pins']['client_factory'], 'ACTUAL_FACTORY_BINDING_REQUIRED')
    _need(all(actual.get(k) for k in ('current_profile_provenance_sha256', 'current_runtime_dependency_closure_sha256',
          'protected_host_identity_sha256', 'expected_principal_sha256', 'expected_auth_database_sha256',
          'expected_client_seed_set_sha256', 'current_config_secret_version_context_sha256')), 'CURRENT_CLIENT_PROVENANCE_REQUIRED')
    loop = context.get_client_event_loop()
    _need(not loop.is_closed() and loop.is_running(), 'OWNED_MAIN_EVENT_LOOP_REQUIRED')
    context.assert_valid()
    admission = _read_pinned(ADMISSION_PATH, ADMISSION_SHA256, False)
    binding = _read_pinned(admission['database_binding']['path'], admission['database_binding']['sha256'], True)
    _need(set(binding) == {'database', 'database_name_sha256'} and type(binding['database']) is str,
          'ORIGINAL_DATABASE_BINDING_SCHEMA')
    _need(hashlib.sha256(binding['database'].encode('utf-8')).hexdigest() == binding['database_name_sha256']
          == runtime['database_name_sha256'] == DATABASE_SHA256, 'ORIGINAL_DATABASE_BINDING_REQUIRED')
    profile = _read_pinned(admission['mongo_profile']['path'], admission['mongo_profile']['sha256'], True)
    _need(set(profile) == {'uri'} and type(profile['uri']) is str
          and profile['uri'].startswith(('mongodb://', 'mongodb+srv://')), 'ORIGINAL_PROFILE_SCHEMA')
    context.assert_valid()
    from importlib.metadata import version
    _need({name: version(name) for name in ('motor', 'pymongo', 'dnspython')}
          == runtime['expected_driver_versions'] == {'motor': '3.3.1', 'pymongo': '4.5.0', 'dnspython': '2.8.0'},
          'EXACT_DRIVER_VERSIONS_REQUIRED')
    from motor.motor_asyncio import AsyncIOMotorClient
    context.assert_valid()
    # Register uncertainty BEFORE construction, including possible SRV DNS work.
    # On any exception this sentinel remains live: no false cleanup completion.
    construction_unknown = object()
    context.retain_client(construction_unknown)
    try:
        client = AsyncIOMotorClient(profile['uri'], io_loop=loop, connect=False,
            maxPoolSize=1, minPoolSize=0, maxConnecting=1,
            serverSelectionTimeoutMS=1000, connectTimeoutMS=1000, socketTimeoutMS=1000,
            waitQueueTimeoutMS=1000, retryReads=False, retryWrites=False,
            tz_aware=True, document_class=dict)
        context.retain_client(client)
        database = client[binding['database']]
        context.client_closed(construction_unknown)
    except BaseException:
        # Suppress constructor diagnostics that could contain private URI data.
        # The unknown sentinel and any constructed client stay owned, no retry.
        raise RuntimeError('CLIENT_CONSTRUCTION_OR_SELECTION_UNKNOWN_HELD') from None
    # Return late results to the original owned Future for observer cleanup.
    return client, database
