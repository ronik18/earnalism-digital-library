"""Optional public JSON metadata cache with a durable Mongo read/fill fence.

No customer/financial records, provider configuration or implicit fence recovery.
Every cached read consults one primary linearizable control document. This costs
one Mongo request and intentionally favors correctness over a cache-only hit.
"""
import asyncio
import hashlib
import json
import math
import re
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pymongo import ReturnDocument, ReadPreference, timeout
from pymongo.errors import DuplicateKeyError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

CONTROL_ID = 'public-metadata-cache-v1'
MAX_TIME_MS = 2000
SLOTS = 64
MAX_BYTES = 131072
MAX_ITEMS = 8192
MAX_DEPTH = 16
MAX_STRING = 32768
_held = ContextVar('public_metadata_mutation_owner', default=None)
EPOCH = re.compile(r'^[0-9a-f]{32}$')
READ = """
if redis.call('HSTRLEN',KEYS[1],'epoch')>32 or redis.call('HSTRLEN',KEYS[1],'key')>64 or redis.call('HSTRLEN',KEYS[1],'body')>131072 then return false end
local row=redis.call('HMGET',KEYS[1],'epoch','key','body')
if row[1]~=ARGV[1] or row[2]~=ARGV[2] then return false end
return row[3]
"""
FILL = """
if #ARGV[3]>131072 then return 0 end
redis.call('HSET',KEYS[1],'epoch',ARGV[1],'key',ARGV[2],'body',ARGV[3])
redis.call('EXPIRE',KEYS[1],ARGV[4])
return 1
"""


def epoch():
    return uuid.uuid4().hex


def valid(row):
    return (isinstance(row, dict) and row.get('_id') == CONTROL_ID
            and row.get('state') in {'ACTIVE', 'FENCED'}
            and isinstance(row.get('epoch'), str) and EPOCH.fullmatch(row['epoch'])
            and (row['state'] == 'ACTIVE' and row.get('token') is None
                 or row['state'] == 'FENCED' and isinstance(row.get('token'), str)
                 and EPOCH.fullmatch(row['token'])))


class Control:
    def __init__(self, db):
        self.collection = db.public_metadata_cache_control.with_options(
            read_preference=ReadPreference.PRIMARY,
            read_concern=ReadConcern('linearizable'),
            write_concern=WriteConcern(w='majority', j=True, wtimeout=MAX_TIME_MS))

    async def _command(self, name, *args, _seconds=2.0, **kwargs):
        # Motor copies the CSOT context into its executor; wait_for also bounds
        # the async caller. A timed-out write remains an unknown fenced outcome.
        with timeout(_seconds):
            return await asyncio.wait_for(getattr(self.collection, name)(*args, **kwargs), _seconds)

    async def read(self, *, cache=False):
        row = await self._command('find_one', {'_id': CONTROL_ID},
                                  max_time_ms=200 if cache else MAX_TIME_MS,
                                  _seconds=.25 if cache else 2.0)
        if row is not None and not valid(row):
            raise ValueError('Malformed metadata cache control; reconcile, never reset')
        return row

    async def startup(self):
        row = await self.read()
        if row is None:
            try:
                await self._command('insert_one', dict(_id=CONTROL_ID, state='ACTIVE', epoch=epoch(), token=None))
            except DuplicateKeyError:
                pass
            row = await self.read()
        if row is None or row['state'] != 'ACTIVE':
            return False  # An ambiguous mutation fence never expires or auto-clears.
        new = await self._command('find_one_and_update', 
            {'_id': CONTROL_ID, 'state': 'ACTIVE', 'epoch': row['epoch'], 'token': None},
            {'$set': {'epoch': epoch()}}, return_document=ReturnDocument.AFTER, maxTimeMS=MAX_TIME_MS)
        # A concurrent startup/mutation may supersede us. Cache only after a new
        # authoritative ACTIVE read; never reuse a pre-startup Redis epoch.
        current = await self.read()
        return bool(current and current['state'] == 'ACTIVE' and (new is not None or current['epoch'] != row['epoch']))

    async def begin(self, enabled, operation="metadata"):
        if not re.fullmatch(r"[a-zA-Z0-9_]{1,80}", operation):
            raise ValueError("Invalid fixed metadata operation label")
        row = await self.read()
        if row is None:
            if not enabled:
                return None  # Defaults OFF: no control creation or writes.
            token = epoch()
            await self._command('insert_one', dict(_id=CONTROL_ID, state='FENCED', epoch=epoch(), token=token, operation=operation))
            return token
        if row['state'] != 'ACTIVE':
            raise ValueError('Metadata mutation fenced; authoritative reconciliation required')
        token = epoch()
        held = await self._command('find_one_and_update', 
            {'_id': CONTROL_ID, 'state': 'ACTIVE', 'epoch': row['epoch'], 'token': None},
            {'$set': {'state': 'FENCED', 'epoch': epoch(), 'token': token, 'operation': operation}},
            return_document=ReturnDocument.AFTER, maxTimeMS=MAX_TIME_MS)
        if not valid(held) or held['state'] != 'FENCED' or held['token'] != token:
            raise ValueError('Concurrent metadata mutation; handler not started')
        return token

    async def finish(self, token):
        if token is None:
            return
        row = await self._command('find_one_and_update', 
            {'_id': CONTROL_ID, 'state': 'FENCED', 'token': token},
            {'$set': {'state': 'ACTIVE', 'epoch': epoch(), 'token': None}},
            return_document=ReturnDocument.AFTER, maxTimeMS=MAX_TIME_MS)
        if not valid(row) or row['state'] != 'ACTIVE':
            raise ValueError('Metadata mutation outcome requires reconciliation')

    async def rotate(self):
        row = await self.read()
        if row is None:
            return
        if row['state'] != 'ACTIVE':
            raise ValueError('Outstanding metadata fence cannot be invalidated away')
        result = await self._command('find_one_and_update', 
            {'_id': CONTROL_ID, 'state': 'ACTIVE', 'epoch': row['epoch'], 'token': None},
            {'$set': {'epoch': epoch()}}, return_document=ReturnDocument.AFTER, maxTimeMS=MAX_TIME_MS)
        if result is None:
            raise ValueError('Concurrent metadata invalidation; reconcile')


def encode(value):
    """Bound structure BEFORE JSON serialization; no pickle or decompression."""
    budget = [MAX_ITEMS]
    byte_budget = [MAX_BYTES]
    def consume(n):
        byte_budget[0] -= n
        if byte_budget[0] < 0: raise ValueError("Encoded metadata budget")
    def check(v, depth):
        budget[0] -= 1
        consume(4)  # punctuation/type overhead, deliberately conservative
        if budget[0] < 0 or depth > MAX_DEPTH:
            raise ValueError('Metadata structure bound')
        if v is None or type(v) in {bool, int}:
            if type(v) is int and v.bit_length() > 64:
                raise ValueError('Integer bound')
            consume(24)
            return
        if type(v) is float:
            consume(32)
            if not math.isfinite(v):
                raise ValueError('Nonfinite metadata')
            return
        if type(v) is str:
            consume(2 + 12 * len(v))  # ensure_ascii non-BMP worst case, before serialization
            if len(v) > MAX_STRING or 'data:' in v.lower():
                raise ValueError('String/media bound')
            return
        if type(v) is list:
            if len(v) > MAX_ITEMS:
                raise ValueError('Item bound')
            for x in v: check(x, depth + 1)
            return
        if type(v) is dict:
            if len(v) > MAX_ITEMS:
                raise ValueError('Item bound')
            for k, x in v.items():
                if type(k) is not str: raise ValueError('JSON key required')
                check(k, depth + 1); check(x, depth + 1)
            return
        raise ValueError('Only JSON public metadata admitted')
    check(value, 0)
    body = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode()
    if len(body) > MAX_BYTES:
        raise ValueError('Metadata payload bound')
    return body


def decode(body):
    if not isinstance(body, (bytes, str)) or len(body) > MAX_BYTES:
        raise ValueError('Metadata payload bound')
    value = json.loads(body)
    encode(value)  # Same structural/type limits on cached input.
    return value


def slot(prefix, key):
    digest = hashlib.sha256(key.encode()).hexdigest()
    return f'{prefix}:public-metadata-v3:slot:{int(digest, 16) % SLOTS}', digest


def mutation_held(db):
    value = _held.get()
    return value is not None and value[0] is db and value[2] is asyncio.current_task()


@asynccontextmanager
async def mutation(db, enabled, operation="metadata"):
    """Reentrant only in the same task/db; exceptions retain durable fence."""
    if mutation_held(db):
        yield
        return
    control = Control(db)
    token = await control.begin(enabled, operation)
    reset = _held.set((db, token, asyncio.current_task(), operation))
    try:
        yield
    except BaseException:
        raise  # Neither timeout, cancellation nor an error proves no commit.
    else:
        await control.finish(token)
    finally:
        _held.reset(reset)


class AmbiguousResponse(Exception):
    def __init__(self, response):
        self.response = response


def reject_unsupported_writer(db):
    """Sync external writer: refuse active metadata-cache authority before APPLY.

    Activation must drain older/off-mode writers; this check is not a lock for a
    concurrently enabling operator. No control write or Redis TTL fallback.
    """
    collection = db.public_metadata_cache_control.with_options(
        read_preference=ReadPreference.PRIMARY, read_concern=ReadConcern('linearizable'))
    if collection.find_one({'_id': CONTROL_ID}, max_time_ms=MAX_TIME_MS) is not None:
        raise ValueError('External metadata writer not admitted; use fenced server path or reconcile cache admission')


def current_operation(db):
    value = _held.get()
    return {"token": value[1], "operation": value[3]} if mutation_held(db) else None


async def reject_unsupported_writer_async(db):
    if mutation_held(db):
        return
    if await Control(db).read() is not None:
        raise ValueError('External metadata writer not admitted; use fenced server path')
