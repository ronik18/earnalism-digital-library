# Redis current state

Observed current state only. The present decoder uses pickle; that is a high-severity future-remediation target, not a change made by this baseline.

## Evidence

| Topic | Current finding | Evidence |
|---|---|---|
| public catalog | TTL 300; pickle, zlib above 4096 bytes | backend/server.py:1508-1969 |
| reader access/chapter/manifest | TTL 900/3600/1800; pickle/zlib | backend/server.py:2127-2185, 2880-2971 |
| user, session, wallet | TTL 20/20/8; pickle/zlib for dicts; integer for wallet | backend/server.py:1999-2124 |
| payments and transactions | TTL 15/20; pickle/zlib | backend/server.py:7888-7892, 10728-10732 |
| rate limits | TTL 120; Redis native | backend/server.py:4896-4996 |
| startup lock | TTL 180; Redis native | backend/server.py:4109-4355 |
| Maximum value | No hard serialized-value limit found. | backend/server.py:1508-1572 |
| Stampede | No cross-replica singleflight for cache fills found. | backend/server.py:1537-1572 |
