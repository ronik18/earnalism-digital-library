"""Finite, persistent-slot shared limiter, preparation only.

No manifest/slot initialization, credentials or provider actions. Explicit
migration must first drain old writers/state and admit immutable generation and
policy. Missing state denies. Collisions conservatively deny; these bounds are
not latency, memory, capacity or deployment qualification.
"""
from dataclasses import dataclass
import hashlib
import json
import re
from types import MappingProxyType
import uuid

SCOPES = frozenset({'public', 'reading-pass', 'reader', 'auth', 'webhook',
                    'payments', 'analytics', 'upload', 'api'})

@dataclass(frozen=True)
class Policy:
    slots: int
    window: int
    limits: dict
    generation: str

    def __post_init__(self):
        if type(self.slots) is not int or not 1 <= self.slots <= 4096:
            raise ValueError('Explicit finite Redis limiter slot count required')
        if type(self.window) is not int or not 1 <= self.window <= 120:
            raise ValueError('Redis limiter window must be 1..120 seconds')
        if (type(self.limits) is not dict or set(self.limits) != SCOPES or
                any(type(n) is not int or not 1 <= n <= 30000 for n in self.limits.values())):
            raise ValueError('Finite declared Redis limiter scope limits required')
        if type(self.generation) is not str or not re.fullmatch('[0-9a-f]{32}', self.generation):
            raise ValueError('Explicit admitted Redis limiter generation required')
        object.__setattr__(self, 'limits', MappingProxyType(dict(self.limits)))

    @property
    def manifest(self):
        return json.dumps({'version': 3, 'slots': self.slots, 'generation': self.generation,
                           'window': self.window, 'limits': dict(self.limits)},
                          sort_keys=True, separators=(',', ':'))

    @property
    def slot_header(self):
        # Integrity binding, not an authorization signature. Admission/custody
        # remains external; SHA1 is also available in the Redis Lua sandbox.
        return '#' + hashlib.sha1(self.manifest.encode()).hexdigest()

    @property
    def maximum_keys(self):
        return len(SCOPES) * self.slots + 1

    @property
    def maximum_members(self):
        return self.slots * sum(2 * n + 2 for n in self.limits.values())

SCRIPT = """
if redis.call('GET', KEYS[4]) ~= ARGV[5] then return -1 end
local ok, policy = pcall(cjson.decode, ARGV[5])
local window, limit, slot = tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[8])
local scope, prefix = ARGV[7], ARGV[9]
local function hex(s, n)
    return type(s) == 'string' and #s == n and not string.find(s, '[^0-9a-f]')
end
local function identifier(s)
    return #s == 36 and string.sub(s,9,9) == '-' and string.sub(s,14,14) == '-'
        and string.sub(s,19,19) == '-' and string.sub(s,24,24) == '-'
        and hex(string.gsub(s, '-', ''), 32)
end
if not ok or type(policy) ~= 'table' or policy.version ~= 3
    or type(policy.limits) ~= 'table' or not hex(policy.generation,32)
    or not window or window < 1 or window > 120 or window ~= math.floor(window)
    or not limit or limit < 1 or limit > 30000 or limit ~= math.floor(limit)
    or policy.window ~= window or policy.limits[scope] ~= limit
    or type(policy.slots) ~= 'number' or policy.slots < 1 or policy.slots > 4096
    or policy.slots ~= math.floor(policy.slots)
    or not slot or slot < 0 or slot >= policy.slots or slot ~= math.floor(slot)
    or not hex(ARGV[4],64) or not identifier(ARGV[3])
    or slot ~= tonumber(string.sub(ARGV[4],1,8),16) % policy.slots
    or KEYS[1] ~= prefix .. ':rate-limit-v3-bounded:' .. scope .. ':' .. slot
    or KEYS[2] ~= prefix .. ':rate-limit-v2-server-time:' .. ARGV[4]
    or KEYS[3] ~= prefix .. ':rate-limit:' .. ARGV[4]
    or KEYS[4] ~= prefix .. ':rate-limit-v3-policy'
    or ARGV[6] ~= '#' .. redis.sha1hex(ARGV[5]) then return -1 end
-- A persistent, preinitialized slot is mandatory. Loss/expiry never resets it.
if redis.call('PTTL',KEYS[1]) ~= -1 or redis.call('PTTL',KEYS[4]) ~= -1 then return -1 end
for i = 2,3 do
    if redis.call('EXISTS',KEYS[i]) == 1 then
        local ttl = redis.call('PTTL',KEYS[i])
        if ttl <= 0 then return -1 end
        return math.max(1,math.ceil(ttl / 1000))
    end
end
local size = redis.call('ZCARD',KEYS[1])
if size < 2 or size > 2 * limit + 2 then return -1 end
local clock = redis.call('TIME')
local now = tonumber(clock[1]) + tonumber(clock[2]) / 1000000
local rows = redis.call('ZRANGE',KEYS[1],0,-1,'WITHSCORES')
local current, headers, owners, active, retained, last, replay = nil,0,0,0,0,0,false
for i = 1,#rows,2 do
    local member, score = rows[i],tonumber(rows[i+1])
    if not score or score ~= score or score == math.huge or score == -math.huge then return -1 end
    if member == ARGV[6] and score == -2 then
        headers = headers + 1
    elseif string.sub(member,1,1) == '@' and hex(string.sub(member,2),64) and score == -1 then
        current = member
        owners = owners + 1
    elseif identifier(member) and score > 0 and score <= now then
        if score > now - window then active = active + 1 end
        if score > now - 2 * window then retained = retained + 1 end
        if score > last then last = score end
        if member == ARGV[3] then replay = true end
    else return -1 end
end
if headers ~= 1 or owners ~= 1 then return -1 end
local owner = '@' .. ARGV[4]
-- Preserve dedup for the whole retained 2W history; retries do not mutate it.
if current == owner and replay then return 0 end
if current ~= owner and retained > 0 then
    return math.max(1,math.ceil(2 * window - (now-last)))
end
if active >= limit or retained >= 2 * limit then
    return math.max(1,math.ceil(2 * window - (now-last)))
end
-- Only logically expired history is removed. Lua errors do not roll back:
-- cleanup cannot relax an active limit; one final ZADD admits owner+request.
redis.call('ZREMRANGEBYSCORE',KEYS[1],0,now - 2 * window)
if current ~= owner then redis.call('ZREM',KEYS[1],current) end
redis.call('ZADD',KEYS[1],-1,owner,now,ARGV[3])
return 0
"""

def keys(prefix, policy, scope, digest):
    if (not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,128}', prefix) or
            scope not in SCOPES or not re.fullmatch(r'[0-9a-f]{64}', digest)):
        raise ValueError('Invalid fixed Redis limiter namespace/scope/identity')
    slot = int(digest[:8],16) % policy.slots
    return (f'{prefix}:rate-limit-v3-bounded:{scope}:{slot}',
            f'{prefix}:rate-limit-v2-server-time:{digest}',
            f'{prefix}:rate-limit:{digest}', f'{prefix}:rate-limit-v3-policy')

async def verify_policy(client, prefix, policy):
    marker = keys(prefix,policy,'api','0'*64)[3]
    value = await client.get(marker)
    if isinstance(value,bytes):value = value.decode('utf-8',errors='strict')
    if value != policy.manifest or await client.pttl(marker) != -1:
        raise RuntimeError('Bounded Redis limiter requires admitted matching policy')

async def retry_after(client, prefix, policy, scope, digest):
    names = keys(prefix,policy,scope,digest)
    slot = int(digest[:8],16) % policy.slots
    result = int(await client.eval(SCRIPT,4,*names,policy.window,policy.limits[scope],
                                   str(uuid.uuid4()),digest,policy.manifest,
                                   policy.slot_header,scope,slot,prefix))
    if result < 0:
        raise RuntimeError('Bounded Redis limiter state requires reconciliation')
    return result or None
