# Mutation and invalidation map

This maps observed current controls and identifies missing proof; it makes no invalidation change.

## Evidence

| Topic | Current finding | Evidence |
|---|---|---|
| book create/update/delete/publication/rights/cover/audio release | _public_cache_clear generation increment on observed catalog mutations | backend/server.py:5880-6262, 6903, 7600 |
| chapter create/update/delete/reorder | public generation invalidation present around admin mutations; reader-content generation exists | backend/server.py:6703-6766, 1963-1969 |
| session revocation/account permission | _invalidate_user_cache deletes user, wallet, session, transaction, and payment keys | backend/server.py:944-1122, 2115-2124, 10308-10327 |
| wallet/payment transaction | _invalidate_user_cache after observed writes | backend/server.py:10439-10674 |
| Reading Pass configuration | user invalidation on session changes; no dedicated entitlement cache discovered | backend/server.py:9419-9563 |
| PDF replacement | not applicable | media-lifecycle-map.json |
