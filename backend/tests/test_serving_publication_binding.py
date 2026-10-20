import asyncio
import copy
import json
from types import SimpleNamespace

import pytest
from backend.serving_publication_binding import (BindingUnavailable, OPEN_WINDOW_UUID,
    OPEN_WINDOW_SLUG, OPEN_WINDOW_SERVING_ID, serving_binding_metadata)


def fixture(tmp_path):
    root = tmp_path / OPEN_WINDOW_SLUG
    root.mkdir()
    source = {'slug': OPEN_WINDOW_SLUG, 'source_hash': 'a'*64,
              'content_hash': 'b'*64, 'provenance_hash': 'c'*64}
    public = dict(source, id=OPEN_WINDOW_SERVING_ID,
                  chapters=[{'id': 'chapter-001', 'order': 1}])
    records = {'public_book.json': public, 'reader_manifest.json': {'slug': OPEN_WINDOW_SLUG},
        'source_evidence.json': source, 'approval_evidence.json': {'slug': OPEN_WINDOW_SLUG},
        'publication_manifest.json': {'slug': OPEN_WINDOW_SLUG, 'manifest_sha256': 'e'*64},
        'checksum_manifest.json': {'files': [{'file': 'chapters/chapter-001.json', 'sha256': 'd'*64}]}}
    for name, data in records.items():
        (root/name).write_text(json.dumps(data))
    return dict(requested_uuid=OPEN_WINDOW_UUID,
        uuid_rows=[{'id': OPEN_WINDOW_UUID, 'slug': OPEN_WINDOW_SLUG}],
        serving_doc=copy.deepcopy(public), root=root)


def test_metadata_projection_uses_selected_packet_without_chapter_body(tmp_path):
    args = fixture(tmp_path)
    result = serving_binding_metadata(**args)
    assert result['serving_id'] == OPEN_WINDOW_SERVING_ID
    assert result['serving_hashes']['source_hash'] == 'a'*64
    assert result['ordered_chapter_file_hashes'][0]['declared_file_sha256'] == 'd'*64
    assert '"content":' not in json.dumps(result)
    assert not (args['root']/'chapters').exists()  # no chapter-body access


@pytest.mark.parametrize('failure', ['wrong-uuid', 'duplicate-uuid', 'wrong-slug', 'wrong-serving-id',
                                    'source-mismatch', 'missing-file', 'missing-chapter-hash'])
def test_unknown_mismatched_or_incomplete_binding_fails_closed(tmp_path, failure):
    args = fixture(tmp_path)
    if failure == 'wrong-uuid': args['requested_uuid'] = 'other'
    elif failure == 'duplicate-uuid': args['uuid_rows'] *= 2
    elif failure == 'wrong-slug': args['uuid_rows'][0]['slug'] = 'other'
    elif failure == 'wrong-serving-id': args['serving_doc']['id'] = 'other'
    elif failure == 'source-mismatch': args['serving_doc']['source_hash'] = 'f'*64
    elif failure == 'missing-file': (args['root']/'source_evidence.json').unlink()
    else: (args['root']/'checksum_manifest.json').write_text('{"files": []}')
    with pytest.raises((BindingUnavailable, OSError)):
        serving_binding_metadata(**args)


def test_route_requires_real_admin_and_does_not_read_database_for_guest(monkeypatch):
    async def run():
        import os
        monkeypatch.setenv('MONGODB_URL', 'mongodb://127.0.0.1:29998/binding_test_unused')
        monkeypatch.setenv('REDIS_CACHE_ENABLED', 'false')
        monkeypatch.setenv('RATE_LIMIT_ENABLED', 'false')
        os.environ.setdefault('JWT_SECRET', 'binding-test-only')
        os.environ.setdefault('READING_PASS_TOKEN_SECRET', 'binding-test-only-not-production')
        from backend import server
        from httpx import ASGITransport, AsyncClient
        class NoDatabase:
            def __getattr__(self, name):
                raise AssertionError('Guest must not reach database')
        monkeypatch.setattr(server, 'db', NoDatabase())
        async with AsyncClient(transport=ASGITransport(app=server.app), base_url='http://test') as client:
            result = await client.get(f'/api/admin/books/{OPEN_WINDOW_UUID}/serving-binding')
        assert result.status_code in (401, 403)
        route = next(route for route in server.api.routes if route.path.endswith('/serving-binding'))
        assert any(dependency.call is server.require_admin for dependency in route.dependant.dependencies)
    asyncio.run(run())


@pytest.mark.parametrize('case', ['valid', 'missing-pointer', 'mismatched-pointer', 'missing-provider'])
def test_authenticated_route_metadata_and_fail_closed_states(tmp_path, monkeypatch, case):
    async def run():
        import os
        monkeypatch.setenv('MONGODB_URL', 'mongodb://127.0.0.1:29998/binding_test_unused')
        os.environ.setdefault('JWT_SECRET', 'binding-test-only')
        os.environ.setdefault('READING_PASS_TOKEN_SECRET', 'binding-test-only-not-production')
        from backend import server, catalog_truth
        from backend.utils import deployment_attestation
        from backend.tests.test_reading_pass_service_concurrency import Collection
        from httpx import ASGITransport, AsyncClient
        args = fixture(tmp_path)
        database = SimpleNamespace(books=Collection(args['uuid_rows']),
            reader_segment_manifests=Collection([] if case == 'missing-pointer' else [{
                'book_slug': OPEN_WINDOW_SLUG, 'status': 'active', 'version': 'manifest-fixture', 'segmentation_version': 'edition-fixture'}]),
            reader_segment_activation_state=Collection([{'book_slug': OPEN_WINDOW_SLUG,
                'active_segmentation_version': 'other' if case == 'mismatched-pointer' else 'edition-fixture', 'generation': 1}]))
        monkeypatch.setattr(server, 'db', database)
        monkeypatch.setattr(server, '_controlled_artifact_doc', lambda slug, include_content: args['serving_doc'])
        monkeypatch.setattr(catalog_truth, 'controlled_artifact_dir', lambda slug: args['root'])
        monkeypatch.setattr(deployment_attestation, 'deployment_attestation',
            lambda: {'status': 'UNAVAILABLE' if case == 'missing-provider' else 'AVAILABLE', 'git_sha': 'f'*40})
        async def admin(): return {'role': 'admin', 'id': 'synthetic-admin'}
        server.app.dependency_overrides[server.require_admin] = admin
        try:
            async with AsyncClient(transport=ASGITransport(app=server.app), base_url='http://test') as client:
                response = await client.get(f'/api/admin/books/{OPEN_WINDOW_UUID}/serving-binding')
            assert response.status_code == (200 if case == 'valid' else 409)
            if case == 'valid':
                data = response.json()
                assert data['requested_uuid'] == OPEN_WINDOW_UUID
                assert data['canonical_pointer']['activation_generation'] == 1
                assert data['deployment']['git_sha'] == 'f'*40
                assert response.headers['cache-control'] == 'private, no-store'
                assert 'does not independently attest' in data['canonical_pointer_source_join']
        finally:
            server.app.dependency_overrides.pop(server.require_admin, None)
    asyncio.run(run())
