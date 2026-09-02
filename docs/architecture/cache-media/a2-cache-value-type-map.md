# A2 cache value type map

Six migrated namespaces were characterized with synthetic local values. The largest required characterized representation is 3,006 bytes; the fixed 1,048,576-byte A2 decode ceiling is therefore finite and above every characterized value. It is a compatibility safety ceiling, not an A3 Redis storage policy.

The v2 codec accepts JSON primitives and explicit tagged datetime, date, UUID, ObjectId, and Decimal values. It rejects enum, tuple, set, binary, stream, generator, and arbitrary-object inputs; no unsupported type was observed in the migrated synthetic shapes.
