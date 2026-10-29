"""Canary packaging must preserve the real public rights middleware boundary."""
import os
os.environ.setdefault('MONGODB_URL', 'mongodb://127.0.0.1:27017/earnalism_test')
os.environ.setdefault('JWT_SECRET', 'isolated-rights-regression-key')
import pytest
from starlette.requests import Request
from backend import server

@pytest.mark.parametrize('path', [
    '/api/books', '/api/books/the-selfish-giant',
    '/api/reader/book/the-selfish-giant/manifest',
])
def test_canary_metadata_keeps_accepted_india_catalogue_and_reader_access(path):
    request = Request({'type': 'http', 'method': 'GET', 'path': path,
                       'headers': [], 'scheme': 'https', 'server': ('test', 443)})
    verdict = server._release_rights_verdict(request, country='IN')
    assert verdict.passed, verdict.reasons

@pytest.mark.parametrize('country', ['', 'US', 'GB'])
def test_canary_does_not_expand_reader_territory_or_trust(country):
    request = Request({'type': 'http', 'method': 'GET',
                       'path': '/api/books/the-selfish-giant', 'headers': [],
                       'scheme': 'https', 'server': ('test', 443)})
    assert not server._release_rights_verdict(request, country=country).passed
