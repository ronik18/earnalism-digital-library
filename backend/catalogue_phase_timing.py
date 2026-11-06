"""Bounded passive catalogue diagnostics; no request or database payload logging."""
import json
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar

_current = ContextVar('catalogue_phase_timing', default=None)
_last = {}
_log = logging.getLogger('earnalism.catalogue_timing')
PHASES = frozenset(('cache_lookup', 'database', 'projection', 'cache_store'))

@contextmanager
def phase(name):
    state = _current.get()
    if state is None or name not in PHASES:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        state['phases'][name] = round((time.perf_counter() - start) * 1000, 3)

@contextmanager
def catalogue_request(source):
    start = time.perf_counter()
    state = {'phases': {}}
    token = _current.set(state)
    outcome = 'error_or_cancel'
    try:
        yield
        outcome = 'returned'
    finally:
        _current.reset(token)
        # Telemetry cannot replace a response, suppress cancellation or leak payloads.
        try:
            now = time.perf_counter()
            elapsed = (now - start) * 1000
            slow = elapsed >= 500
            key = bool(slow)
            if now - _last.get(key, float('-inf')) >= 60:
                _last[key] = now
                _log.info('catalogue_phase_v1 %s', json.dumps({
                    'source_base_sha256': source,
                    'route': 'GET /api/books',
                    'handler_ms': round(elapsed, 3),
                    'phases_ms': state['phases'],
                    'outcome': outcome,
                    'slow': slow,
                }, sort_keys=True, allow_nan=False))
        except Exception:
            pass
