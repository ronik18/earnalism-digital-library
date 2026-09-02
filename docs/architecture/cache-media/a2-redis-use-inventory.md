# A2 Redis use inventory

Result: PASS. Twelve Redis uses were classified before the v2 design. Six are `PICKLE_BACKED_APPLICATION_CACHE` and are migrated: public-cache, reader-content, reader-manifest, user-private, user-doc, and user-session. Generation counters, wallet values, maintenance locks/status, rate-limit sorted sets, and admin status calls remain Redis operational state and are unchanged.

Protected callers retain their existing authorization-before-cache ordering. No live Redis, production data, or user values were inspected.
