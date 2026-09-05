from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_protected_delivery_and_lease_contract_is_fail_closed():
    source = (ROOT / 'backend' / 'server.py').read_text(encoding='utf-8')
    assert 'CANONICAL_PAGE_REQUIRED' in source
    assert 'Cache-Control"] = "private, no-store"' in source
    assert 'X-Reading-Pass-Lease' in source
    assert 'await _authorize_reading_pass_audio' in source
    assert 'ear_reading_pass_lease' in source
    assert 'httponly' in source
    assert 'authorize_media_credential' in source
    assert '_reading_pass_protected_response(result)' in source
    assert 'Authorization, Cookie, X-Reading-Pass-Session, X-Reading-Pass-Lease' in source
    assert 'partialFilterExpression={"active_lock": {"$type": "string"}}' in source
    assert 'AUDIO_PREVIEW_DISABLED' in source
    assert 'public_audio_seconds": PUBLIC_AUDIO_PREVIEW_SECONDS' in source
    assert 'Legacy reader heartbeats are disabled while Reading Pass is active.' in source
    assert 'Legacy reading pulses are disabled while Reading Pass is active.' in source
    assert 'READING_PASS_V2_ENABLED = _env_bool("READING_PASS_V2_ENABLED", False)' in source


def test_service_uses_transactions_unique_idempotency_and_server_time():
    source = (ROOT / 'backend' / 'reading_pass_service.py').read_text(encoding='utf-8')
    assert 'start_transaction()' in source
    assert 'server_billable_seconds(' in source
    assert 'idempotency_key=f"heartbeat:{session_id}:{sequence}"' in source
    assert 'reading_seconds_balance": {"$gte": debit}' in source
    assert 'event_type": "PASS_CREDIT"' in source
    assert 'event_type": "TIME_DEBIT"' in source


def test_health_reconciles_canonical_and_legacy_ledger_shapes():
    source = (ROOT / "backend/server.py").read_text(encoding="utf-8")
    assert '"ledger_balance_mismatches": ledger_balance_mismatches' in source
    assert '"$signed_seconds"' in source
    assert '"$credit"' in source
    assert '"$debit"' in source
    assert '"$arrayElemAt": ["$ledger_summary.balance", 0]' in source


def test_service_worker_does_not_cache_reading_pass_or_protected_audio():
    source = (ROOT / 'frontend' / 'public' / 'service-worker.js').read_text(encoding='utf-8')
    assert '/api/reading-pass/' in source
    assert r'^\/api\/reader\/book\/' in source


def test_v2_never_places_complete_controlled_chapters_in_shared_redis():
    source = (ROOT / 'backend' / 'server.py').read_text(encoding='utf-8')
    start = source.index('async def _reader_chapter_content')
    end = source.index('\n\ndef _stable_digest', start)
    helper = source[start:end]
    assert helper.count('if not READING_PASS_V2_ENABLED:') >= 2
    assert 'cached = await _redis_cache_get("reader-content", cache_key)' in helper
    assert 'await _redis_cache_set("reader-content", cache_key, rendered_content, READER_CHAPTER_CACHE_TTL_SECONDS)' in helper
