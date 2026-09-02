# A1.2 media extraction map

Only low-level, dependency-free media transport primitives move in A1.2. `backend/server.py` retains all FastAPI routes, authorization, controlled-publication truth, database access, rollout decisions, B2 configuration assembly, the mutable B2 client registry, and route-level streaming orchestration.

The detailed symbol-by-symbol decisions are in `a1-media-extraction-map.json`. The deliberately retained B2 registry is an A5 boundary: moving it now would weaken the existing server-level monkeypatch contract without improving customer behavior.
