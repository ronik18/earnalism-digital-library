"""Exercise the real signup handler with in-memory failures; no database connection."""
import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
os.environ.setdefault('MONGODB_URL', 'mongodb://localhost:27017/earnalism_test')
os.environ.setdefault('JWT_SECRET', 'dummy-test-secret')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


@pytest.mark.parametrize('pattern,known_email', [
    ({'email': 1}, True),
    ({'email': True}, False),
    ({'email': -1}, False),
    ({'email': '1'}, False),
    ({'id': 1}, False),
    ({'email': 1, 'role': 1}, False),
    (None, False),
])
def test_duplicate_insert_only_translates_known_email_index(monkeypatch, pattern, known_email):
    error = server.DuplicateKeyError('dummy unique index race', details={'keyPattern': pattern})
    users = SimpleNamespace(find_one=AsyncMock(return_value=None), insert_one=AsyncMock(side_effect=error))
    session = AsyncMock()
    monkeypatch.setattr(server, 'db', SimpleNamespace(users=users))
    monkeypatch.setattr(server, 'hash_password', lambda _: 'dummy-hash')
    monkeypatch.setattr(server, '_create_user_session', session)
    payload = SimpleNamespace(name='Dummy Reader', email='DUMMY@example.invalid', password='dummy-password')
    with pytest.raises(server.HTTPException if known_email else server.DuplicateKeyError) as caught:
        asyncio.run(server.user_signup(payload, None, None))
    if known_email:
        assert caught.value.status_code == 400
        assert caught.value.detail == 'An account with this email already exists'
    else:
        assert caught.value is error
    session.assert_not_awaited()
    users.insert_one.assert_awaited_once()
