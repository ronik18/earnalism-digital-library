"""Private offline accounting only. No Mongo clients, custody authority or grants.

The caller must supply an independently enforced custody boundary. This ledger
only accounts declared disjoint client instances, and cannot discover or stop
unmanaged clients. No expiry releases capacity. Never auto-initializes a ledger.
"""
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

MAX = 2**60
COHORTS = frozenset({'active_web', 'old_draining_web', 'new_replacement_web',
                    'recovery_web', 'background_jobs', 'manual_operator_tools'})
STATES = frozenset({'RESERVED', 'ACTIVE', 'DRAIN_REQUESTED', 'PENDING', 'UNKNOWN', 'CLOSE_CONFIRMED'})
META_SQL = 'CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)'
ROW_SQL = 'CREATE TABLE reservations (intent TEXT PRIMARY KEY, resource TEXT NOT NULL UNIQUE, payload TEXT NOT NULL, checksum TEXT NOT NULL)'

class Held(Exception):
    """No operation or admission may proceed from this accounting failure."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def label(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}', value) is not None


def hex_digest(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


@dataclass(frozen=True)
class Binding:
    target: str
    source_sha256: str
    budget_sha256: str
    provider_revision: str
    generation: str

    def checked(self):
        if (not label(self.target) or not label(self.provider_revision)
                or not hex_digest(self.source_sha256) or not hex_digest(self.budget_sha256)
                or type(self.generation) is not str or not re.fullmatch(r'[0-9a-f]{32}', self.generation)):
            raise Held('BINDING_REQUIRED')
        return asdict(self)


@dataclass(frozen=True)
class CloseProof:
    binding_sha256: str
    reservation_sha256: str
    evidence_sha256: str
    physical_closed_or_dead: bool
    reconnect_fenced: bool


class DisabledCloseVerifier:
    def verify(self, *, binding, reservation):
        raise Held('TRUSTED_CLOSE_AND_RECONNECT_FENCE_UNAVAILABLE')


def capacities_checked(capacities):
    if (type(capacities) is not dict or not 1 <= len(capacities) <= 16
            or any(not label(k) or type(v) is not int or not 1 <= v <= MAX for k, v in capacities.items())):
        raise Held('EXPLICIT_PER_NODE_CAPACITY_REQUIRED')
    return dict(capacities)


def file_checked(path, *, exists):
    path = Path(path)
    if not path.is_absolute() or path.parent.is_symlink() or path.is_symlink():
        raise Held('PRIVATE_LEDGER_PATH_REQUIRED')
    parent = path.parent.stat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
        raise Held('PRIVATE_OWNED_PARENT_REQUIRED')
    if exists:
        info = path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
            raise Held('PRIVATE_OWNED_LEDGER_REQUIRED')
    return path


def initialize_offline(path, binding, capacities, *, offline=False):
    """Explicit new *offline* ledger. Not a production provisioning operation."""
    if offline is not True or type(binding) is not Binding:
        raise Held('EXPLICIT_OFFLINE_INITIALIZATION_REQUIRED')
    meta = {'schema': 1, 'binding': binding.checked(), 'capacities': capacities_checked(capacities)}
    try:
        path = file_checked(path, exists=False)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
        db = sqlite3.connect(path, timeout=1)
        try:
            db.execute('PRAGMA synchronous=FULL')
            with db:
                db.execute(META_SQL)
                db.execute(ROW_SQL)
                db.execute('INSERT INTO metadata VALUES (1, ?)', (canonical(meta),))
        finally:
            db.close()
        # Persist directory entry as well as SQLite's synchronous commit.
        fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    except Held:
        raise
    except (OSError, sqlite3.Error, ValueError, TypeError):
        # Never delete a pre-existing ledger or silently reinitialize a failure.
        raise Held('OFFLINE_INITIALIZATION_FAILED') from None
    return Ledger(path, binding, capacities)


class Ledger:
    def __init__(self, path, binding, capacities):
        if type(binding) is not Binding:
            raise Held('EXACT_BINDING_REQUIRED')
        self.path = Path(path)
        self.expected = {'schema': 1, 'binding': binding.checked(), 'capacities': capacities_checked(capacities)}
        self.binding_digest = digest(self.expected)
        with self._transaction(write=False): pass

    @contextmanager
    def _transaction(self, *, write):
        db = None
        try:
            path = file_checked(self.path, exists=True)
            db = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=1)
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            rows = self._validate(db)
            yield db, rows
            db.commit()
        except Held:
            if db is not None: db.rollback()
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, OverflowError):
            if db is not None: db.rollback()
            raise Held('LEDGER_UNAVAILABLE_OR_CORRUPT') from None
        finally:
            if db is not None: db.close()

    def _validate(self, db):
        schema = {name: sql for name, sql in db.execute("SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL")}
        if schema != {'metadata': META_SQL, 'reservations': ROW_SQL}:
            raise Held('LEDGER_SCHEMA_CHANGED')
        meta = db.execute('SELECT id,payload FROM metadata').fetchall()
        if meta != [(1, canonical(self.expected))]:
            raise Held('GENERATION_OR_IMMUTABLE_BINDING_CHANGED')
        rows = {}
        resources = set()
        for intent, resource, payload, checksum in db.execute('SELECT intent,resource,payload,checksum FROM reservations'):
            row = json.loads(payload)
            if (canonical(row) != payload or digest(row) != checksum or set(row) != {'request', 'state', 'close_proof'}
                    or row['state'] not in STATES):
                raise Held('RESERVATION_CORRUPT')
            request = row['request']
            self._request(request)
            if request['intent'] != intent or request['resource'] != resource or resource in resources:
                raise Held('RESERVATION_IDENTITY_CHANGED')
            resources.add(resource)
            if row['state'] == 'CLOSE_CONFIRMED':
                self._proof(row['close_proof'], request)
            elif row['close_proof'] is not None:
                raise Held('UNEXPECTED_CLOSE_PROOF')
            rows[intent] = row
        self._totals(rows)  # Over-quota or malformed retained data must fail closed.
        return rows

    def _request(self, request):
        if (type(request) is not dict or set(request) != {'intent', 'resource', 'cohort', 'units', 'binding_sha256'}
                or not label(request['intent']) or not label(request['resource'])
                or type(request['cohort']) is not str or request['cohort'] not in COHORTS or request['binding_sha256'] != self.binding_digest):
            raise Held('EXACT_RESERVATION_BINDING_REQUIRED')
        units = request['units']
        if (type(units) is not dict or set(units) != set(self.expected['capacities'])
                or any(type(n) is not int or not 1 <= n <= MAX for n in units.values())):
            raise Held('EXPLICIT_DISJOINT_PER_NODE_UNITS_REQUIRED')

    def _totals(self, rows):
        totals = {node: 0 for node in self.expected['capacities']}
        for row in rows.values():
            if row['state'] != 'CLOSE_CONFIRMED':
                for node, units in row['request']['units'].items(): totals[node] += units
        if any(totals[k] > v for k, v in self.expected['capacities'].items()):
            raise Held('PER_NODE_ACCOUNTING_QUOTA_EXCEEDED')
        return totals

    def reserve(self, intent, *, resource, cohort, units):
        request = {'intent': intent, 'resource': resource, 'cohort': cohort,
                   'units': units, 'binding_sha256': self.binding_digest}
        self._request(request)
        # Freeze caller-owned mutable maps before any transaction/verifier seam.
        request = json.loads(canonical(request))
        self._request(request)  # Validate the detached snapshot, not only caller-owned data.
        with self._transaction(write=True) as (db, rows):
            if intent in rows:
                if rows[intent]['request'] != request: raise Held('INTENT_REPLAY_BINDING_MISMATCH')
                return rows[intent]['state']
            if any(r['request']['resource'] == resource for r in rows.values()):
                raise Held('CLIENT_INSTANCE_ALREADY_ACCOUNTED')
            row = {'request': request, 'state': 'RESERVED', 'close_proof': None}
            self._totals({**rows, intent: row})
            db.execute('INSERT INTO reservations VALUES (?,?,?,?)', (intent, resource, canonical(row), digest(row)))
            return 'RESERVED'

    def mark(self, intent, state):
        if type(state) is not str or state not in {'ACTIVE', 'DRAIN_REQUESTED', 'PENDING', 'UNKNOWN'}:
            raise Held('NONRELEASING_STATE_REQUIRED')
        with self._transaction(write=True) as (db, rows):
            if intent not in rows or rows[intent]['state'] == 'CLOSE_CONFIRMED':
                raise Held('LIVE_RESERVATION_REQUIRED')
            row = rows[intent]
            row['state'] = state
            db.execute('UPDATE reservations SET payload=?,checksum=? WHERE intent=?', (canonical(row), digest(row), intent))

    def _proof(self, proof, request):
        if (type(proof) is not dict or set(proof) != set(CloseProof.__dataclass_fields__)
                or proof['binding_sha256'] != self.binding_digest
                or proof['reservation_sha256'] != digest(request)
                or not hex_digest(proof['evidence_sha256'])
                or proof['physical_closed_or_dead'] is not True or proof['reconnect_fenced'] is not True):
            raise Held('TRUSTED_PHYSICAL_CLOSE_AND_FENCE_REQUIRED')

    def release(self, intent, *, verifier=None):
        """Verifier is a future trusted no-I/O custodian snapshot, NOT user JSON.

        A supplied fake in offline tests does not establish custody. This method
        neither closes a client nor fences reconnects; verifier must prove both.
        """
        with self._transaction(write=True) as (db, rows):
            if intent not in rows: raise Held('RESERVATION_REQUIRED')
            row = rows[intent]
            if row['state'] == 'CLOSE_CONFIRMED': return 'CLOSE_CONFIRMED'
            try:
                proof = (verifier if verifier is not None else DisabledCloseVerifier()).verify(
                    binding=json.loads(canonical(self.expected)), reservation=json.loads(canonical(row['request'])))
            except Held: raise
            except Exception: raise Held('CLOSE_VERIFIER_FAILED') from None
            if type(proof) is not CloseProof: raise Held('TYPED_TRUSTED_CLOSE_PROOF_REQUIRED')
            proof = asdict(proof)
            self._proof(proof, row['request'])
            row.update(state='CLOSE_CONFIRMED', close_proof=proof)
            db.execute('UPDATE reservations SET payload=?,checksum=? WHERE intent=?', (canonical(row), digest(row), intent))
            return 'CLOSE_CONFIRMED'

    def snapshot(self):
        with self._transaction(write=False) as (_, rows):
            return {'accounting_only': True, 'custody_verified': False,
                    'binding_sha256': self.binding_digest, 'charged_per_node': self._totals(rows),
                    'states': {intent: row['state'] for intent, row in rows.items()}}
