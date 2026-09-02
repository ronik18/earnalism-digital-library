# A1.1 cache extraction map

The JSON map records every moved cache primitive, its current callers and side effects, target module, compatibility facade, and characterization coverage. The only production authority before extraction is `backend/server.py`; the extracted modules do not import it.

The extraction is limited to Redis construction/lifecycle, keys, current pickle/zlib codec, policy/jitter, and current counters. Public/local cache and user-cache route helpers retain their server-level compatibility facades. No audio streaming primitive is in scope.
